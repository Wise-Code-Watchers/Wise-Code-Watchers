"""
LLM Scoring-Based Issue Filter

Scores all issues using LLM on relevance and severity dimensions,
then filters based on configurable thresholds.

This provides transparency (scores + reasoning) and control (thresholds).
"""

import logging
from typing import Optional
from dataclasses import dataclass

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from output.models import Bug, FeaturePoint

logger = logging.getLogger(__name__)


class IssueScore(BaseModel):
    """Score for a single issue."""
    issue_id: str = Field(description="ID of the issue being scored")
    relevance_score: float = Field(
        ge=0.0, le=1.0,
        description="How related is this to PR changes (0.0-1.0)"
    )
    severity_score: float = Field(
        ge=0.0, le=1.0,
        description="How serious is this issue (0.0-1.0)"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in this assessment (0.0-1.0)"
    )
    reasoning: str = Field(description="Brief explanation for the scores")


class IssueScoringResult(BaseModel):
    """Batch scoring result."""
    scores: list[IssueScore]


@dataclass
class ScoringConfig:
    """Configuration for issue scoring filter."""
    relevance_threshold: float = 0.5
    severity_threshold: float = 0.4
    max_issues_per_batch: int = 25
    include_low_confidence: bool = False
    min_confidence: float = 0.3


SCORING_SYSTEM_PROMPT = """You are evaluating code review issues for relevance and severity.

Your task is to score each issue on THREE dimensions (0.0 to 1.0):

1. **relevance_score**: How related is this issue to the PR changes?
   - 1.0 = Directly in changed code, clearly introduced by this PR
   - 0.7 = In a changed file, likely affected by the changes
   - 0.4 = In related code, might be relevant
   - 0.1 = In unchanged code, unrelated to PR

2. **severity_score**: How serious is this issue?
   - 1.0 = Critical - security vulnerability, crash, data loss
   - 0.8 = High - significant bug, logic error, resource leak
   - 0.5 = Medium - should fix but not urgent
   - 0.2 = Low - minor improvement, style issue

3. **confidence_score**: How confident are you in this assessment?
   - 1.0 = Very confident, clear evidence in the diff
   - 0.5 = Moderately confident
   - 0.2 = Uncertain, need more context

IMPORTANT GUIDELINES:
- Issues in test files with test fixtures (test passwords, mock secrets) should get LOW relevance (0.1-0.2)
- Issues in unchanged files should get LOW relevance (0.1-0.3)
- Security vulnerabilities in production code should get HIGH severity (0.8-1.0)
- Logic errors and resource leaks should get HIGH severity (0.7-0.9)
- Style issues should get LOW severity (0.1-0.3)

Provide a brief reasoning for each score."""

SCORING_USER_PROMPT = """Evaluate these issues for a code review.

## PR Context

**Changed Files:**
{changed_files}

**Feature Points:**
{feature_points}

**Diff Summary:**
{diff_context}

## Issues to Score

{issues_json}

Score each issue with relevance_score, severity_score, confidence_score, and reasoning."""


class IssueScoringFilter:
    """
    LLM-powered scoring filter for all issue types.
    
    Scores issues on relevance and severity, then filters by thresholds.
    Works for security, logic, memory, and syntax issues.
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        config: Optional[ScoringConfig] = None,
    ):
        self.llm = llm
        self.config = config or ScoringConfig()
    
    async def score_and_filter(
        self,
        issues: list[Bug],
        diff_context: str,
        feature_points: list[FeaturePoint],
        changed_files: list[str] = None,
    ) -> list[Bug]:
        """
        Score all issues and filter by thresholds.
        
        Args:
            issues: List of Bug objects from all agents
            diff_context: Summary of PR diff
            feature_points: Feature points identified in PR
            changed_files: List of files changed in PR
            
        Returns:
            Filtered list of bugs that pass threshold criteria
        """
        if not issues:
            return []
        
        if not self.llm:
            logger.warning("No LLM provided, returning all issues unfiltered")
            return issues
        
        # Score issues in batches
        all_scores = []
        for i in range(0, len(issues), self.config.max_issues_per_batch):
            batch = issues[i:i + self.config.max_issues_per_batch]
            batch_scores = await self._score_batch(
                batch, diff_context, feature_points, changed_files
            )
            all_scores.extend(batch_scores)
        
        # Build score map
        score_map = {s.issue_id: s for s in all_scores}
        
        # Filter by thresholds
        filtered = []
        kept_count = 0
        dropped_count = 0
        
        for issue in issues:
            score = score_map.get(issue.id)
            
            if score is None:
                # No score available, keep if high severity
                if issue.severity.value in ("critical", "high"):
                    filtered.append(issue)
                    kept_count += 1
                else:
                    dropped_count += 1
                continue
            
            # Check thresholds
            passes_relevance = score.relevance_score >= self.config.relevance_threshold
            passes_severity = score.severity_score >= self.config.severity_threshold
            passes_confidence = (
                self.config.include_low_confidence or 
                score.confidence_score >= self.config.min_confidence
            )
            
            if passes_relevance and passes_severity and passes_confidence:
                # Attach scores to issue for transparency
                issue.relevance_score = score.relevance_score
                issue.severity_score = score.severity_score
                issue.score_reasoning = score.reasoning
                filtered.append(issue)
                kept_count += 1
                logger.debug(
                    f"KEEP {issue.id}: relevance={score.relevance_score:.2f}, "
                    f"severity={score.severity_score:.2f} - {score.reasoning[:50]}"
                )
            else:
                dropped_count += 1
                logger.debug(
                    f"DROP {issue.id}: relevance={score.relevance_score:.2f}, "
                    f"severity={score.severity_score:.2f} - {score.reasoning[:50]}"
                )
        
        logger.info(
            f"Scoring filter: kept {kept_count}/{len(issues)} issues "
            f"(thresholds: relevance>={self.config.relevance_threshold}, "
            f"severity>={self.config.severity_threshold})"
        )
        
        return filtered
    
    async def _score_batch(
        self,
        issues: list[Bug],
        diff_context: str,
        feature_points: list[FeaturePoint],
        changed_files: list[str] = None,
    ) -> list[IssueScore]:
        """Score a batch of issues using LLM."""
        try:
            # Format issues for LLM
            issues_json = self._format_issues(issues)
            fp_text = self._format_feature_points(feature_points)
            files_text = "\n".join(changed_files[:20]) if changed_files else "Not provided"
            
            # Truncate diff if too long
            max_diff = 6000
            if len(diff_context) > max_diff:
                diff_context = diff_context[:max_diff] + "\n... (truncated)"
            
            # Get structured output
            structured_llm = self.llm.with_structured_output(IssueScoringResult)
            
            result = await structured_llm.ainvoke([
                SystemMessage(content=SCORING_SYSTEM_PROMPT),
                HumanMessage(content=SCORING_USER_PROMPT.format(
                    changed_files=files_text,
                    feature_points=fp_text,
                    diff_context=diff_context,
                    issues_json=issues_json,
                )),
            ])
            
            return result.scores
            
        except Exception as e:
            logger.warning(f"Batch scoring failed: {e}")
            # Return neutral scores on failure
            return [
                IssueScore(
                    issue_id=issue.id,
                    relevance_score=0.5,
                    severity_score=0.5,
                    confidence_score=0.3,
                    reasoning=f"Scoring failed: {str(e)[:50]}"
                )
                for issue in issues
            ]
    
    def _format_issues(self, issues: list[Bug]) -> str:
        """Format issues for LLM consumption."""
        lines = []
        for issue in issues:
            lines.append(f"""
Issue ID: {issue.id}
Type: {issue.type.value}
Severity: {issue.severity.value}
File: {issue.file}
Line: {issue.line}
Title: {issue.title}
Description: {issue.description[:200] if issue.description else 'N/A'}
""".strip())
        return "\n\n---\n\n".join(lines)
    
    def _format_feature_points(self, feature_points: list[FeaturePoint]) -> str:
        """Format feature points for context."""
        if not feature_points:
            return "No feature points identified"
        
        lines = []
        for fp in feature_points:
            lines.append(f"- [{fp.id}] {fp.name}: {fp.description}")
            if fp.files:
                lines.append(f"  Files: {', '.join(fp.files[:5])}")
        return "\n".join(lines)


def create_scoring_filter(
    llm: BaseChatModel,
    relevance_threshold: float = 0.5,
    severity_threshold: float = 0.4,
) -> IssueScoringFilter:
    """
    Create a scoring filter with custom thresholds.
    
    Args:
        llm: Language model for scoring
        relevance_threshold: Minimum relevance score (0.0-1.0)
        severity_threshold: Minimum severity score (0.0-1.0)
        
    Returns:
        Configured IssueScoringFilter
    """
    config = ScoringConfig(
        relevance_threshold=relevance_threshold,
        severity_threshold=severity_threshold,
    )
    return IssueScoringFilter(llm=llm, config=config)
