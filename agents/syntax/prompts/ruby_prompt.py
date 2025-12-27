"""Ruby-specific analysis prompt."""

from .base import ANALYSIS_OUTPUT_FORMAT, BASE_SYSTEM_PROMPT

RUBY_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT.format(language="Ruby")

RUBY_LINTER_CONFIG = {
    "tool": "rubocop",
    "cops": ["Lint", "Security", "Performance"],
    "require": ["rubocop-performance"],
}

RUBY_MEMORY_RULES = {
    "Lint/UselessAssignment": "Useless assignment (dead code)",
    "Style/BlockDelimiters": "Block delimiters for resource management",
    "Lint/SuppressedException": "Suppressed exception (hiding errors)",
    "Lint/UnusedBlockArgument": "Unused block argument",
    "Lint/UnusedMethodArgument": "Unused method argument",
    "Performance/StringReplacement": "Inefficient string operation",
}

RUBY_ANALYSIS_PROMPT = """
## Ruby Code Analysis

You are analyzing Ruby code for syntax, memory, and security issues.

### Linter Configuration Used
- Tool: RuboCop
- Cops: Lint, Security, Performance

### Memory/Resource Issues to Prioritize
Ruby resource management patterns:
- Always use blocks for file operations:
  ```ruby
  # Good - auto-closes
  File.open('file.txt') do |f|
    f.read
  end
  
  # Bad - may leak
  f = File.open('file.txt')
  f.read
  f.close  # May not be called on exception
  ```
- Use ensure for cleanup:
  ```ruby
  begin
    resource = acquire_resource
    use(resource)
  ensure
    resource.release
  end
  ```

### Common Memory Issues
1. Large arrays/hashes kept in memory
2. String concatenation in loops (use StringIO)
3. Symbols created from user input (symbol table leak)
4. Circular references preventing GC

### Security Rules (RuboCop)
- Security/Eval: Eval usage (code injection)
- Security/Open: Kernel#open with user input (command injection)
- Security/YAMLLoad: YAML.load with untrusted data (deserialization)

### Linter Results
{linter_results}

### Files Analyzed
{files_info}

### Code Context (if available)
{code_snippets}

""" + ANALYSIS_OUTPUT_FORMAT
