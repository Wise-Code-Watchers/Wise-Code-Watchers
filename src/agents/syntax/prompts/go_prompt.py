"""Go-specific analysis prompt."""

from .base import ANALYSIS_OUTPUT_FORMAT, BASE_SYSTEM_PROMPT

GO_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT.format(language="Go")

GO_LINTER_CONFIG = {
    "tool": "golangci-lint",
    "enable": [
        "bodyclose",      # HTTP response body not closed
        "sqlclosecheck",  # SQL rows/stmt not closed
        "rowserrcheck",   # SQL rows.Err() not checked
        "govet",          # Go vet checks
        "staticcheck",    # Static analysis
        "gosec",          # Security issues
        "ineffassign",    # Ineffectual assignments
        "errcheck",       # Unchecked errors
    ],
}

GO_MEMORY_RULES = {
    "bodyclose": "HTTP response body not closed (connection leak)",
    "sqlclosecheck": "SQL rows/statement not closed",
    "rowserrcheck": "SQL rows.Err() not checked after iteration",
    "ineffassign": "Ineffectual assignment (dead code)",
    "SA4006": "Value assigned but never used",
}

GO_ANALYSIS_PROMPT = """
## Go Code Analysis

You are analyzing Go code for syntax, memory, and security issues.

### Linter Configuration Used
- Tool: golangci-lint
- Linters: bodyclose, sqlclosecheck, rowserrcheck, govet, staticcheck, gosec

### Memory/Resource Issues to Prioritize
Go-specific resource leak patterns:
- bodyclose: HTTP response body must be closed
  ```go
  resp, err := http.Get(url)
  if err != nil {{ return err }}
  defer resp.Body.Close() // REQUIRED!
  ```
- sqlclosecheck: Database rows/statements must be closed
  ```go
  rows, err := db.Query(query)
  if err != nil {{ return err }}
  defer rows.Close() // REQUIRED!
  ```
- rowserrcheck: Must check rows.Err() after iteration
- File handles must be closed with defer

### Goroutine Leak Patterns
1. Goroutine blocked on channel forever
2. Goroutine waiting on WaitGroup that never completes
3. Context not canceled, causing goroutine leak

### Security Rules (gosec)
- G101: Hardcoded credentials
- G201-G204: SQL injection risks
- G401: Weak cryptographic primitive
- G501: Blacklisted import (crypto/md5, etc.)

### Linter Results
{linter_results}

### Files Analyzed
{files_info}

### Code Context (if available)
{code_snippets}

""" + ANALYSIS_OUTPUT_FORMAT
