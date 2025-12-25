"""
Syntax Analysis Agent - 2025 LangGraph Implementation

Uses LangGraph StateGraph for stateful workflow:
1. Lint node: Run deterministic linters (no hallucination)
2. Analyze node: LLM interprets results with structured output

Based on 2025 LangChain best practices:
- StateGraph with TypedDict state
- add_messages reducer for message handling
- Pydantic schemas for structured output
- @tool decorator for tool integration
"""

import os
import logging
from typing import Annotated, TypedDict, Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from agents.syntax.schemas import (
    CodeIssue,
    AnalysisInsight,
    SyntaxAnalysisResult,
)
from agents.syntax.prompts import LanguagePromptLoader
from tools.linter import LinterTool

logger = logging.getLogger(__name__)

LANG_EXTENSIONS = {
    "python": [".py"],
    "java": [".java"],
    "go": [".go"],
    "ruby": [".rb"],
    "typescript": [".ts", ".tsx"],
    "javascript": [".js", ".jsx"],
}


class AgentState(TypedDict):
    """State for the syntax analysis workflow."""
    messages: Annotated[list[BaseMessage], add_messages]
    codebase_path: str
    files_to_analyze: list[str]
    linter_issues: list[dict]
    languages_detected: list[str]
    structured_response: SyntaxAnalysisResult | None


def _detect_language(filepath: str) -> str | None:
    """Detect programming language from file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    for lang, extensions in LANG_EXTENSIONS.items():
        if ext in extensions:
            return lang
    return None


def _group_by_language(files: list[str]) -> dict[str, list[str]]:
    """Group files by detected programming language."""
    result: dict[str, list[str]] = {}
    for filepath in files:
        lang = _detect_language(filepath)
        if lang:
            if lang not in result:
                result[lang] = []
            result[lang].append(filepath)
    return result


def _categorize_issue(rule: str, language: str) -> str:
    """Categorize issue based on rule code using core_rules module."""
    from agents.syntax.core_rules import get_rule_category
    return get_rule_category(rule, language)


def create_lint_node(linter: LinterTool):
    """Create the lint node that runs deterministic linters."""
    
    async def lint_node(state: AgentState) -> dict[str, Any]:
        """Run linters on files - deterministic, no LLM."""
        codebase_path = state["codebase_path"]
        files = state["files_to_analyze"]
        
        full_paths = [
            os.path.join(codebase_path, f) for f in files
            if os.path.exists(os.path.join(codebase_path, f))
        ]
        
        if not full_paths:
            return {
                "linter_issues": [],
                "languages_detected": [],
                "messages": [HumanMessage(content="No files to analyze")],
            }
        
        files_by_lang = _group_by_language(full_paths)
        languages = list(files_by_lang.keys())
        
        logger.info(f"Linting {len(full_paths)} files across {len(languages)} languages")
        
        all_issues = []
        for lang, lang_files in files_by_lang.items():
            result = await linter.run_on_files(lang_files, language=lang)
            if result.success and result.issues:
                for issue in result.issues:
                    issue["language"] = lang
                    issue["category"] = _categorize_issue(
                        issue.get("rule", ""),
                        lang
                    )
                all_issues.extend(result.issues)
                logger.info(f"  {lang}: {len(result.issues)} issues")
        
        summary = f"Found {len(all_issues)} issues in {len(full_paths)} files"
        
        return {
            "linter_issues": all_issues,
            "languages_detected": languages,
            "messages": [HumanMessage(content=summary)],
        }
    
    return lint_node


def create_analyze_node(llm: BaseChatModel | None):
    """Create the analyze node that uses LLM for insights."""
    
    async def analyze_node(state: AgentState) -> dict[str, Any]:
        """Generate LLM insights from linter results."""
        issues = state["linter_issues"]
        languages = state["languages_detected"]
        files = state["files_to_analyze"]
        
        if not llm:
            result = SyntaxAnalysisResult(
                success=True,
                files_analyzed=len(files),
                languages=languages,
                total_issues=len(issues),
                issues=[CodeIssue(**i) for i in issues if _is_valid_issue(i)],
                insight=None,
            )
            return {"structured_response": result}
        
        try:
            prompt_loader = LanguagePromptLoader()
            primary_lang = languages[0] if languages else "python"
            
            system_prompt = prompt_loader.get_system_prompt(primary_lang)
            
            issues_summary = _format_issues_for_llm(issues[:50])
            
            structured_llm = llm.with_structured_output(AnalysisInsight)
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"""Analyze these linter results and provide insights:

Files analyzed: {len(files)}
Languages: {', '.join(languages)}
Total issues: {len(issues)}

Issues:
{issues_summary}

Provide a structured analysis with summary, critical issues, memory issues, security issues, recommendations, and quality score (1-10)."""),
            ]
            
            insight = await structured_llm.ainvoke(messages)
            
            result = SyntaxAnalysisResult(
                success=True,
                files_analyzed=len(files),
                languages=languages,
                total_issues=len(issues),
                issues=[CodeIssue(**i) for i in issues if _is_valid_issue(i)],
                insight=insight,
            )
            
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")
            result = SyntaxAnalysisResult(
                success=True,
                files_analyzed=len(files),
                languages=languages,
                total_issues=len(issues),
                issues=[CodeIssue(**i) for i in issues if _is_valid_issue(i)],
                insight=None,
                error=str(e),
            )
        
        return {"structured_response": result}
    
    return analyze_node


def _is_valid_issue(issue: dict) -> bool:
    """Check if issue dict has required fields for CodeIssue."""
    return all(k in issue for k in ["file", "line", "rule", "message"])


def _format_issues_for_llm(issues: list[dict]) -> str:
    """Format issues for LLM consumption."""
    lines = []
    for i in issues:
        cat = i.get("category", "style")
        lines.append(
            f"[{cat.upper()}] {i.get('file', '?')}:{i.get('line', '?')} "
            f"[{i.get('rule', '?')}] {i.get('message', '')[:100]}"
        )
    return "\n".join(lines)


def create_syntax_agent(
    llm: BaseChatModel | None = None,
    linter: LinterTool | None = None,
) -> StateGraph:
    """
    Create a syntax analysis agent using LangGraph.
    
    Args:
        llm: Language model for generating insights (optional)
        linter: Linter tool instance (created if not provided)
        
    Returns:
        Compiled StateGraph agent
        
    Example:
        ```python
        from langchain_anthropic import ChatAnthropic
        
        llm = ChatAnthropic(model="claude-sonnet-4-20250514")
        agent = create_syntax_agent(llm)
        
        result = await agent.ainvoke({
            "messages": [],
            "codebase_path": "/path/to/repo",
            "files_to_analyze": ["src/app.py"],
            "linter_issues": [],
            "languages_detected": [],
            "structured_response": None,
        })
        
        analysis = result["structured_response"]
        print(f"Found {analysis.total_issues} issues")
        if analysis.insight:
            print(f"Quality score: {analysis.insight.quality_score}/10")
        ```
    """
    if linter is None:
        linter = LinterTool()
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("lint", create_lint_node(linter))
    workflow.add_node("analyze", create_analyze_node(llm))
    
    workflow.set_entry_point("lint")
    workflow.add_edge("lint", "analyze")
    workflow.add_edge("analyze", END)
    
    return workflow.compile()


async def analyze_files(
    codebase_path: str,
    files: list[str],
    llm: BaseChatModel | None = None,
) -> SyntaxAnalysisResult:
    """
    Convenience function to analyze files.
    
    Args:
        codebase_path: Root path of the codebase
        files: List of files to analyze (relative paths)
        llm: Optional LLM for insights
        
    Returns:
        SyntaxAnalysisResult with issues and optional insights
    """
    agent = create_syntax_agent(llm)
    
    result = await agent.ainvoke({
        "messages": [],
        "codebase_path": codebase_path,
        "files_to_analyze": files,
        "linter_issues": [],
        "languages_detected": [],
        "structured_response": None,
    })
    
    return result["structured_response"]


def print_analysis_report(result: SyntaxAnalysisResult):
    """Print formatted analysis report."""
    print(f"\n{'='*60}")
    print(" Syntax Analysis Report (LangGraph 2025)")
    print('='*60)

    if not result.success:
        print(f"\nError: {result.error}")
        return

    print(f"\nFiles analyzed: {result.files_analyzed}")
    print(f"Languages: {', '.join(result.languages)}")
    print(f"\nTotal issues: {result.total_issues}")
    print(f"  - Memory issues: {result.memory_issue_count}")
    print(f"  - Security issues: {result.security_issue_count}")

    if result.insight:
        print(f"\n--- LLM Analysis (Quality: {result.insight.quality_score}/10) ---")
        print(result.insight.summary)
        
        if result.insight.critical_issues:
            print(f"\nCritical Issues:")
            for issue in result.insight.critical_issues[:3]:
                print(f"  - {issue}")
        
        if result.insight.recommendations:
            print(f"\nRecommendations:")
            for rec in result.insight.recommendations[:3]:
                print(f"  - {rec}")

    if result.issues:
        print(f"\n--- Sample Issues ---")
        for issue in result.issues[:5]:
            print(f"  {issue.file}:{issue.line} [{issue.rule}]")
            print(f"    {issue.message[:80]}")

    print(f"\n{'='*60}")
