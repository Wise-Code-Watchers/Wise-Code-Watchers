from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ToolResult:
    success: bool
    output: str
    issues: list[dict] = field(default_factory=list)
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    async def run(self, target: str, **kwargs) -> ToolResult:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass
