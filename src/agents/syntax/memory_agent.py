import json
import re
import os
from typing import Optional

from langchain_openai import ChatOpenAI

from src.agents.base import BaseAgent, AgentResult
from src.knowledge.best_practices_kb import BestPracticesKB
from src.tools.linter import LinterTool
from src.output.models import Bug, BugType, Severity, MemoryAnalysis


class MemoryAnalysisAgent(BaseAgent):
    name = "memory_analysis_agent"
    description = "Analyzes code context, variable lifecycle, and memory patterns"

    def __init__(
        self,
        llm: Optional[ChatOpenAI] = None,
        best_practices_kb: Optional[BestPracticesKB] = None,
        linter: Optional[LinterTool] = None,
        verbose: bool = False,
    ):
        super().__init__(llm, verbose)
        self.best_practices_kb = best_practices_kb or BestPracticesKB()
        self.linter = linter or LinterTool()
        self.add_knowledge_base(self.best_practices_kb)
        self.add_tool(self.linter)

        self.prompt = self._create_prompt(
            system_message="""You are a memory and context analyzer. Analyze the provided code for:
1. Variable lifecycle issues (unused variables, scope problems)
2. Resource management (unclosed files, connections, memory leaks)
3. Context manager usage (proper with statements)
4. Circular references and memory retention issues
5. Global state management problems

Use best practices knowledge to inform your analysis.

Respond in JSON format:
{{
    "issues": [
        {{
            "title": "short title",
            "description": "detailed description",
            "file": "filename",
            "line": line_number,
            "severity": "low|medium|high|critical",
            "pattern": "pattern name if applicable"
        }}
    ],
    "summary": "overall assessment",
    "patterns_found": ["list of patterns detected"]
}}""",
            human_message="""Analyze the following code for memory and context issues:

Changed files:
{files_info}

Code snippets:
{code_snippets}

Best practices reference:
{best_practices}

Provide your memory and context analysis.""",
        )

    async def analyze(
        self,
        codebase_path: str,
        changed_files: list[str] = None,
        **kwargs,
    ) -> AgentResult:
        try:
            if changed_files:
                files_to_analyze = [
                    os.path.join(codebase_path, f) for f in changed_files
                    if os.path.exists(os.path.join(codebase_path, f))
                ]
            else:
                files_to_analyze = self._get_source_files(codebase_path)

            best_practices = self._query_knowledge_bases("resource management context memory")

            code_snippets = self._extract_relevant_code(files_to_analyze[:5])

            basic_issues = self._run_basic_memory_analysis(files_to_analyze)

            files_info = "\n".join([f"- {f}" for f in files_to_analyze[:20]])

            chain = self.prompt | self.llm
            response = await chain.ainvoke({
                "files_info": files_info,
                "code_snippets": code_snippets,
                "best_practices": json.dumps(best_practices[:5], indent=2),
            })

            result = self._parse_response(response.content, basic_issues)

            return AgentResult(
                agent_name=self.name,
                success=True,
                issues=[self._bug_to_dict(bug) for bug in result.issues],
                summary=result.summary,
                metrics={"patterns_found": result.patterns_found},
            )

        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(e),
            )

    def _get_source_files(self, path: str) -> list[str]:
        source_files = []
        extensions = {".py", ".js", ".ts", ".java", ".go"}
        for root, _, files in os.walk(path):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    source_files.append(os.path.join(root, file))
        return source_files

    def _extract_relevant_code(self, files: list[str]) -> str:
        snippets = []
        patterns_to_find = [
            r"open\s*\(",
            r"connect\s*\(",
            r"with\s+",
            r"global\s+",
            r"__del__",
            r"\.close\s*\(",
        ]

        for filepath in files:
            try:
                with open(filepath, "r") as f:
                    lines = f.readlines()

                relevant_lines = []
                for i, line in enumerate(lines):
                    for pattern in patterns_to_find:
                        if re.search(pattern, line):
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            context = lines[start:end]
                            relevant_lines.append(f"Lines {start+1}-{end}:\n{''.join(context)}")
                            break

                if relevant_lines:
                    snippets.append(f"=== {filepath} ===\n" + "\n".join(relevant_lines[:3]))

            except Exception:
                pass

        return "\n\n".join(snippets[:5]) or "No relevant patterns found in code"

    def _run_basic_memory_analysis(self, files: list[str]) -> list[Bug]:
        issues = []

        memory_patterns = [
            (r"open\s*\([^)]+\)(?!\s*as\s)", "File opened without context manager", BugType.MEMORY_ISSUE, Severity.MEDIUM),
            (r"\.connect\s*\([^)]+\)(?!\s*as\s)", "Connection opened without context manager", BugType.MEMORY_ISSUE, Severity.MEDIUM),
            (r"global\s+\w+", "Global variable usage detected", BugType.STYLE_VIOLATION, Severity.LOW),
            (r"\bself\.\w+\s*=\s*\[\].*#.*cache", "Potential unbounded cache", BugType.MEMORY_ISSUE, Severity.MEDIUM),
        ]

        for filepath in files:
            try:
                with open(filepath, "r") as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    for pattern, message, bug_type, severity in memory_patterns:
                        if re.search(pattern, line):
                            issues.append(Bug(
                                id=f"mem-{filepath}-{line_num}",
                                type=bug_type,
                                severity=severity,
                                title=message,
                                description=f"Found pattern: {line.strip()[:50]}",
                                file=filepath,
                                line=line_num,
                            ))
            except Exception:
                pass

        return issues

    def _parse_response(self, content: str, basic_issues: list[Bug]) -> MemoryAnalysis:
        issues = list(basic_issues)
        patterns_found = []

        try:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(content)

            for issue_data in result.get("issues", []):
                issues.append(Bug(
                    id=f"mem-llm-{len(issues)}",
                    type=BugType.MEMORY_ISSUE,
                    severity=self._map_severity(issue_data.get("severity", "low")),
                    title=issue_data.get("title", ""),
                    description=issue_data.get("description", ""),
                    file=issue_data.get("file", ""),
                    line=issue_data.get("line", 0),
                ))

            patterns_found = result.get("patterns_found", [])

            return MemoryAnalysis(
                issues=issues,
                summary=result.get("summary", ""),
                patterns_found=patterns_found,
            )

        except json.JSONDecodeError:
            return MemoryAnalysis(
                issues=issues,
                summary="Basic memory analysis completed",
                patterns_found=[],
            )

    def _map_severity(self, severity: str) -> Severity:
        mapping = {
            "low": Severity.LOW,
            "medium": Severity.MEDIUM,
            "high": Severity.HIGH,
            "critical": Severity.CRITICAL,
        }
        return mapping.get(severity.lower(), Severity.LOW)

    def _bug_to_dict(self, bug: Bug) -> dict:
        return {
            "id": bug.id,
            "type": bug.type.value,
            "severity": bug.severity.value,
            "title": bug.title,
            "description": bug.description,
            "file": bug.file,
            "line": bug.line,
        }
