import hmac
import hashlib
import logging
import json
import os
import threading
import time
import atexit
import signal
from queue import Queue
from flask import Flask, request, jsonify
from config import Config
from core.github_client import GitHubClient
from core.git_client import GitClient
from export.pr_exporter import PRExporter
from publish.github_publisher import GitHubPublisher

from langchain_openai import ChatOpenAI
from agents.vulnerability.src import WiseCodeWatchersWorkflow

from langfuse import get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize Langfuse client for tracing
langfuse_client = None
langfuse_handler = None

try:
    if Config.LANGFUSE_PUBLIC_KEY and Config.LANGFUSE_SECRET_KEY:
        langfuse_client = get_client()
        langfuse_handler = CallbackHandler()
        logger.info(f"Langfuse initialized: {Config.LANGFUSE_BASE_URL}")
        logger.info(f"Langfuse tracing enabled with sample_rate={Config.LANGFUSE_SAMPLE_RATE}")
    else:
        logger.warning("Langfuse credentials not found, tracing disabled")
except Exception as e:
    logger.error(f"Failed to initialize Langfuse: {e}")
    langfuse_client = None
    langfuse_handler = None

# 任务队列和线程池
task_queue = Queue()
worker_threads = []
MAX_WORKERS = 2  # 降低并行数以避免GitHub API速率限制

# GitHub Client 缓存 (按installation_id共享token)
github_client_cache = {}
github_client_lock = threading.Lock()


def get_github_client(installation_id: int) -> GitHubClient:
    """获取或创建缓存的GitHub客户端实例"""
    with github_client_lock:
        if installation_id not in github_client_cache:
            github_client_cache[installation_id] = GitHubClient(installation_id)
            logger.info(f"Created new GitHubClient for installation {installation_id}")
        return github_client_cache[installation_id]


class PRTask:
    """PR 任务包装类"""

    def __init__(self, payload: dict):
        self.payload = payload
        self.created_at = time.time()
        self.pr_number = payload.get("pull_request", {}).get("number")
        self.repo_full_name = payload.get("repository", {}).get("full_name")

    def __repr__(self):
        return f"PRTask(PR#{self.pr_number} in {self.repo_full_name})"


def create_workflow_llm(callbacks=None) -> ChatOpenAI:
    """Create LLM instance for the comprehensive workflow (OpenAI-compatible API)."""
    kwargs = {
        "model": Config.LLM_MODEL,
        "temperature": 0,
    }
    if Config.LLM_API_KEY:
        kwargs["api_key"] = Config.LLM_API_KEY
    if Config.LLM_BASE_URL:
        kwargs["base_url"] = Config.LLM_BASE_URL

    # Initialize with Langfuse callback handler if available
    if langfuse_handler:
        if callbacks is None:
            callbacks = [langfuse_handler]
        else:
            callbacks = callbacks + [langfuse_handler]

    if callbacks:
        kwargs["callbacks"] = callbacks

    return ChatOpenAI(**kwargs)


def verify_signature(payload: bytes, signature: str) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        Config.GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def process_pr_task(task: PRTask):
    """处理单个PR任务 - 在后台线程中运行"""
    payload = task.payload
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    installation = payload.get("installation", {})

    pr_number = pr.get("number")
    repo_full_name = repo.get("full_name")
    installation_id = installation.get("id")
    base_branch = pr.get("base", {}).get("ref", "main")

    thread_name = threading.current_thread().name
    logger.info(f"[{thread_name}] Starting PR #{pr_number} processing in {repo_full_name}")

    # Langfuse Trace Context
    session_id = f"{repo_full_name}-{pr_number}"
    user_id = payload.get("sender", {}).get("login", "unknown")

    with propagate_attributes(
        session_id=session_id,
        user_id=user_id,
        metadata={
            "pr_number": pr_number,
            "repo_full_name": repo_full_name,
            "action": action,
            "installation_id": installation_id,
        }
    ):
        if langfuse_client:
            langfuse_client.update_current_trace(
                name=f"pr-review-{repo_full_name}-{pr_number}",
                session_id=session_id,
                user_id=user_id,
                metadata={
                    "pr_title": pr.get("title", ""),
                    "pr_author": pr.get("user", {}).get("login", ""),
                    "base_branch": base_branch,
                    "pr_additions": pr.get("additions", 0),
                    "pr_deletions": pr.get("deletions", 0),
                    "changed_files": pr.get("changed_files", 0),
                }
            )

        try:
            # 使用缓存的GitHub客户端
            client = get_github_client(installation_id)
            llm = create_workflow_llm()
            exporter = PRExporter(client, llm=llm)
            git_client = GitClient()

            logger.info(f"[{thread_name}] Exporting PR #{pr_number}")
            pr_folder, functional_summary = exporter.export_pr_to_folder(repo_full_name, pr_number)
            logger.info(f"[{thread_name}] Exported PR #{pr_number} to {pr_folder}")

            # Publish functional summary if available
            if functional_summary:
                logger.info(f"[{thread_name}] Publishing functional summary for PR #{pr_number}")
                publisher = GitHubPublisher(client)
                pr_metadata = client.get_pr_metadata(repo_full_name, pr_number)
                summary_result = publisher.publish_functional_summary(
                    functional_summary=functional_summary,
                    pr_number=pr_number,
                    repo_full_name=repo_full_name,
                    pr_metadata=pr_metadata,
                )
                logger.info(f"[{thread_name}] Published functional summary: {summary_result}")

            logger.info(f"[{thread_name}] Cloning {repo_full_name} branch {base_branch}")
            installation_token = client.get_access_token()
            clone_result = git_client.clone_for_pr(
                repo_full_name=repo_full_name,
                base_branch=base_branch,
                installation_token=installation_token,
            )

            if not clone_result.success:
                logger.error(f"[{thread_name}] Failed to clone repo: {clone_result.error}")
                return

            codebase_path = clone_result.path
            logger.info(f"[{thread_name}] Cloned to {codebase_path}")

            # Run comprehensive WiseCodeWatchersWorkflow with LangGraph
            logger.info(f"[{thread_name}] Starting comprehensive workflow review for PR #{pr_number}")
            workflow = WiseCodeWatchersWorkflow(llm=llm)

            final_report = workflow.run(
                pr_dir=pr_folder,
                codebase_path=codebase_path,
                top_n=20,
                batch_size=8,
                max_workers=4
            )

            # Extract issue counts from comprehensive report
            logic_issues = final_report.get("logic_review", {}).get("issues_found", 0)
            security_issues = final_report.get("security_review", {}).get("issues_found", 0)
            total_issues = logic_issues + security_issues

            logger.info(f"[{thread_name}] Comprehensive review complete. Found {total_issues} issues (logic: {logic_issues}, security: {security_issues})")

            # Save comprehensive report to pr_folder
            report_path = os.path.join(pr_folder, "out", "comprehensive_report.json")
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(final_report, f, ensure_ascii=False, indent=2)
            logger.info(f"[{thread_name}] Saved comprehensive report to {report_path}")

            # Load diff_ir for inline comments
            diff_ir_path = os.path.join(pr_folder, "out", "diff_ir.json")
            diff_ir = None
            if os.path.exists(diff_ir_path):
                try:
                    with open(diff_ir_path, "r", encoding="utf-8") as f:
                        diff_ir = json.load(f)
                    logger.info(f"[{thread_name}] Loaded diff_ir from {diff_ir_path}")
                except Exception as e:
                    logger.warning(f"[{thread_name}] Failed to load diff_ir.json: {e}")

            # Publish to GitHub with inline comments
            publisher = GitHubPublisher(client)
            publish_result = publisher.publish_comprehensive_report(
                final_report=final_report,
                pr_number=pr_number,
                repo_full_name=repo_full_name,
                diff_ir=diff_ir,
            )
            logger.info(f"[{thread_name}] Published comprehensive review: {publish_result}")

            git_client.cleanup(codebase_path)

            logger.info(f"[{thread_name}] ✓ PR #{pr_number} processing completed successfully")

        except Exception as e:
            logger.error(f"[{thread_name}] ✗ Error processing PR #{pr_number}: {e}", exc_info=True)


def worker():
    """后台工作线程 - 从队列中获取任务并处理"""
    thread_name = threading.current_thread().name
    logger.info(f"[{thread_name}] Worker started")

    while True:
        try:
            # 从队列获取任务,阻塞等待
            task = task_queue.get()

            if task is None:  # 收到退出信号
                logger.info(f"[{thread_name}] Worker received exit signal")
                break

            logger.info(f"[{thread_name}] Worker picked up {task}")
            logger.info(f"[{thread_name}] Queue size: {task_queue.qsize()}")

            # 添加延迟以避免GitHub API速率限制
            time.sleep(2)  # 每个任务之间延迟2秒

            # 处理任务
            process_pr_task(task)

            # 任务完成后再次延迟
            time.sleep(3)  # 任务完成后延迟3秒

            # 标记任务完成
            task_queue.task_done()

        except Exception as e:
            logger.error(f"[{thread_name}] Worker error: {e}", exc_info=True)

    logger.info(f"[{thread_name}] Worker stopped")


def start_worker_threads(num_workers: int = MAX_WORKERS):
    """启动工作线程池"""
    global worker_threads

    for i in range(num_workers):
        thread = threading.Thread(
            target=worker,
            name=f"Worker-{i+1}",
            daemon=True
        )
        thread.start()
        worker_threads.append(thread)
        logger.info(f"Started worker thread: {thread.name}")


@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(request.data, signature):
        logger.warning("Invalid webhook signature")
        return jsonify({"error": "Invalid signature"}), 401

    event_type = request.headers.get("X-GitHub-Event")
    payload = request.json

    logger.info(f"Received event: {event_type}")

    if event_type == "ping":
        return jsonify({"message": "pong"}), 200

    if event_type == "pull_request":
        return handle_pull_request_async(payload)

    return jsonify({"message": f"Event {event_type} ignored"}), 200


def handle_pull_request_async(payload: dict):
    """异步处理PR请求 - 立即返回,任务在后台处理"""
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})

    pr_number = pr.get("number")
    repo_full_name = repo.get("full_name")

    logger.info(f"PR #{pr_number} action: {action} in {repo_full_name}")

    if action not in ("opened", "synchronize", "reopened"):
        return jsonify({"message": f"PR action {action} ignored"}), 200

    # Check if repository is monitored
    if not Config.is_repo_monitored(repo_full_name):
        logger.info(f"Repository {repo_full_name} is not in monitored list, skipping PR #{pr_number}")
        return jsonify({
            "message": "Repository not monitored",
            "repo": repo_full_name,
            "status": "skipped"
        }), 200

    # 创建任务并放入队列
    task = PRTask(payload)
    task_queue.put(task)

    queue_size = task_queue.qsize()
    logger.info(f"✓ PR #{pr_number} added to queue (queue size: {queue_size})")

    # 立即返回响应,不等待处理完成
    return jsonify({
        "message": "PR review queued successfully",
        "pr": pr_number,
        "queue_position": queue_size,
        "status": "queued"
    }), 202  # 202 Accepted


@app.route("/health", methods=["GET"])
def health():
    """健康检查端点"""
    monitored_repos = Config.get_monitored_repos()
    return jsonify({
        "status": "healthy",
        "queue_size": task_queue.qsize(),
        "active_workers": len(worker_threads),
        "monitored_repos": list(monitored_repos) if monitored_repos else "all",
        "monitoring_mode": "specific" if monitored_repos else "all"
    }), 200


@app.route("/queue", methods=["GET"])
def queue_status():
    """队列状态端点"""
    return jsonify({
        "queue_size": task_queue.qsize(),
        "active_workers": len(worker_threads),
        "max_workers": MAX_WORKERS,
    }), 200


@app.route("/config", methods=["GET"])
def config_status():
    """配置状态端点 - 查看当前监控配置"""
    monitored_repos = Config.get_monitored_repos()

    return jsonify({
        "monitoring_mode": "specific" if monitored_repos else "all",
        "monitored_repos": list(monitored_repos) if monitored_repos else [],
        "monitored_repos_count": len(monitored_repos) if monitored_repos else 0,
        "config_description": "Monitoring specific repositories" if monitored_repos else "Monitoring all repositories with GitHub App installed"
    }), 200


# Langfuse Shutdown Handlers
def cleanup_langfuse():
    """Flush Langfuse traces on shutdown."""
    if langfuse_client:
        logger.info("Flushing Langfuse traces...")
        try:
            langfuse_client.flush()
            logger.info("Langfuse traces flushed successfully")
        except Exception as e:
            logger.error(f"Failed to flush Langfuse traces: {e}")


# Register cleanup on exit
atexit.register(cleanup_langfuse)


# Handle SIGTERM and SIGINT for graceful shutdown
def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down...")
    cleanup_langfuse()
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    Config.validate()

    # Log monitoring configuration
    monitored_repos = Config.get_monitored_repos()
    if monitored_repos:
        logger.info(f"🎯 Monitoring mode: SPECIFIC repositories")
        logger.info(f"📋 Monitored repositories ({len(monitored_repos)}):")
        for repo in sorted(monitored_repos):
            logger.info(f"   - {repo}")
    else:
        logger.info(f"🌍 Monitoring mode: ALL repositories")
        logger.info(f"📋 Will monitor all repositories where the GitHub App is installed")

    # 启动后台工作线程
    logger.info(f"Starting {MAX_WORKERS} worker threads...")
    start_worker_threads(MAX_WORKERS)

    logger.info(f"Starting webhook server on port {Config.PORT}")
    logger.info(f"PR processing is asynchronous - max {MAX_WORKERS} PRs can be processed in parallel")
    logger.info(f"View monitoring config: GET http://localhost:{Config.PORT}/config")

    app.run(host="0.0.0.0", port=Config.PORT, debug=False, threaded=True)
