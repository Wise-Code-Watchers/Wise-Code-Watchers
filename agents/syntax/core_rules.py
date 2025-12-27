"""
Core rules definitions for multi-language issue filtering.

Defines which linter rules are considered "core" (syntax, memory, security)
vs "style" (formatting, conventions) for each supported language.

Only core issues are surfaced to users by default.
"""

# Python (ruff/pylint)
PYTHON_CORE_RULES = {
    "syntax": [
        "E9",      # Runtime errors (E901, E902, etc.)
        "F821",    # Undefined name
        "F822",    # Undefined name in __all__
        "F823",    # Local variable referenced before assignment
        "F831",    # Duplicate argument name
        "F632",    # Use == to compare with str, bytes, int
        "F633",    # Invalid print() format
    ],
    "memory": [
        "SIM115",  # Use context manager for opening files
        "B006",    # Mutable default argument
        "B008",    # Function call in default argument
        "PLW0603", # Global statement
        "PLW0602", # Global variable not assigned
        "R1732",   # Consider using with for resource-allocating operations
        "W1514",   # Using open without explicit encoding
        "RUF013",  # Implicit Optional
    ],
    "security": [
        "S",       # All security rules (S101-S703)
    ],
}

PYTHON_IGNORE_RULES = [
    "E1",      # Indentation
    "E2",      # Whitespace
    "E3",      # Blank line
    "E4",      # Import
    "E5",      # Line length (E501)
    "E7",      # Statement
    "W",       # Warnings (style)
    "F401",    # Unused import
    "F841",    # Unused variable
    "C9",      # McCabe complexity
    "N",       # Naming conventions
    "D",       # Docstrings
    "ANN",     # Annotations
    "Q",       # Quotes
    "COM",     # Commas
    "ISC",     # Implicit string concatenation
    "T20",     # Print statements
]

# TypeScript/JavaScript (eslint)
TYPESCRIPT_CORE_RULES = {
    "syntax": [
        "no-undef",
        "no-unreachable",
        "no-dupe-keys",
        "no-dupe-args",
        "no-func-assign",
        "no-import-assign",
        "no-const-assign",
        "no-class-assign",
        "valid-typeof",
        "no-obj-calls",
        "no-invalid-regexp",
        "no-unexpected-multiline",
        "@typescript-eslint/no-misused-promises",
    ],
    "memory": [
        "react-hooks/exhaustive-deps",
        "no-async-promise-executor",
        "require-await",
        "no-return-await",
        "prefer-promise-reject-errors",
        "no-floating-promises",
        "@typescript-eslint/no-floating-promises",
    ],
    "security": [
        "no-eval",
        "no-implied-eval",
        "no-new-func",
        "no-script-url",
        "security/detect-eval-with-expression",
        "security/detect-non-literal-regexp",
        "security/detect-non-literal-require",
        "security/detect-possible-timing-attacks",
    ],
}

TYPESCRIPT_IGNORE_RULES = [
    "no-unused-vars",
    "@typescript-eslint/no-unused-vars",
    "semi",
    "quotes",
    "indent",
    "comma-dangle",
    "no-trailing-spaces",
    "eol-last",
    "max-len",
    "no-multiple-empty-lines",
    "object-curly-spacing",
    "array-bracket-spacing",
    "space-before-function-paren",
    "prettier/prettier",
    "@typescript-eslint/explicit-function-return-type",
    "@typescript-eslint/explicit-module-boundary-types",
]

# Go (golangci-lint)
GO_CORE_RULES = {
    "syntax": [
        "govet",
        "typecheck",
        "staticcheck",
        "ineffassign",
    ],
    "memory": [
        "bodyclose",      # HTTP response body not closed
        "sqlclosecheck",  # SQL rows/stmt not closed
        "rowserrcheck",   # SQL rows.Err() not checked
        "contextcheck",   # Context cancellation
        "noctx",          # HTTP request without context
        "unparam",        # Unused parameters
    ],
    "security": [
        "gosec",
    ],
}

GO_IGNORE_RULES = [
    "gofmt",
    "goimports",
    "gofumpt",
    "goconst",
    "gocritic",
    "godot",
    "godox",
    "gocyclo",
    "gocognit",
    "lll",        # Line length
    "wsl",        # Whitespace
    "nlreturn",
    "wrapcheck",
    "varnamelen",
    "nonamedreturns",
]

# Java (checkstyle/spotbugs)
JAVA_CORE_RULES = {
    "syntax": [
        "compiler",       # Compilation errors
        "UnusedLocalVariable",
    ],
    "memory": [
        "DMI",            # Doubtful method invocation
        "OBL",            # Object bloat
        "OS_OPEN_STREAM", # Unclosed streams
        "ODR_OPEN_DATABASE_RESOURCE",
        "SBSC_USE_STRINGBUFFER_CONCATENATION",
        "WMI_WRONG_MAP_ITERATOR",
    ],
    "security": [
        "SQL",            # SQL injection
        "XSS",            # Cross-site scripting
        "PATH_TRAVERSAL",
        "COMMAND_INJECTION",
        "LDAP_INJECTION",
        "XPATH_INJECTION",
        "XXE",            # XML external entity
        "SSRF",           # Server-side request forgery
    ],
}

JAVA_IGNORE_RULES = [
    "Javadoc",
    "LineLength",
    "Indentation",
    "WhitespaceAround",
    "WhitespaceAfter",
    "NoWhitespaceBefore",
    "EmptyLineSeparator",
    "NeedBraces",
    "LeftCurly",
    "RightCurly",
    "MethodName",
    "ConstantName",
    "LocalVariableName",
    "MemberName",
    "ParameterName",
    "TypeName",
    "PackageName",
    "ImportOrder",
    "AvoidStarImport",
    "UnusedImports",
]

# Ruby (rubocop)
RUBY_CORE_RULES = {
    "syntax": [
        "Lint/Syntax",
        "Lint/Void",
        "Lint/UnreachableCode",
        "Lint/DuplicateMethods",
        "Lint/CircularArgumentReference",
        "Lint/ParenthesesAsGroupedExpression",
    ],
    "memory": [
        "Lint/UselessAssignment",
        "Lint/SuppressedException",
        "Lint/RescueException",
        "Lint/EnsureReturn",
        "Lint/FloatOutOfRange",
    ],
    "security": [
        "Security",       # All Security/* rules
        "Lint/Eval",
    ],
}

RUBY_IGNORE_RULES = [
    "Style/",
    "Layout/",
    "Metrics/",
    "Naming/",
]

# Aggregate all rules by language
CORE_RULES = {
    "python": PYTHON_CORE_RULES,
    "typescript": TYPESCRIPT_CORE_RULES,
    "javascript": TYPESCRIPT_CORE_RULES,  # Same as TypeScript
    "go": GO_CORE_RULES,
    "java": JAVA_CORE_RULES,
    "ruby": RUBY_CORE_RULES,
}

IGNORE_RULES = {
    "python": PYTHON_IGNORE_RULES,
    "typescript": TYPESCRIPT_IGNORE_RULES,
    "javascript": TYPESCRIPT_IGNORE_RULES,
    "go": GO_IGNORE_RULES,
    "java": JAVA_IGNORE_RULES,
    "ruby": RUBY_IGNORE_RULES,
}


def is_core_rule(rule: str, language: str) -> bool:
    """
    Check if a rule is a core rule (syntax, memory, security).
    
    Args:
        rule: The rule code (e.g., "F821", "no-undef", "gosec")
        language: The programming language
        
    Returns:
        True if the rule is a core rule, False if it's style/ignorable
    """
    lang_rules = CORE_RULES.get(language, {})
    
    for category_rules in lang_rules.values():
        for core_rule in category_rules:
            if rule.startswith(core_rule) or rule == core_rule:
                return True
    
    return False


def is_ignored_rule(rule: str, language: str) -> bool:
    """
    Check if a rule should be ignored (style/formatting).
    
    Args:
        rule: The rule code
        language: The programming language
        
    Returns:
        True if the rule should be ignored
    """
    ignore_list = IGNORE_RULES.get(language, [])
    
    for ignore_pattern in ignore_list:
        if rule.startswith(ignore_pattern) or rule == ignore_pattern:
            return True
    
    return False


def get_rule_category(rule: str, language: str) -> str:
    """
    Get the category of a rule (syntax, memory, security, style).
    
    Args:
        rule: The rule code
        language: The programming language
        
    Returns:
        Category string: "syntax", "memory", "security", or "style"
    """
    lang_rules = CORE_RULES.get(language, {})
    
    for category, rules in lang_rules.items():
        for core_rule in rules:
            if rule.startswith(core_rule) or rule == core_rule:
                return category
    
    return "style"


def get_supported_languages() -> list[str]:
    """Return list of supported languages."""
    return list(CORE_RULES.keys())


def should_keep_issue(rule: str, language: str, severity: str = "warning") -> tuple[bool, str]:
    """
    Determine if an issue should be kept using blocklist-first logic.
    
    This function prioritizes NOT missing important issues over reducing noise.
    Unknown rules are kept by default (better false positive than false negative).
    
    Args:
        rule: The rule code (e.g., "F821", "no-undef")
        language: The programming language
        severity: Issue severity ("error", "warning", "info")
        
    Returns:
        Tuple of (should_keep: bool, category: str)
        - should_keep: True if issue should be shown to user
        - category: "syntax", "memory", "security", "style", or "unknown"
    """
    # Step 1: Explicitly ignored rules → drop
    # These are known style/formatting rules we're confident about
    if is_ignored_rule(rule, language):
        return (False, "style")
    
    # Step 2: Known core rules → keep with correct category
    if is_core_rule(rule, language):
        return (True, get_rule_category(rule, language))
    
    # Step 3: Error severity → always keep (safety first)
    # If a linter marks something as "error", it's likely important
    if severity.lower() == "error":
        return (True, "unknown")
    
    # Step 4: Unknown rules → keep but mark as unknown
    # Let LLM stage or human review decide importance
    # Better to show a potential false positive than miss a real bug
    return (True, "unknown")


def classify_unknown_issue(rule: str, language: str, message: str = "") -> str:
    """
    Attempt to classify an unknown rule based on heuristics.
    
    Used as a fallback when rule is not in CORE_RULES or IGNORE_RULES.
    
    Args:
        rule: The rule code
        language: The programming language
        message: The issue message (can provide hints)
        
    Returns:
        Best-guess category: "syntax", "memory", "security", or "unknown"
    """
    rule_lower = rule.lower()
    message_lower = message.lower()
    
    # Security keywords
    security_keywords = [
        "injection", "xss", "csrf", "auth", "password", "secret", 
        "credential", "vulnerability", "unsafe", "insecure", "sql"
    ]
    if any(kw in rule_lower or kw in message_lower for kw in security_keywords):
        return "security"
    
    # Memory/resource keywords
    memory_keywords = [
        "leak", "resource", "close", "dispose", "release", "memory",
        "stream", "connection", "file", "handle", "buffer"
    ]
    if any(kw in rule_lower or kw in message_lower for kw in memory_keywords):
        return "memory"
    
    # Syntax/error keywords
    syntax_keywords = [
        "undefined", "undeclared", "syntax", "parse", "type", "error",
        "invalid", "illegal", "unreachable", "deadcode"
    ]
    if any(kw in rule_lower or kw in message_lower for kw in syntax_keywords):
        return "syntax"
    
    return "unknown"
