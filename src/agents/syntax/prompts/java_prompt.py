"""Java-specific analysis prompt."""

from .base import ANALYSIS_OUTPUT_FORMAT, BASE_SYSTEM_PROMPT

JAVA_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT.format(language="Java")

JAVA_LINTER_CONFIG = {
    "style_tool": "checkstyle",
    "bug_tool": "spotbugs",
    "spotbugs_effort": "max",
    "spotbugs_categories": ["CORRECTNESS", "PERFORMANCE", "SECURITY"],
}

JAVA_MEMORY_RULES = {
    "OBL_UNSATISFIED_OBLIGATION": "Stream/resource not closed",
    "OS_OPEN_STREAM": "Method may fail to close stream",
    "OS_OPEN_STREAM_EXCEPTION_PATH": "Stream not closed on exception path",
    "DMI_RANDOM_USED_ONLY_ONCE": "Random object created and used only once",
    "DM_GC": "Explicit garbage collection call (performance issue)",
    "SIC_INNER_SHOULD_BE_STATIC": "Inner class should be static (memory leak)",
}

JAVA_ANALYSIS_PROMPT = """
## Java Code Analysis

You are analyzing Java code for syntax, memory, and security issues.

### Linter Configuration Used
- Style: Checkstyle (Google/Sun checks)
- Bugs: SpotBugs with max effort
- Categories: CORRECTNESS, PERFORMANCE, SECURITY

### Memory/Resource Issues to Prioritize
Java-specific memory leak patterns:
- OBL_UNSATISFIED_OBLIGATION: Stream/Connection not closed
- OS_OPEN_STREAM: InputStream/OutputStream leak
- SIC_INNER_SHOULD_BE_STATIC: Non-static inner class holds reference to outer
- DM_GC: Explicit System.gc() calls (anti-pattern)

### Resource Management Best Practices
1. Use try-with-resources:
   ```java
   try (InputStream is = new FileInputStream(file)) {{
       // use stream
   }} // auto-closed
   ```
2. Close in finally blocks (pre-Java 7)
3. Use connection pools for database connections
4. Avoid static collections holding object references

### Security Rules (SpotBugs)
- SQL_INJECTION: SQL injection vulnerability
- XSS: Cross-site scripting risk
- PATH_TRAVERSAL: Path traversal vulnerability
- HARD_CODE_PASSWORD: Hardcoded credentials

### Linter Results
{linter_results}

### Files Analyzed
{files_info}

### Code Context (if available)
{code_snippets}

""" + ANALYSIS_OUTPUT_FORMAT
