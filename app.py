import hmac
import hashlib
import logging
import json
import os
from flask import Flask, request, jsonify
from config import Config
from core.github_client import GitHubClient
from core.git_client import GitClient
from export.pr_exporter import PRExporter
from publish.github_publisher import GitHubPublisher

from langchain_openai import ChatOpenAI
from agents.vulnerability.src import WiseCodeWatchersWorkflow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def create_workflow_llm() -> ChatOpenAI:
    """Create LLM instance for the comprehensive workflow (OpenAI-compatible API)."""
    kwargs = {
        "model": Config.LLM_MODEL,
        "temperature": 0,
    }
    if Config.LLM_API_KEY:
        kwargs["api_key"] = Config.LLM_API_KEY
    if Config.LLM_BASE_URL:
        kwargs["base_url"] = Config.LLM_BASE_URL
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
        return handle_pull_request(payload)

    return jsonify({"message": f"Event {event_type} ignored"}), 200


def handle_pull_request(payload: dict):
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    installation = payload.get("installation", {})

    pr_number = pr.get("number")
    repo_full_name = repo.get("full_name")
    installation_id = installation.get("id")
    base_branch = pr.get("base", {}).get("ref", "main")

    logger.info(f"PR #{pr_number} action: {action} in {repo_full_name}")

    if action not in ("opened", "synchronize", "reopened"):
        return jsonify({"message": f"PR action {action} ignored"}), 200

    try:
        client = GitHubClient(installation_id)
        exporter = PRExporter(client)
        git_client = GitClient()

        logger.info(f"Exporting PR #{pr_number}")
        pr_folder = exporter.export_pr_to_folder(repo_full_name, pr_number)
        logger.info(f"Exported PR #{pr_number} to {pr_folder}")

        logger.info(f"Cloning {repo_full_name} branch {base_branch}")
        installation_token = client.get_access_token()
        clone_result = git_client.clone_for_pr(
            repo_full_name=repo_full_name,
            base_branch=base_branch,
            installation_token=installation_token,
        )

        if not clone_result.success:
            logger.error(f"Failed to clone repo: {clone_result.error}")
            return jsonify({"error": f"Failed to clone repo: {clone_result.error}"}), 500

        codebase_path = clone_result.path
        logger.info(f"Cloned to {codebase_path}")

        # Run comprehensive WiseCodeWatchersWorkflow with LangGraph
        logger.info(f"Starting comprehensive workflow review for PR #{pr_number}")
        llm = create_workflow_llm()
        workflow = WiseCodeWatchersWorkflow(llm=llm)

        final_report = workflow.run(
            pr_dir=pr_folder,
            codebase_path=codebase_path,  # 🆕 传递克隆的源代码路径
            top_n=20,
            batch_size=8,
            max_workers=4
        )
        
        # Extract issue counts from comprehensive report
        logic_issues = final_report.get("logic_review", {}).get("issues_found", 0)
        security_issues = final_report.get("security_review", {}).get("issues_found", 0)
        total_issues = logic_issues + security_issues
        
        logger.info(f"Comprehensive review complete. Found {total_issues} issues (logic: {logic_issues}, security: {security_issues})")
        
        # Save comprehensive report to pr_folder
        report_path = os.path.join(pr_folder, "out", "comprehensive_report.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(final_report, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved comprehensive report to {report_path}")
        
        # Publish to GitHub
        publisher = GitHubPublisher(client)
        publish_result = publisher.publish_comprehensive_report(
            final_report=final_report,
            pr_number=pr_number,
            repo_full_name=repo_full_name,
        )
        logger.info(f"Published comprehensive review: {publish_result}")

        git_client.cleanup(codebase_path)

        return jsonify({
            "message": "PR review completed successfully",
            "pr": pr_number,
            "export_path": pr_folder,
            "issues_found": total_issues,
            "publish_result": publish_result,
        }), 200

    except Exception as e:
        logger.error(f"Error processing PR: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    Config.validate()
    logger.info(f"Starting webhook server on port {Config.PORT}")
    app.run(host="0.0.0.0", port=Config.PORT, debug=False)
