#!/usr/bin/env python3
"""
测试 .env 配置文件是否正确

验证内容包括:
1. 必需的环境变量是否存在
2. GitHub 私钥文件是否存在且可读
3. GitHub App 配置是否有效
4. LLM API 配置是否可用
5. 监控的仓库配置格式是否正确
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ANSI 颜色代码
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")

def print_header(message):
    print(f"\n{Colors.BOLD}{message}{Colors.END}")
    print("=" * len(message))


def test_required_env_vars():
    """测试必需的环境变量"""
    print_header("1. 测试必需的环境变量")

    required_vars = {
        "GITHUB_APP_ID": "GitHub App ID",
        "GITHUB_PRIVATE_KEY_PATH": "GitHub 私钥文件路径",
        "GITHUB_WEBHOOK_SECRET": "Webhook 密钥",
        "PORT": "服务器端口",
    }

    optional_vars = {
        "BASE_URL": "LLM API 基础 URL",
        "OPENAI_API_KEY": "LLM API 密钥",
        "MODEL": "LLM 模型名称",
        "MONITORED_REPOS": "监控的仓库列表",
    }

    all_passed = True

    # 检查必需变量
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # 隐藏敏感信息
            if "SECRET" in var or "KEY" in var or "TOKEN" in var:
                display_value = f"{value[:8]}..." if len(value) > 8 else "***"
            else:
                display_value = value
            print_success(f"{description} ({var}): {display_value}")
        else:
            print_error(f"{description} ({var}): 未设置")
            all_passed = False

    # 检查可选变量
    print_info("\n可选配置:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            if "KEY" in var or "SECRET" in var or "TOKEN" in var:
                display_value = f"{value[:8]}..." if len(value) > 8 else "***"
            else:
                display_value = value
            print_success(f"{description} ({var}): {display_value}")
        else:
            print_warning(f"{description} ({var}): 未设置")

    return all_passed


def test_private_key_file():
    """测试 GitHub 私钥文件"""
    print_header("2. 测试 GitHub 私钥文件")

    key_path = os.getenv("GITHUB_PRIVATE_KEY_PATH")

    if not key_path:
        print_error("GITHUB_PRIVATE_KEY_PATH 未设置")
        return False

    print_info(f"私钥路径: {key_path}")

    # 检查文件是否存在
    if not os.path.exists(key_path):
        print_error(f"私钥文件不存在: {key_path}")
        return False
    print_success("私钥文件存在")

    # 检查文件是否可读
    if not os.path.isfile(key_path):
        print_error(f"路径不是文件: {key_path}")
        return False
    print_success("路径是有效的文件")

    # 尝试读取文件
    try:
        with open(key_path, 'r') as f:
            content = f.read()

        # 检查文件内容是否为空
        if not content.strip():
            print_error("私钥文件为空")
            return False

        # 检查是否包含 PEM 标记
        if "-----BEGIN RSA PRIVATE KEY-----" not in content:
            print_warning("文件可能不是有效的 PEM 格式 RSA 私钥")
            print_info("预期的格式应以 '-----BEGIN RSA PRIVATE KEY-----' 开头")
        elif "-----END RSA PRIVATE KEY-----" not in content:
            print_warning("私钥文件可能不完整")
        else:
            print_success("私钥文件格式正确 (PEM 格式)")

        print_success(f"私钥文件大小: {len(content)} 字节")
        return True

    except PermissionError:
        print_error("没有读取私钥文件的权限")
        return False
    except Exception as e:
        print_error(f"读取私钥文件时出错: {e}")
        return False


def test_github_app_config():
    """测试 GitHub App 配置"""
    print_header("3. 测试 GitHub App 配置")

    app_id = os.getenv("GITHUB_APP_ID")

    if not app_id:
        print_error("GITHUB_APP_ID 未设置")
        return False

    # 检查 App ID 是否为数字
    try:
        app_id_int = int(app_id)
        print_success(f"GitHub App ID: {app_id_int}")
    except ValueError:
        print_error(f"GitHub App ID 必须是数字,当前值: {app_id}")
        return False

    # 检查 Webhook Secret
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not webhook_secret:
        print_error("GITHUB_WEBHOOK_SECRET 未设置")
        return False

    if len(webhook_secret) < 20:
        print_warning(f"Webhook Secret 长度较短 ({len(webhook_secret)} 字符),建议使用更长的密钥")
    else:
        print_success(f"Webhook Secret 长度: {len(webhook_secret)} 字符")

    return True


def test_llm_config():
    """测试 LLM API 配置"""
    print_header("4. 测试 LLM API 配置")

    base_url = os.getenv("BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    model = os.getenv("MODEL") or os.getenv("LLM_MODEL")

    # 检查基础 URL
    if base_url:
        print_success(f"LLM API Base URL: {base_url}")
    else:
        print_warning("BASE_URL 未设置,将使用默认值")

    # 检查 API Key
    if api_key:
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        print_success(f"LLM API Key: {masked_key}")
    else:
        print_error("OPENAI_API_KEY 或 LLM_API_KEY 未设置")
        return False

    # 检查模型名称
    if model:
        print_success(f"LLM Model: {model}")
    else:
        print_warning("MODEL 未设置,将使用默认值 (GLM-4.6)")

    # 尝试导入 langchain_openai 以验证配置
    try:
        from langchain_openai import ChatOpenAI
        print_success("langchain_openai 库已安装")

        # 尝试创建 LLM 实例（不发送实际请求）
        try:
            kwargs = {
                "model": model or "GLM-4.6",
                "temperature": 0,
            }
            if api_key:
                kwargs["api_key"] = api_key
            if base_url:
                kwargs["base_url"] = base_url

            llm = ChatOpenAI(**kwargs)
            print_success("成功创建 LLM 实例 (配置验证通过)")
            return True
        except Exception as e:
            print_error(f"创建 LLM 实例失败: {e}")
            return False

    except ImportError:
        print_error("langchain_openai 库未安装")
        print_info("请运行: pip install langchain-openai")
        return False


def test_monitored_repos():
    """测试监控仓库配置"""
    print_header("5. 测试监控仓库配置")

    monitored_repos_str = os.getenv("MONITORED_REPOS", "").strip()

    if not monitored_repos_str or monitored_repos_str == "*":
        print_info("MONITORED_REPOS 未设置或设置为 '*'")
        print_info("将监控所有安装了此 GitHub App 的仓库")
        return True

    # 解析仓库列表
    repos = [repo.strip() for repo in monitored_repos_str.split(",") if repo.strip()]

    if not repos:
        print_warning("MONITORED_REPOS 设置为空")
        return True

    print_success(f"配置了 {len(repos)} 个监控仓库:")

    all_valid = True
    for repo in repos:
        # 支持两种格式: "repo" 或 "owner/repo"
        if "/" in repo:
            # 提取仓库名称
            repo_name = repo.split("/")[-1]
            print_success(f"  - {repo} (将监控仓库名: {repo_name})")
        else:
            # 直接使用仓库名称
            print_success(f"  - {repo}")

    return all_valid


def test_config_class():
    """测试 Config 类"""
    print_header("6. 测试 Config 类")

    try:
        from config import Config

        # 测试验证方法
        try:
            Config.validate()
            print_success("Config.validate() 通过")
        except ValueError as e:
            print_error(f"Config.validate() 失败: {e}")
            return False

        # 测试获取监控仓库
        monitored_repos = Config.get_monitored_repos()
        if monitored_repos:
            print_success(f"监控仓库数量: {len(monitored_repos)}")
            print_info(f"仓库名称列表: {', '.join(sorted(monitored_repos))}")
        else:
            print_info("监控所有仓库 (MONITORED_REPOS 为空)")

        # 测试仓库检查方法 - 使用新的仓库名匹配逻辑
        test_cases = [
            ("Wise-Code-Watchers/keycloak-wcw", "keycloak-wcw"),
            ("some-org/sentry-wcw", "sentry-wcw"),
            ("Wise-Code-Watchers/unknown-repo", "unknown-repo"),
            ("some-org/random-repo", "random-repo"),
        ]

        print_info("\n测试仓库监控匹配逻辑:")
        for repo_full_name, repo_name in test_cases:
            is_monitored = Config.is_repo_monitored(repo_full_name)
            status = f"{Colors.GREEN}监控{Colors.END}" if is_monitored else f"{Colors.YELLOW}不监控{Colors.END}"
            print(f"  {repo_full_name} (仓库名: {repo_name}): {status}")

        return True

    except Exception as e:
        print_error(f"导入或测试 Config 类失败: {e}")
        return False


def test_github_client():
    """测试 GitHub Client (可选)"""
    print_header("7. 测试 GitHub Client (可选)")

    try:
        from core.github_client import GitHubClient

        # 注意: 这里不创建实际的客户端实例,因为需要 installation_id
        print_info("GitHub Client 模块导入成功")
        print_info("实际连接测试需要有效的 installation_id")
        return True

    except Exception as e:
        print_error(f"导入 GitHub Client 失败: {e}")
        return False


def main():
    """主测试函数"""
    print(f"\n{Colors.BOLD}Wise Code Watchers - .env 配置测试工具{Colors.END}")
    print("=" * 60)

    results = {}

    # 运行所有测试
    results["环境变量"] = test_required_env_vars()
    results["私钥文件"] = test_private_key_file()
    results["GitHub App"] = test_github_app_config()
    results["LLM 配置"] = test_llm_config()
    results["监控仓库"] = test_monitored_repos()
    results["Config 类"] = test_config_class()
    results["GitHub Client"] = test_github_client()

    # 打印总结
    print_header("测试总结")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = f"{Colors.GREEN}通过{Colors.END}" if result else f"{Colors.RED}失败{Colors.END}"
        print(f"{test_name}: {status}")

    print(f"\n总计: {passed}/{total} 项测试通过")

    if all(results.values()):
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ 所有测试通过! .env 配置正确。{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ 部分测试失败,请检查配置。{Colors.END}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
