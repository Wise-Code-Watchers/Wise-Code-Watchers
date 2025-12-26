"""
Syntax Checker - Fixed Node Implementation

A deterministic syntax checking node that runs linters on modified files
without requiring LLM agent. Faster, cheaper, and more reliable for
pure syntax/style checking.

Enhanced with memory/resource leak detection capabilities.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional

from src.tools.linter import LinterTool, LinterConfig

logger = logging.getLogger(__name__)

LANG_EXTENSIONS = {
    "python": [".py"],
    "java": [".java"],
    "go": [".go"],
    "ruby": [".rb"],
    "typescript": [".ts", ".tsx", ".js", ".jsx"],
}

# Issue categories
CATEGORY_SYNTAX = "syntax"
CATEGORY_MEMORY = "memory"
CATEGORY_SECURITY = "security"
CATEGORY_STYLE = "style"


@dataclass
class SyntaxIssue:
    file: str
    line: int
    column: int
    severity: str
    message: str
    rule: str
    language: str
    category: str = "style"  # syntax, memory, security, style


@dataclass
class SyntaxCheckResult:
    success: bool
    issues: list[SyntaxIssue] = field(default_factory=list)
    files_analyzed: int = 0
    files_by_language: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def total_issues(self) -> int:
        return len(self.issues)

    @property
    def issues_by_severity(self) -> dict[str, int]:
        counts = {}
        for issue in self.issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
        return counts

    @property
    def issues_by_file(self) -> dict[str, list[SyntaxIssue]]:
        by_file = {}
        for issue in self.issues:
            by_file.setdefault(issue.file, []).append(issue)
        return by_file

    @property
    def issues_by_category(self) -> dict[str, list[SyntaxIssue]]:
        """Group issues by category (syntax, memory, security, style)."""
        by_category = {}
        for issue in self.issues:
            by_category.setdefault(issue.category, []).append(issue)
        return by_category

    @property
    def memory_issues(self) -> list[SyntaxIssue]:
        """Get only memory/resource leak related issues."""
        return [i for i in self.issues if i.category == CATEGORY_MEMORY]

    @property
    def security_issues(self) -> list[SyntaxIssue]:
        """Get only security related issues."""
        return [i for i in self.issues if i.category == CATEGORY_SECURITY]

    @property
    def syntax_errors(self) -> list[SyntaxIssue]:
        """Get only syntax error issues."""
        return [i for i in self.issues if i.category == CATEGORY_SYNTAX]
    
    @property
    def core_issues(self) -> list[SyntaxIssue]:
        """Get only core issues (syntax, memory, security) - excludes style."""
        return [i for i in self.issues if i.category in (CATEGORY_SYNTAX, CATEGORY_MEMORY, CATEGORY_SECURITY)]

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "total_issues": self.total_issues,
            "files_analyzed": self.files_analyzed,
            "files_by_language": self.files_by_language,
            "issues_by_severity": self.issues_by_severity,
            "issues": [
                {
                    "file": i.file,
                    "line": i.line,
                    "column": i.column,
                    "severity": i.severity,
                    "message": i.message,
                    "rule": i.rule,
                    "language": i.language,
                }
                for i in self.issues
            ],
            "error": self.error,
        }


class SyntaxChecker:
    """
    Fixed node for syntax checking - no LLM required.
    
    Runs language-specific linters on modified files and returns
    structured results. Deterministic and fast.
    
    Enhanced with memory/resource leak detection when enable_memory_checks=True.
    """

    def __init__(
        self,
        linter: Optional[LinterTool] = None,
        enable_memory_checks: bool = True,
        strict_mode: bool = False,
    ):
        config = LinterConfig(
            enable_memory_checks=enable_memory_checks,
            strict_mode=strict_mode,
        )
        self.linter = linter or LinterTool(config=config)
        self._available_linters = self.linter._available_linters
        self.enable_memory_checks = enable_memory_checks

    def get_available_linters(self) -> dict[str, bool]:
        return {k: v for k, v in self._available_linters.items() if v}

    def _group_by_language(self, files: list[str]) -> dict[str, list[str]]:
        """Group files by their detected language."""
        result = {lang: [] for lang in LANG_EXTENSIONS}
        for filepath in files:
            ext = os.path.splitext(filepath)[1].lower()
            for lang, extensions in LANG_EXTENSIONS.items():
                if ext in extensions:
                    result[lang].append(filepath)
                    break
        return {k: v for k, v in result.items() if v}

    def _get_linter_for_language(self, lang: str) -> Optional[str]:
        """Get the linter name for a language."""
        lang_to_linter = {
            "python": "ruff",
            "typescript": "eslint",
            "java": "checkstyle",
            "go": "golangci-lint",
            "ruby": "rubocop",
        }
        linter_name = lang_to_linter.get(lang)
        if linter_name and self._available_linters.get(linter_name):
            return linter_name
        return None

    async def check(
        self,
        codebase_path: str,
        changed_files: list[str],
    ) -> SyntaxCheckResult:
        """
        Run syntax checks on the specified files.
        
        Args:
            codebase_path: Root path of the codebase
            changed_files: List of file paths relative to codebase_path
            
        Returns:
            SyntaxCheckResult with all found issues
        """
        try:
            # Build full paths and filter existing files
            full_paths = []
            for f in changed_files:
                full_path = os.path.join(codebase_path, f)
                if os.path.exists(full_path):
                    full_paths.append(full_path)

            if not full_paths:
                return SyntaxCheckResult(
                    success=True,
                    files_analyzed=0,
                    error="No files to analyze",
                )

            # Group by language
            files_by_lang = self._group_by_language(full_paths)
            
            logger.info(f"Checking {len(full_paths)} files across {len(files_by_lang)} languages")

            all_issues = []
            files_analyzed_by_lang = {}

            # Run linters per language
            for lang, files in files_by_lang.items():
                linter_name = self._get_linter_for_language(lang)
                files_analyzed_by_lang[lang] = len(files)

                if not linter_name:
                    logger.warning(f"No linter available for {lang}, skipping {len(files)} files")
                    continue

                logger.info(f"Running {linter_name} on {len(files)} {lang} files")
                
                result = await self.linter.run_on_files(files, language=lang)
                
                if result.success and result.issues:
                    for issue in result.issues:
                        # Make file path relative for cleaner output
                        file_path = issue.get("file", "")
                        if file_path.startswith(codebase_path):
                            file_path = os.path.relpath(file_path, codebase_path)
                        
                        all_issues.append(SyntaxIssue(
                            file=file_path,
                            line=issue.get("line", 0),
                            column=issue.get("column", 0),
                            severity=issue.get("severity", "warning"),
                            message=issue.get("message", ""),
                            rule=issue.get("rule", ""),
                            language=lang,
                            category=issue.get("category", "style"),
                        ))
                    
                    logger.info(f"  Found {len(result.issues)} issues in {lang} files")
                elif not result.success:
                    logger.error(f"  Linter error for {lang}: {result.error}")

            return SyntaxCheckResult(
                success=True,
                issues=all_issues,
                files_analyzed=len(full_paths),
                files_by_language=files_analyzed_by_lang,
            )

        except Exception as e:
            logger.exception("Syntax check failed")
            return SyntaxCheckResult(
                success=False,
                error=str(e),
            )

    async def check_files(self, files: list[str]) -> SyntaxCheckResult:
        """
        Run syntax checks on files with absolute paths.
        
        Args:
            files: List of absolute file paths
            
        Returns:
            SyntaxCheckResult with all found issues
        """
        existing_files = [f for f in files if os.path.exists(f)]
        
        if not existing_files:
            return SyntaxCheckResult(
                success=True,
                files_analyzed=0,
                error="No files to analyze",
            )

        files_by_lang = self._group_by_language(existing_files)
        
        all_issues = []
        files_analyzed_by_lang = {}

        for lang, lang_files in files_by_lang.items():
            linter_name = self._get_linter_for_language(lang)
            files_analyzed_by_lang[lang] = len(lang_files)

            if not linter_name:
                continue

            result = await self.linter.run_on_files(lang_files, language=lang)
            
            if result.success and result.issues:
                for issue in result.issues:
                    all_issues.append(SyntaxIssue(
                        file=issue.get("file", ""),
                        line=issue.get("line", 0),
                        column=issue.get("column", 0),
                        severity=issue.get("severity", "warning"),
                        message=issue.get("message", ""),
                        rule=issue.get("rule", ""),
                        language=lang,
                    ))

        return SyntaxCheckResult(
            success=True,
            issues=all_issues,
            files_analyzed=len(existing_files),
            files_by_language=files_analyzed_by_lang,
        )


def print_syntax_report(result: SyntaxCheckResult, verbose: bool = False):
    """Print a formatted syntax check report."""
    print(f"\n{'='*60}")
    print(" Syntax Check Report (with Memory/Resource Analysis)")
    print('='*60)
    
    if not result.success:
        print(f"\nError: {result.error}")
        return
    
    print(f"\nFiles analyzed: {result.files_analyzed}")
    if result.files_by_language:
        for lang, count in result.files_by_language.items():
            print(f"  - {lang}: {count} files")
    
    print(f"\nTotal issues: {result.total_issues}")
    
    # Show issues by category
    by_category = result.issues_by_category
    if by_category:
        print("\nIssues by category:")
        category_icons = {
            "syntax": "!",
            "memory": "M",
            "security": "S", 
            "style": "-",
        }
        for cat in ["syntax", "memory", "security", "style"]:
            count = len(by_category.get(cat, []))
            if count:
                icon = category_icons.get(cat, "-")
                print(f"  [{icon}] {cat}: {count}")
    
    # Show issues by severity
    if result.issues_by_severity:
        print("\nIssues by severity:")
        for severity in ["error", "warning", "info"]:
            count = result.issues_by_severity.get(severity, 0)
            if count:
                print(f"  - {severity}: {count}")
    
    # Highlight memory issues specifically
    memory_issues = result.memory_issues
    if memory_issues:
        print(f"\n*** Memory/Resource Issues ({len(memory_issues)}) ***")
        for issue in memory_issues[:5]:
            print(f"  {issue.file}:{issue.line} [{issue.rule}]")
            print(f"    {issue.message}")
        if len(memory_issues) > 5:
            print(f"  ... and {len(memory_issues) - 5} more memory issues")
    
    # Highlight security issues
    security_issues = result.security_issues
    if security_issues:
        print(f"\n*** Security Issues ({len(security_issues)}) ***")
        for issue in security_issues[:5]:
            print(f"  {issue.file}:{issue.line} [{issue.rule}]")
            print(f"    {issue.message}")
        if len(security_issues) > 5:
            print(f"  ... and {len(security_issues) - 5} more security issues")
    
    if result.issues and verbose:
        print("\nAll issues by file:")
        for filepath, issues in result.issues_by_file.items():
            print(f"\n  {filepath} ({len(issues)} issues):")
            for issue in issues[:10]:
                cat_icon = {"memory": "M", "security": "S", "syntax": "!", "style": "-"}.get(issue.category, "-")
                print(f"    Line {issue.line}: [{cat_icon}][{issue.severity.upper()}] {issue.rule}")
                print(f"      {issue.message}")
            if len(issues) > 10:
                print(f"    ... and {len(issues) - 10} more")
    elif result.issues and not memory_issues and not security_issues:
        print("\nRun with verbose=True for detailed issues")
    
    print(f"\n{'='*60}")
