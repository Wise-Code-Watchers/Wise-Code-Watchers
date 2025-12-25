"""
Issue Filter - Two-Stage Filtering for Core Issues

Stage 1: Static pre-filter using language-specific rules
Stage 2: LLM relevance filter for context-aware filtering

Reduces noise by 80%+ while keeping actionable issues.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from agents.syntax.core_rules import (
    is_core_rule,
    is_ignored_rule,
    get_rule_category,
    should_keep_issue,
    classify_unknown_issue,
)
from agents.syntax.schemas import CodeIssue

logger = logging.getLogger(__name__)


class IssueRelevance(BaseModel):
    """LLM-evaluated relevance of an issue to the PR."""
    
    issue_id: str = Field(description="Identifier for the issue")
    is_in_changed_code: bool = Field(
        description="Is this issue in code that was added or modified?"
    )
    is_introduced_by_pr: bool = Field(
        description="Was this issue introduced by this PR (not pre-existing)?"
    )
    is_blocking: bool = Field(
        description="Would this issue prevent the code from working correctly?"
    )
    relevance_score: float = Field(
        ge=0.0, le=1.0,
        description="Overall relevance score from 0.0 to 1.0"
    )
    reason: str = Field(description="Brief explanation of the relevance assessment")


class IssueRelevanceBatch(BaseModel):
    """Batch of issue relevance evaluations."""
    evaluations: list[IssueRelevance]


@dataclass
class FilterConfig:
    """Configuration for issue filtering."""
    include_style: bool = False
    relevance_threshold: float = 0.6
    max_issues_for_llm: int = 30
    skip_llm_filter: bool = False


class IssueFilter:
    """
    Two-stage issue filter for surfacing only core issues.
    
    Stage 1: Static rule-based filtering (fast, deterministic)
    Stage 2: LLM relevance scoring (smart, context-aware)
    """
    
    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        config: Optional[FilterConfig] = None,
    ):
        self.llm = llm
        self.config = config or FilterConfig()
    
    def static_filter(
        self,
        issues: list[CodeIssue],
        include_style: bool = False,
    ) -> list[CodeIssue]:
        """
        Stage 1: Filter issues using blocklist-first static rules.
        
        Uses blocklist-first approach to avoid missing important issues:
        1. Explicitly ignored rules → drop
        2. Known core rules → keep with category
        3. Error severity → always keep
        4. Unknown rules → keep (let LLM decide)
        
        Args:
            issues: List of CodeIssue objects
            include_style: If True, also keep style issues (ignored rules still dropped)
            
        Returns:
            Filtered list of issues
        """
        filtered = []
        stats = {"kept": 0, "dropped": 0, "by_category": {}}
        
        for issue in issues:
            language = issue.language.lower() if issue.language else "unknown"
            rule = issue.rule
            severity = issue.severity if hasattr(issue, 'severity') else "warning"
            
            # Use blocklist-first logic
            keep, category = should_keep_issue(rule, language, severity)
            
            if not keep:
                # Only explicitly ignored rules are dropped
                stats["dropped"] += 1
                continue
            
            # Update issue category
            if category == "unknown":
                # Try to classify based on message heuristics
                message = issue.message if hasattr(issue, 'message') else ""
                guessed_category = classify_unknown_issue(rule, language, message)
                if guessed_category != "unknown":
                    category = guessed_category
            
            issue.category = category
            
            # Keep all non-style issues, or style if include_style=True
            if category != "style" or include_style:
                filtered.append(issue)
                stats["kept"] += 1
                stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
            else:
                stats["dropped"] += 1
        
        logger.info(
            f"Static filter (blocklist-first): kept {stats['kept']}/{len(issues)} issues "
            f"(categories: {stats['by_category']})"
        )
        
        return filtered
    
    async def llm_relevance_filter(
        self,
        issues: list[CodeIssue],
        diff_context: str,
        pr_description: str = "",
    ) -> list[CodeIssue]:
        """
        Stage 2: Filter issues using LLM relevance scoring.
        
        Args:
            issues: Pre-filtered list of issues
            diff_context: The PR diff for context
            pr_description: Optional PR description
            
        Returns:
            Issues with relevance_score >= threshold
        """
        if not self.llm or self.config.skip_llm_filter:
            logger.info("LLM filter skipped (no LLM or disabled)")
            return issues
        
        if not issues:
            return issues
        
        # Limit issues sent to LLM
        issues_to_evaluate = issues[:self.config.max_issues_for_llm]
        
        try:
            # Format issues for LLM
            issues_text = self._format_issues_for_llm(issues_to_evaluate)
            
            # Truncate diff if too long
            max_diff_chars = 8000
            if len(diff_context) > max_diff_chars:
                diff_context = diff_context[:max_diff_chars] + "\n... (truncated)"
            
            system_prompt = """You are a code review expert evaluating issue relevance.
For each issue, determine:
1. Is it in code that was added/modified in this PR?
2. Was it introduced by this PR (not pre-existing)?
3. Would it block the code from working correctly?
4. Overall relevance score (0.0-1.0)

Focus on issues that:
- Are in the changed lines
- Were introduced by the PR author
- Would cause runtime errors, security vulnerabilities, or resource leaks

Deprioritize issues that:
- Exist in unchanged code
- Are stylistic preferences
- Would not affect functionality"""

            user_prompt = f"""Evaluate the relevance of these issues to the PR.

PR Description: {pr_description or "Not provided"}

Diff:
```
{diff_context}
```

Issues to evaluate:
{issues_text}

For each issue, provide: issue_id, is_in_changed_code, is_introduced_by_pr, is_blocking, relevance_score, reason."""

            structured_llm = self.llm.with_structured_output(IssueRelevanceBatch)
            
            result = await structured_llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ])
            
            # Build relevance map
            relevance_map = {e.issue_id: e for e in result.evaluations}
            
            # Filter by threshold
            filtered = []
            for i, issue in enumerate(issues_to_evaluate):
                issue_id = f"issue_{i}"
                relevance = relevance_map.get(issue_id)
                
                if relevance and relevance.relevance_score >= self.config.relevance_threshold:
                    filtered.append(issue)
                    logger.debug(
                        f"Kept issue {issue_id}: score={relevance.relevance_score:.2f}, "
                        f"reason={relevance.reason}"
                    )
                elif relevance:
                    logger.debug(
                        f"Dropped issue {issue_id}: score={relevance.relevance_score:.2f}, "
                        f"reason={relevance.reason}"
                    )
            
            # Add back issues that weren't evaluated (beyond max_issues_for_llm)
            if len(issues) > self.config.max_issues_for_llm:
                remaining = issues[self.config.max_issues_for_llm:]
                # Keep only high-severity remaining issues
                for issue in remaining:
                    if issue.severity == "error" or issue.category in ("syntax", "security"):
                        filtered.append(issue)
            
            logger.info(
                f"LLM filter: kept {len(filtered)}/{len(issues)} issues "
                f"(threshold={self.config.relevance_threshold})"
            )
            
            return filtered
            
        except Exception as e:
            logger.warning(f"LLM relevance filter failed: {e}, returning all issues")
            return issues
    
    def _format_issues_for_llm(self, issues: list[CodeIssue]) -> str:
        """Format issues for LLM consumption."""
        lines = []
        for i, issue in enumerate(issues):
            lines.append(
                f"issue_{i}: [{issue.category.upper()}] {issue.file}:{issue.line} "
                f"[{issue.rule}] {issue.message[:150]}"
            )
        return "\n".join(lines)
    
    async def filter(
        self,
        issues: list[CodeIssue],
        diff_context: str = "",
        pr_description: str = "",
    ) -> list[CodeIssue]:
        """
        Run full two-stage filtering pipeline.
        
        Args:
            issues: Raw list of issues from linters
            diff_context: The PR diff (for LLM stage)
            pr_description: PR description (for LLM stage)
            
        Returns:
            Filtered list of core, relevant issues
        """
        # Stage 1: Static filter
        stage1_issues = self.static_filter(
            issues, 
            include_style=self.config.include_style
        )
        
        if not stage1_issues:
            return []
        
        # Stage 2: LLM relevance filter (if enabled)
        if diff_context and self.llm and not self.config.skip_llm_filter:
            return await self.llm_relevance_filter(
                stage1_issues,
                diff_context,
                pr_description,
            )
        
        return stage1_issues


def filter_issues_static(
    issues: list[CodeIssue],
    include_style: bool = False,
) -> list[CodeIssue]:
    """
    Convenience function for static-only filtering.
    
    Args:
        issues: List of CodeIssue objects
        include_style: Whether to include style issues
        
    Returns:
        Filtered list of core issues
    """
    filter_instance = IssueFilter()
    return filter_instance.static_filter(issues, include_style=include_style)
