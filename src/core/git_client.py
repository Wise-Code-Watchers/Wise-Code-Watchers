import os
import shutil
import subprocess
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CloneResult:
    success: bool
    path: str
    branch: str
    commit_sha: str
    error: str = None


class GitClient:
    def __init__(self, workspace_dir: str = "workspace"):
        self.workspace_dir = workspace_dir
        os.makedirs(workspace_dir, exist_ok=True)

    def clone_repo(
        self,
        repo_url: str,
        branch: str,
        target_dir: str = None,
        depth: int = 1,
    ) -> CloneResult:
        if target_dir is None:
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            target_dir = os.path.join(self.workspace_dir, repo_name)

        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)

        try:
            cmd = ["git", "clone", "--branch", branch, "--depth", str(depth), repo_url, target_dir]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Cloned {repo_url} branch {branch} to {target_dir}")

            commit_sha = self._get_commit_sha(target_dir)

            return CloneResult(
                success=True,
                path=target_dir,
                branch=branch,
                commit_sha=commit_sha,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repo: {e.stderr}")
            return CloneResult(
                success=False,
                path=target_dir,
                branch=branch,
                commit_sha="",
                error=e.stderr,
            )

    def clone_for_pr(
        self,
        repo_full_name: str,
        base_branch: str,
        installation_token: str = None,
    ) -> CloneResult:
        if installation_token:
            repo_url = f"https://x-access-token:{installation_token}@github.com/{repo_full_name}.git"
        else:
            repo_url = f"https://github.com/{repo_full_name}.git"

        target_dir = os.path.join(
            self.workspace_dir,
            repo_full_name.replace("/", "_"),
            base_branch,
        )

        return self.clone_repo(repo_url, base_branch, target_dir)

    def _get_commit_sha(self, repo_path: str) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""

    def checkout_commit(self, repo_path: str, commit_sha: str) -> bool:
        try:
            subprocess.run(
                ["git", "fetch", "--depth", "1", "origin", commit_sha],
                cwd=repo_path,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "checkout", commit_sha],
                cwd=repo_path,
                capture_output=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to checkout commit {commit_sha}: {e}")
            return False

    def cleanup(self, path: str):
        if os.path.exists(path):
            shutil.rmtree(path)
            logger.info(f"Cleaned up {path}")
