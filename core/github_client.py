import os
import time
import jwt
import requests
from github import Github, GithubIntegration
from config import Config


class GitHubClient:
    def __init__(self, installation_id: int):
        self.installation_id = installation_id
        self.app_id = Config.GITHUB_APP_ID
        self.private_key = Config.get_private_key()
        self._github = None
        self._token_expires_at = 0

    def _generate_jwt(self) -> str:
        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + (10 * 60),
            "iss": self.app_id,
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def _get_installation_token(self) -> str:
        jwt_token = self._generate_jwt()
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
        }
        url = f"https://api.github.com/app/installations/{self.installation_id}/access_tokens"
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        self._token_expires_at = time.time() + 3500
        return data["token"]

    def get_access_token(self) -> str:
        """Get installation access token for Git operations (e.g., cloning private repos)."""
        return self._get_installation_token()

    @property
    def github(self) -> Github:
        if self._github is None or time.time() >= self._token_expires_at:
            token = self._get_installation_token()
            self._github = Github(token)
        return self._github

    def get_pr(self, repo_full_name: str, pr_number: int):
        repo = self.github.get_repo(repo_full_name)
        return repo.get_pull(pr_number)

    def get_pr_files(self, repo_full_name: str, pr_number: int):
        pr = self.get_pr(repo_full_name, pr_number)
        return list(pr.get_files())

    def create_review(
        self,
        repo_full_name: str,
        pr_number: int,
        body: str,
        event: str = "COMMENT",
        comments: list = None,
    ):
        pr = self.get_pr(repo_full_name, pr_number)
        pr.create_review(body=body, event=event, comments=comments or [])

    def create_issue_comment(self, repo_full_name: str, pr_number: int, body: str):
        pr = self.get_pr(repo_full_name, pr_number)
        pr.create_issue_comment(body)

    def get_pr_metadata(self, repo_full_name: str, pr_number: int) -> dict:
        pr = self.get_pr(repo_full_name, pr_number)
        return {
            "number": pr.number,
            "title": pr.title,
            "body": pr.body,
            "state": pr.state,
            "draft": pr.draft,
            "author": pr.user.login,
            "created_at": pr.created_at.isoformat() if pr.created_at else None,
            "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
            "merged": pr.merged,
            "mergeable": pr.mergeable,
            "mergeable_state": pr.mergeable_state,
            "head_branch": pr.head.ref,
            "head_sha": pr.head.sha,
            "base_branch": pr.base.ref,
            "base_sha": pr.base.sha,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "changed_files": pr.changed_files,
            "commits_count": pr.commits,
            "comments_count": pr.comments,
            "review_comments_count": pr.review_comments,
            "labels": [label.name for label in pr.labels],
            "assignees": [a.login for a in pr.assignees],
            "requested_reviewers": [r.login for r in pr.requested_reviewers],
            "html_url": pr.html_url,
        }

    def get_pr_commits(self, repo_full_name: str, pr_number: int) -> list:
        pr = self.get_pr(repo_full_name, pr_number)
        commits = []
        for commit in pr.get_commits():
            commits.append({
                "sha": commit.sha,
                "message": commit.commit.message,
                "author": commit.commit.author.name if commit.commit.author else None,
                "author_email": commit.commit.author.email if commit.commit.author else None,
                "date": commit.commit.author.date.isoformat() if commit.commit.author and commit.commit.author.date else None,
                "html_url": commit.html_url,
            })
        return commits

    def get_commit_files_diff(self, repo_full_name: str, commit_sha: str, output_dir: str = None) -> list:
        repo = self.github.get_repo(repo_full_name)
        commit = repo.get_commit(commit_sha)
        files = []
        for file in commit.files:
            file_info = {
                "filename": file.filename,
                "status": file.status,
                "additions": file.additions,
                "deletions": file.deletions,
                "changes": file.changes,
                "patch": file.patch,
            }
            files.append(file_info)
            if output_dir and file.patch:
                self._save_diff_file(output_dir, commit_sha, file.filename, file.patch)
        return files

    def _save_diff_file(self, output_dir: str, commit_sha: str, filename: str, patch: str):
        commit_dir = os.path.join(output_dir, commit_sha[:8])
        os.makedirs(commit_dir, exist_ok=True)
        safe_filename = filename.replace("/", "_").replace("\\", "_")
        diff_path = os.path.join(commit_dir, f"{safe_filename}.diff")
        with open(diff_path, "w") as f:
            f.write(f"--- a/{filename}\n")
            f.write(f"+++ b/{filename}\n")
            f.write(patch)

    def export_pr_full_info(self, repo_full_name: str, pr_number: int, output_dir: str = None) -> dict:
        metadata = self.get_pr_metadata(repo_full_name, pr_number)
        commits = self.get_pr_commits(repo_full_name, pr_number)
        commits_with_files = []
        for commit in commits:
            commit_files = self.get_commit_files_diff(
                repo_full_name, commit["sha"], output_dir
            )
            commits_with_files.append({
                **commit,
                "files": commit_files,
            })
        return {
            "metadata": metadata,
            "commits": commits_with_files,
        }

    def get_pr_comments(self, repo_full_name: str, pr_number: int) -> list:
        pr = self.get_pr(repo_full_name, pr_number)
        comments = []
        for comment in pr.get_issue_comments():
            comments.append({
                "id": comment.id,
                "author": comment.user.login if comment.user else None,
                "body": comment.body,
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
                "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
                "html_url": comment.html_url,
            })
        return comments

    def get_pr_reviews(self, repo_full_name: str, pr_number: int) -> list:
        pr = self.get_pr(repo_full_name, pr_number)
        reviews = []
        for review in pr.get_reviews():
            reviews.append({
                "id": review.id,
                "author": review.user.login if review.user else None,
                "state": review.state,
                "body": review.body,
                "submitted_at": review.submitted_at.isoformat() if review.submitted_at else None,
                "html_url": review.html_url,
            })
        return reviews

    def get_pr_review_comments(self, repo_full_name: str, pr_number: int) -> list:
        pr = self.get_pr(repo_full_name, pr_number)
        comments = []
        for comment in pr.get_review_comments():
            comments.append({
                "id": comment.id,
                "author": comment.user.login if comment.user else None,
                "body": comment.body,
                "path": comment.path,
                "line": comment.line,
                "original_line": comment.original_line,
                "diff_hunk": comment.diff_hunk,
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
                "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
                "html_url": comment.html_url,
            })
        return comments

    def get_pr_files_changed(self, repo_full_name: str, pr_number: int) -> list:
        files = self.get_pr_files(repo_full_name, pr_number)
        return [
            {
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "changes": f.changes,
            }
            for f in files
        ]

    def get_pr_full_diff(self, repo_full_name: str, pr_number: int) -> str:
        pr = self.get_pr(repo_full_name, pr_number)
        files = pr.get_files()
        diff_parts = []
        for f in files:
            if f.patch:
                diff_parts.append(f"diff --git a/{f.filename} b/{f.filename}")
                diff_parts.append(f"--- a/{f.filename}")
                diff_parts.append(f"+++ b/{f.filename}")
                diff_parts.append(f.patch)
                diff_parts.append("")
        return "\n".join(diff_parts)
