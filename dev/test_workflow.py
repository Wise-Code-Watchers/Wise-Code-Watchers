#!/usr/bin/env python3
"""
Wise Code Watchers - 工作流测试脚本

用于测试 LangGraph 工作流的完整流程。
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import Config
from langchain_openai import ChatOpenAI
from agents.vulnerability.src import WiseCodeWatchersWorkflow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_test_llm():
    """创建测试用的 LLM 实例"""
    kwargs = {
        "model": Config.LLM_MODEL,
        "temperature": 0,
    }
    if Config.LLM_API_KEY:
        kwargs["api_key"] = Config.LLM_API_KEY
    if Config.LLM_BASE_URL:
        kwargs["base_url"] = Config.LLM_BASE_URL
    return ChatOpenAI(**kwargs)


def test_workflow():
    """测试工作流"""
    # 配置测试参数
    pr_dir = os.environ.get("TEST_PR_DIR")
    codebase_path = os.environ.get("TEST_CODEBASE_PATH")

    if not pr_dir or not codebase_path:
        logger.error("请设置环境变量 TEST_PR_DIR 和 TEST_CODEBASE_PATH")
        logger.error("示例: export TEST_PR_DIR=/path/to/pr/folder")
        logger.error("      export TEST_CODEBASE_PATH=/path/to/codebase")
        sys.exit(1)

    logger.info(f"测试参数:")
    logger.info(f"  PR 目录: {pr_dir}")
    logger.info(f"  代码库路径: {codebase_path}")

    # 创建 LLM 和工作流
    llm = create_test_llm()
    workflow = WiseCodeWatchersWorkflow(llm=llm)

    # 运行工作流
    logger.info("开始运行工作流...")
    try:
        final_report = workflow.run(
            pr_dir=pr_dir,
            codebase_path=codebase_path,
            top_n=5,  # 测试时使用较小的值
            batch_size=2,
            max_workers=2
        )

        # 输出结果摘要
        logic_issues = final_report.get("logic_review", {}).get("issues_found", 0)
        security_issues = final_report.get("security_review", {}).get("issues_found", 0)
        total_issues = logic_issues + security_issues

        logger.info(f"工作流执行完成!")
        logger.info(f"  发现问题总数: {total_issues}")
        logger.info(f"  逻辑问题: {logic_issues}")
        logger.info(f"  安全问题: {security_issues}")

        # 保存报告
        report_path = os.path.join(pr_dir, "out", "test_report.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        import json
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(final_report, f, ensure_ascii=False, indent=2)
        logger.info(f"报告已保存到: {report_path}")

        return final_report

    except Exception as e:
        logger.error(f"工作流执行失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    logger.info("Wise Code Watchers - 工作流测试")
    logger.info("=" * 60)

    try:
        test_workflow()
        logger.info("=" * 60)
        logger.info("测试完成!")
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"测试失败: {e}")
        sys.exit(1)
