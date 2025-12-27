from datetime import datetime
from typing import Optional
from collections import defaultdict
import logging

from langchain_core.language_models import BaseChatModel

from agents.base import AgentResult
from agents.issue_scoring_filter import IssueScoringFilter, ScoringConfig
from output.models import (
    AnalysisReport,
    PRSummary,
    BugDetectionResult,
    LineComment,
    Bug,
    BugType,
    Severity,
    FeaturePoint,
    StructureAnalysis,
    MemoryAnalysis,
    LogicAnalysis,
    SecurityAnalysis,
)

logger = logging.getLogger(__name__)


class ResultAggregator:
    def __init__(
        self,
        include_style: bool = False,
        llm: Optional[BaseChatModel] = None,
        relevance_threshold: float = 0.5,
        severity_threshold: float = 0.4,
    ):
        """
        Initialize the result aggregator.
        
        Args:
            include_style: If False (default), style violations are filtered out.
                          Only core issues (syntax, memory, security, logic) are kept.
            llm: Language model for LLM-based scoring filter.
            relevance_threshold: Minimum relevance score to keep issue (0.0-1.0).
            severity_threshold: Minimum severity score to keep issue (0.0-1.0).
        """
        self.include_style = include_style
        self.severity_priority = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
        }
        
        # Initialize LLM scoring filter if LLM provided
        self.scoring_filter = None
        if llm:
            config = ScoringConfig(
                relevance_threshold=relevance_threshold,
                severity_threshold=severity_threshold,
            )
            self.scoring_filter = IssueScoringFilter(llm=llm, config=config)
            logger.info(
                f"LLM scoring filter enabled "
                f"(relevance>={relevance_threshold}, severity>={severity_threshold})"
            )

    async def aggregate(
        self,
        pr_number: int,
        repo_full_name: str,
        feature_points: list[FeaturePoint],
        structure_result: AgentResult,
        memory_result: AgentResult,
        logic_result: AgentResult,
        security_result: AgentResult,
        pr_metadata: Optional[dict] = None,
        parsed_diff=None,
    ) -> AnalysisReport:
        all_issues = []

        for result in [structure_result, memory_result, logic_result, security_result]:
            if result.success:
                all_issues.extend(result.issues)

        logger.info(f"Collected {len(all_issues)} raw issues from all agents")

        all_issues = self._deduplicate_issues(all_issues)

        bugs = self._convert_to_bugs(all_issues)
        
        # Apply LLM scoring filter if available
        if self.scoring_filter and parsed_diff:
            diff_context = self._get_diff_summary(parsed_diff)
            changed_files = [f.filename for f in parsed_diff.files]
            
            logger.info(f"Applying LLM scoring filter to {len(bugs)} issues")
            bugs = await self.scoring_filter.score_and_filter(
                issues=bugs,
                diff_context=diff_context,
                feature_points=feature_points,
                changed_files=changed_files,
            )
            logger.info(f"After LLM scoring filter: {len(bugs)} issues remaining")

        bugs = sorted(bugs, key=lambda b: self.severity_priority.get(b.severity, 99))

        pr_summary = self._create_pr_summary(pr_metadata, feature_points, all_issues, parsed_diff)

        bug_detection = self._create_bug_detection(bugs)

        line_comments, off_diff_bugs = self._create_line_comments(bugs, parsed_diff)
        
        # Update PR summary to include off-diff issues
        if off_diff_bugs:
            pr_summary = self._add_off_diff_issues_to_summary(pr_summary, off_diff_bugs)

        return AnalysisReport(
            pr_number=pr_number,
            repo_full_name=repo_full_name,
            pr_summary=pr_summary,
            bug_detection=bug_detection,
            line_comments=line_comments,
            structure_analysis=self._extract_structure_analysis(structure_result),
            memory_analysis=self._extract_memory_analysis(memory_result),
            logic_analysis=self._extract_logic_analysis(logic_result),
            security_analysis=self._extract_security_analysis(security_result),
            generated_at=datetime.utcnow().isoformat(),
        )

    def _deduplicate_issues(self, issues: list[dict]) -> list[dict]:
        seen = set()
        unique = []

        for issue in issues:
            key = (
                issue.get("file", ""),
                issue.get("line", 0),
                issue.get("title", "")[:30],
            )
            if key not in seen:
                seen.add(key)
                unique.append(issue)

        return unique

    def _convert_to_bugs(self, issues: list[dict]) -> list[Bug]:
        bugs = []
        for issue in issues:
            bug_type = self._map_bug_type(issue.get("type", ""))
            severity = self._map_severity(issue.get("severity", "medium"))
            
            # Filter out style violations unless explicitly included
            if not self.include_style and bug_type == BugType.STYLE_VIOLATION:
                continue
            
            # Also filter based on category field if present
            category = issue.get("category", "")
            if not self.include_style and category == "style":
                continue

            bugs.append(Bug(
                id=issue.get("id", f"bug-{len(bugs)}"),
                type=bug_type,
                severity=severity,
                title=issue.get("title", "Issue found"),
                description=issue.get("description", ""),
                file=issue.get("file", ""),
                line=issue.get("line", 0),
                suggestion=issue.get("suggestion"),
                feature_point_id=issue.get("feature_point_id"),
            ))

        return bugs

    def _map_bug_type(self, type_str: str) -> BugType:
        mapping = {
            "logic_error": BugType.LOGIC_ERROR,
            "security_vulnerability": BugType.SECURITY_VULNERABILITY,
            "memory_issue": BugType.MEMORY_ISSUE,
            "syntax_error": BugType.SYNTAX_ERROR,
            "style_violation": BugType.STYLE_VIOLATION,
            "performance_issue": BugType.PERFORMANCE_ISSUE,
        }
        return mapping.get(type_str, BugType.LOGIC_ERROR)

    def _map_severity(self, severity_str: str) -> Severity:
        if isinstance(severity_str, Severity):
            return severity_str
        mapping = {
            "low": Severity.LOW,
            "medium": Severity.MEDIUM,
            "high": Severity.HIGH,
            "critical": Severity.CRITICAL,
        }
        return mapping.get(severity_str.lower() if isinstance(severity_str, str) else "medium", Severity.MEDIUM)

    def _create_pr_summary(
        self,
        pr_metadata: Optional[dict],
        feature_points: list[FeaturePoint],
        all_issues: list[dict],
        parsed_diff=None,
    ) -> PRSummary:
        if pr_metadata:
            title = pr_metadata.get("title", "")
            description = pr_metadata.get("body", "") or ""
            files_changed = [f.get("filename", "") for f in pr_metadata.get("files", [])]
            total_additions = pr_metadata.get("additions", 0)
            total_deletions = pr_metadata.get("deletions", 0)
        else:
            title = ""
            description = ""
            files_changed = list(set(i.get("file", "") for i in all_issues if i.get("file")))
            total_additions = 0
            total_deletions = 0

        if not files_changed and parsed_diff:
            files_changed = [f.filename for f in parsed_diff.files]
            total_additions = parsed_diff.total_additions
            total_deletions = parsed_diff.total_deletions

        feature_summary = ""
        if feature_points:
            feature_summary = "Feature points identified:\n"
            for fp in feature_points:
                feature_summary += f"- **{fp.name}**: {fp.description}\n"

        issue_summary = f"\n\nAnalysis found {len(all_issues)} potential issues across {len(files_changed)} files."

        ai_summary = feature_summary + issue_summary

        return PRSummary(
            title=title,
            description=description,
            files_changed=files_changed,
            total_additions=total_additions,
            total_deletions=total_deletions,
            feature_points=feature_points,
            ai_summary=ai_summary,
        )

    def _add_off_diff_issues_to_summary(
        self, pr_summary: PRSummary, off_diff_bugs: list[Bug]
    ) -> PRSummary:
        """Add issues in unchanged code to the PR summary."""
        if not off_diff_bugs:
            return pr_summary
        
        # Group by severity
        by_severity = {}
        for bug in off_diff_bugs:
            sev = bug.severity.value
            if sev not in by_severity:
                by_severity[sev] = []
            by_severity[sev].append(bug)
        
        # Build additional summary section
        lines = [
            "",
            "---",
            f"### Issues in Existing Code ({len(off_diff_bugs)} found)",
            "",
            "*These issues are in unchanged code and cannot receive line comments:*",
            "",
        ]
        
        for severity in ["critical", "high", "medium", "low"]:
            if severity in by_severity:
                bugs = by_severity[severity]
                lines.append(f"**{severity.upper()}** ({len(bugs)}):")
                for bug in bugs[:5]:  # Limit to 5 per severity
                    file_short = bug.file.split("/")[-1] if bug.file else "unknown"
                    lines.append(f"- `{file_short}:{bug.line}` - {bug.title}")
                if len(bugs) > 5:
                    lines.append(f"  - ... and {len(bugs) - 5} more")
                lines.append("")
        
        # Update the summary
        pr_summary.ai_summary += "\n".join(lines)
        return pr_summary

    def _create_bug_detection(self, bugs: list[Bug]) -> BugDetectionResult:
        by_severity = defaultdict(int)
        by_type = defaultdict(int)

        for bug in bugs:
            by_severity[bug.severity.value] += 1
            by_type[bug.type.value] += 1

        return BugDetectionResult(
            has_bugs=len(bugs) > 0,
            total_count=len(bugs),
            by_severity=dict(by_severity),
            by_type=dict(by_type),
            bugs=bugs,
        )

    def _create_line_comments(
        self, bugs: list[Bug], parsed_diff=None
    ) -> tuple[list[LineComment], list[Bug]]:
        """
        Create line comments for bugs, merging multiple issues on same line.
        
        Returns:
            Tuple of (line_comments, off_diff_bugs)
            - line_comments: Comments that can be posted on PR lines
            - off_diff_bugs: Bugs not in diff (can't get line comments)
        """
        comments = []
        
        # Build a set of valid (file, line) pairs from the diff
        valid_lines = self._get_valid_diff_lines(parsed_diff) if parsed_diff else None
        
        # Group bugs by (file, line) to merge multiple issues on same line
        bugs_by_location: dict[tuple[str, int], list[Bug]] = {}
        off_diff_bugs = []
        
        for bug in bugs:
            if not bug.file or bug.line <= 0:
                continue
            
            location = (bug.file, bug.line)
            
            # Check if line is in the diff
            if valid_lines is not None and location not in valid_lines:
                off_diff_bugs.append(bug)
                continue
            
            if location not in bugs_by_location:
                bugs_by_location[location] = []
            bugs_by_location[location].append(bug)
        
        # Log skipped bugs for transparency
        if off_diff_bugs:
            logger.info(
                f"{len(off_diff_bugs)} issues in unchanged code (will be in summary): "
                f"{[(b.file.split('/')[-1], b.line, b.title[:25]) for b in off_diff_bugs[:3]]}"
            )
        
        # Create one comment per location, merging multiple issues
        for (file_path, line), location_bugs in bugs_by_location.items():
            if len(location_bugs) == 1:
                # Single issue - simple format
                bug = location_bugs[0]
                body_parts = [
                    f"**{bug.severity.value.upper()}**: {bug.title}",
                    "",
                    bug.description,
                ]
                if bug.suggestion:
                    body_parts.extend(["", f"**Suggestion**: {bug.suggestion}"])
            else:
                # Multiple issues on same line - merge them
                body_parts = [f"**{len(location_bugs)} issues found on this line:**", ""]
                for i, bug in enumerate(location_bugs, 1):
                    body_parts.append(f"### {i}. [{bug.severity.value.upper()}] {bug.title}")
                    body_parts.append("")
                    body_parts.append(bug.description)
                    if bug.suggestion:
                        body_parts.append(f"\n**Suggestion**: {bug.suggestion}")
                    body_parts.append("")

            comments.append(LineComment(
                path=file_path,
                line=line,
                body="\n".join(body_parts),
                side="RIGHT",
            ))

        return comments, off_diff_bugs

    def _get_valid_diff_lines(self, parsed_diff) -> set[tuple[str, int]]:
        """Extract all valid (file, line) pairs from the parsed diff.
        
        Only lines that appear in the diff hunks can receive review comments.
        """
        valid_lines = set()
        
        for file_diff in parsed_diff.files:
            filename = file_diff.filename
            for hunk in file_diff.hunks:
                # Add all lines in the hunk's range (new file lines)
                # GitHub allows comments on any line visible in the diff
                for line_num in range(hunk.new_start, hunk.new_start + hunk.new_count):
                    valid_lines.add((filename, line_num))
                # Also add specifically added lines
                for line_num, _ in hunk.added_lines:
                    valid_lines.add((filename, line_num))
        
        return valid_lines

    def _get_diff_summary(self, parsed_diff) -> str:
        """Extract a summary of the diff for LLM context."""
        lines = []
        
        lines.append(f"Total files changed: {parsed_diff.total_files}")
        lines.append(f"Total additions: {parsed_diff.total_additions}")
        lines.append(f"Total deletions: {parsed_diff.total_deletions}")
        lines.append("")
        
        for file_diff in parsed_diff.files[:10]:  # Limit to first 10 files
            lines.append(f"=== {file_diff.filename} ===")
            lines.append(f"Status: {file_diff.status}")
            
            # Include first few hunks
            for hunk in file_diff.hunks[:3]:
                lines.append(f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@")
                
                # Include added lines (truncated)
                for line_num, content in hunk.added_lines[:5]:
                    lines.append(f"+{line_num}: {content[:100]}")
                
                if len(hunk.added_lines) > 5:
                    lines.append(f"  ... and {len(hunk.added_lines) - 5} more added lines")
            
            lines.append("")
        
        if len(parsed_diff.files) > 10:
            lines.append(f"... and {len(parsed_diff.files) - 10} more files")
        
        # Truncate total output
        result = "\n".join(lines)
        if len(result) > 8000:
            result = result[:8000] + "\n... (truncated)"
        
        return result

    def _extract_structure_analysis(self, result: AgentResult) -> StructureAnalysis:
        if not result.success:
            return StructureAnalysis(summary=f"Analysis failed: {result.error}")

        return StructureAnalysis(
            issues=self._convert_to_bugs(result.issues),
            summary=result.summary,
            metrics=result.metrics,
        )

    def _extract_memory_analysis(self, result: AgentResult) -> MemoryAnalysis:
        if not result.success:
            return MemoryAnalysis(summary=f"Analysis failed: {result.error}")

        return MemoryAnalysis(
            issues=self._convert_to_bugs(result.issues),
            summary=result.summary,
            patterns_found=result.metrics.get("patterns_found", []),
        )

    def _extract_logic_analysis(self, result: AgentResult) -> LogicAnalysis:
        if not result.success:
            return LogicAnalysis(summary=f"Analysis failed: {result.error}")

        return LogicAnalysis(
            issues=self._convert_to_bugs(result.issues),
            summary=result.summary,
            edge_cases=result.metrics.get("edge_cases", []),
        )

    def _extract_security_analysis(self, result: AgentResult) -> SecurityAnalysis:
        if not result.success:
            return SecurityAnalysis(summary=f"Analysis failed: {result.error}")

        return SecurityAnalysis(
            issues=self._convert_to_bugs(result.issues),
            summary=result.summary,
            vulnerabilities=result.metrics.get("vulnerabilities", []),
        )
