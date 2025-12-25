import json
import os
import asyncio
from typing import Optional
from dataclasses import dataclass

from tools.base import BaseTool, ToolResult


# Memory/Resource leak related rules by linter
MEMORY_CHECK_RULES = {
    "ruff": {
        # Resource management rules
        "SIM115",  # Use context manager for opening files
        "B006",    # Mutable default argument
        "B008",    # Function call in default argument
        "PLR1711", # Useless return
        "PLW0602", # Global variable not assigned
        "PLW0603", # Global statement
        "S608",    # SQL injection
        "SIM105",  # Use contextlib.suppress
        "RUF013",  # Implicit Optional
    },
    "pylint": {
        "W1514",   # Using open without explicit encoding
        "W0612",   # Unused variable
        "W0611",   # Unused import  
        "R1732",   # Consider using with for resource-allocating operations
        "W1501",   # Bad open mode
        "E1111",   # Assigning result of function call where return is None
        "W0702",   # No exception type specified
        "R1705",   # Unnecessary else after return
    },
    "eslint": {
        "no-unused-vars",
        "no-undef",
        "react-hooks/exhaustive-deps",  # Uncleaned useEffect
        "no-async-promise-executor",
        "require-await",
        "no-return-await",
        "prefer-promise-reject-errors",
    },
    "golangci-lint": {
        "bodyclose",     # HTTP response body not closed
        "sqlclosecheck", # SQL rows/stmt not closed
        "rowserrcheck",  # SQL rows.Err() not checked
        "govet",         # Go vet checks
        "staticcheck",   # Static analysis
        "gosec",         # Security issues
        "ineffassign",   # Ineffectual assignments
        "unparam",       # Unused parameters
    },
    "rubocop": {
        "Lint/UselessAssignment",
        "Style/BlockDelimiters",  # Ensure blocks for resource management
        "Lint/SuppressedException",
        "Lint/UnusedBlockArgument",
        "Lint/UnusedMethodArgument",
    },
}


@dataclass
class LinterConfig:
    """Configuration for enhanced linting with memory checks."""
    enable_memory_checks: bool = True
    strict_mode: bool = False
    extra_rules: list = None
    
    def __post_init__(self):
        if self.extra_rules is None:
            self.extra_rules = []


class LinterTool(BaseTool):
    name = "linter"
    description = "Run linting tools to check code style, memory leaks, and resource issues"

    def __init__(self, config_path: Optional[str] = None, config: Optional[LinterConfig] = None):
        self.config_path = config_path
        self.config = config or LinterConfig()
        self._available_linters = self._detect_linters()

    def _detect_linters(self) -> dict[str, bool]:
        linters = {}
        linter_cmds = {
            "pylint": "pylint",
            "flake8": "flake8",
            "eslint": "eslint",
            "ruff": "ruff",
            "checkstyle": "checkstyle",
            "spotbugs": "spotbugs",  # Better for Java memory checks
            "golangci-lint": "golangci-lint",
            "rubocop": "rubocop",
        }
        for linter, cmd in linter_cmds.items():
            linters[linter] = self._find_executable(cmd) is not None
        return linters

    def _find_executable(self, name: str) -> Optional[str]:
        """Find executable in PATH or common venv locations."""
        import shutil
        import sys
        path = shutil.which(name)
        if path:
            return path
        venv_bin = os.path.dirname(sys.executable)
        venv_path = os.path.join(venv_bin, name)
        if os.path.isfile(venv_path) and os.access(venv_path, os.X_OK):
            return venv_path
        return None

    def is_available(self) -> bool:
        return any(self._available_linters.values())

    def get_available_linters(self) -> dict[str, bool]:
        """Return dict of available linters."""
        return {k: v for k, v in self._available_linters.items() if v}

    async def run(self, target: str, **kwargs) -> ToolResult:
        if not os.path.exists(target):
            return ToolResult(
                success=False,
                output="",
                error=f"Target path does not exist: {target}",
            )

        language = kwargs.get("language", self._detect_language(target))
        issues = []
        outputs = []

        if language == "python":
            if self._available_linters.get("ruff"):
                result = await self._run_ruff(target)
                issues.extend(result.issues)
                outputs.append(result.output)
            elif self._available_linters.get("pylint"):
                result = await self._run_pylint(target)
                issues.extend(result.issues)
                outputs.append(result.output)

        elif language == "javascript":
            if self._available_linters.get("eslint"):
                result = await self._run_eslint(target)
                issues.extend(result.issues)
                outputs.append(result.output)

        return ToolResult(
            success=True,
            output="\n".join(outputs),
            issues=issues,
            metadata={"language": language},
        )

    def _detect_language(self, path: str) -> str:
        if os.path.isfile(path):
            ext = os.path.splitext(path)[1]
            if ext in [".py"]:
                return "python"
            if ext in [".js", ".jsx", ".ts", ".tsx"]:
                return "typescript"
            if ext in [".java"]:
                return "java"
            if ext in [".go"]:
                return "go"
            if ext in [".rb"]:
                return "ruby"
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith(".py"):
                        return "python"
                    if file.endswith((".js", ".jsx", ".ts", ".tsx")):
                        return "typescript"
                    if file.endswith(".java"):
                        return "java"
                    if file.endswith(".go"):
                        return "go"
                    if file.endswith(".rb"):
                        return "ruby"
        return "unknown"

    async def run_on_files(self, files: list[str], language: str) -> ToolResult:
        """Run linter on specific files for a given language."""
        existing_files = [f for f in files if os.path.exists(f)]
        if not existing_files:
            return ToolResult(
                success=True,
                output="",
                issues=[],
                metadata={"language": language, "skipped": "no files found"},
            )

        if language == "python":
            if self._available_linters.get("ruff"):
                return await self._run_ruff_files(existing_files)
            elif self._available_linters.get("pylint"):
                return await self._run_pylint_files(existing_files)
        elif language == "typescript":
            if self._available_linters.get("eslint"):
                return await self._run_eslint_files(existing_files)
        elif language == "java":
            if self._available_linters.get("checkstyle"):
                return await self._run_checkstyle(existing_files)
        elif language == "go":
            if self._available_linters.get("golangci-lint"):
                return await self._run_golangci_lint(existing_files)
        elif language == "ruby":
            if self._available_linters.get("rubocop"):
                return await self._run_rubocop(existing_files)

        return ToolResult(
            success=True,
            output="",
            issues=[],
            metadata={"language": language, "skipped": "no linter available"},
        )

    async def _run_pylint(self, target: str) -> ToolResult:
        cmd = ["pylint", "--output-format=json", target]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode()

            issues = []
            try:
                results = json.loads(output) if output.strip() else []
                for item in results:
                    issues.append({
                        "file": item.get("path", ""),
                        "line": item.get("line", 0),
                        "column": item.get("column", 0),
                        "severity": self._map_pylint_severity(item.get("type", "")),
                        "message": item.get("message", ""),
                        "rule": item.get("symbol", ""),
                    })
            except json.JSONDecodeError:
                pass

            return ToolResult(success=True, output=output, issues=issues)

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _run_ruff(self, target: str) -> ToolResult:
        cmd = ["ruff", "check", "--output-format=json", target]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode()

            issues = []
            try:
                results = json.loads(output) if output.strip() else []
                for item in results:
                    issues.append({
                        "file": item.get("filename", ""),
                        "line": item.get("location", {}).get("row", 0),
                        "column": item.get("location", {}).get("column", 0),
                        "severity": "warning",
                        "message": item.get("message", ""),
                        "rule": item.get("code", ""),
                    })
            except json.JSONDecodeError:
                pass

            return ToolResult(success=True, output=output, issues=issues)

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _run_eslint(self, target: str) -> ToolResult:
        cmd = ["eslint", "--format=json", target]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode()

            issues = []
            try:
                results = json.loads(output) if output.strip() else []
                for file_result in results:
                    for msg in file_result.get("messages", []):
                        issues.append({
                            "file": file_result.get("filePath", ""),
                            "line": msg.get("line", 0),
                            "column": msg.get("column", 0),
                            "severity": "error" if msg.get("severity") == 2 else "warning",
                            "message": msg.get("message", ""),
                            "rule": msg.get("ruleId", ""),
                        })
            except json.JSONDecodeError:
                pass

            return ToolResult(success=True, output=output, issues=issues)

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    def _map_pylint_severity(self, pylint_type: str) -> str:
        mapping = {
            "error": "error",
            "fatal": "error",
            "warning": "warning",
            "convention": "info",
            "refactor": "info",
        }
        return mapping.get(pylint_type.lower(), "info")

    async def _run_ruff_files(self, files: list[str]) -> ToolResult:
        ruff_path = self._find_executable("ruff") or "ruff"
        cmd = [ruff_path, "check", "--output-format=json"]
        
        # Enable extended rules for memory/resource checking
        if self.config.enable_memory_checks:
            cmd.extend([
                "--select=E,F,W,B,SIM,PLR,PLW,S,RUF",  # Extended rule sets
                "--ignore=E501",  # Ignore line length
            ])
        
        cmd.extend(files)
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode()

            issues = []
            try:
                results = json.loads(output) if output.strip() else []
                for item in results:
                    rule_code = item.get("code", "")
                    issues.append({
                        "file": item.get("filename", ""),
                        "line": item.get("location", {}).get("row", 0),
                        "column": item.get("location", {}).get("column", 0),
                        "severity": self._get_ruff_severity(rule_code),
                        "message": item.get("message", ""),
                        "rule": rule_code,
                        "category": self._categorize_issue(rule_code, "ruff"),
                    })
            except json.JSONDecodeError:
                pass

            return ToolResult(success=True, output=output, issues=issues)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    def _get_ruff_severity(self, rule_code: str) -> str:
        """Map ruff rule codes to severity levels."""
        if rule_code.startswith(("E9", "F")):
            return "error"
        if rule_code.startswith(("B", "S", "PLW")):
            return "warning"
        return "info"

    def _categorize_issue(self, rule: str, linter: str) -> str:
        """Categorize issue as syntax, memory, security, or style."""
        memory_rules = MEMORY_CHECK_RULES.get(linter, set())
        
        # Check if rule is memory-related
        for mem_rule in memory_rules:
            if rule.startswith(mem_rule) or rule == mem_rule:
                return "memory"
        
        # Security rules by linter
        if linter == "ruff" and rule.startswith("S"):
            return "security"
        if linter == "golangci-lint" and rule == "gosec":
            return "security"
        if linter == "eslint" and rule in (
            "no-eval", "no-implied-eval", "no-new-func", "no-script-url"
        ):
            return "security"
        if linter == "eslint" and rule.startswith("security/"):
            return "security"
        if linter == "checkstyle" and any(
            x in rule for x in ("SQL", "XSS", "INJECTION", "XXE", "SSRF")
        ):
            return "security"
        if linter == "rubocop" and rule.startswith("Security"):
            return "security"
        
        # Syntax errors - be precise, not all E/F codes are syntax errors
        # Python (ruff/pylint)
        if linter == "ruff":
            # Only E9xx are actual runtime/syntax errors
            if rule.startswith("E9"):
                return "syntax"
            # Specific F codes that are true errors
            if rule in ("F821", "F822", "F823", "F831", "F632", "F633"):
                return "syntax"
        if linter == "pylint":
            # E codes in pylint are actual errors
            if rule.startswith("E"):
                return "syntax"
        
        # Go (golangci-lint)
        if linter == "golangci-lint" and rule in ("govet", "typecheck", "staticcheck"):
            return "syntax"
        
        # TypeScript/JavaScript (eslint)
        if linter == "eslint" and rule in (
            "no-undef", "no-unreachable", "no-dupe-keys", "no-dupe-args",
            "no-func-assign", "no-import-assign", "no-const-assign",
            "valid-typeof", "no-obj-calls", "no-invalid-regexp"
        ):
            return "syntax"
        
        # Java (checkstyle)
        if linter == "checkstyle" and rule == "compiler":
            return "syntax"
        
        # Ruby (rubocop)
        if linter == "rubocop" and rule.startswith("Lint/Syntax"):
            return "syntax"
        if linter == "rubocop" and rule in (
            "Lint/Void", "Lint/UnreachableCode", "Lint/DuplicateMethods"
        ):
            return "syntax"
        
        return "style"

    async def _run_pylint_files(self, files: list[str]) -> ToolResult:
        pylint_path = self._find_executable("pylint") or "pylint"
        cmd = [pylint_path, "--output-format=json"] + files
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode()

            issues = []
            try:
                results = json.loads(output) if output.strip() else []
                for item in results:
                    issues.append({
                        "file": item.get("path", ""),
                        "line": item.get("line", 0),
                        "column": item.get("column", 0),
                        "severity": self._map_pylint_severity(item.get("type", "")),
                        "message": item.get("message", ""),
                        "rule": item.get("symbol", ""),
                    })
            except json.JSONDecodeError:
                pass

            return ToolResult(success=True, output=output, issues=issues)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _run_eslint_files(self, files: list[str]) -> ToolResult:
        eslint_path = self._find_executable("eslint") or "eslint"
        cmd = [eslint_path, "--format=json"] + files
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode()

            issues = []
            try:
                results = json.loads(output) if output.strip() else []
                for file_result in results:
                    for msg in file_result.get("messages", []):
                        issues.append({
                            "file": file_result.get("filePath", ""),
                            "line": msg.get("line", 0),
                            "column": msg.get("column", 0),
                            "severity": "error" if msg.get("severity") == 2 else "warning",
                            "message": msg.get("message", ""),
                            "rule": msg.get("ruleId", ""),
                        })
            except json.JSONDecodeError:
                pass

            return ToolResult(success=True, output=output, issues=issues)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _run_checkstyle(self, files: list[str]) -> ToolResult:
        checkstyle_path = self._find_executable("checkstyle") or "checkstyle"
        cmd = [checkstyle_path, "-f", "json"] + files
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode()

            issues = []
            try:
                results = json.loads(output) if output.strip() else []
                for file_result in results:
                    filepath = file_result.get("filename", "")
                    for error in file_result.get("errors", []):
                        issues.append({
                            "file": filepath,
                            "line": error.get("line", 0),
                            "column": error.get("column", 0),
                            "severity": error.get("severity", "warning").lower(),
                            "message": error.get("message", ""),
                            "rule": error.get("source", ""),
                        })
            except json.JSONDecodeError:
                pass

            return ToolResult(success=True, output=output, issues=issues)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _run_golangci_lint(self, files: list[str]) -> ToolResult:
        golangci_path = self._find_executable("golangci-lint") or "golangci-lint"
        cmd = [golangci_path, "run", "--out-format=json"]
        
        # Enable memory/resource leak checking linters
        if self.config.enable_memory_checks:
            cmd.extend([
                "--enable=bodyclose",      # HTTP response body not closed
                "--enable=sqlclosecheck",  # SQL rows/stmt not closed
                "--enable=rowserrcheck",   # SQL rows.Err() not checked
                "--enable=gosec",          # Security issues
                "--enable=ineffassign",    # Ineffectual assignments
                "--enable=govet",          # Go vet checks
            ])
        
        cmd.append("--")
        cmd.extend(files)
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode()

            issues = []
            try:
                result = json.loads(output) if output.strip() else {}
                for item in result.get("Issues", []):
                    pos = item.get("Pos", {})
                    rule = item.get("FromLinter", "")
                    issues.append({
                        "file": pos.get("Filename", ""),
                        "line": pos.get("Line", 0),
                        "column": pos.get("Column", 0),
                        "severity": item.get("Severity", "warning"),
                        "message": item.get("Text", ""),
                        "rule": rule,
                        "category": self._categorize_issue(rule, "golangci-lint"),
                    })
            except json.JSONDecodeError:
                pass

            return ToolResult(success=True, output=output, issues=issues)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _run_rubocop(self, files: list[str]) -> ToolResult:
        rubocop_path = self._find_executable("rubocop") or "rubocop"
        cmd = [rubocop_path, "--format", "json"] + files
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode()

            issues = []
            try:
                result = json.loads(output) if output.strip() else {}
                for file_result in result.get("files", []):
                    filepath = file_result.get("path", "")
                    for offense in file_result.get("offenses", []):
                        loc = offense.get("location", {})
                        issues.append({
                            "file": filepath,
                            "line": loc.get("start_line", 0),
                            "column": loc.get("start_column", 0),
                            "severity": offense.get("severity", "warning"),
                            "message": offense.get("message", ""),
                            "rule": offense.get("cop_name", ""),
                        })
            except json.JSONDecodeError:
                pass

            return ToolResult(success=True, output=output, issues=issues)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
