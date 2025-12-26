import json
import re
import os
from typing import Optional

from langchain_core.language_models import BaseChatModel

from src.agents.base import BaseAgent, AgentResult
from src.knowledge.code_patterns_kb import CodePatternsKB
from src.tools.linter import LinterTool
from src.output.models import Bug, BugType, Severity, StructureAnalysis

LANG_EXTENSIONS = {
    "python": [".py"],
    "java": [".java"],
    "go": [".go"],
    "ruby": [".rb"],
    "typescript": [".ts", ".tsx", ".js", ".jsx"],
}


class SyntaxStructureAgent(BaseAgent):
    name = "syntax_structure_agent"
    description = "Analyzes code structure, AST, and syntax correctness"

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        code_patterns_kb: Optional[CodePatternsKB] = None,
        linter: Optional[LinterTool] = None,
        verbose: bool = False,
    ):
        super().__init__(llm, verbose)
        self.code_patterns_kb = code_patterns_kb or CodePatternsKB()
        self.linter = linter or LinterTool()
        self.add_knowledge_base(self.code_patterns_kb)
        self.add_tool(self.linter)

        self.prompt = self._create_prompt(
            system_message="""You are a code structure analyzer. Analyze the provided code for:
1. Syntax issues and errors
2. Code structure problems (deep nesting, long functions, god classes)
3. Anti-patterns related to code organization
4. Complexity issues

Use the linter results and knowledge base patterns to inform your analysis.

Respond in JSON format:
{{
    "issues": [
        {{
            "title": "short title",
            "description": "detailed description",
            "file": "filename",
            "line": line_number,
            "severity": "low|medium|high|critical",
            "type": "syntax_error|style_violation"
        }}
    ],
    "summary": "overall assessment",
    "metrics": {{
        "files_analyzed": number,
        "total_issues": number,
        "complexity_score": number
    }}
}}""",
            human_message="""Analyze the following code structure:

Files changed:
{files_info}

Linter results:
{linter_results}

Relevant patterns from knowledge base:
{kb_patterns}

Code snippets:
{code_snippets}

Provide your structural analysis.""",
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

            files_by_lang = self._group_by_language(files_to_analyze)

            linter_issues = []
            for lang, files in files_by_lang.items():
                if files:
                    result = await self.linter.run_on_files(files, language=lang)
                    if result.success and result.issues:
                        linter_issues.extend(result.issues)

            kb_patterns = self._query_knowledge_bases("structure complexity nesting")

            code_snippets = self._extract_code_snippets(files_to_analyze[:5])

            files_info = "\n".join([f"- {f}" for f in files_to_analyze[:20]])
            if len(files_to_analyze) > 20:
                files_info += f"\n... and {len(files_to_analyze) - 20} more files"

            chain = self.prompt | self.llm
            response = await chain.ainvoke({
                "files_info": files_info,
                "linter_results": json.dumps(linter_issues[:20], indent=2),
                "kb_patterns": json.dumps(kb_patterns[:5], indent=2),
                "code_snippets": code_snippets,
            })

            result = self._parse_response(response.content, linter_issues)

            return AgentResult(
                agent_name=self.name,
                success=True,
                issues=[self._bug_to_dict(bug) for bug in result.issues],
                summary=result.summary,
                metrics=result.metrics,
            )

        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                success=False,
                error=str(e),
            )

    def _group_by_language(self, files: list[str]) -> dict[str, list[str]]:
        """Group files by their detected language."""
        result = {lang: [] for lang in LANG_EXTENSIONS}
        for filepath in files:
            ext = os.path.splitext(filepath)[1].lower()
            for lang, extensions in LANG_EXTENSIONS.items():
                if ext in extensions:
                    result[lang].append(filepath)
                    break
        return result

    def _get_source_files(self, path: str) -> list[str]:
        source_files = []
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb"}
        for root, _, files in os.walk(path):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    source_files.append(os.path.join(root, file))
        return source_files

    def _extract_code_snippets(self, files: list[str], max_lines: int = 50) -> str:
        snippets = []
        for filepath in files:
            try:
                with open(filepath, "r") as f:
                    content = f.read()
                    lines = content.split("\n")[:max_lines]
                    snippets.append(f"=== {filepath} ===\n" + "\n".join(lines))
            except Exception:
                pass
        return "\n\n".join(snippets[:3])

    def _parse_response(self, content: str, linter_issues: list[dict]) -> StructureAnalysis:
        issues = []

        for li in linter_issues:
            if li.get("severity") in ["error", "warning"]:
                issues.append(Bug(
                    id=f"lint-{li.get('line', 0)}",
                    type=BugType.SYNTAX_ERROR if li.get("severity") == "error" else BugType.STYLE_VIOLATION,
                    severity=Severity.MEDIUM if li.get("severity") == "error" else Severity.LOW,
                    title=li.get("rule", "Linter issue"),
                    description=li.get("message", ""),
                    file=li.get("file", ""),
                    line=li.get("line", 0),
                ))

        try:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(content)

            for issue_data in result.get("issues", []):
                issues.append(Bug(
                    id=f"struct-{len(issues)}",
                    type=BugType.SYNTAX_ERROR if issue_data.get("type") == "syntax_error" else BugType.STYLE_VIOLATION,
                    severity=self._map_severity(issue_data.get("severity", "low")),
                    title=issue_data.get("title", ""),
                    description=issue_data.get("description", ""),
                    file=issue_data.get("file", ""),
                    line=issue_data.get("line", 0),
                ))

            return StructureAnalysis(
                issues=issues,
                summary=result.get("summary", ""),
                metrics=result.get("metrics", {}),
            )

        except json.JSONDecodeError:
            return StructureAnalysis(
                issues=issues,
                summary="Analysis completed with linter results",
                metrics={"linter_issues": len(linter_issues)},
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
