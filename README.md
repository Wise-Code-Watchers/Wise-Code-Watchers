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

## 📖 项目简介

**Wise Code Watchers** 是一个基于 LangGraph 多 Agent 架构的智能代码审查系统，以 GitHub App 的形式运行，自动对 Pull Request 进行深度代码审查。系统能够自动检测逻辑缺陷、安全漏洞，并将审查结果以行内评论的形式发布到 GitHub PR 中。

### ✨ 核心特性

- 🤖 **多 Agent 协作架构**：基于 LangGraph 的工作流引擎，多个专业 Agent 并行协作
- 🔒 **安全漏洞检测**：专业的 Security Agent 结合 Semgrep 规则检测安全漏洞
- 🧠 **逻辑缺陷分析**：Logic Agent 深度分析代码逻辑，发现潜在 Bug
- 📊 **智能风险评估**：AI 驱动的风险评分系统，优先审查高风险代码
- 🔗 **跨文件分析**：分析代码变更的跨文件影响
- 💬 **GitHub 深度集成**：自动发布行内评论到 PR，支持 GitHub App Webhook

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Wise Code Watchers                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────────┐  │
│  │  GitHub App  │───▶│   Webhook    │───▶│       PR Exporter            │  │
│  │   Webhook    │    │   Handler    │    │  (metadata/diff/commits)     │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────────┘  │
│                                                      │                       │
│                                                      ▼                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     LangGraph Workflow Engine                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  │
│  │  │ Data Parse  │─▶│ Risk Analyze│─▶│  Triage    │─▶│  Parallel   │   │  │
│  │  │    Node     │  │    Node     │  │   Node      │  │  Analysis   │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │  │
│  │                                                            │           │  │
│  │                    ┌─────────────────────┬────────────────┘            │  │
│  │                    ▼                     ▼                               │  │
│  │            ┌──────────────┐      ┌──────────────┐                       │  │
│  │            │ Logic Agent  │      │Security Agent│                       │  │
│  │            │  (缺陷检测)  │      │  (漏洞检测)  │                       │  │
│  │            └──────────────┘      └──────────────┘                       │  │
│  │                    │                      │                               │  │
│  │                    └──────────┬───────────┘                               │  │
│  │                               ▼                                         │  │
│  │                    ┌──────────────────┐                                  │  │
│  │                    │ Report Generator │                                │  │
│  │                    └──────────────────┘                                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                        │                                     │
│                                        ▼                                     │
│                         ┌──────────────────────────┐                        │
│                         │    GitHub Publisher      │                        │
│                         │  (PR Comments/Reviews)   │                        │
│                         └──────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 项目结构

```
wise-code-watchers/
├── app.py                      # 🚀 主应用入口 (Flask Webhook Server)
├── config.py                   # ⚙️ 配置管理
├── requirements.txt            # 📦 Python 依赖
├── Dockerfile                  # 🐳 Docker 镜像配置
├── docker-compose.yml          # 🐳 Docker Compose 配置
│
├── core/                       # 🔧 核心模块
│   ├── github_client.py        # GitHub API 客户端
│   ├── git_client.py           # Git 操作客户端
│   └── repo_manager.py         # 仓库管理器
│
├── agents/                     # 🤖 Agent 模块
│   ├── base.py                 # Agent 基类
│   ├── aggregator.py           # 结果聚合器
│   ├── orchestrator.py         # Agent 编排器
│   ├── issue_scoring_filter.py # Issue 评分过滤器
│   │
│   ├── preprocessing/          # 预处理模块
│   │   ├── diff_parser.py      # Diff 解析器
│   │   ├── description_analyzer.py # PR 描述分析
│   │   └── feature_divider.py  # 功能特性分割
│   │
│   ├── syntax/                 # 语法分析模块
│   │   ├── syntax_analysis_agent.py
│   │   ├── syntax_checker.py
│   │   ├── structure_agent.py
│   │   ├── memory_agent.py
│   │   └── prompts/            # 提示词模板
│   │
│   └── vulnerability/          # 🔒 漏洞检测模块 (核心)
│       ├── logic_agent.py      # 逻辑缺陷 Agent
│       ├── security_agent.py   # 安全漏洞 Agent
│       └── src/
│           ├── main_workflow.py    # 🌟 LangGraph 主工作流
│           ├── agents/
│           │   ├── logic_agent.py    # 增强版逻辑 Agent
│           │   ├── security_agent.py # 增强版安全 Agent
│           │   └── triage_agent.py   # 分类预筛 Agent
│           ├── analysis/           # 分析引擎
│           │   ├── risk_analyzer.py     # 风险分析
│           │   ├── cross_file_analyzer.py # 跨文件分析
│           │   ├── impact_analyzer.py   # 影响分析
│           │   └── security_validator.py # 安全验证
│           ├── prompts/            # LLM 提示词
│           ├── scripts/            # 辅助脚本
│           │   ├── scanning/       # 扫描工具
│           │   ├── parsing/        # 解析工具
│           │   └── todolist/       # TODO 列表生成
│           ├── mcpTools/           # MCP 工具集成
│           └── semgrep_rules/      # Semgrep 规则模板
│
├── tools/                      # 🛠️ 外部工具集成
│   ├── base.py                 # 工具基类
│   ├── linter.py               # 多语言 Linter
│   ├── security_scanner.py     # 安全扫描器
│   └── static_analyzer.py      # 静态分析器
│
├── knowledge/                  # 📚 知识库
│   ├── base.py                 # 知识库基类
│   ├── vulnerability_kb.py     # 漏洞知识库
│   ├── code_patterns_kb.py     # 代码模式库
│   └── best_practices_kb.py    # 最佳实践库
│
├── output/                     # 📊 输出模块
│   ├── models.py               # 数据模型
│   └── report_generator.py     # 报告生成器
│
├── export/                     # 📤 导出模块
│   └── pr_exporter.py          # PR 数据导出
│
├── publish/                    # 📢 发布模块
│   └── github_publisher.py     # GitHub 评论发布
│
├── dev/                        # 🧪 开发/测试
│   ├── architecture.md         # 架构文档
│   ├── test_workflow.py        # 工作流测试
│   └── test_hybrid_agent.py    # Agent 测试
│
└── docs/                       # 📖 文档
    └── linter-installation.md  # Linter 安装指南
```

---

## 🔄 工作流程

### 完整审查流程

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
    
    WF->>WF: 1. Data Parsing (解析 diff)
    WF->>WF: 2. Risk Analysis (AI 风险评估)
    WF->>WF: 3. Build Audit Units (构建审计单元)
    
    par Parallel Agent Analysis
        WF->>LA: Logic Review
        LA->>LA: 分析逻辑缺陷
        LA-->>WF: Logic Issues
    and
        WF->>SA: Security Review
        SA->>SA: 分析安全漏洞
        SA-->>WF: Security Issues
    end
    
    WF->>WF: 4. Generate Report
    WF->>PUB: Publish Results
    PUB->>GH: Create PR Review + Inline Comments
    GH-->>PUB: Review Created
```

### 工作流节点详解

| 节点                    | 功能                                 | 输入                    | 输出              |
| ----------------------- | ------------------------------------ | ----------------------- | ----------------- |
| **Initialization**      | 初始化审计单元，过滤不需要审查的代码 | PR 目录                 | 审计单元列表      |
| **Data Parsing**        | 解析 PR 元数据和 diff                | PR 文件夹               | diff_ir, pr_data  |
| **Risk Analysis**       | AI 驱动的风险评估                    | diff_ir                 | feature_risk_plan |
| **Semgrep Scanning**    | 运行安全扫描规则                     | 代码库                  | semgrep_results   |
| **Logic Agent**         | 检测逻辑缺陷                         | 审计单元                | logic_review      |
| **Security Agent**      | 检测安全漏洞                         | 审计单元 + Semgrep 证据 | security_review   |
| **Cross-File Analysis** | 分析跨文件影响                       | 所有分析结果            | cross_file_impact |
| **Report Generation**   | 生成最终报告                         | 所有分析结果            | final_report      |

---

## 🚀 快速开始

### 环境要求

- Python 3.12+
- Docker (推荐)
- GitHub App 配置

### 1. 克隆项目

```bash
git clone https://github.com/your-org/wise-code-watchers.git
cd wise-code-watchers
```

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件：

```bash
# GitHub App 配置
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY_PATH=/path/to/private-key.pem
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# LLM 配置
OPENAI_API_KEY=your_openai_api_key
# 或使用兼容 OpenAI 的 API
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=gpt-4

# 服务配置
PORT=3000

# 可选：漏洞检测阈值
VULN_RISK_THRESHOLD_LOGIC=60
VULN_RISK_THRESHOLD_SECURITY=35
VULN_MAX_UNITS_LOGIC=12
VULN_MAX_UNITS_SECURITY=10
```

### 4. 运行服务

```bash
# 直接运行
python app.py

```



---

## ⚙️ 配置说明

### 环境变量

| 变量名                         | 必需 | 默认值    | 说明                    |
| ------------------------------ | ---- | --------- | ----------------------- |
| `GITHUB_APP_ID`                | ✅    | -         | GitHub App ID           |
| `GITHUB_PRIVATE_KEY_PATH`      | ✅    | -         | 私钥文件路径            |
| `GITHUB_WEBHOOK_SECRET`        | ✅    | -         | Webhook 密钥            |
| `OPENAI_API_KEY`               | ⚠️    | -         | OpenAI API Key          |
| `LLM_BASE_URL`                 | ❌    | -         | 兼容 OpenAI 的 API 地址 |
| `LLM_MODEL`                    | ❌    | `GLM-4.6` | 模型名称                |
| `PORT`                         | ❌    | `3000`    | 服务端口                |
| `VULN_RISK_THRESHOLD_LOGIC`    | ❌    | `60`      | 逻辑审查风险阈值        |
| `VULN_RISK_THRESHOLD_SECURITY` | ❌    | `35`      | 安全审查风险阈值        |

### GitHub App 配置

1. 创建 GitHub App：
   - Homepage URL: 你的服务地址
   - Webhook URL: `https://your-domain.com/webhook`
   - Webhook Secret: 自定义密钥

2. 权限配置：
   - **Repository permissions**:
     - Contents: Read
     - Pull requests: Read and write
     - Metadata: Read
   - **Subscribe to events**:
     - Pull request

3. 生成并下载私钥文件

---

## 🔌 API 端点

### Webhook 端点

```
POST /webhook
```

接收 GitHub Webhook 事件。支持的事件：

- `ping`: 健康检查
- `pull_request`: PR 事件 (opened, synchronize, reopened)

### 健康检查

```
GET /health
```

返回服务状态。

---

## 🤖 Agent 详解

### Logic Agent

**职责**：检测由 PR diff 引入或修改导致的逻辑错误

**检测类型**：

- 边界条件错误
- 空值/空指针处理
- 资源泄漏
- 并发问题
- 算法错误

### Security Agent

**职责**：基于工具证据检测安全漏洞

**检测类型**：

- SQL 注入 (SQLi)
- 命令注入 (RCE)
- 服务端请求伪造 (SSRF)
- 跨站脚本 (XSS)
- 不安全的反序列化
- 敏感信息泄露
- 认证/授权缺陷

**证据先行机制**：

1. `entrypoint_evidence`: 外部输入来源
2. `call_chain_evidence`: 调用链分析
3. `framework_evidence`: 框架自动暴露
4. `context_evidence`: 上下文关联

### Triage Agent

**职责**：快速预筛选，确定审查优先级

**优先级**：

- P0: 紧急 (高风险安全问题)
- P1: 高 (重要逻辑问题)
- P2: 中 (一般问题)
- P3: 低 (轻微问题)
- SKIP: 跳过 (测试/文档等)

---

## 🔧 工具集成

### Linter 集成

支持的 Linter：

| 语言                  | 工具                 | 检测能力                        |
| --------------------- | -------------------- | -------------------------------|
| Python                | Ruff                 | 代码风格、资源管理、类型检查     |
| JavaScript/TypeScript | ESLint               | 语法错误、未使用变量、Hook 依赖  |
| Go                    | golangci-lint        | 资源关闭、SQL 检查、安全问题     |
| Ruby                  | RuboCop              | 代码风格、资源管理               |
| Java                  | Checkstyle, SpotBugs | 代码风格、Bug 检测              |

### 安全扫描器

- **Bandit**: Python 安全扫描
- **模式匹配扫描**: 通用安全模式检测
- **Semgrep**: 自定义规则扫描

---

## 📊 输出报告

### 报告结构

```json
{
  "logic_review": {
    "issues_found": 2,
    "issues": [
      {
        "result": "ISSUE",
        "issues": [
          {
            "title": "空指针解引用风险",
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

### GitHub 评论示例

系统会自动在 PR 中发布：

- **总结评论**：包含整体审查结果
- **行内评论**：在具体问题代码行添加评论

---

## 🧪 开发与测试

### 运行测试

```bash
# 工作流测试
python dev/test_workflow.py

# Agent 测试
python dev/test_hybrid_agent.py
```

### 本地调试

```bash
# 启用详细日志
export ENABLE_DETAILED_LOGS=true
python app.py
```

---

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送分支：`git push origin feature/AmazingFeature`
5. 提交 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - 多 Agent 工作流
- [Semgrep](https://github.com/semgrep/semgrep) - 代码扫描引擎
- [PyGithub](https://github.com/PyGithub/PyGithub) - GitHub API 客户端

---

<p align="center">
  <strong>Made with ❤️ by Wise Code Watchers Team</strong>
</p>

