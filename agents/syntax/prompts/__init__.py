"""Language-specific prompts for syntax analysis."""

from .base import BASE_SYSTEM_PROMPT, ANALYSIS_OUTPUT_FORMAT
from .python_prompt import (
    PYTHON_SYSTEM_PROMPT,
    PYTHON_ANALYSIS_PROMPT,
    PYTHON_LINTER_CONFIG,
    PYTHON_MEMORY_RULES,
)
from .typescript_prompt import (
    TYPESCRIPT_SYSTEM_PROMPT,
    TYPESCRIPT_ANALYSIS_PROMPT,
    TYPESCRIPT_LINTER_CONFIG,
    TYPESCRIPT_MEMORY_RULES,
)
from .java_prompt import (
    JAVA_SYSTEM_PROMPT,
    JAVA_ANALYSIS_PROMPT,
    JAVA_LINTER_CONFIG,
    JAVA_MEMORY_RULES,
)
from .go_prompt import (
    GO_SYSTEM_PROMPT,
    GO_ANALYSIS_PROMPT,
    GO_LINTER_CONFIG,
    GO_MEMORY_RULES,
)
from .ruby_prompt import (
    RUBY_SYSTEM_PROMPT,
    RUBY_ANALYSIS_PROMPT,
    RUBY_LINTER_CONFIG,
    RUBY_MEMORY_RULES,
)


class LanguagePromptLoader:
    """Load language-specific prompts and configurations dynamically."""

    SYSTEM_PROMPTS = {
        "python": PYTHON_SYSTEM_PROMPT,
        "typescript": TYPESCRIPT_SYSTEM_PROMPT,
        "javascript": TYPESCRIPT_SYSTEM_PROMPT,
        "java": JAVA_SYSTEM_PROMPT,
        "go": GO_SYSTEM_PROMPT,
        "ruby": RUBY_SYSTEM_PROMPT,
    }

    ANALYSIS_PROMPTS = {
        "python": PYTHON_ANALYSIS_PROMPT,
        "typescript": TYPESCRIPT_ANALYSIS_PROMPT,
        "javascript": TYPESCRIPT_ANALYSIS_PROMPT,
        "java": JAVA_ANALYSIS_PROMPT,
        "go": GO_ANALYSIS_PROMPT,
        "ruby": RUBY_ANALYSIS_PROMPT,
    }

    LINTER_CONFIGS = {
        "python": PYTHON_LINTER_CONFIG,
        "typescript": TYPESCRIPT_LINTER_CONFIG,
        "javascript": TYPESCRIPT_LINTER_CONFIG,
        "java": JAVA_LINTER_CONFIG,
        "go": GO_LINTER_CONFIG,
        "ruby": RUBY_LINTER_CONFIG,
    }

    MEMORY_RULES = {
        "python": PYTHON_MEMORY_RULES,
        "typescript": TYPESCRIPT_MEMORY_RULES,
        "javascript": TYPESCRIPT_MEMORY_RULES,
        "java": JAVA_MEMORY_RULES,
        "go": GO_MEMORY_RULES,
        "ruby": RUBY_MEMORY_RULES,
    }

    @classmethod
    def get_system_prompt(cls, language: str) -> str:
        """Get system prompt for a language."""
        return cls.SYSTEM_PROMPTS.get(
            language.lower(),
            BASE_SYSTEM_PROMPT.format(language=language)
        )

    @classmethod
    def get_analysis_prompt(cls, language: str) -> str:
        """Get analysis prompt template for a language."""
        return cls.ANALYSIS_PROMPTS.get(
            language.lower(),
            cls.ANALYSIS_PROMPTS["python"]  # Default to Python
        )

    @classmethod
    def get_linter_config(cls, language: str) -> dict:
        """Get recommended linter configuration for a language."""
        return cls.LINTER_CONFIGS.get(language.lower(), {})

    @classmethod
    def get_memory_rules(cls, language: str) -> dict:
        """Get memory-related rules for a language."""
        return cls.MEMORY_RULES.get(language.lower(), {})

    @classmethod
    def supported_languages(cls) -> list[str]:
        """List of supported languages."""
        return list(cls.ANALYSIS_PROMPTS.keys())

    @classmethod
    def is_supported(cls, language: str) -> bool:
        """Check if a language is supported."""
        return language.lower() in cls.ANALYSIS_PROMPTS


__all__ = [
    "LanguagePromptLoader",
    "BASE_SYSTEM_PROMPT",
    "ANALYSIS_OUTPUT_FORMAT",
    "PYTHON_ANALYSIS_PROMPT",
    "TYPESCRIPT_ANALYSIS_PROMPT",
    "JAVA_ANALYSIS_PROMPT",
    "GO_ANALYSIS_PROMPT",
    "RUBY_ANALYSIS_PROMPT",
]
