# Contributing to Wise Code Watchers

First off, thank you for considering contributing to Wise Code Watchers! It's people like you that make Wise Code Watchers such a great tool.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Commit Message Guidelines](#commit-message-guidelines)

## Code of Conduct

This project and everyone participating in it is governed by the basic principle of **treat others as you would like to be treated**. Please be respectful, constructive, and professional in all interactions.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

**Bug Report Template:**

```markdown
**Description**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected Behavior**
A clear description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment:**
- OS: [e.g. Ubuntu 20.04]
- Python Version: [e.g. 3.12]
- Docker Version: [e.g. 20.10]
- GitHub App ID: [if applicable]

**Additional Context**
Add any other context about the problem here.
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Use a clear title**
- **Provide a detailed description of the suggested enhancement**
- **Explain why this enhancement would be useful**
- **List some examples of how this feature would be used**
- **Include mock-ups or screenshots if applicable**

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
git clone https://github.com/YOUR_USERNAME/wise-code-watchers.git
cd wise-code-watchers
git remote add upstream https://github.com/ORIGINAL_OWNER/wise-code-watchers.git
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_workflow.py

# Run with coverage
pytest --cov=agents --cov=core --cov-report=html
```

### 5. Code Style

We use:
- **Black** for code formatting
- **Ruff** for linting
- **mypy** for type checking

```bash
# Format code
black .

# Lint code
ruff check .

# Type check
mypy .
```

## Pull Request Process

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Your Changes

- Write clean, readable code
- Add tests for new features
- Update documentation as needed
- Follow our coding standards

### 3. Commit Your Changes

See [Commit Message Guidelines](#commit-message-guidelines) below.

### 4. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 5. Create a Pull Request

1. Go to the original repository on GitHub
2. Click "Compare & pull request"
3. Provide a clear description of your changes
4. Link any related issues
5. Wait for code review

### PR Description Template

```markdown
## Description
Brief description of the changes made in this pull request.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issues
Fixes #issue_number
Related to #issue_number

## Testing
- [ ] Tests have been added/updated
- [ ] All tests pass locally

## Checklist
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
```

## Coding Standards

### Python Code Style

- Follow **PEP 8** guidelines
- Use **type hints** for function signatures
- Write **docstrings** for all modules, classes, and functions
- Keep functions **focused and small** (< 50 lines)
- Use **descriptive variable names**

### Example:

```python
from typing import List, Dict, Optional
from github import Github

def get_pr_metadata(
    github_client: Github,
    repo_name: str,
    pr_number: int
) -> Optional[Dict[str, any]]:
    """
    Retrieve metadata for a specific pull request.

    Args:
        github_client: Authenticated GitHub client instance
        repo_name: Repository name in format "owner/repo"
        pr_number: Pull request number

    Returns:
        Dictionary containing PR metadata, or None if not found

    Raises:
        GithubException: If API request fails
    """
    # Implementation here
    pass
```

### Documentation Standards

- Use **clear, concise language**
- Provide **examples** for complex features
- Update **README.md** for user-facing changes
- Update **API documentation** for code changes

## Commit Message Guidelines

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **chore**: Changes to the build process or auxiliary tools

### Examples

**Good:**
```
feat(workflow): add parallel processing for multiple PRs

- Implement worker thread pool with MAX_WORKERS=2
- Add task queue for asynchronous PR processing
- Cache GitHub client instances to reduce API calls

Closes #123
```

```
fix(github-client): handle rate limit errors gracefully

- Add retry logic with exponential backoff
- Implement rate limit detection and logging
- Add tests for rate limit handling

Fixes #456
```

**Bad:**
```
update code
fix bug
stuff
```

## Development Workflow

### Before Submitting

1. **Run tests**: `pytest`
2. **Format code**: `black .`
3. **Check linting**: `ruff check .`
4. **Type check**: `mypy .`
5. **Update docs**: If applicable

### Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and ideas
- **Discord/Slack**: For real-time chat (if available)

## Project Structure

```
wise-code-watchers/
├── agents/          # Agent implementations
├── core/            # Core modules (GitHub, Git clients)
├── tools/           # External tool integrations
├── knowledge/       # Knowledge bases
├── dev/             # Development tools and tests
└── docs/            # Documentation
```

### Adding New Features

1. Identify the appropriate module
2. Create feature branch
3. Implement with tests
4. Update documentation
5. Submit PR

### Adding New Agents

1. Inherit from `agents.base.AgentBase`
2. Implement required methods
3. Add tests in `dev/`
4. Update documentation
5. Register in orchestrator

## Recognition

Contributors will be:
- Listed in [CONTRIBUTORS.md](CONTRIBUTORS.md)
- Mentioned in release notes for significant contributions
- Eligible for project maintainer role (for active, long-term contributors)

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

**Thank you for your contributions! 🎉**

Questions? Feel free to open an issue or start a discussion!
