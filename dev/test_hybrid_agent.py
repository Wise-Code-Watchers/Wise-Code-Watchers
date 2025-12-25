#!/usr/bin/env python3
"""
Test script for the LangGraph SyntaxAnalysisAgent (2025 patterns).

Demonstrates:
1. Fixed node mode (no LLM) - fast, deterministic
2. LangGraph mode (with LLM) - structured output with Pydantic
3. Diff-line filtering - only show issues on lines changed in the PR
"""

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Union

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.text import Text
from rich import box

from core.repo_manager import RepoManager
from agents.syntax import (
    SyntaxChecker,
    create_syntax_agent,
    analyze_files,
    print_analysis_report,
    SyntaxAnalysisResult,
)
from agents.syntax.syntax_checker import SyntaxCheckResult, SyntaxIssue
from agents.syntax.schemas import CodeIssue
from agents.syntax.prompts import LanguagePromptLoader
from agents.preprocessing.diff_parser import DiffParser, ParsedDiff, FileDiff

console = Console()


@dataclass
class DiffLineFilter:
    """
    Filters linter issues to only include those on lines changed in the PR diff.
    
    This ensures that code review focuses only on the changes introduced by the PR,
    not pre-existing issues in unchanged code.
    """
    parsed_diff: ParsedDiff
    _changed_lines_cache: dict[str, set[int]] = field(default_factory=dict)
    
    def __post_init__(self):
        self._build_changed_lines_index()
    
    def _build_changed_lines_index(self):
        """Build an index of changed line numbers per file."""
        for file_diff in self.parsed_diff.files:
            changed_lines = set()
            for hunk in file_diff.hunks:
                # Include all added lines (these are the new line numbers)
                for line_num, _ in hunk.added_lines:
                    changed_lines.add(line_num)
                # Also include context around hunks (lines that touch the change)
                # This helps catch issues on lines adjacent to changes
                for line_num in range(hunk.new_start, hunk.new_start + hunk.new_count):
                    changed_lines.add(line_num)
            self._changed_lines_cache[file_diff.filename] = changed_lines
    
    def get_changed_lines(self, filename: str) -> set[int]:
        """Get the set of changed line numbers for a file."""
        # Try exact match first
        if filename in self._changed_lines_cache:
            return self._changed_lines_cache[filename]
        # Try matching by basename or partial path
        for cached_file, lines in self._changed_lines_cache.items():
            if cached_file.endswith(filename) or filename.endswith(cached_file):
                return lines
        return set()
    
    def is_line_changed(self, filename: str, line: int) -> bool:
        """Check if a specific line in a file was changed."""
        return line in self.get_changed_lines(filename)
    
    def filter_syntax_issues(self, issues: list[SyntaxIssue]) -> list[SyntaxIssue]:
        """Filter SyntaxIssue list to only include issues on changed lines."""
        return [
            issue for issue in issues
            if self.is_line_changed(issue.file, issue.line)
        ]
    
    def filter_code_issues(self, issues: list[CodeIssue]) -> list[CodeIssue]:
        """Filter CodeIssue list to only include issues on changed lines."""
        return [
            issue for issue in issues
            if self.is_line_changed(issue.file, issue.line)
        ]
    
    def filter_syntax_check_result(self, result: SyntaxCheckResult) -> SyntaxCheckResult:
        """Create a new SyntaxCheckResult with only issues on changed lines."""
        filtered_issues = self.filter_syntax_issues(result.issues)
        return SyntaxCheckResult(
            success=result.success,
            issues=filtered_issues,
            files_analyzed=result.files_analyzed,
            files_by_language=result.files_by_language,
            error=result.error,
        )
    
    def filter_analysis_result(self, result: SyntaxAnalysisResult) -> SyntaxAnalysisResult:
        """Create a new SyntaxAnalysisResult with only issues on changed lines."""
        filtered_issues = self.filter_code_issues(result.issues)
        return SyntaxAnalysisResult(
            success=result.success,
            files_analyzed=result.files_analyzed,
            languages=result.languages,
            total_issues=len(filtered_issues),
            issues=filtered_issues,
            insight=result.insight,
            error=result.error,
        )
    
    def get_stats(self) -> dict:
        """Get statistics about the diff coverage."""
        total_files = len(self._changed_lines_cache)
        total_changed_lines = sum(len(lines) for lines in self._changed_lines_cache.values())
        return {
            "files_with_changes": total_files,
            "total_changed_lines": total_changed_lines,
            "files": {f: len(lines) for f, lines in self._changed_lines_cache.items()},
        }


def create_diff_filter(pr_folder: str) -> DiffLineFilter:
    """Create a DiffLineFilter from a PR export folder."""
    parser = DiffParser()
    parsed_diff = parser.parse_pr_folder(pr_folder)
    return DiffLineFilter(parsed_diff=parsed_diff)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Severity/category color mapping
SEVERITY_COLORS = {
    "error": "red",
    "warning": "yellow",
    "info": "blue",
}

CATEGORY_COLORS = {
    "syntax": "red",
    "memory": "magenta",
    "security": "red bold",
    "style": "cyan",
    "performance": "yellow",
}


def print_section(title: str, subtitle: str = None):
    """Print a styled section header."""
    content = f"[bold]{title}[/bold]"
    if subtitle:
        content += f"\n[dim]{subtitle}[/dim]"
    console.print()
    console.print(Panel(content, box=box.DOUBLE, border_style="blue"))


def create_stats_table(title: str, data: dict[str, any]) -> Table:
    """Create a stats table with key-value pairs."""
    table = Table(title=title, box=box.ROUNDED, show_header=False, title_style="bold")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    for key, value in data.items():
        table.add_row(key, str(value))
    return table


def create_issues_table(issues: list, title: str = "Issues", max_rows: int = 5) -> Table:
    """Create a table displaying code issues."""
    table = Table(title=title, box=box.ROUNDED, title_style="bold yellow")
    table.add_column("Location", style="cyan", no_wrap=True)
    table.add_column("Cat", style="magenta", width=8)
    table.add_column("Sev", width=7)
    table.add_column("Rule", style="blue", width=12)
    table.add_column("Message", style="white")
    
    for issue in issues[:max_rows]:
        # Get colors
        sev_color = SEVERITY_COLORS.get(issue.severity, "white")
        cat_color = CATEGORY_COLORS.get(issue.category, "white")
        
        # Truncate message
        msg = issue.message[:50] + "..." if len(issue.message) > 50 else issue.message
        
        table.add_row(
            f"{issue.file}:{issue.line}",
            f"[{cat_color}]{issue.category}[/{cat_color}]",
            f"[{sev_color}]{issue.severity}[/{sev_color}]",
            issue.rule,
            msg,
        )
    
    if len(issues) > max_rows:
        table.add_row(
            f"[dim]... and {len(issues) - max_rows} more[/dim]",
            "", "", "", ""
        )
    
    return table


def print_filter_summary(raw_count: int, filtered_count: int):
    """Print a summary of filtering results."""
    filtered_out = raw_count - filtered_count
    if filtered_out > 0:
        console.print(f"  [green]{filtered_count}[/green] issues on diff lines "
                     f"([dim]{filtered_out} filtered out from {raw_count} total[/dim])")
    else:
        console.print(f"  [green]{filtered_count}[/green] issues on diff lines")


async def test_fixed_node(ctx, diff_filter: DiffLineFilter):
    """Test the fixed node approach (no LLM, fast)."""
    print_section("Test 1: Fixed Node", "SyntaxChecker - No LLM, fast & deterministic")
    
    checker = SyntaxChecker(enable_memory_checks=True)
    linters = list(checker.get_available_linters().keys())
    console.print(f"  [cyan]Available linters:[/cyan] {', '.join(linters)}")
    console.print(f"  [cyan]Scope:[/cyan] {len(ctx.existing_changed_files)} PR-changed files")
    
    raw_result = await checker.check(ctx.codebase_path, ctx.existing_changed_files)
    result = diff_filter.filter_syntax_check_result(raw_result)
    
    # Results summary table
    status = "[green]Success[/green]" if result.success else "[red]Failed[/red]"
    stats_data = {
        "Status": status,
        "Files analyzed": result.files_analyzed,
        "Total issues (all lines)": raw_result.total_issues,
        "Issues on diff lines": result.total_issues,
        "Filtered out": f"{raw_result.total_issues - result.total_issues} (not on changed lines)",
    }
    console.print(create_stats_table("Results (Diff Lines Only)", stats_data))
    
    # Files by language
    if result.files_by_language:
        lang_table = Table(title="Files by Language", box=box.SIMPLE)
        lang_table.add_column("Language", style="cyan")
        lang_table.add_column("Count", style="green")
        for lang, count in result.files_by_language.items():
            lang_table.add_row(lang, str(count))
        console.print(lang_table)
    
    # Issues breakdown
    if result.issues_by_category:
        cat_table = Table(title="Issues by Category (Diff Lines)", box=box.SIMPLE)
        cat_table.add_column("Category", style="cyan")
        cat_table.add_column("Count", style="yellow")
        for cat, issues in result.issues_by_category.items():
            color = CATEGORY_COLORS.get(cat, "white")
            cat_table.add_row(f"[{color}]{cat}[/{color}]", str(len(issues)))
        console.print(cat_table)
    
    # Special issues highlights
    if result.memory_issues:
        console.print(f"\n[magenta bold]Memory/Resource Issues ({len(result.memory_issues)})[/magenta bold]")
        console.print(create_issues_table(result.memory_issues, "Memory Issues", max_rows=3))
    
    if result.security_issues:
        console.print(f"\n[red bold]Security Issues ({len(result.security_issues)})[/red bold]")
        console.print(create_issues_table(result.security_issues, "Security Issues", max_rows=3))
    
    # All issues table
    if result.issues:
        console.print(create_issues_table(result.issues, f"All Issues on Diff Lines ({len(result.issues)})", max_rows=5))
    elif raw_result.issues:
        console.print(f"\n[dim]No issues on diff lines (all {raw_result.total_issues} issues are on unchanged lines)[/dim]")
    
    if result.error:
        console.print(f"\n[red]Error: {result.error}[/red]")
    
    return result


async def test_langgraph_no_llm(ctx, diff_filter: DiffLineFilter):
    """Test the LangGraph agent without LLM (linter only)."""
    print_section("Test 2: LangGraph Agent", "Linter Only - No LLM")
    
    console.print(f"  [cyan]Scope:[/cyan] {len(ctx.changed_files)} PR-changed files")
    
    agent = create_syntax_agent(llm=None)
    
    result = await agent.ainvoke({
        "messages": [],
        "codebase_path": ctx.codebase_path,
        "files_to_analyze": ctx.changed_files,
        "linter_issues": [],
        "languages_detected": [],
        "structured_response": None,
    })
    
    raw_analysis: SyntaxAnalysisResult = result["structured_response"]
    analysis = diff_filter.filter_analysis_result(raw_analysis)
    
    # Results table
    status = "[green]Success[/green]" if analysis.success else "[red]Failed[/red]"
    langs = ', '.join(analysis.languages) if analysis.languages else 'None'
    stats_data = {
        "Status": status,
        "Files analyzed": analysis.files_analyzed,
        "Languages": langs,
        "Total issues (all lines)": raw_analysis.total_issues,
        "Issues on diff lines": analysis.total_issues,
        "Filtered out": f"{raw_analysis.total_issues - analysis.total_issues} (not on changed lines)",
        "Memory issues": analysis.memory_issue_count,
        "Security issues": analysis.security_issue_count,
    }
    console.print(create_stats_table("Results (Diff Lines Only)", stats_data))
    
    if analysis.issues_by_category:
        cat_table = Table(title="Issues by Category", box=box.SIMPLE)
        cat_table.add_column("Category", style="cyan")
        cat_table.add_column("Count", style="yellow")
        for cat, issues in analysis.issues_by_category.items():
            color = CATEGORY_COLORS.get(cat, "white")
            cat_table.add_row(f"[{color}]{cat}[/{color}]", str(len(issues)))
        console.print(cat_table)
    
    if analysis.issues:
        console.print(create_issues_table(analysis.issues, f"Issues on Diff Lines ({len(analysis.issues)})", max_rows=5))
    elif raw_analysis.issues:
        console.print(f"\n[dim]No issues on diff lines (all {raw_analysis.total_issues} on unchanged lines)[/dim]")
    
    if analysis.error:
        console.print(f"\n[red]Error: {analysis.error}[/red]")
    
    return analysis


async def test_langgraph_with_llm(ctx, diff_filter: DiffLineFilter):
    """Test the LangGraph agent with LLM (full analysis with structured output)."""
    print_section("Test 3: LangGraph Agent + LLM", "Full analysis with structured output")
    
    console.print(f"  [cyan]Scope:[/cyan] {len(ctx.changed_files)} PR-changed files")
    
    try:
        from agents.orchestrator import create_llm
        llm = create_llm()
        console.print(f"  [green]LLM loaded:[/green] {type(llm).__name__}")
    except Exception as e:
        console.print(f"  [red]Could not load LLM:[/red] {e}")
        console.print("  [dim]Skipping LLM test - set LLM_API_KEY to enable[/dim]")
        return None
    
    raw_result = await analyze_files(
        codebase_path=ctx.codebase_path,
        files=ctx.changed_files,
        llm=llm,
    )
    
    result = diff_filter.filter_analysis_result(raw_result)
    
    # Results table
    status = "[green]Success[/green]" if result.success else "[red]Failed[/red]"
    langs = ', '.join(result.languages) if result.languages else 'None'
    stats_data = {
        "Status": status,
        "Files analyzed": result.files_analyzed,
        "Languages": langs,
        "Total issues (all lines)": raw_result.total_issues,
        "Issues on diff lines": result.total_issues,
        "Filtered out": f"{raw_result.total_issues - result.total_issues} (not on changed lines)",
        "Memory issues": result.memory_issue_count,
        "Security issues": result.security_issue_count,
    }
    console.print(create_stats_table("Linter Results (Diff Lines Only)", stats_data))
    
    if result.issues_by_category:
        cat_table = Table(title="Issues by Category", box=box.SIMPLE)
        cat_table.add_column("Category", style="cyan")
        cat_table.add_column("Count", style="yellow")
        for cat, issues in result.issues_by_category.items():
            color = CATEGORY_COLORS.get(cat, "white")
            cat_table.add_row(f"[{color}]{cat}[/{color}]", str(len(issues)))
        console.print(cat_table)
    
    if result.issues:
        console.print(create_issues_table(result.issues, f"Linter Issues ({len(result.issues)})", max_rows=3))
    elif raw_result.issues:
        console.print(f"\n[dim]No linter issues on diff lines[/dim]")
    
    # LLM Insight Panel
    if result.insight:
        insight = result.insight
        
        # Quality score with color
        score = insight.quality_score
        score_color = "green" if score >= 7 else "yellow" if score >= 4 else "red"
        
        insight_content = f"[bold]Quality Score:[/bold] [{score_color}]{score}/10[/{score_color}]\n\n"
        insight_content += f"[bold]Summary:[/bold]\n{insight.summary}"
        
        console.print()
        console.print(Panel(insight_content, title="LLM Analysis Insight", 
                           title_align="left", border_style="green", box=box.ROUNDED))
        
        # Critical issues
        if insight.critical_issues:
            tree = Tree(f"[red bold]Critical Issues ({len(insight.critical_issues)})[/red bold]")
            for issue in insight.critical_issues:
                tree.add(f"[red]{issue}[/red]")
            console.print(tree)
        
        # Memory issues
        if insight.memory_issues:
            tree = Tree(f"[magenta bold]Memory Issues ({len(insight.memory_issues)})[/magenta bold]")
            for issue in insight.memory_issues:
                tree.add(f"[magenta]{issue}[/magenta]")
            console.print(tree)
        
        # Security issues
        if insight.security_issues:
            tree = Tree(f"[red bold]Security Issues ({len(insight.security_issues)})[/red bold]")
            for issue in insight.security_issues:
                tree.add(f"[red]{issue}[/red]")
            console.print(tree)
        
        # Recommendations
        if insight.recommendations:
            tree = Tree(f"[blue bold]Recommendations ({len(insight.recommendations)})[/blue bold]")
            for rec in insight.recommendations:
                tree.add(f"[blue]{rec}[/blue]")
            console.print(tree)
    else:
        console.print(f"\n[dim]No LLM insight generated[/dim]")
    
    if result.error:
        console.print(f"\n[red]Error: {result.error}[/red]")
    
    return result


async def test_convenience_function(ctx, diff_filter: DiffLineFilter):
    """Test the analyze_files convenience function."""
    print_section("Test 4: Convenience Function", "analyze_files() - Simple API")
    
    console.print(f"  [cyan]Scope:[/cyan] {len(ctx.changed_files)} PR-changed files")
    
    raw_result = await analyze_files(
        codebase_path=ctx.codebase_path,
        files=ctx.changed_files,
        llm=None,
    )
    
    result = diff_filter.filter_analysis_result(raw_result)
    
    # Results table
    status = "[green]Success[/green]" if result.success else "[red]Failed[/red]"
    langs = ', '.join(result.languages) if result.languages else 'None'
    stats_data = {
        "Status": status,
        "Result type": type(result).__name__,
        "Files analyzed": result.files_analyzed,
        "Languages": langs,
        "Total issues (all lines)": raw_result.total_issues,
        "Issues on diff lines": result.total_issues,
        "Filtered out": f"{raw_result.total_issues - result.total_issues} (not on changed lines)",
        "Memory issues": result.memory_issue_count,
        "Security issues": result.security_issue_count,
        "Has LLM insight": "Yes" if result.insight else "No",
    }
    console.print(create_stats_table("Results (Diff Lines Only)", stats_data))
    
    if result.issues_by_category:
        cat_table = Table(title="Issues by Category", box=box.SIMPLE)
        cat_table.add_column("Category", style="cyan")
        cat_table.add_column("Count", style="yellow")
        for cat, issues in result.issues_by_category.items():
            color = CATEGORY_COLORS.get(cat, "white")
            cat_table.add_row(f"[{color}]{cat}[/{color}]", str(len(issues)))
        console.print(cat_table)
    
    # Issues grouped by file
    if result.issues:
        issues_by_file: dict[str, list] = {}
        for issue in result.issues:
            issues_by_file.setdefault(issue.file, []).append(issue)
        
        tree = Tree(f"[bold]Issues by File ({len(result.issues)} total)[/bold]")
        for filepath, issues in list(issues_by_file.items())[:3]:
            file_branch = tree.add(f"[cyan]{filepath}[/cyan] ({len(issues)} issues)")
            for issue in issues[:2]:
                sev_color = SEVERITY_COLORS.get(issue.severity, "white")
                msg = issue.message[:50] + "..." if len(issue.message) > 50 else issue.message
                file_branch.add(f"L{issue.line}: [{sev_color}]{issue.rule}[/{sev_color}] - {msg}")
            if len(issues) > 2:
                file_branch.add(f"[dim]... and {len(issues) - 2} more[/dim]")
        if len(issues_by_file) > 3:
            tree.add(f"[dim]... and {len(issues_by_file) - 3} more files[/dim]")
        console.print(tree)
    elif raw_result.issues:
        console.print(f"\n[dim]No issues on diff lines (all {raw_result.total_issues} on unchanged lines)[/dim]")
    
    if result.error:
        console.print(f"\n[red]Error: {result.error}[/red]")
    
    return result


async def main():
    console.print()
    console.print(Panel.fit(
        "[bold blue]LangGraph SyntaxAnalysisAgent Test[/bold blue]\n"
        "[dim]2025 Patterns with Diff-Line Filtering[/dim]",
        border_style="blue"
    ))
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pr_folder = os.path.join(project_root, "pr_export", "Wise-Code-Watchers_sentry-wcw_PR3")
    
    # Language support
    loader = LanguagePromptLoader()
    console.print(f"\n[cyan]Supported Languages:[/cyan] {', '.join(loader.supported_languages())}")
    
    # Create diff filter
    diff_filter = create_diff_filter(pr_folder)
    diff_stats = diff_filter.get_stats()
    
    # Diff analysis table
    diff_table = Table(title="Diff Analysis", box=box.ROUNDED, title_style="bold")
    diff_table.add_column("File", style="cyan")
    diff_table.add_column("Changed Lines", style="green", justify="right")
    for filepath, line_count in list(diff_stats['files'].items())[:5]:
        diff_table.add_row(filepath, str(line_count))
    if len(diff_stats['files']) > 5:
        diff_table.add_row(f"[dim]... and {len(diff_stats['files']) - 5} more[/dim]", "")
    diff_table.add_row("[bold]Total[/bold]", f"[bold]{diff_stats['total_changed_lines']}[/bold]")
    console.print(diff_table)
    
    repo_manager = RepoManager()
    
    with repo_manager.prepare_for_analysis(pr_folder) as ctx:
        # PR Context panel
        pr_info = f"""[cyan]Repository:[/cyan] {ctx.repo_full_name}
[cyan]PR Number:[/cyan] #{ctx.pr_number}
[cyan]Codebase:[/cyan] {ctx.codebase_path}
[cyan]Changed Files:[/cyan] {len(ctx.changed_files)} total, {len(ctx.existing_changed_files)} existing

[yellow]NOTE:[/yellow] All linter checks are filtered to PR diff lines ONLY.
      Issues on unchanged lines within changed files are excluded."""
        
        console.print(Panel(pr_info, title="PR Context", border_style="cyan"))
        
        # Files tree
        if ctx.changed_files:
            tree = Tree("[bold]PR-changed files to analyze[/bold]")
            for f in ctx.changed_files[:10]:
                status = "[green](exists)[/green]" if f in ctx.existing_changed_files else "[red](deleted)[/red]"
                changed_lines = len(diff_filter.get_changed_lines(f))
                tree.add(f"{f} {status} [dim][{changed_lines} lines][/dim]")
            if len(ctx.changed_files) > 10:
                tree.add(f"[dim]... and {len(ctx.changed_files) - 10} more files[/dim]")
            console.print(tree)
        
        # Run tests
        await test_fixed_node(ctx, diff_filter)
        await test_langgraph_no_llm(ctx, diff_filter)
        await test_convenience_function(ctx, diff_filter)
        await test_langgraph_with_llm(ctx, diff_filter)
    
    console.print()
    console.print(Panel("[bold green]All Tests Complete[/bold green]", border_style="green"))


if __name__ == "__main__":
    asyncio.run(main())
