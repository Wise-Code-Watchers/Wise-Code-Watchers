"""TypeScript/JavaScript-specific analysis prompt."""

from .base import ANALYSIS_OUTPUT_FORMAT, BASE_SYSTEM_PROMPT

TYPESCRIPT_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT.format(language="TypeScript/JavaScript")

TYPESCRIPT_LINTER_CONFIG = {
    "tool": "eslint",
    "plugins": ["@typescript-eslint", "react-hooks"],
    "extends": ["eslint:recommended", "plugin:@typescript-eslint/recommended"],
}

TYPESCRIPT_MEMORY_RULES = {
    "react-hooks/exhaustive-deps": "Missing cleanup in useEffect (memory leak)",
    "no-unused-vars": "Unused variable (potential memory retention)",
    "require-await": "Async function without await (unhandled promise)",
    "no-async-promise-executor": "Async promise executor (error handling issue)",
}

TYPESCRIPT_ANALYSIS_PROMPT = """
## TypeScript/JavaScript Code Analysis

You are analyzing TypeScript/JavaScript code for syntax, memory, and security issues.

### Linter Configuration Used
- Tool: ESLint with TypeScript parser
- Plugins: @typescript-eslint, react-hooks

### Memory/Resource Issues to Prioritize
These patterns indicate potential memory leaks:
- react-hooks/exhaustive-deps: useEffect without cleanup function
- Event listeners not removed in cleanup
- Subscriptions not unsubscribed
- Timers (setInterval/setTimeout) not cleared
- WebSocket connections not closed

### Security Rules
- no-eval: Eval usage (code injection risk)
- no-implied-eval: Implied eval in setTimeout/setInterval
- @typescript-eslint/no-explicit-any: Type safety issues

### Common Memory Leak Patterns in React
1. useEffect without cleanup: 
   ```
   useEffect(() => {{ 
     const subscription = subscribe(); 
     return () => subscription.unsubscribe(); // Missing?
   }}, []);
   ```
2. Event listeners without removal
3. Async operations after unmount

### Linter Results
{linter_results}

### Files Analyzed
{files_info}

### Code Context (if available)
{code_snippets}

""" + ANALYSIS_OUTPUT_FORMAT
