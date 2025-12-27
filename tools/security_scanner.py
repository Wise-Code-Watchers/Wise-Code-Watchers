import subprocess
import json
import os
import asyncio
import re
from typing import Optional

from tools.base import BaseTool, ToolResult


class SecurityScannerTool(BaseTool):
    name = "security_scanner"
    description = "Scan code for security vulnerabilities"

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path

    def is_available(self) -> bool:
        try:
            subprocess.run(
                ["bandit", "--version"],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    async def run(self, target: str, **kwargs) -> ToolResult:
        if not os.path.exists(target):
            return ToolResult(
                success=False,
                output="",
                error=f"Target path does not exist: {target}",
            )

        # Support scanning specific files only
        changed_files = kwargs.get("changed_files")
        
        language = kwargs.get("language", self._detect_language(target))

        if language == "python" and self.is_available():
            return await self._run_bandit(target, changed_files=changed_files)
        else:
            return await self._run_pattern_scan(target, changed_files=changed_files)

    def _detect_language(self, path: str) -> str:
        if os.path.isfile(path):
            if path.endswith(".py"):
                return "python"
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith(".py"):
                        return "python"
        return "unknown"

    async def _run_bandit(self, target: str, changed_files: list[str] = None) -> ToolResult:
        # If changed_files provided, only scan those files
        if changed_files:
            files_to_scan = []
            for f in changed_files:
                full_path = os.path.join(target, f)
                if os.path.exists(full_path) and f.endswith(".py"):
                    files_to_scan.append(full_path)
            
            if not files_to_scan:
                return ToolResult(
                    success=True,
                    output="No Python files to scan",
                    issues=[],
                    metadata={"tool": "bandit", "scoped": True},
                )
            
            cmd = ["bandit", "-f", "json"] + files_to_scan
        else:
            cmd = ["bandit", "-r", "-f", "json", target]
        
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
                results = json.loads(output) if output.strip() else {}
                for result in results.get("results", []):
                    issues.append({
                        "file": result.get("filename", ""),
                        "line": result.get("line_number", 0),
                        "severity": result.get("issue_severity", "").lower(),
                        "confidence": result.get("issue_confidence", "").lower(),
                        "message": result.get("issue_text", ""),
                        "rule": result.get("test_id", ""),
                        "cwe": result.get("issue_cwe", {}).get("id", ""),
                        "code_snippet": result.get("code", ""),
                    })
            except json.JSONDecodeError:
                pass

            return ToolResult(
                success=True,
                output=output,
                issues=issues,
                metadata={"tool": "bandit", "scoped": bool(changed_files)},
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _run_pattern_scan(self, target: str, changed_files: list[str] = None) -> ToolResult:
        issues = []

        security_patterns = [
            (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password detected", "critical", "CWE-259"),
            (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key detected", "critical", "CWE-798"),
            (r"secret\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret detected", "critical", "CWE-798"),
            (r"token\s*=\s*['\"][A-Za-z0-9]{20,}['\"]", "Possible hardcoded token", "high", "CWE-798"),
            (r"(?:os\.system|subprocess\.call)\s*\([^)]*\+", "Possible command injection", "critical", "CWE-78"),
            (r"eval\s*\(", "Use of eval() - potential code injection", "high", "CWE-94"),
            (r"exec\s*\(", "Use of exec() - potential code injection", "high", "CWE-94"),
            (r"pickle\.loads?\s*\(", "Unsafe deserialization with pickle", "critical", "CWE-502"),
            (r"yaml\.load\s*\([^)]*\)(?!.*Loader)", "Unsafe YAML loading", "high", "CWE-502"),
            (r"verify\s*=\s*False", "SSL verification disabled", "high", "CWE-295"),
            (r"hashlib\.md5\s*\(", "Weak hash function MD5", "medium", "CWE-328"),
            (r"hashlib\.sha1\s*\(", "Weak hash function SHA1", "medium", "CWE-328"),
            (r"chmod\s*\(\s*['\"]?\d*7\d*['\"]?\s*\)", "World-writable permissions", "medium", "CWE-732"),
            (r"debug\s*=\s*True", "Debug mode enabled", "low", "CWE-489"),
        ]

        def scan_file(filepath: str):
            file_issues = []
            try:
                with open(filepath, "r", errors="ignore") as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    for pattern, message, severity, cwe in security_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            file_issues.append({
                                "file": filepath,
                                "line": line_num,
                                "severity": severity,
                                "message": message,
                                "rule": f"pattern-{cwe}",
                                "cwe": cwe,
                                "code_snippet": line.strip()[:100],
                            })
            except Exception:
                pass
            return file_issues

        # If changed_files provided, only scan those files
        if changed_files:
            for f in changed_files:
                full_path = os.path.join(target, f)
                if os.path.exists(full_path) and f.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go")):
                    issues.extend(scan_file(full_path))
        elif os.path.isfile(target):
            issues.extend(scan_file(target))
        else:
            for root, _, files in os.walk(target):
                for file in files:
                    if file.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go")):
                        filepath = os.path.join(root, file)
                        issues.extend(scan_file(filepath))

        return ToolResult(
            success=True,
            output=f"Found {len(issues)} security issues",
            issues=issues,
            metadata={"tool": "pattern-scan", "scoped": bool(changed_files)},
        )
