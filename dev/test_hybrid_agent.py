#!/usr/bin/env python3
"""
Wise Code Watchers - Agent 测试脚本

用于测试单个 Agent 的功能。
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
from agents.vulnerability.src.agents.logic_agent import LogicAgent
from agents.vulnerability.src.agents.security_agent import SecurityAgent
from agents.vulnerability.src.agents.triage_agent import TriageAgent

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


def test_logic_agent(llm, audit_unit):
    """测试逻辑 Agent"""
    logger.info("测试 Logic Agent...")

    agent = LogicAgent(llm=llm)
    result = agent.analyze(audit_unit=audit_unit)

    logger.info(f"Logic Agent 结果:")
    logger.info(f"  结果类型: {result.get('result')}")
    logger.info(f"  发现问题: {result.get('issues_found', 0)}")

    return result


def test_security_agent(llm, audit_unit, semgrep_evidence=None):
    """测试安全 Agent"""
    logger.info("测试 Security Agent...")

    agent = SecurityAgent(llm=llm)
    result = agent.analyze(
        audit_unit=audit_unit,
        semgrep_evidence=semgrep_evidence or {}
    )

    logger.info(f"Security Agent 结果:")
    logger.info(f"  结果类型: {result.get('result')}")
    logger.info(f"  发现问题: {result.get('issues_found', 0)}")

    return result


def test_triage_agent(llm, audit_units):
    """测试分类 Agent"""
    logger.info("测试 Triage Agent...")

    agent = TriageAgent(llm=llm)
    results = agent.classify(audit_units=audit_units)

    logger.info(f"Triage Agent 结果:")
    for priority, units in results.items():
        logger.info(f"  {priority}: {len(units)} 个单元")

    return results


def main():
    """主测试函数"""
    logger.info("Wise Code Watchers - Agent 测试")
    logger.info("=" * 60)

    # 创建 LLM
    llm = create_test_llm()

    # 准备测试数据
    test_audit_unit = {
        "unit_id": "test_1",
        "file_path": "test.py",
        "language": "python",
        "feature_name": "test_feature",
        "hunks": [
            {
                "hunk_number": 1,
                "line_start": 10,
                "line_end": 20,
                "added_lines": ["def test_function():", "    pass", "    return None"],
            }
        ],
        "risk_score": 50,
        "feature_summary": "测试功能",
    }

    # 测试 Logic Agent
    try:
        logic_result = test_logic_agent(llm, test_audit_unit)
        logger.info("✓ Logic Agent 测试通过")
    except Exception as e:
        logger.error(f"✗ Logic Agent 测试失败: {e}")

    # 测试 Security Agent
    try:
        security_result = test_security_agent(llm, test_audit_unit)
        logger.info("✓ Security Agent 测试通过")
    except Exception as e:
        logger.error(f"✗ Security Agent 测试失败: {e}")

    # 测试 Triage Agent
    try:
        triage_result = test_triage_agent(llm, [test_audit_unit])
        logger.info("✓ Triage Agent 测试通过")
    except Exception as e:
        logger.error(f"✗ Triage Agent 测试失败: {e}")

    logger.info("=" * 60)
    logger.info("测试完成!")


if __name__ == "__main__":
    main()
