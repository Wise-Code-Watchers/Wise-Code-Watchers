import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
    GITHUB_PRIVATE_KEY_PATH = os.getenv("GITHUB_PRIVATE_KEY_PATH")
    GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
    PORT = int(os.getenv("PORT", 3000))

    # LLM Configuration
    LLM_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    LLM_BASE_URL = os.getenv("BASE_URL") or os.getenv("LLM_BASE_URL")
    LLM_MODEL = os.getenv("MODEL") or os.getenv("LLM_MODEL", "GLM-4.6")

    # Enhanced Vulnerability Detection Configuration
    VULN_RISK_THRESHOLD_LOGIC = int(os.getenv("VULN_RISK_THRESHOLD_LOGIC", 60))
    VULN_RISK_THRESHOLD_SECURITY = int(os.getenv("VULN_RISK_THRESHOLD_SECURITY", 60))
    VULN_MAX_UNITS_LOGIC = int(os.getenv("VULN_MAX_UNITS_LOGIC", 12))
    VULN_MAX_UNITS_SECURITY = int(os.getenv("VULN_MAX_UNITS_SECURITY", 10))

    # Monitored Repositories Configuration
    # Format: comma-separated list of repository names (e.g., "repo1,repo2")
    # Can also use full names "org/repo1,org/repo2" for backward compatibility
    # Empty or "*" means monitor all repositories
    MONITORED_REPOS = os.getenv("MONITORED_REPOS", "").strip()

    @classmethod
    def get_private_key(cls) -> str:
        if not cls.GITHUB_PRIVATE_KEY_PATH:
            raise ValueError("GITHUB_PRIVATE_KEY_PATH not set")
        with open(cls.GITHUB_PRIVATE_KEY_PATH, "r") as f:
            return f.read()

    @classmethod
    def get_monitored_repos(cls) -> set:
        """Get the set of monitored repository names.

        Returns:
            set: Set of repository names (e.g., "repo1", "repo2").
                 Empty set means monitor all repositories.
                 The set only contains repository names without org prefix.
        """
        if not cls.MONITORED_REPOS or cls.MONITORED_REPOS == "*":
            # Empty or "*" means monitor all repositories
            return set()

        # Parse comma-separated repository list
        repos = []
        for repo in cls.MONITORED_REPOS.split(","):
            repo = repo.strip()
            if not repo:
                continue

            # Support both "repo" and "org/repo" formats
            if "/" in repo:
                # Extract only the repo name from "org/repo"
                repo_name = repo.split("/")[-1]
            else:
                repo_name = repo

            repos.append(repo_name)

        return set(repos)

    @classmethod
    def is_repo_monitored(cls, repo_full_name: str) -> bool:
        """Check if a repository is monitored.

        Args:
            repo_full_name: Full repository name (e.g., "org/repo")

        Returns:
            bool: True if the repository is monitored, False otherwise.
        """
        monitored_repos = cls.get_monitored_repos()

        # If no specific repos are configured, monitor all
        if not monitored_repos:
            return True

        # Extract repository name from full name
        # e.g., "Wise-Code-Watchers/keycloak-wcw" -> "keycloak-wcw"
        if "/" not in repo_full_name:
            return False

        repo_name = repo_full_name.split("/")[-1]

        # Check if the repo name is in the monitored list
        return repo_name in monitored_repos

    @classmethod
    def validate(cls):
        required = ["GITHUB_APP_ID", "GITHUB_PRIVATE_KEY_PATH", "GITHUB_WEBHOOK_SECRET"]
        missing = [var for var in required if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
