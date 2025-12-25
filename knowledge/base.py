from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class KnowledgeEntry:
    id: str
    category: str
    title: str
    description: str
    pattern: Optional[str] = None
    example: Optional[str] = None
    severity: Optional[str] = None
    tags: list[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class KnowledgeBase(ABC):
    def __init__(self):
        self.entries: list[KnowledgeEntry] = []
        self._load_entries()

    @abstractmethod
    def _load_entries(self):
        pass

    def search(self, query: str, limit: int = 10) -> list[KnowledgeEntry]:
        query_lower = query.lower()
        scored = []
        for entry in self.entries:
            score = 0
            if query_lower in entry.title.lower():
                score += 3
            if query_lower in entry.description.lower():
                score += 2
            for tag in entry.tags:
                if query_lower in tag.lower():
                    score += 1
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def get_by_category(self, category: str) -> list[KnowledgeEntry]:
        return [e for e in self.entries if e.category == category]

    def get_by_tags(self, tags: list[str]) -> list[KnowledgeEntry]:
        tags_lower = [t.lower() for t in tags]
        return [
            e for e in self.entries
            if any(t.lower() in tags_lower for t in e.tags)
        ]

    def get_all(self) -> list[KnowledgeEntry]:
        return self.entries
