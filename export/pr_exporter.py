import os
import json
from core.github_client import GitHubClient


class PRExporter:
    def __init__(self, github_client: GitHubClient):
        self.client = github_client

    def export_pr_to_folder(self, repo_full_name: str, pr_number: int, base_output_dir: str = "pr_export") -> str:
        owner, repo = repo_full_name.split("/")
        pr_folder = f"{owner}_{repo}_PR{pr_number}"
        output_dir = os.path.join(base_output_dir, pr_folder)
        os.makedirs(output_dir, exist_ok=True)

        metadata = self.client.get_pr_metadata(repo_full_name, pr_number)
        self._save_json(output_dir, "metadata.json", metadata)

        commits = self.client.get_pr_commits(repo_full_name, pr_number)
        self._save_json(output_dir, "commits.json", commits)

        comments = self.client.get_pr_comments(repo_full_name, pr_number)
        self._save_json(output_dir, "comments.json", comments)

        reviews = self.client.get_pr_reviews(repo_full_name, pr_number)
        self._save_json(output_dir, "reviews.json", reviews)

        review_comments = self.client.get_pr_review_comments(repo_full_name, pr_number)
        self._save_json(output_dir, "review_comments.json", review_comments)

        files_changed = self.client.get_pr_files_changed(repo_full_name, pr_number)
        self._save_json(output_dir, "files_changed.json", files_changed)

        full_diff = self.client.get_pr_full_diff(repo_full_name, pr_number)
        self._save_text(output_dir, "pr.diff", full_diff)

        self._export_commits_with_diffs(repo_full_name, commits, output_dir)

        return output_dir

    def _export_commits_with_diffs(self, repo_full_name: str, commits: list, output_dir: str):
        commits_dir = os.path.join(output_dir, "commits")
        os.makedirs(commits_dir, exist_ok=True)

        for commit in commits:
            sha = commit["sha"]
            sha_short = sha[:8]
            commit_dir = os.path.join(commits_dir, sha_short)
            os.makedirs(commit_dir, exist_ok=True)

            self._save_json(commit_dir, "commit_info.json", commit)

            diffs_dir = os.path.join(commit_dir, "diffs")
            os.makedirs(diffs_dir, exist_ok=True)

            files = self.client.get_commit_files_diff(repo_full_name, sha)
            for file_info in files:
                if file_info.get("patch"):
                    safe_filename = file_info["filename"].replace("/", "_").replace("\\", "_")
                    diff_path = os.path.join(diffs_dir, f"{safe_filename}.diff")
                    with open(diff_path, "w") as f:
                        f.write(f"--- a/{file_info['filename']}\n")
                        f.write(f"+++ b/{file_info['filename']}\n")
                        f.write(file_info["patch"])

    def _save_json(self, directory: str, filename: str, data):
        filepath = os.path.join(directory, filename)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_text(self, directory: str, filename: str, content: str):
        filepath = os.path.join(directory, filename)
        with open(filepath, "w") as f:
            f.write(content)
