# AGENT.md - WiseCodeWatcher

## Quick Reference

```bash
# Setup
source .venv/bin/activate
pip install -r requirements.txt

# Run server
python app.py

# Check syntax of all files
python -c "import ast; [ast.parse(open(f).read()) for f in __import__('glob').glob('**/*.py', recursive=True) if '.venv' not in f]"

# Test imports
python -c "from agents.orchestrator import ReviewOrchestrator; print('OK')"
```

## Project Overview

Multi-agent PR review system using LangChain. Analyzes GitHub PRs via webhook, runs 4 parallel AI agents, posts review comments back to GitHub.

**Stack**: Python 3.12+, Flask, LangChain, OpenAI GPT-4o-mini, PyGithub

## Code Conventions

### Style Rules
- Use `async/await` for agent methods
- Type hints required on all function signatures
- Dataclasses for data models (not dicts)
- No bare `except:` clauses - always specify exception type
- Imports: stdlib → third-party → local (separated by blank lines)

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

### Agent Pattern
```python
from agents.base import BaseAgent, AgentResult

class MyAgent(BaseAgent):
    name = "my_agent"
    description = "What this agent does"

    async def analyze(self, codebase_path: str, **kwargs) -> AgentResult:
        # 1. Run tools
        # 2. Query knowledge bases
        # 3. Call LLM with prompt
        # 4. Parse response
        return AgentResult(
            agent_name=self.name,
            success=True,
            issues=[...],
            summary="...",
        )
```

## Project Structure

```
wcw/
├── app.py                      # Flask webhook entry point
├── config.py                   # Environment config (loads .env)
├── core/
│   ├── github_client.py        # GitHub API (PyGithub wrapper)
│   └── git_client.py           # Git clone operations
├── export/
│   └── pr_exporter.py          # Exports PR to folder
├── agents/
│   ├── orchestrator.py         # MAIN ENTRY - coordinates all agents
│   ├── aggregator.py           # Merges agent results
│   ├── base.py                 # BaseAgent class
│   ├── preprocessing/          # Diff parsing, feature division
│   ├── syntax/                 # structure_agent, memory_agent
│   └── vulnerability/          # logic_agent, security_agent
├── knowledge/                  # Knowledge bases (patterns, vulns)
├── tools/                      # External tools (linter, scanner)
├── output/
│   ├── models.py               # Data models (Bug, Report, etc.)
│   └── report_generator.py     # Markdown report generation
└── publish/
    └── github_publisher.py     # Posts to GitHub
```

## Key Entry Points

| Task | File | Function/Class |
|------|------|----------------|
| Webhook handler | `app.py` | `handle_pull_request()` |
| Run full review | `agents/orchestrator.py` | `ReviewOrchestrator.run_review()` |
| Add new agent | `agents/syntax/` or `agents/vulnerability/` | Inherit `BaseAgent` |
| Modify report | `output/report_generator.py` | `generate_github_review_body()` |
| Add security pattern | `tools/security_scanner.py` | `security_patterns` list |

## Data Flow

```
Webhook → Export PR → Clone repo → Parse diff → Divide features
                                        ↓
          ┌─────────────┬───────────────┼───────────────┬─────────────┐
          ↓             ↓               ↓               ↓             ↓
     Structure     Memory          Logic          Security
       Agent       Agent           Agent           Agent
          ↓             ↓               ↓               ↓             ↓
          └─────────────┴───────────────┼───────────────┴─────────────┘
                                        ↓
                              Aggregate results → Publish to GitHub
```

## Environment Variables

```bash
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY_PATH=./secret/private-key.pem
GITHUB_WEBHOOK_SECRET=your-webhook-secret
OPENAI_API_KEY=sk-...
PORT=3000
```

## Do's and Don'ts

### Do
- Use `AgentResult` dataclass for all agent returns
- Use `Bug` model from `output/models.py` for issues
- Run tools asynchronously with `await tool.run()`
- Query knowledge bases before LLM calls for context
- Handle JSON parse errors with fallback logic
- Log important steps with `logger.info()`

### Don't
- Don't use `print()` - use `logging.getLogger(__name__)`
- Don't hardcode file paths - use `os.path.join()`
- Don't catch bare exceptions without logging
- Don't make synchronous HTTP calls in async functions
- Don't store secrets in code - use environment variables
- Don't modify `output/models.py` without updating `aggregator.py`

## Common Modifications

### Add a new agent
```python
# 1. Create agents/vulnerability/my_agent.py
from agents.base import BaseAgent, AgentResult

class MyNewAgent(BaseAgent):
    name = "my_new_agent"
    
    async def analyze(self, codebase_path: str, **kwargs) -> AgentResult:
        # implementation
        pass

# 2. Add to orchestrator.py __init__():
self.my_agent = MyNewAgent(llm=self.llm)

# 3. Add to run_review() parallel tasks:
my_task = self.my_agent.analyze(codebase_path=codebase_path)
results = await asyncio.gather(..., my_task)

# 4. Update aggregator.aggregate() parameters
```

### Add knowledge base entry
```python
# In knowledge/vulnerability_kb.py
KnowledgeEntry(
    id="vuln013",
    category="injection",
    title="LDAP Injection",
    description="User input in LDAP queries without sanitization",
    pattern=r"ldap\.search\s*\(.*\+",
    severity="critical",
    tags=["ldap", "injection"],
)
```

### Change LLM model
```python
# In agents/orchestrator.py
self.llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
```

## Key Models

```python
from output.models import (
    AnalysisReport,    # Full report container
    Bug,               # Individual issue
    BugType,           # LOGIC_ERROR, SECURITY_VULNERABILITY, etc.
    Severity,          # LOW, MEDIUM, HIGH, CRITICAL
    FeaturePoint,      # Logical change unit
    LineComment,       # GitHub line comment
)
```

## Testing Locally

```bash
source .venv/bin/activate
python -c "
import asyncio
from agents.orchestrator import ReviewOrchestrator

async def test():
    orch = ReviewOrchestrator()
    # Requires existing PR export folder and cloned codebase
    report = await orch.run_review(
        pr_folder='pr_export/owner_repo_PR1',
        codebase_path='workspace/owner_repo/main',
        pr_number=1,
        repo_full_name='owner/repo',
    )
    print(report.bug_detection.total_count, 'issues found')

asyncio.run(test())
"
```
