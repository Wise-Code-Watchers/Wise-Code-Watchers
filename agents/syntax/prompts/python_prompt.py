"""Python-specific analysis prompt."""

from .base import ANALYSIS_OUTPUT_FORMAT, BASE_SYSTEM_PROMPT

PYTHON_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT.format(language="Python")

PYTHON_LINTER_CONFIG = {
    "tool": "ruff",
    "rules": "E,F,W,B,SIM,PLR,PLW,S,RUF",
    "ignore": "E501",
}

PYTHON_MEMORY_RULES = {
    "SIM115": "Use context manager for opening files",
    "B006": "Mutable default argument (can cause unexpected behavior)",
    "B008": "Function call in default argument",
    "PLW0603": "Using global statement (potential memory leak)",
    "PLR1711": "Useless return (dead code)",
    "W1514": "Using open without explicit encoding",
    "R1732": "Consider using 'with' for resource-allocating operations",
}

PYTHON_ANALYSIS_PROMPT = """
## Python Code Analysis

You are analyzing Python code for syntax, memory, and security issues.

### Linter Configuration Used
- Tool: ruff
- Rule sets: E (errors), F (pyflakes), B (bugbear), SIM (simplify), PLW (pylint), S (security)

### Memory/Resource Issues to Prioritize
These rules indicate potential memory leaks or resource issues:
- SIM115: File opened without context manager (unclosed handle)
- B006: Mutable default argument (shared state bug)
- PLW0603: Global statement usage (memory retention)
- R1732: Resource allocation without 'with' statement

### Security Rules
- S101: Assert used (can be disabled in production)
- S608: SQL injection risk
- S301: Pickle usage (deserialization vulnerability)

### Linter Results
{linter_results}

### Files Analyzed
{files_info}

### Code Context (if available)
{code_snippets}

""" + ANALYSIS_OUTPUT_FORMAT
