"""PR Functional Summary Agent - Generates functional summary of PR changes."""
import json
import logging
import os
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from src.config import Config

logger = logging.getLogger(__name__)


class PRSummaryAgent:
    """Agent to generate functional summary of PR changes."""

    def __init__(self, llm: ChatOpenAI = None):
        """Initialize the PR summary agent.

        Args:
            llm: Optional LLM instance. If not provided, creates default one.
        """
        self.llm = llm or self._create_default_llm()

    def _create_default_llm(self) -> ChatOpenAI:
        """Create default LLM instance."""
        kwargs = {
            "model": Config.LLM_MODEL,
            "temperature": 0.3,  # Slightly higher for more creative summaries
        }
        if Config.LLM_API_KEY:
            kwargs["api_key"] = Config.LLM_API_KEY
        if Config.LLM_BASE_URL:
            kwargs["base_url"] = Config.LLM_BASE_URL
        return ChatOpenAI(**kwargs)

    def generate_summary(
        self,
        pr_metadata: Dict[str, Any],
        files_changed: List[Dict[str, Any]],
        commits: List[Dict[str, Any]],
        full_diff: str = None
    ) -> Dict[str, Any]:
        """Generate functional summary of PR changes.

        Args:
            pr_metadata: PR metadata from GitHub API
            files_changed: List of changed files
            commits: List of commits with messages
            full_diff: Optional full diff text

        Returns:
            Dictionary containing functional summary with keys:
            - overview: High-level overview
            - key_changes: List of key functional changes
            - affected_components: List of affected components/modules
            - change_categories: Categorization of changes
            - complexity_assessment: Complexity assessment
        """
        # Prepare context for LLM
        context = self._prepare_summary_context(
            pr_metadata, files_changed, commits, full_diff
        )

        # Generate summary using LLM
        summary = self._generate_summary_with_llm(context)

        return {
            "overview": summary.get("overview", ""),
            "key_changes": summary.get("key_changes", []),
            "affected_components": summary.get("affected_components", []),
            "change_categories": summary.get("change_categories", {}),
            "complexity_assessment": summary.get("complexity_assessment", ""),
            "testing_suggestions": summary.get("testing_suggestions", []),
            "files_summary": {
                "total_files": len(files_changed),
                "added": sum(1 for f in files_changed if f.get("status") == "added"),
                "modified": sum(1 for f in files_changed if f.get("status") == "modified"),
                "deleted": sum(1 for f in files_changed if f.get("status") == "deleted"),
                "renamed": sum(1 for f in files_changed if f.get("status") == "renamed"),
            },
            "commits_summary": {
                "total_commits": len(commits),
                "commit_messages": [c.get("message", "") for c in commits],
            }
        }

    def _prepare_summary_context(
        self,
        pr_metadata: Dict[str, Any],
        files_changed: List[Dict[str, Any]],
        commits: List[Dict[str, Any]],
        full_diff: str = None
    ) -> str:
        """Prepare context text for LLM summary generation."""
        context_parts = [
            f"# Pull Request 功能分析请求\n",
            f"## PR 标题: {pr_metadata.get('title', 'N/A')}",
            f"## PR 描述:\n{pr_metadata.get('body', '无描述')}\n",
            f"## 作者: {pr_metadata.get('author', 'Unknown')}",
            f"## 目标分支: {pr_metadata.get('base_branch', 'main')}",
            f"## 源分支: {pr_metadata.get('head_branch', 'unknown')}",
            f"## 变更统计: +{pr_metadata.get('additions', 0)} -{pr_metadata.get('deletions', 0)} 行\n",
        ]

        # Files changed
        context_parts.append("## 修改文件:")
        for file in files_changed[:20]:  # Limit to first 20 files
            status_icon = {
                "added": "+",
                "modified": "~",
                "deleted": "-",
                "renamed": "→"
            }.get(file.get("status", ""), "?")
            context_parts.append(
                f"{status_icon} {file.get('filename', 'unknown')} "
                f"(+{file.get('additions', 0)} -{file.get('deletions', 0)})"
            )

        # Commit messages
        context_parts.append("\n## 提交记录:")
        for commit in commits[:10]:  # Limit to first 10 commits
            msg = commit.get("message", "").split("\n")[0]  # First line only
            sha = commit.get("sha", "")[:8]
            context_parts.append(f"- {sha}: {msg}")

        # Add truncated diff if available (limit to 5000 chars)
        if full_diff and len(full_diff) > 0:
            truncated_diff = full_diff[:5000]
            if len(full_diff) > 5000:
                truncated_diff += "\n... (已截断)"
            context_parts.append(f"\n## 代码差异 (前5000字符):\n{truncated_diff}")

        context_parts.append("\n" + "="*80)
        context_parts.append(
            "基于以上信息,请提供此PR的**功能分析总结**。"
            "重点关注:修改了什么功能、为什么修改、影响了哪些模块。"
            "不要关注安全性或脆弱性分析,仅从功能角度分析。"
        )

        return "\n".join(context_parts)

    def _generate_summary_with_llm(self, context: str) -> Dict[str, Any]:
        """Generate summary using LLM."""
        prompt = f"""{context}

请提供一个结构化的功能分析总结,使用以下JSON格式:

{{
    "overview": "用2-3句话概述这个PR的主要功能和目的",
    "key_changes": [
        "具体的功能变更1",
        "具体的功能变更2",
        ...
    ],
    "affected_components": [
        "受影响的组件/模块1",
        "受影响的组件/模块2",
        ...
    ],
    "change_categories": {{
        "feature": ["新功能或增强"],
        "bugfix": ["缺陷修复"],
        "refactor": ["重构或优化"],
        "performance": ["性能改进"],
        "documentation": ["文档更新"],
        "tests": ["测试相关"],
        "config": ["配置变更"],
        "other": ["其他变更"]
    }},
    "complexity_assessment": "复杂度评估(低/中/高)及原因说明",
    "testing_suggestions": [
        "建议测试的功能点1",
        "建议测试的功能点2",
        ...
    ]
}}

注意:
1. 所有内容使用中文
2. 只关注功能分析,不涉及安全性或脆弱性
3. 从用户角度和业务价值角度描述变更
4. 提供实用的测试建议

只返回JSON,不要有其他文本。"""

        try:
            response = self.llm.invoke(prompt)
            response_text = response.content.strip()

            # Extract JSON from response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            summary = json.loads(response_text)
            logger.info("Successfully generated PR functional summary")
            return summary

        except Exception as e:
            logger.error(f"Failed to generate summary with LLM: {e}", exc_info=True)
            # Return fallback summary
            return {
                "overview": "无法自动生成功能总结",
                "key_changes": ["无法解析具体变更"],
                "affected_components": [],
                "change_categories": {},
                "complexity_assessment": "无法评估复杂度",
                "testing_suggestions": []
            }

    def save_summary(self, summary: Dict[str, Any], output_dir: str):
        """Save functional summary to JSON file.

        Args:
            summary: Generated summary dictionary
            output_dir: Directory to save summary
        """
        os.makedirs(output_dir, exist_ok=True)
        summary_path = f"{output_dir}/functional_summary.json"

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved functional summary to {summary_path}")
