# Wise Code Watchers 架构文档

## 系统概述

Wise Code Watchers 是一个基于 LangGraph 多 Agent 架构的智能代码审查系统,专门用于自动审查 GitHub Pull Request。

## 核心架构

### 1. 数据流架构

```
GitHub Webhook → Flask Server → PR Exporter → LangGraph Workflow → Report Generator → GitHub Publisher
```

### 2. 模块划分

#### 2.1 Core Module (核心模块)
- **github_client.py**: GitHub API 客户端,处理与 GitHub 的所有交互
- **git_client.py**: Git 操作客户端,负责代码仓库的克隆和清理
- **repo_manager.py**: 仓库管理器,统一管理仓库相关操作

#### 2.2 Agents Module (Agent 模块)
- **base.py**: Agent 基类,定义所有 Agent 的通用接口
- **orchestrator.py**: Agent 编排器,协调多个 Agent 的执行
- **aggregator.py**: 结果聚合器,聚合多个 Agent 的分析结果
- **issue_scoring_filter.py**: Issue 评分过滤器,对发现的问题进行评分和过滤

##### 2.2.1 Preprocessing Module (预处理模块)
- **diff_parser.py**: Diff 解析器,解析 PR 的代码变更
- **description_analyzer.py**: PR 描述分析器,分析 PR 的描述信息
- **feature_divider.py**: 功能特性分割器,将 PR 分割为多个功能特性

##### 2.2.2 Syntax Module (语法分析模块)
- **syntax_analysis_agent.py**: 语法分析 Agent
- **syntax_checker.py**: 语法检查器
- **structure_agent.py**: 结构分析 Agent
- **memory_agent.py**: 记忆 Agent,维护代码的上下文记忆
- **prompts/**: 提示词模板,存储各种语言的提示词

##### 2.2.3 Vulnerability Module (漏洞检测模块 - 核心)
- **logic_agent.py**: 逻辑缺陷 Agent,检测逻辑错误
- **security_agent.py**: 安全漏洞 Agent,检测安全漏洞
- **src/main_workflow.py**: LangGraph 主工作流
- **src/agents/**: 增强版 Agent 实现
  - **logic_agent.py**: 增强版逻辑 Agent
  - **security_agent.py**: 增强版安全 Agent
  - **triage_agent.py**: 分类预筛 Agent
- **src/analysis/**: 分析引擎
  - **risk_analyzer.py**: 风险分析器
  - **cross_file_analyzer.py**: 跨文件分析器
  - **impact_analyzer.py**: 影响分析器
  - **security_validator.py**: 安全验证器
- **src/prompts/**: LLM 提示词
- **src/scripts/**: 辅助脚本
  - **scanning/**: 扫描工具
  - **parsing/**: 解析工具
  - **todolist/**: TODO 列表生成
- **src/mcpTools/**: MCP 工具集成
- **src/semgrep_rules/**: Semgrep 规则模板

#### 2.3 Tools Module (工具集成模块)
- **base.py**: 工具基类
- **linter.py**: 多语言 Linter 集成
- **security_scanner.py**: 安全扫描器
- **static_analyzer.py**: 静态分析器

#### 2.4 Knowledge Module (知识库模块)
- **base.py**: 知识库基类
- **vulnerability_kb.py**: 漏洞知识库
- **code_patterns_kb.py**: 代码模式库
- **best_practices_kb.py**: 最佳实践库

#### 2.5 Output Module (输出模块)
- **models.py**: 数据模型定义
- **report_generator.py**: 报告生成器

#### 2.6 Export Module (导出模块)
- **pr_exporter.py**: PR 数据导出器

#### 2.7 Publish Module (发布模块)
- **github_publisher.py**: GitHub 评论发布器

## LangGraph 工作流详解

### 工作流节点

1. **Initialization Node**: 初始化审计单元
2. **Data Parsing Node**: 解析 PR 元数据和 diff
3. **Risk Analysis Node**: AI 驱动的风险评估
4. **Triage Node**: 分类预筛,确定审查优先级
5. **Parallel Analysis Node**: 并行分析节点
   - **Logic Agent**: 检测逻辑缺陷
   - **Security Agent**: 检测安全漏洞
6. **Report Generator Node**: 生成最终报告

### 数据流转

```python
PR Event → PR Exporter → LangGraph State
State = {
    "pr_dir": str,
    "codebase_path": str,
    "diff_ir": dict,
    "pr_data": dict,
    "audit_units": list,
    "feature_risk_plan": dict,
    "logic_review": dict,
    "security_review": dict,
    "cross_file_impact": dict,
    "final_report": dict
}
```

## 关键设计决策

### 1. 多 Agent 协作
采用 LangGraph 实现状态机式的多 Agent 协作,每个 Agent 专注于特定领域的问题检测。

### 2. 证据先行机制
Security Agent 采用证据先行机制,在报告漏洞前必须有工具证据支持:
- entrypoint_evidence: 外部输入来源
- call_chain_evidence: 调用链分析
- framework_evidence: 框架自动暴露
- context_evidence: 上下文关联

### 3. 智能风险评估
使用 AI 对代码变更进行风险评估,优先审查高风险代码,提高审查效率。

### 4. 跨文件分析
分析代码变更的跨文件影响,发现因修改引入的连锁问题。

## 性能优化

1. **并行扫描**: 使用多进程并行执行 Semgrep 扫描
2. **批量处理**: 批量处理审计单元,减少 LLM 调用次数
3. **缓存机制**: 缓存代码克隆结果,避免重复下载
4. **增量分析**: 只分析变更的代码,减少分析范围

## 扩展性

### 添加新的 Agent
1. 继承 `agents.base.AgentBase`
2. 实现 `analyze` 方法
3. 在 `orchestrator.py` 中注册

### 添加新的 Linter
1. 在 `tools/linter.py` 中添加新的 Linter 配置
2. 更新知识库以支持新的规则

### 添加新的扫描规则
1. 在 `agents/vulnerability/src/semgrep_rules/` 中添加规则模板
2. 在 `knowledge/` 中更新漏洞知识库

## 安全考虑

1. **GitHub Webhook 签名验证**: 验证所有 Webhook 请求的签名
2. **密钥管理**: 使用环境变量管理敏感信息
3. **权限最小化**: GitHub App 只申请必要的权限
4. **代码沙箱**: 克隆的代码在隔离环境中运行

## 监控和日志

- 使用 Python logging 模块记录关键操作
- 支持 DEBUG 级别的详细日志
- 通过 `ENABLE_DETAILED_LOGS` 环境变量控制
