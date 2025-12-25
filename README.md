# WiseCodeWatcher (wcw)

Multi-agent PR review system that analyzes GitHub pull requests using LangChain, then posts review comments back to GitHub.

## Features

- **Webhook-driven**: Automatically triggers on PR opened/synchronize/reopened events
- **Multi-agent architecture**: 4 parallel AI agents (Structure, Memory, Logic, Security)
- **Enhanced vulnerability detection**: Risk-based analysis with tool evidence collection
- **GitHub App integration**: Posts inline comments and review summaries
- **Automatic codebase cloning**: Analyzes PRs with full repository context

## Prerequisites

- Python 3.12+
- GitHub App with webhook configured
- LLM API key (Anthropic, OpenAI compatible, or ZhipuAI)

## Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Configure the following environment variables in `.env`:
   ```bash
   # GitHub App
   GITHUB_APP_ID=your-app-id
   GITHUB_PRIVATE_KEY_PATH=./secret/private-key.pem
   GITHUB_WEBHOOK_SECRET=your-webhook-secret
   PORT=3000

   # LLM Configuration
   LLM_API_KEY=sk-...
   LLM_BASE_URL=https://api.openai.com/v1
   LLM_MODEL=gpt-4o-mini

   # Enhanced Vulnerability Detection (optional)
   VULN_RISK_THRESHOLD_LOGIC=60      # Risk score threshold for logic agent (0-100)
   VULN_RISK_THRESHOLD_SECURITY=35   # Risk score threshold for security agent (0-100)
   VULN_MAX_UNITS_LOGIC=12           # Max audit units for logic analysis
   VULN_MAX_UNITS_SECURITY=10        # Max audit units for security analysis
   ```

3. Place your GitHub App private key in the `secret/` directory.

## Running the App

```bash
source .venv/bin/activate
python app.py
```

The server starts on `http://0.0.0.0:3000` by default.

### Exposing to the Internet (for GitHub Webhooks)

GitHub needs to reach your webhook endpoint. Options:

**Option 1: ngrok (recommended for development)**
```bash
pip install pyngrok
ngrok config add-authtoken YOUR_NGROK_TOKEN
ngrok http 3000
```
Then update your GitHub App webhook URL to the ngrok URL.

**Option 2: Docker with reverse proxy**
```bash
docker-compose up -d
```

**Option 3: Direct deployment**
Deploy to a server with a public IP and configure your firewall to allow port 3000.

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook` | POST | GitHub webhook receiver |
| `/health` | GET | Health check |

## Architecture

### Agent Pipeline

```
Webhook → Export PR → Clone repo → Parse diff → Divide features
                                        ↓
          ┌─────────────┬───────────────┼───────────────┬─────────────┐
          ↓             ↓               ↓               ↓             
     Structure     Memory          Logic          Security
       Agent       Agent           Agent           Agent
          ↓             ↓               ↓               ↓             
          └─────────────┴───────────────┼───────────────┴─────────────┘
                                        ↓
                              Aggregate results → Publish to GitHub
```

### Enhanced Vulnerability Detection

The Logic and Security agents support two modes:

- **Legacy mode**: Uses feature points and changed files (backward compatible)
- **Enhanced mode**: Risk-based prioritization with hunk-level analysis

Enhanced mode activates automatically when `diff_ir` and `feature_risk_plan` are available.

## GitHub App Setup

1. Create a GitHub App with the following permissions:
   - **Pull requests**: Read & Write
   - **Contents**: Read
2. Subscribe to the `pull_request` webhook event
3. Set the webhook URL to `https://your-server/webhook`
4. Generate and download the private key

## Project Structure

```
wcw/
├── app.py                      # Flask webhook entry point
├── config.py                   # Environment configuration
├── agents/
│   ├── orchestrator.py         # Main entry - coordinates all agents
│   ├── aggregator.py           # Merges agent results
│   ├── base.py                 # BaseAgent class
│   ├── preprocessing/          # Diff parsing, feature division
│   ├── syntax/                 # structure_agent, memory_agent
│   └── vulnerability/          # logic_agent, security_agent
│       └── src/                # Enhanced analysis engine
│           ├── analysis/       # Risk analyzer, hunk indexing
│           ├── agents/         # Core agent implementations
│           ├── scripts/        # Scanning, reporting tools
│           └── prompts/        # Agent prompts
├── core/                       # GitHub/Git clients
├── export/                     # PR data exporter
├── knowledge/                  # Knowledge bases
├── output/                     # Data models and reports
├── publish/                    # GitHub publisher
└── tools/                      # External tools (linter, scanner)
```

## License

MIT
