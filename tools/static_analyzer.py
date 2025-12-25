import subprocess
import json
import os
import asyncio
from typing import Optional

from tools.base import BaseTool, ToolResult


class StaticAnalyzerTool(BaseTool):
    name = "static_analyzer"
    description = "Run static analysis to detect code quality issues and potential bugs"

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path

    def is_available(self) -> bool:
        try:
            subprocess.run(
                ["semgrep", "--version"],
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

        rules = kwargs.get("rules", ["p/default"])

        if self.is_available():
            return await self._run_semgrep(target, rules)
        else:
            return await self._run_basic_analysis(target)

    async def _run_semgrep(self, target: str, rules: list[str]) -> ToolResult:
        cmd = ["semgrep", "--json", "--config", ",".join(rules), target]
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
                        "file": result.get("path", ""),
                        "line": result.get("start", {}).get("line", 0),
                        "end_line": result.get("end", {}).get("line", 0),
                        "severity": self._map_semgrep_severity(result.get("extra", {}).get("severity", "")),
                        "message": result.get("extra", {}).get("message", ""),
                        "rule": result.get("check_id", ""),
                        "code_snippet": result.get("extra", {}).get("lines", ""),
                    })
            except json.JSONDecodeError:
                pass

            return ToolResult(
                success=True,
                output=output,
                issues=issues,
                metadata={"tool": "semgrep", "rules": rules},
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _run_basic_analysis(self, target: str) -> ToolResult:
        issues = []
        patterns = [
            (r"eval\s*\(", "Use of eval() is dangerous", "error"),
            (r"exec\s*\(", "Use of exec() is dangerous", "error"),
            (r"__import__\s*\(", "Dynamic import may be security risk", "warning"),
            (r"pickle\.loads?\s*\(", "Pickle deserialization is unsafe", "error"),
            (r"yaml\.load\s*\([^,]+\)(?!.*Loader)", "Use yaml.safe_load instead", "warning"),
            (r"subprocess\..*shell\s*=\s*True", "Shell=True in subprocess is dangerous", "warning"),
        ]

        import re
        for root, _, files in os.walk(target) if os.path.isdir(target) else [("", [], [target])]:
            for file in files:
                if not file.endswith(".py"):
                    continue
                filepath = os.path.join(root, file) if root else file
                try:
                    with open(filepath, "r") as f:
                        content = f.read()
                        lines = content.split("\n")

                    for line_num, line in enumerate(lines, 1):
                        for pattern, message, severity in patterns:
                            if re.search(pattern, line):
                                issues.append({
                                    "file": filepath,
                                    "line": line_num,
                                    "severity": severity,
                                    "message": message,
                                    "rule": "basic-analysis",
                                    "code_snippet": line.strip(),
                                })
                except Exception:
                    pass

        return ToolResult(
            success=True,
            output=f"Found {len(issues)} potential issues",
            issues=issues,
            metadata={"tool": "basic-analysis"},
        )

    def _map_semgrep_severity(self, severity: str) -> str:
        mapping = {
            "ERROR": "error",
            "WARNING": "warning",
            "INFO": "info",
        }
        return mapping.get(severity.upper(), "info")
