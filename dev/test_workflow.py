#!/usr/bin/env python3
"""
End-to-end test for the PR review workflow.

Workflow steps:
1. Export PRs as folders via the GitHub App (use existing pr_export data)
2. Clone the head branch (merged code) to a temporary folder (via RepoManager)
3. Determine modified files from PR info
4. Run syntax checks on the actual modified files
5. Print syntax detection results and detailed logs
"""

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.repo_manager import RepoManager, PRContext
from agents.syntax.syntax_checker import SyntaxChecker, print_syntax_report

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_separator(title: str):
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)


def init_syntax_checker():
    """Initialize syntax checker and show available linters."""
    print_separator("Step 0: Initialize Syntax Checker")
    
    checker = SyntaxChecker()
    available = checker.get_available_linters()
    
    print(f"Available linters: {list(available.keys()) if available else 'None'}")
    print(f"Supported languages: python, java, go, ruby, typescript")
    
    if not available:
        print("WARNING: No linters installed. Install ruff for Python: pip install ruff")
    
    return checker


def print_pr_context(ctx: PRContext):
    """Print PR context information."""
    print_separator("Step 1-2: PR Context (Clone via RepoManager)")
    
    print(f"PR #{ctx.pr_number}: {ctx.repo_full_name}")
    print(f"Head branch: {ctx.head_branch} (code to review)")
    print(f"Base branch: {ctx.base_branch} (merge target)")
    print(f"Codebase path: {ctx.codebase_path}")
    print(f"Changed files: {len(ctx.changed_files)}")
    
    existing = ctx.existing_changed_files
    print(f"Files found: {len(existing)}/{len(ctx.changed_files)}")
    
    for f in existing:
        full_path = ctx.get_full_path(f)
        size = os.path.getsize(full_path)
        print(f"  - {f} ({size} bytes)")


async def run_syntax_checks(checker: SyntaxChecker, ctx: PRContext):
    """Step 3: Run syntax checks on modified files (Fixed Node - No LLM)."""
    print_separator("Step 3: Syntax Check (Fixed Node)")
    
    changed_files = ctx.existing_changed_files
    print(f"Running syntax checker on {len(changed_files)} files...")
    
    result = await checker.check(ctx.codebase_path, changed_files)
    
    if result.files_by_language:
        print("\nFiles by language:")
        for lang, count in result.files_by_language.items():
            linter = checker._get_linter_for_language(lang)
            status = f"({linter})" if linter else "(no linter)"
            print(f"  {lang}: {count} files {status}")
    
    return result


def print_results(result, codebase_path: str):
    """Step 5: Print detailed results and logs."""
    print_separator("Step 5: Syntax Detection Results")
    
    if not result.success:
        print(f"Error: {result.error}")
        return
    
    if not result.issues:
        print("No syntax issues detected!")
        return
    
    print(f"Total issues found: {result.total_issues}\n")
    
    # Issues by severity
    if result.issues_by_severity:
        print("Issues by severity:")
        for severity in ["error", "warning", "info"]:
            count = result.issues_by_severity.get(severity, 0)
            if count:
                print(f"  {severity}: {count}")
    
    # Detailed issues by file
    print("\nDetailed issues by file:")
    for filepath, file_issues in result.issues_by_file.items():
        print(f"\n  {filepath} ({len(file_issues)} issues):")
        for issue in file_issues[:5]:
            print(f"    Line {issue.line}: [{issue.severity.upper()}] {issue.rule}")
            print(f"      {issue.message}")
        if len(file_issues) > 5:
            print(f"    ... and {len(file_issues) - 5} more issues in this file")


async def main():
    """Run the complete workflow test."""
    print_separator("PR Review Workflow Test")
    
    # Configuration
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pr_folder = os.path.join(project_root, "pr_export", "Wise-Code-Watchers_sentry-wcw_PR3")
    
    # Step 0: Initialize syntax checker
    checker = init_syntax_checker()
    
    # Steps 1-2: Clone repo via RepoManager (auto cleanup)
    repo_manager = RepoManager()
    
    with repo_manager.prepare_for_analysis(pr_folder) as ctx:
        # Print context info
        print_pr_context(ctx)
        
        if not ctx.existing_changed_files:
            print("ERROR: No modified files found in cloned repo")
            return
        
        # Step 3: Run syntax checks (Fixed Node - No LLM)
        result = await run_syntax_checks(checker, ctx)
        
        # Step 4: Print results
        print_results(result, ctx.codebase_path)
        
        # Summary
        print_separator("Workflow Test Complete")
        print(f"Summary:")
        print(f"  - PR: #{ctx.pr_number} ({ctx.head_branch})")
        print(f"  - Files in PR: {len(ctx.changed_files)}")
        print(f"  - Files analyzed: {result.files_analyzed}")
        print(f"  - Syntax issues found: {result.total_issues}")
        print(f"  - Implementation: Fixed Node (No LLM)")
    
    print("\nTemp directory cleaned up automatically by RepoManager")


if __name__ == "__main__":
    asyncio.run(main())
