"""
Base agent utilities for LangGraph-based agents.

2025 LangChain/LangGraph patterns:
- Use StateGraph for workflow management
- Use Pydantic for structured output
- Use @tool decorator for tool integration
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel


@dataclass
class AgentResult:
    """Legacy result format for backward compatibility."""
    agent_name: str
    success: bool
    issues: list[dict] = field(default_factory=list)
    summary: str = ""
    metrics: dict = field(default_factory=dict)
    error: Optional[str] = None


class BaseAgent(ABC):
    """Legacy base agent class - prefer LangGraph StateGraph for new agents"""
    name: str
    description: str

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        verbose: bool = False,
    ):
        self.llm = llm
        self.verbose = verbose
        self.tools = []
        self.knowledge_bases = []

    def add_tool(self, tool: Any):
        self.tools.append(tool)

    def add_knowledge_base(self, kb: Any):
        self.knowledge_bases.append(kb)

    @abstractmethod
    async def analyze(self, **kwargs) -> AgentResult:
        pass

    def _create_prompt(self, system_message: str, human_message: str) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message),
        ])

    def _query_knowledge_bases(self, query: str) -> list[dict]:
        results = []
        for kb in self.knowledge_bases:
            entries = kb.search(query)
            for entry in entries:
                results.append({
                    "source": kb.__class__.__name__,
                    "title": entry.title,
                    "description": entry.description,
                    "severity": entry.severity,
                })
        return results


def create_llm_with_structured_output(
    llm: BaseChatModel,
    schema: type,
):
    """Bind structured output schema to LLM"""
    return llm.with_structured_output(schema)
