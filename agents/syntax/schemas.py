"""
Pydantic schemas for structured output in syntax analysis.

Following 2025 LangChain best practices for structured output:
- Use Pydantic BaseModel for schema definition
- Use Field with descriptions for LLM guidance
- Validate output automatically
"""

from typing import Literal
from pydantic import BaseModel, Field


class CodeIssue(BaseModel):
    """A single code issue found by linter or analysis."""
    
    file: str = Field(description="File path where issue was found")
    line: int = Field(description="Line number of the issue")
    column: int = Field(default=0, description="Column number (0 if unknown)")
    rule: str = Field(description="Rule code (e.g., E501, S101)")
    message: str = Field(description="Human-readable issue description")
    severity: Literal["error", "warning", "info"] = Field(
        default="warning",
        description="Issue severity level"
    )
    category: Literal["syntax", "memory", "security", "style", "performance", "unknown"] = Field(
        default="unknown",
        description="Issue category for grouping. 'unknown' means rule not recognized."
    )
    language: str = Field(default="unknown", description="Programming language")


class AnalysisInsight(BaseModel):
    """LLM-generated analysis insight for code review."""
    
    summary: str = Field(
        description="Brief 1-2 sentence summary of the code quality"
    )
    critical_issues: list[str] = Field(
        default_factory=list,
        description="List of critical issues that must be fixed"
    )
    memory_issues: list[str] = Field(
        default_factory=list,
        description="Memory leaks or resource management issues"
    )
    security_issues: list[str] = Field(
        default_factory=list,
        description="Security vulnerabilities or concerns"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations for improvement"
    )
    quality_score: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Overall code quality score from 1-10"
    )


class SyntaxAnalysisResult(BaseModel):
    """Complete result of syntax analysis combining linter output and LLM insight."""
    
    success: bool = Field(description="Whether analysis completed successfully")
    files_analyzed: int = Field(default=0, description="Number of files analyzed")
    languages: list[str] = Field(
        default_factory=list,
        description="Programming languages detected"
    )
    total_issues: int = Field(default=0, description="Total number of issues found")
    issues: list[CodeIssue] = Field(
        default_factory=list,
        description="List of all issues found by linters"
    )
    insight: AnalysisInsight | None = Field(
        default=None,
        description="LLM-generated analysis insight"
    )
    error: str | None = Field(default=None, description="Error message if failed")

    @property
    def memory_issue_count(self) -> int:
        return len([i for i in self.issues if i.category == "memory"])

    @property
    def security_issue_count(self) -> int:
        return len([i for i in self.issues if i.category == "security"])

    @property
    def issues_by_category(self) -> dict[str, list[CodeIssue]]:
        result: dict[str, list[CodeIssue]] = {}
        for issue in self.issues:
            if issue.category not in result:
                result[issue.category] = []
            result[issue.category].append(issue)
        return result
