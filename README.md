# 🦉 Wise Code Watchers

<p align="center">
  <strong>AI-Powered Multi-Agent PR Code Review System</strong>
</p>


<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/LangGraph-Multi--Agent-green.svg" alt="LangGraph">
  <img src="https://img.shields.io/badge/GitHub-App-black.svg" alt="GitHub App">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>


---

## 📖 Project Overview

**Wise Code Watchers** is an intelligent code review system built on LangGraph's multi-agent architecture. Running as a GitHub App, it automatically performs in-depth code reviews on Pull Requests. The system detects logic defects and security vulnerabilities, publishing review results as inline comments directly in GitHub PRs.

### ✨ Key Features

- 🤖 **Multi-Agent Collaboration Architecture**: LangGraph-based workflow engine with multiple specialized agents working in parallel
- 🔒 **Security Vulnerability Detection**: Professional Security Agent combined with Semgrep rules to detect security vulnerabilities
- 🧠 **Logic Defect Analysis**: Logic Agent performs deep analysis of code logic to uncover potential bugs
- 📊 **Intelligent Risk Assessment**: AI-driven risk scoring system prioritizes high-risk code for review
- 🔗 **Cross-File Analysis**: Analyzes the cross-file impact of code changes
- 💬 **Deep GitHub Integration**: Automatically posts inline comments to PRs with GitHub App Webhook support
- 🗳️ **LLM Consensus Voting**: 3 LLMs analyze each feature in parallel, selecting the best result to avoid single-point bias
- 🛡️ **Nil-Guard Filter**: Automatically filters nil/NoMethodError false positives to improve report quality
- 🔍 **Full Observability with Langfuse**: Automatic tracing of all LLM calls, LangGraph workflows, and agent executions with rich metadata

---

## 🏗️ System Architecture

### High-Level System Architecture

```mermaid
graph TB
    subgraph "External Systems"
        GitHub[GitHub<br/>Webhooks & API]
        LLM[LLM API<br/>OpenAI/GLM]
        Langfuse[Langfuse<br/>Observability]
        Semgrep[Semgrep<br/>Security Scanner]
    end

    subgraph "Wise Code Watchers"
        subgraph "Web Layer"
            Flask[Flask Web Server]
            Webhook[Webhook Handler]
            Queue[Task Queue]
        end

        subgraph "Processing Layer"
            LangGraph[LangGraph Workflow Engine]
        end

        subgraph "Agent Layer"
            Logic[Logic Agent<br/>Logic Defects]
            Security[Security Agent<br/>Vulnerabilities]
            Triage[Triage Agent<br/>Priority Filtering]
        end

        subgraph "Output Layer"
            Report[Report Generator]
            Publisher[GitHub Publisher]
        end
    end

    GitHub --> Webhook
    Webhook --> Queue
    Queue --> LangGraph

    LangGraph --> Logic
    LangGraph --> Security
    LangGraph --> Triage

    Semgrep -.->|Evidence| LangGraph
    LLM -.->|Analysis| LangGraph

    Logic --> Report
    Security --> Report
    Triage --> Report

    Report --> Publisher
    Publisher --> GitHub

    LangGraph -.->|Tracing| Langfuse

    style GitHub fill:#f0f9ff,stroke:#0284c7,stroke-width:2px
    style LLM fill:#f0fdf4,stroke:#16a34a,stroke-width:2px
    style Langfuse fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style Semgrep fill:#fef2f2,stroke:#dc2626,stroke-width:2px
```

### Data Flow

```mermaid
flowchart LR
    GH[GitHub PR Event] --> WH[Webhook Handler]
    WH --> EXP[PR Exporter]
    EXP --> WF[LangGraph Workflow]

    WF --> DP[Data Parsing]
    DP --> RA[Risk Analysis]
    RA --> SC[Semgrep Scan]
    SC --> TR[Triage]
    TR --> CF[Cross-File Analysis]

    CF --> PAR[Parallel Review]
    PAR --> LA[Logic Agent]
    PAR --> SA[Security Agent]

    LA --> RG[Report Generator]
    SA --> RG
    CF --> RG

    RG --> PUB[GitHub Publisher]
    PUB --> PR[PR Review & Comments]

    style GH fill:#f0f9ff,stroke:#0284c7,stroke-width:2px
    style PR fill:#f0f9ff,stroke:#0284c7,stroke-width:2px
    style PAR fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style RG fill:#d1fae5,stroke:#10b981,stroke-width:2px
```

### LangGraph Workflow Nodes

```mermaid
graph LR
    Start([Start]) --> Init[Initialization<br/>Parse PR Data]
    Init --> Parse[Data Parsing<br/>Extract Diff]
    Parse --> Risk[Risk Analysis<br/>AI Prioritization]
    Risk --> Semgrep[Semgrep Scan<br/>Security Rules]
    Semgrep --> Triage[Triage<br/>Priority Filter]
    Triage --> Cross[Cross-File Analysis<br/>Impact Propagation]
    Cross --> Parallel[Parallel Review<br/>Logic + Security]
    Parallel --> Final[Final Report<br/>Consolidate Results]
    Final --> End([End])

    style Start fill:#f0f9ff,stroke:#0284c7
    style End fill:#f0f9ff,stroke:#0284c7
    style Parallel fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style Final fill:#d1fae5,stroke:#10b981,stroke-width:2px
```

### Agent Collaboration

```mermaid
graph TB
    subgraph "Input Sources"
        Diff[PR Diff Data]
        Scan[Semgrep Scan Results]
        Linter[Linter Results]
    end

    subgraph "Agents"
        TriageAgent[Triage Agent<br/>Fast Pre-screening<br/>P0/P1/P2/P3/SKIP]
        LogicAgent[Logic Agent<br/>Logic Defects<br/>Boundary/Null/Leaks]
        SecurityAgent[Security Agent<br/>Vulnerabilities<br/>SQLi/XSS/RCE]
    end

    subgraph "Output"
        Issues[Filtered Issues<br/>Relevance & Severity]
        Report[Final Report]
    end

    Diff --> TriageAgent
    Diff --> LogicAgent
    Diff --> SecurityAgent

    Scan -.->|Evidence Injection| LogicAgent
    Scan -.->|Evidence Injection| SecurityAgent
    Linter -.->|Style Issues| LogicAgent

    TriageAgent --> Issues
    LogicAgent --> Issues
    SecurityAgent --> Issues

    Issues --> Report

    style TriageAgent fill:#f3e8ff,stroke:#9333ea
    style LogicAgent fill:#dbeafe,stroke:#2563eb
    style SecurityAgent fill:#fee2e2,stroke:#dc2626
    style Report fill:#d1fae5,stroke:#10b981,stroke-width:2px
```

---

## 📁 Project Structure

```
wise-code-watchers/
├── app.py                      # 🚀 Main entry point (Flask Webhook Server)
├── config.py                   # ⚙️ Configuration management
├── backup.py                   # 💾 Backup script
├── scan_pr_with_templates.py   # 🔍 PR scanning script
├── requirements.txt            # 📦 Python dependencies
├── Dockerfile                  # 🐳 Docker image configuration
├── docker-compose.yml          # 🐳 Docker Compose configuration
├── .env.example                # 🔐 Environment variables example
├── linter-installation.md      # 📖 Linter installation guide
├── CONTRIBUTING.md             # 🤝 Contributing guide
├── CONTRIBUTORS.md             # 👥 Contributors list
│
├── core/                       # 🔧 Core modules
│   ├── github_client.py        # GitHub API client
│   ├── git_client.py           # Git operations client
│   └── repo_manager.py         # Repository manager
│
├── agents/                     # 🤖 Agent modules
│   ├── __init__.py
│   ├── base.py                 # Agent base class
│   ├── orchestrator.py         # Agent orchestrator
│   ├── summary_agent.py        # Summary agent
│   │
│   ├── preprocessing/          # Preprocessing modules
│   │   ├── diff_parser.py      # Diff parser
│   │   ├── description_analyzer.py # PR description analyzer
│   │   └── feature_divider.py  # Feature divider
│   │
│   ├── syntax/                 # Syntax analysis modules
│   │   ├── syntax_analysis_agent.py  # Syntax analysis agent
│   │   ├── syntax_checker.py         # Syntax checker
│   │   ├── structure_agent.py        # Structure agent
│   │   ├── memory_agent.py           # Memory agent
│   │   ├── issue_filter.py           # Issue filter
│   │   ├── core_rules.py             # Core rules
│   │   ├── schemas.py                # Data schemas
│   │   └── prompts/                  # Prompt templates
│   │       ├── base.py
│   │       ├── python_prompt.py
│   │       ├── java_prompt.py
│   │       ├── go_prompt.py
│   │       ├── ruby_prompt.py
│   │       └── typescript_prompt.py
│   │
│   └── vulnerability/          # 🔒 Vulnerability detection module (core)
│       └── src/
│           ├── main_workflow.py      # 🌟 LangGraph main workflow
│           │
│           ├── agents/               # Agent implementations
│           │   ├── logic_agent.py    # Logic defect agent
│           │   ├── security_agent.py # Security vulnerability agent
│           │   └── triage_agent.py   # Triage pre-screening agent
│           │
│           ├── analysis/             # Analysis engines
│           │   ├── risk_analyzer.py       # Risk analyzer
│           │   ├── cross_file_analyzer.py # Cross-file analyzer
│           │   ├── impact_analyzer.py     # Impact analyzer
│           │   ├── security_validator.py  # Security validator
│           │   └── hunk_index.py          # Hunk index
│           │
│           ├── scripts/             # Utility scripts
│           │   ├── core/
│           │   │   ├── code_tools.py       # Code tools
│           │   │   ├── context_builder.py  # Context builder
│           │   │   └── types.py            # Type definitions
│           │   ├── parsing/
│           │   │   ├── data_parser.py      # Data parser
│           │   │   └── diff_slicer.py      # Diff slicer
│           │   ├── scanning/
│           │   │   ├── parallel_semgrep_scanner.py    # Parallel Semgrep scanner
│           │   │   ├── template_semgrep_scanner.py    # Template Semgrep scanner
│           │   │   ├── scan_task_planner.py           # Scan task planner
│           │   │   └── security_tooling.py            # Security tooling
│           │   ├── reporting/
│           │   │   └── final_report_generator.py      # Final report generator
│           │   ├── todolist/
│           │   │   ├── todolist_generator.py          # TODO list generator
│           │   │   └── todolist_executor.py           # TODO list executor
│           │   ├── analysis/
│           │   │   ├── initialization_engine.py       # Initialization engine
│           │   │   └── vulnerability_analyzer.py      # Vulnerability analyzer (with LLM consensus & Nil-Guard)
│           │   └── smart_context_builder.py           # Smart context builder
│           │
│           ├── prompts/             # LLM prompts
│           │   ├── __init__.py
│           │   ├── prompt.py             # Main prompts
│           │   ├── schema_validator.py  # JSON schema validator
│           │   ├── markdown_renderer.py  # JSON-to-Markdown converter
│           │   ├── structured_output_helper.py  # Structured output integration
│           │   └── report_schema.json      # JSON schema for validation
│           │
│           ├── mcpTools/           # MCP tools integration
│           │   └── mcpTools.py
│           │
│           └── semgrep_rules/      # Semgrep rule templates (36+ templates)
│               └── templates/
│                   ├── c_*.template.yaml              # C language rules
│                   ├── go_*.template.yaml             # Go language rules
│                   ├── java_*.template.yaml           # Java language rules
│                   ├── py_*.template.yaml             # Python language rules
│                   ├── rb_*.template.yaml             # Ruby language rules
│                   └── ts_*.template.yaml             # TypeScript language rules
│
├── tools/                      # 🛠️ External tools integration
│   ├── base.py                 # Tool base class
│   ├── linter.py               # Multi-language Linter (Ruff, ESLint, golangci-lint, etc.)
│   ├── security_scanner.py     # Security scanner (Bandit, pattern matching)
│   └── static_analyzer.py      # Static analyzer
│
├── knowledge/                  # 📚 Knowledge base
│   ├── base.py                 # Knowledge base base class
│   ├── vulnerability_kb.py     # Vulnerability knowledge base
│   ├── code_patterns_kb.py     # Code patterns knowledge base
│   └── best_practices_kb.py    # Best practices knowledge base
│
├── output/                     # 📊 Output modules
│   ├── models.py               # Data models
│   └── report_generator.py     # Report generator
│
├── export/                     # 📤 Export modules
│   └── pr_exporter.py          # PR data exporter (metadata, diff, commits)
│
├── publish/                    # 📢 Publishing modules
│   └── github_publisher.py     # GitHub comment/review publisher
│
├── dev/                        # 🧪 Development/Testing
│   ├── architecture.md         # Architecture documentation
│   ├── test_workflow.py        # Workflow testing
│   └── test_hybrid_agent.py    # Agent testing
│
├── pr_export/                  # 📦 PR export data cache
│   └── Wise-Code-Watchers_*_PR*/
│
├── workspace/                  # 💼 Workspace (repo clone directories)
│   └── discourse-wcw/          # Example: Discourse project
│
└── secret/                     # 🔐 Secret storage
```

---


## 🚀 Quick Start

### Requirements

- Python 3.12+
- Docker (recommended)
- GitHub App configuration

### 1. Clone the Project

```bash
git clone https://github.com/your-org/wise-code-watchers.git
cd wise-code-watchers
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file:

```bash
# GitHub App Configuration
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY_PATH=/path/to/private-key.pem
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# LLM Configuration
BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your_openai_api_key
MODEL=gpt-4

# Langfuse Observability (Optional)
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_SAMPLE_RATE=1.0

# Service Configuration
PORT=3000

# Optional: Monitored Repositories (empty or * means monitor all)
MONITORED_REPOS=repo1,repo2,repo3
```

### 4. Run the Service

```bash
# Run directly
python app.py

# Or with Docker
docker-compose up -d
```

---

## ⚙️ Configuration

### Environment Variables

| Variable Name                | Required | Default            | Description                          |
| ---------------------------- | -------- | ------------------ | ------------------------------------ |
| `GITHUB_APP_ID`              | ✅        | -                  | GitHub App ID                        |
| `GITHUB_PRIVATE_KEY_PATH`    | ✅        | -                  | Private key file path                |
| `GITHUB_WEBHOOK_SECRET`      | ✅        | -                  | Webhook secret                       |
| `BASE_URL`                   | ⚠️        | -                  | LLM API base URL (OpenAI-compatible) |
| `OPENAI_API_KEY`             | ⚠️        | -                  | OpenAI API Key                       |
| `MODEL`                      | ❌        | `GLM-4.6`          | Model name                            |
| `PORT`                       | ❌        | `3000`             | Service port                         |
| `MONITORED_REPOS`            | ❌        | `*` (all)          | Comma-separated repository names to monitor (e.g., `repo1,repo2`). Empty or `*` means monitor all repositories where the GitHub App is installed |
| `LANGFUSE_PUBLIC_KEY`        | ❌        | -                  | Langfuse public key for LLM observability tracing |
| `LANGFUSE_SECRET_KEY`        | ❌        | -                  | Langfuse secret key for LLM observability tracing |
| `LANGFUSE_BASE_URL`          | ❌        | `https://cloud.langfuse.com` | Langfuse server URL (use your self-hosted URL) |
| `LANGFUSE_SAMPLE_RATE`       | ❌        | `1.0`              | Langfuse tracing sampling rate (0.0-1.0, 1.0 = trace all) |

### GitHub App Configuration

1. Create a GitHub App:
   - Homepage URL: Your service address
   - Webhook URL: `https://your-domain.com/webhook`
   - Webhook Secret: Custom secret

2. Permission Configuration:
   - **Repository permissions**:
     - Contents: Read
     - Pull requests: Read and write
     - Metadata: Read
   - **Subscribe to events**:
     - Pull request

3. Generate and download the private key file

---

## 🔍 Langfuse Observability

Wise Code Watchers integrates with [Langfuse](https://langfuse.com) for comprehensive LLM observability and tracing. All LangChain LLM calls, LangGraph workflows, and agent executions are automatically traced with rich metadata.

### What Gets Traced?

- **LLM Calls**: All OpenAI-compatible LLM invocations with prompts, responses, and token usage
- **LangGraph Workflows**: Multi-agent workflow execution with node-by-node tracing
- **Agent Executions**: Logic Agent, Security Agent, and Triage Agent operations
- **Tool Calls**: Semgrep scans, Git operations, and other tool executions
- **PR Metadata**: Repository name, PR number, author, branch, and change statistics

### Setting Up Langfuse

1. **Get Langfuse Credentials**:
   - Sign up at [langfuse.com](https://langfuse.com) or self-host Langfuse
   - Create a new project and generate API keys
   - Copy your public key and secret key

2. **Configure Environment Variables**:
   ```bash
   # Add to your .env file
   LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
   LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
   LANGFUSE_BASE_URL=https://cloud.langfuse.com  # or your self-hosted URL
   LANGFUSE_SAMPLE_RATE=1.0  # 1.0 = trace all, 0.1 = trace 10%
   ```

3. **Restart the Service**:
   ```bash
   python app.py
   ```

4. **Verify Tracing**:
   - Check logs for: `Langfuse initialized: <your-base-url>`
   - Trigger a PR review
   - Visit your Langfuse dashboard to see traces

### Trace Metadata

Each PR review trace includes:

- **Session ID**: `{repo_full_name}-{pr_number}`
- **User ID**: GitHub username of the PR author
- **Trace Name**: `pr-review-{repo_full_name}-{pr_number}`
- **Metadata**:
  - PR title and author
  - Base branch name
  - Additions/deletions count
  - Number of changed files

### Sampling Rate

Control what percentage of PR reviews get traced:

- `LANGFUSE_SAMPLE_RATE=1.0` - Trace all PR reviews (recommended for debugging)
- `LANGFUSE_SAMPLE_RATE=0.1` - Trace 10% of PR reviews (recommended for production)
- `LANGFUSE_SAMPLE_RATE=0.0` - Disable tracing

### Viewing Traces

Open your Langfuse dashboard to:

- **Search traces**: Filter by repo, PR number, or user
- **View timeline**: See the complete execution timeline with all LLM calls
- **Analyze performance**: Identify bottlenecks in agent execution
- **Debug issues**: Inspect prompts, responses, and error messages
- **Track costs**: Monitor token usage across all LLM calls

### Example Trace Structure

```
pr-review-org/repo-123
├── Export PR Data
├── Clone Repository
├── LangGraph Workflow
│   ├── Data Parsing
│   ├── Risk Analysis
│   ├── Semgrep Scanning
│   ├── Logic Agent
│   │   ├── LLM Call 1
│   │   └── LLM Call 2
│   ├── Security Agent
│   │   ├── LLM Call 1
│   │   └── LLM Call 2
│   └── Report Generation
└── Publish to GitHub
```

---

## 🔌 API Endpoints

### Webhook Endpoint

```
POST /webhook
```

Receives GitHub Webhook events. Supported events:

- `ping`: Health check
- `pull_request`: PR events (opened, synchronize, reopened)

### Health Check

```
GET /health
```

Returns service status.

---

## 🔄 Workflow

### Complete Review Process

```mermaid
sequenceDiagram
    participant GH as GitHub
    participant WH as Webhook Server
    participant EXP as PR Exporter
    participant WF as LangGraph Workflow
    participant LA as Logic Agent
    participant SA as Security Agent
    participant PUB as GitHub Publisher

    GH->>WH: PR Webhook Event (opened/synchronize)
    WH->>EXP: Export PR Data
    EXP->>GH: Fetch metadata, diff, commits
    EXP->>WF: Start Workflow

    WF->>WF: 1. Data Parsing (parse diff)
    WF->>WF: 2. Risk Analysis (AI risk assessment)
    WF->>WF: 3. Build Audit Units (build audit units)

    par Parallel Agent Analysis
        WF->>LA: Logic Review
        LA->>LA: Analyze logic defects
        LA-->>WF: Logic Issues
    and
        WF->>SA: Security Review
        SA->>SA: Analyze security vulnerabilities
        SA-->>WF: Security Issues
    end

    WF->>WF: 4. Generate Report
    WF->>PUB: Publish Results
    PUB->>GH: Create PR Review + Inline Comments
    GH-->>PUB: Review Created
```

### Workflow Node Details

| Node                   | Function                              | Input                    | Output            |
| ---------------------- | ------------------------------------- | ----------------------- | ----------------- |
| **Initialization**     | Initialize audit units, filter code   | PR directory            | Audit unit list   |
| **Data Parsing**       | Parse PR metadata and diff            | PR folder               | diff_ir, pr_data  |
| **Risk Analysis**      | AI-driven risk assessment             | diff_ir                 | feature_risk_plan |
| **Semgrep Scanning**   | Run security scanning rules           | Codebase                | semgrep_results   |
| **Logic Agent**        | Detect logic defects                  | Audit unit              | logic_review      |
| **Security Agent**     | Detect security vulnerabilities       | Audit unit + Semgrep evidence | security_review   |
| **Cross-File Analysis**| Analyze cross-file impact             | All analysis results    | cross_file_impact |
| **Report Generation**  | Generate final report                 | All analysis results    | final_report      |

---

## 🤖 Agents Details

### Logic Agent

**Responsibility**: Detect logic errors introduced or modified by PR diff

**Detection Types**:

- Boundary condition errors
- Null/null pointer handling
- Resource leaks
- Concurrency issues
- Algorithm errors

**Semgrep Evidence Enhancement** 🆕:

Logic Agent now supports Semgrep static analysis evidence enhancement, using the same evidence injection mechanism as Security Agent:

1. **Evidence Matching**: Precise matching of Semgrep findings by file path and line number range
2. **Prompt Enhancement**: Injects matched Semgrep findings into LLM prompts
3. **Pattern Reference**: Static analysis results serve as code pattern references to assist logic defect detection
4. **Parallel Execution**: Processes in parallel with Security Agent, both receiving Semgrep evidence

**Data Flow**:

```
Semgrep Scan (all_evidence.json)
    ↓
Match evidence by feature block
    ↓
Inject into Logic Agent prompt
    ↓
Enhanced logic defect detection
```

### Security Agent

**Responsibility**: Detect security vulnerabilities based on tool evidence

**Detection Types**:

- SQL Injection (SQLi)
- Command Injection (RCE)
- Server-Side Request Forgery (SSRF)
- Cross-Site Scripting (XSS)
- Insecure Deserialization
- Sensitive Information Leakage
- Authentication/Authorization Flaws

**Evidence-First Mechanism**:

1. `entrypoint_evidence`: External input sources
2. `call_chain_evidence`: Call chain analysis
3. `framework_evidence`: Framework auto-exposure
4. `context_evidence`: Contextual associations

### Triage Agent

**Responsibility**: Fast pre-screening to determine review priority

**Priorities**:

- P0: Urgent (high-risk security issues)
- P1: High (important logic issues)
- P2: Medium (general issues)
- P3: Low (minor issues)
- SKIP: Skip (tests/docs, etc.)

### Issue Scoring Filter

**Responsibility**: LLM-powered intelligent issue scoring and filtering system

**Function**: Scores all issues from agents on three dimensions and applies intelligent filtering

**Scoring Dimensions**:

1. **Relevance (relevance_score)**: How related is the issue to PR changes (0.0-1.0)
   - `1.0` = Directly in changed code, clearly introduced by this PR
   - `0.7` = In a changed file, likely affected by the changes
   - `0.4` = In related code, might be relevant
   - `0.1` = In unchanged code, unrelated to PR

2. **Severity (severity_score)**: How serious is this issue (0.0-1.0)
   - `1.0` = Critical - security vulnerability, crash, data loss
   - `0.8` = High - significant bug, logic error, resource leak
   - `0.5` = Medium - should fix but not urgent
   - `0.2` = Low - minor improvement, style issue

3. **Confidence (confidence_score)**: How confident in this assessment (0.0-1.0)
   - `1.0` = Very confident, clear evidence in the diff
   - `0.5` = Moderately confident
   - `0.2` = Uncertain, need more context

**Filtering Rules**:

- Must satisfy: `relevance >= 0.5` AND `severity >= 0.4` AND `confidence >= 0.3`
- Special handling: Test file issues → Low relevance, Production code vulnerabilities → High severity

**Workflow**:

```
All Issues from Agents
    ↓
LLM 3D Scoring (relevance/severity/confidence)
    ↓
Filter by Thresholds
    ↓
Output High-Quality Issues to GitHub
```

---

## 🔧 Tools Integration

### Linter Integration

Supported Linters:

| Language              | Tool                 | Detection Capabilities                      |
| --------------------- | -------------------- | ------------------------------------------- |
| Python                | Ruff                 | Code style, resource management, type check |
| JavaScript/TypeScript | ESLint               | Syntax errors, unused variables, Hook deps  |
| Go                    | golangci-lint        | Resource cleanup, SQL checks, security      |
| Ruby                  | RuboCop              | Code style, resource management             |
| Java                  | Checkstyle, SpotBugs | Code style, Bug detection                   |

### Security Scanners

- **Bandit**: Python security scanning
- **Pattern Matching**: Generic security pattern detection
- **Semgrep**: Custom rule scanning

---

## 📊 Output Reports

### Report Structure

```json
{
  "logic_review": {
    "issues_found": 2,
    "issues": [
      {
        "result": "ISSUE",
        "issues": [
          {
            "title": "Null Pointer Dereference Risk",
            "severity": "high",
            "location": {
              "file": "src/main.py",
              "line_start": 42,
              "line_end": 45
            },
            "description": "...",
            "evidence": "..."
          }
        ]
      }
    ]
  },
  "security_review": {
    "issues_found": 1,
    "issues": [...]
  },
  "cross_file_impact": {...},
  "summary": {...}
}
```

### GitHub Comment Example

The system automatically posts to PRs:

- **Summary Comment**: Contains overall review results
- **Inline Comments**: Adds comments at specific problematic code lines

---

## 🧪 Development & Testing

### Running Tests

```bash
# Workflow test
python dev/test_workflow.py

# Agent test
python dev/test_hybrid_agent.py
```

### Local Debugging

```bash
# Enable detailed logging
export ENABLE_DETAILED_LOGS=true
python app.py
```

---

## 🤝 Contributing

1. Fork this repository
2. Create a feature branch: `git checkout -b feature/AmazingFeature`
3. Commit changes: `git commit -m 'Add some AmazingFeature'`
4. Push to branch: `git push origin feature/AmazingFeature`
5. Submit a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) - LLM application framework
- [LangGraph](https://github.com/langchain-ai/langgraph) - Multi-agent workflow
- [Langfuse](https://langfuse.com) - LLM observability and tracing platform
- [Semgrep](https://github.com/semgrep/semgrep) - Code scanning engine
- [PyGithub](https://github.com/PyGithub/PyGithub) - GitHub API client

---

<p align="center">
  <strong>Made with ❤️ by Wise Code Watchers Team</strong>
</p>

**[中文版 README](README_ZH.md)**
