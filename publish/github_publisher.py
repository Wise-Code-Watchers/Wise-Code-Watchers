import logging
from typing import Optional, Dict, Any, List

from output.models import AnalysisReport
from output.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


def _extract_inline_comments_from_issues(
    final_report: Dict[str, Any],
    diff_ir: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Extract issues from final_report and convert them to GitHub inline comments.

    Args:
        final_report: The comprehensive analysis report containing logic_review and security_review
        diff_ir: The diff intermediate representation containing file changes with line numbers

    Returns:
        List of inline comment dicts with format: {path, body, line, side}
    """
    comments = []

    # Build a mapping of (file_path, old_line_range) -> new_line_in_diff
    # This helps us map issue locations to the actual PR diff lines
    file_line_mapping = _build_file_line_mapping(diff_ir)

    # Extract issues from logic_review
    # Structure: logic_review.issues[] is an array of analysis units
    # Each unit has: {result: "ISSUE", issues: [...], _meta: {...} or [...]}
    # _meta can be:
    #   - Object with hunk_id: {hunk_id, file_path, risk_score}  (Logic/Security Agent)
    #   - Array of location objects: [{file_path, line_start, line_end}, ...]  (deprecated)
    logic_review = final_report.get("logic_review", {})
    for analysis_unit in logic_review.get("issues", []):
        # Only process units that found issues
        if analysis_unit.get("result") != "ISSUE":
            continue

        # Get the actual issues array within this unit
        unit_issues = analysis_unit.get("issues", [])
        unit_meta = analysis_unit.get("_meta", {})

        # Handle both object and array formats
        meta_entries = []
        if isinstance(unit_meta, list):
            # Array format: each entry is a location object
            meta_entries = unit_meta
        else:
            # Object format: single meta entry with hunk_id
            meta_entries = [unit_meta]

        # Process each issue in this unit
        for issue_obj in unit_issues:
            for meta_entry in meta_entries:
                issue_obj_with_meta = {
                    **issue_obj,
                    "_meta": meta_entry,
                }
                comments.extend(_convert_issue_to_inline_comment(
                    issue_obj_with_meta, file_line_mapping, "Logic"
                ))

    # Extract issues from security_review
    security_review = final_report.get("security_review", {})
    for analysis_unit in security_review.get("issues", []):
        if analysis_unit.get("result") != "ISSUE":
            continue

        unit_issues = analysis_unit.get("issues", [])
        unit_meta = analysis_unit.get("_meta", {})

        # Handle both object and array formats
        meta_entries = []
        if isinstance(unit_meta, list):
            # Array format: each entry is a location object
            meta_entries = unit_meta
        else:
            # Object format: single meta entry with hunk_id
            meta_entries = [unit_meta]

        for issue_obj in unit_issues:
            for meta_entry in meta_entries:
                issue_obj_with_meta = {
                    **issue_obj,
                    "_meta": meta_entry,
                }
                comments.extend(_convert_issue_to_inline_comment(
                    issue_obj_with_meta, file_line_mapping, "Security"
                ))

    return comments


def _build_file_line_mapping(diff_ir: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a mapping from file paths to their diff hunks with touched line sets.

    Returns structure:
    {
        "file_path": {
            "hunks": [...],
            "touched_new_lines": set(int),  # RIGHT side lines that can be commented on
            "old_to_new": dict(old_lineno -> new_lineno),  # Mapping for modified code
        }
    }
    """
    mapping: Dict[str, Any] = {}

    # 🔧 Validation: Check if hunks have hunk_id
    missing_hunk_id_count = 0
    total_hunks = 0

    for file_entry in diff_ir.get("files", []):
        file_path = file_entry.get("file_path")
        if not file_path:
            continue

        hunks = file_entry.get("hunks", [])
        touched_new_lines = set()
        old_to_new = {}

        for hunk in hunks:
            total_hunks += 1

            # Validate hunk_id presence
            hunk_id = hunk.get("hunk_id")
            if not hunk_id:
                missing_hunk_id_count += 1
                logger.error(
                    f"❌ VALIDATION ERROR: Hunk missing hunk_id in file '{file_path}'. "
                    f"This will cause inline comment publishing to fail. "
                    f"Please regenerate diff_ir with updated data_parser.py."
                )

            for line_entry in hunk.get("lines", []):
                new_ln = line_entry.get("new_lineno")
                old_ln = line_entry.get("old_lineno")
                line_type = line_entry.get("type")  # add/del/context

                # RIGHT side commentable lines: add or context with new_lineno
                if new_ln is not None and line_type in ("add", "context"):
                    touched_new_lines.add(new_ln)

                # old->new mapping: only record if both sides have line numbers
                if old_ln is not None and new_ln is not None:
                    old_to_new[old_ln] = new_ln

        mapping[file_path] = {
            "hunks": hunks,
            "touched_new_lines": touched_new_lines,
            "old_to_new": old_to_new,
        }

    # Log validation summary
    if total_hunks > 0:
        if missing_hunk_id_count > 0:
            logger.error(
                f"❌ VALIDATION FAILED: {missing_hunk_id_count}/{total_hunks} hunks are missing hunk_id. "
                f"This WILL cause inline comment publishing to fail. "
                f"Please regenerate diff_ir by re-running parsing/data_parser.py"
            )
        else:
            logger.info(f"✅ VALIDATION PASSED: All {total_hunks} hunks have hunk_id")

    return mapping


def _resolve_review_line(
    file_mapping: Dict[str, Any],
    line_start: int,
    line_end: Optional[int] = None,
    search_radius: int = 5,
) -> Optional[Dict[str, int]]:
    """
    Resolve an issue location to a GitHub review comment line/start_line on RIGHT side.

    Strategy:
    1) Treat line_start as NEW line number (RIGHT) first
    2) If not in touched_new_lines, treat as OLD line and map via old_to_new
    3) If still not in touched_new_lines, find nearest touched line within search_radius

    Args:
        file_mapping: File mapping from _build_file_line_mapping
        line_start: Issue line_start (could be old or new)
        line_end: Optional issue line_end for multi-line comments
        search_radius: How many lines to search for a touched line

    Returns:
        Dict with "line" (single-line) or "start_line"+"line" (multi-line), or None
    """
    touched = file_mapping.get("touched_new_lines", set())
    old_to_new = file_mapping.get("old_to_new", {})

    def nearest_touched(target: int) -> Optional[int]:
        """Find nearest touched line to target."""
        if target in touched:
            return target
        for d in range(1, search_radius + 1):
            if (target - d) in touched:
                return target - d
            if (target + d) in touched:
                return target + d
        return None

    # ① Assume new line (most common case for issues in PR code)
    start_new = nearest_touched(line_start)
    end_new = None

    # ② Fallback: assume old line (for issues referencing base code)
    if start_new is None:
        mapped = old_to_new.get(line_start)
        if mapped is not None:
            start_new = nearest_touched(mapped)

    if start_new is None:
        return None

    # Handle multi-line comments
    if line_end and line_end != line_start:
        end_candidate = nearest_touched(line_end)
        if end_candidate is None:
            # Try mapping line_end as old line
            mapped_end = old_to_new.get(line_end)
            if mapped_end is not None:
                end_candidate = nearest_touched(mapped_end)

        # If end line not found, degrade to single-line comment
        if end_candidate is None:
            return {"line": start_new}

        # Ensure start_line < line
        if end_candidate < start_new:
            start_new, end_candidate = end_candidate, start_new

        return {"start_line": start_new, "line": end_candidate}

    # Single-line comment
    return {"line": start_new}


def _convert_issue_to_inline_comment(
    issue_obj: Dict[str, Any],
    file_line_mapping: Dict[str, Any],
    issue_type: str,
) -> List[Dict[str, Any]]:
    """
    Convert a single issue object to GitHub inline comment format.

    Args:
        issue_obj: Issue dict containing location, description, etc. (with _meta attached)
        file_line_mapping: Line mapping from _build_file_line_mapping
        issue_type: "Logic" or "Security"

    Returns:
        List of inline comment dicts (may return multiple if issue spans multiple lines)
    """
    comments = []
    meta = issue_obj.get("_meta", {})
    file_path = meta.get("file_path")

    if not file_path or file_path not in file_line_mapping:
        logger.warning(f"File path not found in diff: {file_path}")
        return []

    # Build comment body
    severity = issue_obj.get("severity", "unknown").upper()
    title = issue_obj.get("title", "Issue detected")
    category = issue_obj.get("category", "")
    description = issue_obj.get("description", "")
    suggestion = issue_obj.get("suggestion", "")
    trigger_condition = issue_obj.get("trigger_condition", "")

    body_lines = [
        f"**{issue_type} Issue - {severity}**",
        "",
    ]

    if category:
        body_lines.append(f"**Category:** {category}")

    body_lines.append(f"**{title}**")
    body_lines.append("")

    if description:
        body_lines.append(f"**Description:** {description}")
        body_lines.append("")

    if trigger_condition:
        body_lines.append(f"**Trigger:** {trigger_condition}")
        body_lines.append("")

    if suggestion:
        body_lines.append(f"**Suggestion:** {suggestion}")
        body_lines.append("")

    body = "\n".join(body_lines)

    # Get issue location from _meta
    # _meta can be:
    #   1. Object with hunk_id: {hunk_id, file_path, risk_score}  (Logic/Security Agent + AI analysis)
    #   2. Object with line numbers: {file_path, line_start, line_end}  (deprecated array format entries)
    meta = issue_obj.get("_meta", {})
    hunk_id = meta.get("hunk_id")

    # Strategy 1: Use hunk_id to find exact line numbers (preferred method)
    if hunk_id:
        logger.debug(f"Processing issue with hunk_id: {hunk_id} in {file_path}")

        # Find the hunk in the file mapping
        file_map = file_line_mapping.get(file_path, {})
        hunks = file_map.get("hunks", [])

        target_hunk = None
        for hunk in hunks:
            if hunk.get("hunk_id") == hunk_id:
                target_hunk = hunk
                break

        if not target_hunk:
            logger.warning(
                f"Hunk ID {hunk_id} not found in file {file_path}. "
                f"Available hunks: {[h.get('hunk_id') for h in hunks[:5]]}"
            )
            return []

        # Extract line numbers from hunk metadata
        # Use new_start for RIGHT side positioning
        new_start = target_hunk.get("new_start")
        new_count = target_hunk.get("new_count", 0)

        if new_start is None:
            logger.warning(f"Hunk {hunk_id} has no new_start for {file_path}")
            return []

        # Build comment dict with hunk location
        comment = {
            "path": file_path,
            "body": body,
            "side": "RIGHT",
            "start_line": new_start,
            "line": new_start + new_count - 1,  # End of hunk
        }

        logger.debug(
            f"  → Hunk-based comment from {comment['start_line']} to {comment['line']}"
        )
        comments.append(comment)
        return comments

    # Strategy 2: Use line_start/line_end directly (fallback for deprecated format)
    line_start = meta.get("line_start")
    line_end = meta.get("line_end")

    if line_start is None:
        logger.warning(
            f"No hunk_id or line_start found for issue in {file_path}. "
            f"Meta: {meta}, Issue keys: {list(issue_obj.keys())}"
        )
        return []

    # Ensure line numbers are integers
    try:
        line_start = int(line_start)
        line_end = int(line_end) if line_end is not None else line_start
    except (ValueError, TypeError):
        logger.warning(f"Invalid line number format in meta: {meta}")
        return []

    logger.debug(f"Processing issue at {file_path}:{line_start}-{line_end}")

    # Resolve review line(s) using the improved strategy
    file_map = file_line_mapping[file_path]
    resolved = _resolve_review_line(
        file_mapping=file_map,
        line_start=line_start,
        line_end=line_end if line_end != line_start else None,  # Only specify end if different
    )

    if not resolved:
        logger.warning(
            f"Could not resolve issue line(s) {line_start}-{line_end} to PR diff for {file_path}. "
            f"File has {len(file_map.get('touched_new_lines', set()))} touched lines: "
            f"{sorted(list(file_map.get('touched_new_lines', set())))[:10]}..."
        )
        return []

    # Build comment dict with support for multi-line comments
    comment = {
        "path": file_path,
        "body": body,
        "side": "RIGHT",
    }

    # Single-line comment
    if "start_line" not in resolved:
        comment["line"] = resolved["line"]
        logger.debug(f"  → Single-line comment at line {resolved['line']}")
    else:
        # Multi-line comment: "Comment on lines +x to +y"
        comment["start_line"] = resolved["start_line"]
        comment["line"] = resolved["line"]
        comment["start_side"] = "RIGHT"
        logger.debug(f"  → Multi-line comment from {resolved['start_line']} to {resolved['line']}")

    comments.append(comment)

    return comments


def _find_line_in_pr_diff(
    file_path: str,
    issue_line: int,
    file_info: Dict[str, Any],
) -> Optional[int]:
    """
    Map an issue line number to the PR diff line number (RIGHT side).

    This function handles two cases:
    1. Modified/deleted code: Maps old line numbers to new line numbers
    2. Added code: Returns the new line number directly

    Args:
        file_path: Path to the file
        issue_line: Line number from the issue (could be old or new)
        file_info: File info from _build_file_line_mapping

    Returns:
        The new line number in the PR's RIGHT side, or None if not found
    """
    # First, check if issue_line is a newly added line (type: "add")
    # This means the issue is in the PR's new code
    for hunk in file_info.get("hunks", []):
        new_start = hunk.get("new_start", 0)
        new_end = new_start + hunk.get("new_count", 0)

        # Check if issue_line is within this hunk's new range
        if new_start <= issue_line < new_end:
            # Verify this is an added line by checking the line entries
            for line_entry in hunk.get("lines", []):
                if line_entry.get("new_lineno") == issue_line and line_entry.get("type") == "add":
                    # This is newly added code, return the line as-is
                    return issue_line

    # If not found in new lines, try to map from old line to new line
    # This handles issues in modified/deleted code
    for hunk in file_info.get("hunks", []):
        old_start = hunk.get("old_start", 0)
        old_count = hunk.get("old_count", 0)
        new_start = hunk.get("new_start", 0)

        # Check if the issue line falls within this hunk's old range
        if old_start <= issue_line < old_start + old_count:
            # Search through lines in this hunk to find the exact match
            for line_entry in hunk.get("lines", []):
                if line_entry.get("old_lineno") == issue_line:
                    # Found the line! Return its new line number
                    new_lineno = line_entry.get("new_lineno")
                    if new_lineno is not None:
                        return new_lineno

            # If we didn't find an exact match, estimate based on offset
            offset = issue_line - old_start
            return new_start + offset

    # If we couldn't find it in any hunk's old range, try direct line entry lookup
    # This handles context lines that flow through
    for hunk in file_info.get("hunks", []):
        for line_entry in hunk.get("lines", []):
            if line_entry.get("old_lineno") == issue_line:
                new_lineno = line_entry.get("new_lineno")
                if new_lineno is not None:
                    return new_lineno

    return None


def _generate_functional_summary_body(functional_summary: Dict[str, Any], pr_info: Dict[str, Any]) -> str:
    """Generate GitHub comment body from functional summary."""
    lines = ["## 📋 PR 功能分析总结\n"]

    # Overview
    overview = functional_summary.get("overview", "")
    if overview:
        lines.append(f"**概述:** {overview}\n")

    # Key Changes
    key_changes = functional_summary.get("key_changes", [])
    if key_changes:
        lines.append("### 🔑 核心变更\n")
        for change in key_changes:
            lines.append(f"- {change}")
        lines.append("")

    # Affected Components
    components = functional_summary.get("affected_components", [])
    if components:
        lines.append("### 📦 影响组件\n")
        for component in components:
            lines.append(f"- `{component}`")
        lines.append("")

    # Change Categories
    categories = functional_summary.get("change_categories", {})
    if categories:
        category_names = {
            "feature": "✨ 新功能",
            "bugfix": "🐛 缺陷修复",
            "refactor": "♻️ 重构优化",
            "performance": "⚡ 性能改进",
            "documentation": "📝 文档更新",
            "tests": "🧪 测试相关",
            "config": "⚙️ 配置变更",
            "other": "📦 其他变更"
        }
        lines.append("### 🏷️ 变更分类\n")
        for category, items in categories.items():
            if items:
                name = category_names.get(category, category.capitalize())
                lines.append(f"**{name}:**")
                for item in items:
                    lines.append(f"  - {item}")
        lines.append("")

    # Files Summary
    files_summary = functional_summary.get("files_summary", {})
    if files_summary:
        lines.append("### 📁 文件统计\n")
        lines.append(f"- **总计:** {files_summary.get('total_files', 0)} 个文件")
        lines.append(f"  - 新增: {files_summary.get('added', 0)}")
        lines.append(f"  - 修改: {files_summary.get('modified', 0)}")
        lines.append(f"  - 删除: {files_summary.get('deleted', 0)}")
        lines.append(f"  - 重命名: {files_summary.get('renamed', 0)}")
        lines.append("")

    # Complexity Assessment
    complexity = functional_summary.get("complexity_assessment", "")
    if complexity:
        lines.append("### 📊 复杂度评估\n")
        lines.append(f"{complexity}\n")

    # Testing Suggestions
    testing_suggestions = functional_summary.get("testing_suggestions", [])
    if testing_suggestions:
        lines.append("### 🧪 测试建议\n")
        for suggestion in testing_suggestions:
            lines.append(f"- {suggestion}")
        lines.append("")

    lines.append("---\n*由 WiseCodeWatchers 功能分析生成*")

    return "\n".join(lines)


def _generate_comprehensive_report_body(final_report: Dict[str, Any]) -> str:
    """Generate GitHub review body from comprehensive workflow report."""
    lines = ["## 🔍 WiseCodeWatchers Comprehensive Review\n"]

    # PR Info
    pr_info = final_report.get("pr_info", {})
    if pr_info.get("title"):
        lines.append(f"**PR:** {pr_info.get('title', 'N/A')}")
        lines.append(f"**Changes:** +{pr_info.get('additions', 0)}/-{pr_info.get('deletions', 0)} lines\n")

    # Summary Statistics
    logic_review = final_report.get("logic_review", {})
    security_review = final_report.get("security_review", {})
    triage_summary = final_report.get("triage_summary", {})
    cross_impact = final_report.get("cross_file_impact", {})

    logic_issues = logic_review.get("issues_found", 0)
    security_issues = security_review.get("issues_found", 0)
    total_issues = logic_issues + security_issues

    lines.append("### 📊 Summary\n")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Logic Issues | {logic_issues} |")
    lines.append(f"| Security Issues | {security_issues} |")
    lines.append(f"| **Total Issues** | **{total_issues}** |")

    if triage_summary.get("total_count", 0) > 0:
        lines.append(f"| Hunks Reviewed | {triage_summary.get('to_review_count', 0)}/{triage_summary.get('total_count', 0)} |")

    if cross_impact.get("files_analyzed", 0) > 0:
        lines.append(f"| High Impact Files | {len(cross_impact.get('high_impact_files', []))} |")

    lines.append("")

    # Logic Issues
    if logic_issues > 0:
        lines.append("### 🧠 Logic Issues\n")
        for issue in logic_review.get("issues", [])[:10]:
            issue_data = issue.get("issue", {})
            if issue_data:
                severity = issue_data.get("severity", "unknown").upper()
                title = issue_data.get("title", "Unknown issue")
                file_path = issue.get("_meta", {}).get("file_path", "")
                lines.append(f"- **[{severity}]** {title}")
                if file_path:
                    lines.append(f"  - File: `{file_path}`")
                desc = issue_data.get("description", "")
                if desc:
                    lines.append(f"  - {desc[:200]}...")
        if logic_issues > 10:
            lines.append(f"\n*...and {logic_issues - 10} more logic issues*")
        lines.append("")

    # Security Issues
    if security_issues > 0:
        lines.append("### 🔒 Security Issues\n")
        for issue in security_review.get("issues", [])[:10]:
            issue_data = issue.get("issue", {})
            if issue_data:
                severity = issue_data.get("severity", "unknown").upper()
                title = issue_data.get("title", "Unknown vulnerability")
                file_path = issue.get("_meta", {}).get("file_path", "")
                cwe = issue_data.get("cwe", [])
                lines.append(f"- **[{severity}]** {title}")
                if cwe:
                    lines.append(f"  - CWE: {', '.join(cwe)}")
                if file_path:
                    lines.append(f"  - File: `{file_path}`")
        if security_issues > 10:
            lines.append(f"\n*...and {security_issues - 10} more security issues*")
        lines.append("")

    # Cross-file impact warnings
    breaking_changes = cross_impact.get("breaking_changes", [])
    if breaking_changes:
        lines.append("### ⚠️ Breaking Changes Detected\n")
        for change in breaking_changes[:5]:
            lines.append(f"- {change.get('description', 'Breaking change detected')}")
        lines.append("")

    # Recommendation
    lines.append("### 🎯 Recommendation\n")
    review_summary = final_report.get("review_summary", {})
    recommendation = review_summary.get("recommendation", "needs_review")
    if total_issues == 0:
        lines.append("✅ No significant issues found. Ready to merge.")
    elif security_issues > 0:
        lines.append("🔴 **Security issues detected.** Please review and address before merging.")
    elif logic_issues > 3:
        lines.append("🟡 **Multiple logic issues found.** Consider reviewing before merging.")
    else:
        lines.append("🟢 Minor issues found. Review recommended.")

    lines.append("\n---\n*Generated by WiseCodeWatchers Comprehensive Workflow*")

    return "\n".join(lines)


class GitHubPublisher:
    def __init__(self, github_client):
        self.client = github_client
        self.report_generator = ReportGenerator()
        self._pr_files_cache = {}

    def _get_pr_files(self, repo_full_name: str, pr_number: int) -> set[str]:
        """Get set of file paths that are in the PR diff."""
        cache_key = f"{repo_full_name}#{pr_number}"
        if cache_key not in self._pr_files_cache:
            try:
                files = self.client.get_pr_files_changed(repo_full_name, pr_number)
                self._pr_files_cache[cache_key] = {f["filename"] for f in files}
            except Exception as e:
                logger.warning(f"Failed to get PR files: {e}")
                self._pr_files_cache[cache_key] = set()
        return self._pr_files_cache[cache_key]

    async def publish_review(
        self,
        report: AnalysisReport,
        as_review: bool = True,
        include_line_comments: bool = True,
    ) -> dict:
        try:
            body = self.report_generator.generate_github_review_body(report)

            if as_review:
                result = await self._publish_as_review(
                    report=report,
                    body=body,
                    include_line_comments=include_line_comments,
                )
            else:
                result = await self._publish_as_comment(
                    report=report,
                    body=body,
                )

            logger.info(f"Published review for PR #{report.pr_number}")
            return result

        except Exception as e:
            logger.error(f"Failed to publish review: {e}")
            raise

    async def _publish_as_review(
        self,
        report: AnalysisReport,
        body: str,
        include_line_comments: bool,
    ) -> dict:
        comments = []
        if include_line_comments:
            all_comments = self.report_generator.generate_line_comments(report)
            pr_files = self._get_pr_files(report.repo_full_name, report.pr_number)
            comments = [c for c in all_comments if c.get("path") in pr_files]
            logger.info(f"Filtered comments: {len(comments)}/{len(all_comments)} (files in PR: {len(pr_files)})")

        event = "COMMENT"
        if report.bug_detection.has_bugs:
            critical_count = report.bug_detection.by_severity.get("critical", 0)
            high_count = report.bug_detection.by_severity.get("high", 0)
            if critical_count > 0 or high_count > 3:
                event = "REQUEST_CHANGES"

        self.client.create_review(
            repo_full_name=report.repo_full_name,
            pr_number=report.pr_number,
            body=body,
            event=event,
            comments=comments,
        )

        return {
            "type": "review",
            "event": event,
            "body_length": len(body),
            "line_comments_count": len(comments),
        }

    async def _publish_as_comment(
        self,
        report: AnalysisReport,
        body: str,
    ) -> dict:
        self.client.create_issue_comment(
            repo_full_name=report.repo_full_name,
            pr_number=report.pr_number,
            body=body,
        )

        return {
            "type": "comment",
            "body_length": len(body),
        }

    def publish_review_sync(
        self,
        report: AnalysisReport,
        as_review: bool = True,
        include_line_comments: bool = True,
    ) -> dict:
        try:
            body = self.report_generator.generate_github_review_body(report)

            if as_review:
                comments = []
                if include_line_comments:
                    all_comments = self.report_generator.generate_line_comments(report)
                    # Filter comments to only include files actually in the PR diff
                    pr_files = self._get_pr_files(report.repo_full_name, report.pr_number)
                    comments = [c for c in all_comments if c.get("path") in pr_files]
                    logger.info(f"Filtered comments: {len(comments)}/{len(all_comments)} (files in PR: {len(pr_files)})")

                event = "COMMENT"
                if report.bug_detection.has_bugs:
                    critical_count = report.bug_detection.by_severity.get("critical", 0)
                    high_count = report.bug_detection.by_severity.get("high", 0)
                    if critical_count > 0 or high_count > 3:
                        event = "REQUEST_CHANGES"

                try:
                    self.client.create_review(
                        repo_full_name=report.repo_full_name,
                        pr_number=report.pr_number,
                        body=body,
                        event=event,
                        comments=comments,
                    )
                    return {
                        "type": "review",
                        "event": event,
                        "body_length": len(body),
                        "line_comments_count": len(comments),
                    }
                except Exception as e:
                    if "could not be resolved" in str(e) and comments:
                        logger.warning(f"Line comments failed, retrying without comments: {e}")
                        self.client.create_review(
                            repo_full_name=report.repo_full_name,
                            pr_number=report.pr_number,
                            body=body,
                            event=event,
                            comments=[],
                        )
                        return {
                            "type": "review",
                            "event": event,
                            "body_length": len(body),
                            "line_comments_count": 0,
                            "line_comments_skipped": len(comments),
                        }
                    raise
            else:
                self.client.create_issue_comment(
                    repo_full_name=report.repo_full_name,
                    pr_number=report.pr_number,
                    body=body,
                )

                return {
                    "type": "comment",
                    "body_length": len(body),
                }

        except Exception as e:
            logger.error(f"Failed to publish review: {e}")
            raise

    def publish_comprehensive_report(
        self,
        final_report: Dict[str, Any],
        pr_number: int,
        repo_full_name: str,
        diff_ir: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """
        Publish comprehensive workflow report to GitHub as a review with inline comments.

        Args:
            final_report: The comprehensive analysis report
            pr_number: Pull request number
            repo_full_name: Repository full name (e.g., "owner/repo")
            diff_ir: Optional diff intermediate representation for inline comments
        """
        try:
            body = _generate_comprehensive_report_body(final_report)

            # Determine review event based on issues
            logic_issues = final_report.get("logic_review", {}).get("issues_found", 0)
            security_issues = final_report.get("security_review", {}).get("issues_found", 0)

            event = "COMMENT"
            if security_issues > 0:
                event = "REQUEST_CHANGES"
            elif logic_issues > 3:
                event = "REQUEST_CHANGES"

            # Extract inline comments from issues if diff_ir is provided
            inline_comments = []
            if diff_ir:
                inline_comments = _extract_inline_comments_from_issues(
                    final_report, diff_ir
                )

                # Filter comments to only include files actually in the PR
                pr_files = self._get_pr_files(repo_full_name, pr_number)
                inline_comments = [
                    c for c in inline_comments if c.get("path") in pr_files
                ]

                # Deduplicate comments (same file, line range, and similar body)
                seen = set()
                deduped = []
                for c in inline_comments:
                    key = (
                        c["path"],
                        c.get("start_line"),
                        c.get("line"),
                        c["body"][:50],  # First 50 chars as signature
                    )
                    if key not in seen:
                        seen.add(key)
                        deduped.append(c)
                inline_comments = deduped

                # Limit to max 20 comments (GitHub UX best practice)
                max_comments = 20
                if len(inline_comments) > max_comments:
                    inline_comments = inline_comments[:max_comments]
                    logger.info(
                        f"Truncated inline comments to {max_comments} (had {len(deduped)})"
                    )

                logger.info(
                    f"Generated {len(inline_comments)} inline comments "
                    f"from {logic_issues + security_issues} issues"
                )

            # Publish the review with inline comments
            try:
                self.client.create_review(
                    repo_full_name=repo_full_name,
                    pr_number=pr_number,
                    body=body,
                    event=event,
                    comments=inline_comments,
                )

                return {
                    "type": "comprehensive_review",
                    "event": event,
                    "body_length": len(body),
                    "logic_issues": logic_issues,
                    "security_issues": security_issues,
                    "inline_comments_count": len(inline_comments),
                }
            except Exception as e:
                # If inline comments fail (e.g., line resolution errors), retry without them
                if "could not be resolved" in str(e).lower() and inline_comments:
                    logger.warning(
                        f"Inline comments failed due to line resolution errors. "
                        f"Retrying review without inline comments. Error: {e}"
                    )
                    self.client.create_review(
                        repo_full_name=repo_full_name,
                        pr_number=pr_number,
                        body=body,
                        event=event,
                        comments=[],  # Retry without inline comments
                    )

                    return {
                        "type": "comprehensive_review",
                        "event": event,
                        "body_length": len(body),
                        "logic_issues": logic_issues,
                        "security_issues": security_issues,
                        "inline_comments_count": 0,
                        "inline_comments_skipped": len(inline_comments),
                        "warning": f"Inline comments skipped due to line resolution errors: {str(e)[:200]}",
                    }
                else:
                    # Re-raise if it's a different error
                    raise

        except Exception as e:
            logger.error(f"Failed to publish comprehensive review: {e}")
            raise

    def publish_functional_summary(
        self,
        functional_summary: Dict[str, Any],
        pr_number: int,
        repo_full_name: str,
        pr_metadata: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """
        Publish functional summary to GitHub as a PR comment.

        Args:
            functional_summary: The functional summary dictionary
            pr_number: Pull request number
            repo_full_name: Repository full name (e.g., "owner/repo")
            pr_metadata: Optional PR metadata for additional context
        """
        try:
            body = _generate_functional_summary_body(
                functional_summary,
                pr_metadata or {}
            )

            # Publish as an issue comment (not a review)
            self.client.create_issue_comment(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                body=body,
            )

            logger.info(f"Published functional summary for PR #{pr_number}")

            return {
                "type": "functional_summary",
                "body_length": len(body),
                "overview_length": len(functional_summary.get("overview", "")),
                "key_changes_count": len(functional_summary.get("key_changes", [])),
                "affected_components_count": len(functional_summary.get("affected_components", [])),
            }

        except Exception as e:
            logger.error(f"Failed to publish functional summary: {e}")
            raise
