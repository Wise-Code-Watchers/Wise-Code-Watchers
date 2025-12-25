# Linter Installation Guide

This document describes how to install linter tools for each supported language.

## Quick Start with Docker (Recommended)

The easiest way to get all linters is using Docker:

```bash
# Build the image
docker build -t pr-review-bot .

# Run test workflow
docker run --rm -v $(pwd)/pr_export:/app/pr_export pr-review-bot python dev/test_workflow.py

# Or use docker-compose
docker-compose up pr-review

# Development mode
docker-compose --profile dev up pr-review-dev
```

---

## Supported Languages and Linters

| Language   | Linter        | Purpose |
|------------|---------------|---------|
| Python     | ruff          | Fast Python linter |
| TypeScript/JavaScript | eslint | JS/TS linter |
| Java       | checkstyle    | Java code style checker |
| Go         | golangci-lint | Go linter aggregator |
| Ruby       | rubocop       | Ruby static code analyzer |

---

## Python - Ruff

**Ruff** is an extremely fast Python linter written in Rust.

### Installation

```bash
# Via pip (recommended)
pip install ruff

# Or in virtual environment
.venv/bin/pip install ruff

# Via pipx (isolated install)
pipx install ruff

# Via Homebrew (macOS)
brew install ruff
```

### Verify Installation

```bash
ruff --version
```

---

## TypeScript/JavaScript - ESLint

**ESLint** is the standard linter for JavaScript and TypeScript.

### Installation

```bash
# Global installation
npm install -g eslint

# Or project-local
npm install --save-dev eslint

# With TypeScript support
npm install -g eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin
```

### Configuration

Create `.eslintrc.json` in project root:

```json
{
  "parser": "@typescript-eslint/parser",
  "plugins": ["@typescript-eslint"],
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended"
  ]
}
```

### Verify Installation

```bash
eslint --version
```

---

## Java - Checkstyle

**Checkstyle** is a development tool to help ensure Java code adheres to coding standards.

### Installation

#### Option 1: Download JAR (Recommended)

```bash
# Download latest version
wget https://github.com/checkstyle/checkstyle/releases/download/checkstyle-10.12.5/checkstyle-10.12.5-all.jar

# Create wrapper script
cat > /usr/local/bin/checkstyle << 'EOF'
#!/bin/bash
java -jar /path/to/checkstyle-10.12.5-all.jar "$@"
EOF
chmod +x /usr/local/bin/checkstyle
```

#### Option 2: Via Homebrew (macOS)

```bash
brew install checkstyle
```

#### Option 3: Via SDKMAN

```bash
sdk install checkstyle
```

#### Option 4: Via apt (Ubuntu/Debian)

```bash
sudo apt install checkstyle
```

### Configuration

Create `checkstyle.xml` for custom rules, or use built-in:

```bash
# Use Google style
checkstyle -c /google_checks.xml MyFile.java

# Use Sun style
checkstyle -c /sun_checks.xml MyFile.java
```

### Verify Installation

```bash
checkstyle --version
```

---

## Go - golangci-lint

**golangci-lint** is a fast linters runner for Go that runs multiple linters in parallel.

### Installation

#### Option 1: Binary (Recommended)

```bash
# Linux/macOS
curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin v1.55.2

# Or download specific version
wget https://github.com/golangci/golangci-lint/releases/download/v1.55.2/golangci-lint-1.55.2-linux-amd64.tar.gz
tar -xzf golangci-lint-1.55.2-linux-amd64.tar.gz
sudo mv golangci-lint-1.55.2-linux-amd64/golangci-lint /usr/local/bin/
```

#### Option 2: Via Go install

```bash
go install github.com/golangci/golangci-lint/cmd/golangci-lint@v1.55.2
```

#### Option 3: Via Homebrew (macOS)

```bash
brew install golangci-lint
```

#### Option 4: Via apt (Ubuntu)

```bash
# Add repository
curl -fsSL https://repo.golangci-lint.dev/pubkey.gpg | sudo gpg --dearmor -o /usr/share/keyrings/golangci-lint.gpg
echo "deb [signed-by=/usr/share/keyrings/golangci-lint.gpg] https://repo.golangci-lint.dev/debian stable main" | sudo tee /etc/apt/sources.list.d/golangci-lint.list

sudo apt update
sudo apt install golangci-lint
```

### Verify Installation

```bash
golangci-lint --version
```

---

## Ruby - RuboCop

**RuboCop** is a Ruby static code analyzer and formatter.

### Installation

```bash
# Via gem (recommended)
gem install rubocop

# With specific version
gem install rubocop -v 1.57.0

# Via Bundler (project-local)
# Add to Gemfile:
# gem 'rubocop', require: false
bundle install
```

### Configuration

Create `.rubocop.yml` in project root:

```yaml
AllCops:
  TargetRubyVersion: 3.0
  NewCops: enable

Style/Documentation:
  Enabled: false

Metrics/MethodLength:
  Max: 20
```

### Verify Installation

```bash
rubocop --version
```

---

## Quick Install Script

Run this script to install all linters:

```bash
#!/bin/bash

echo "Installing linters..."

# Python - Ruff
pip install ruff

# JavaScript/TypeScript - ESLint
npm install -g eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin

# Go - golangci-lint
curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin

# Ruby - RuboCop
gem install rubocop

# Java - Checkstyle (requires manual download or package manager)
# brew install checkstyle  # macOS
# apt install checkstyle   # Ubuntu/Debian

echo "Done! Verify with:"
echo "  ruff --version"
echo "  eslint --version"
echo "  golangci-lint --version"
echo "  rubocop --version"
echo "  checkstyle --version"
```

---

## Verify All Linters

```bash
# Check which linters are available
cd /path/to/wcw
.venv/bin/python -c "
from tools.linter import LinterTool
linter = LinterTool()
for name, available in linter._available_linters.items():
    status = '✓' if available else '✗'
    print(f'{status} {name}')
"
```

Expected output with all linters installed:

```
✓ pylint
✓ flake8
✓ eslint
✓ ruff
✓ checkstyle
✓ golangci-lint
✓ rubocop
```
