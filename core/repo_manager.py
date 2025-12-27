"""
Repository Manager - Manages cloned repositories for PR analysis.

Provides a shared context for all analysis nodes to access the cloned
codebase. Handles cloning, temp directory management, and cleanup.
"""

import os
import tempfile
import shutil
import logging
from dataclasses import dataclass, field
from typing import Optional
from contextlib import contextmanager

from core.git_client import GitClient, CloneResult

logger = logging.getLogger(__name__)


@dataclass
class PRContext:
    """Context for PR analysis containing all relevant paths and metadata."""
    pr_number: int
    repo_full_name: str
    repo_url: str
    head_branch: str
    base_branch: str
    codebase_path: str
    changed_files: list[str]
    temp_dir: str
    clone_result: Optional[CloneResult] = None
    
    @property
    def existing_changed_files(self) -> list[str]:
        """Return only changed files that exist in the codebase."""
        return [
            f for f in self.changed_files
            if os.path.exists(os.path.join(self.codebase_path, f))
        ]
    
    def get_full_path(self, relative_path: str) -> str:
        """Get absolute path for a file relative to codebase."""
        return os.path.join(self.codebase_path, relative_path)
    
    def file_exists(self, relative_path: str) -> bool:
        """Check if a file exists in the codebase."""
        return os.path.exists(self.get_full_path(relative_path))


class RepoManager:
    """
    Manages repository cloning and lifecycle for PR analysis.
    
    Usage:
        manager = RepoManager()
        
        # Option 1: Context manager (auto cleanup)
        with manager.prepare_for_analysis(pr_info) as ctx:
            result = await syntax_checker.check(ctx.codebase_path, ctx.changed_files)
        
        # Option 2: Manual management
        ctx = manager.clone_for_pr(pr_info)
        try:
            # ... do analysis ...
        finally:
            manager.cleanup(ctx)
    """
    
    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = workspace_dir
        self.git_client = GitClient(workspace_dir or "workspace")
    
    def clone_for_pr(
        self,
        repo_url: str,
        head_branch: str,
        pr_number: int,
        repo_full_name: str,
        base_branch: str,
        changed_files: list[str],
        use_temp: bool = True,
    ) -> PRContext:
        """
        Clone the head branch for PR analysis.
        
        Args:
            repo_url: Repository URL
            head_branch: Branch to clone (the PR's head branch)
            pr_number: PR number
            repo_full_name: Full repo name (owner/repo)
            base_branch: Target branch of the PR
            changed_files: List of files changed in the PR
            use_temp: If True, clone to temp directory (auto cleanup)
            
        Returns:
            PRContext with all analysis-relevant information
        """
        if use_temp:
            temp_dir = tempfile.mkdtemp(prefix=f"pr_{pr_number}_")
            target_dir = temp_dir
        else:
            temp_dir = None
            target_dir = os.path.join(
                self.git_client.workspace_dir,
                repo_full_name.replace("/", "_"),
                f"PR{pr_number}",
            )
        
        logger.info(f"Cloning {repo_url} branch {head_branch} to {target_dir}")
        
        clone_result = self.git_client.clone_repo(
            repo_url=repo_url,
            branch=head_branch,
            target_dir=target_dir,
        )
        
        if not clone_result.success:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to clone repository: {clone_result.error}")
        
        return PRContext(
            pr_number=pr_number,
            repo_full_name=repo_full_name,
            repo_url=repo_url,
            head_branch=head_branch,
            base_branch=base_branch,
            codebase_path=clone_result.path,
            changed_files=changed_files,
            temp_dir=temp_dir,
            clone_result=clone_result,
        )
    
    def clone_from_pr_export(self, pr_folder: str, use_temp: bool = True) -> PRContext:
        """
        Clone repository based on exported PR folder.
        
        Args:
            pr_folder: Path to exported PR folder containing metadata.json
            use_temp: If True, clone to temp directory
            
        Returns:
            PRContext ready for analysis
        """
        import json
        from agents.preprocessing.diff_parser import DiffParser
        
        # Load metadata
        metadata_path = os.path.join(pr_folder, "metadata.json")
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        # Parse changed files from diff
        parser = DiffParser()
        parsed_diff = parser.parse_pr_folder(pr_folder)
        changed_files = [f.filename for f in parsed_diff.files]
        
        # Extract repo URL from PR URL
        repo_url = metadata['html_url'].rsplit('/pull/', 1)[0]
        
        return self.clone_for_pr(
            repo_url=repo_url,
            head_branch=metadata['head_branch'],
            pr_number=metadata['number'],
            repo_full_name=repo_url.replace('https://github.com/', ''),
            base_branch=metadata['base_branch'],
            changed_files=changed_files,
            use_temp=use_temp,
        )
    
    def cleanup(self, ctx: PRContext):
        """Clean up the cloned repository."""
        if ctx.temp_dir and os.path.exists(ctx.temp_dir):
            shutil.rmtree(ctx.temp_dir, ignore_errors=True)
            logger.info(f"Cleaned up temp directory: {ctx.temp_dir}")
        elif ctx.codebase_path and os.path.exists(ctx.codebase_path):
            shutil.rmtree(ctx.codebase_path, ignore_errors=True)
            logger.info(f"Cleaned up codebase: {ctx.codebase_path}")
    
    @contextmanager
    def prepare_for_analysis(self, pr_folder: str, use_temp: bool = True):
        """
        Context manager for PR analysis with automatic cleanup.
        
        Usage:
            manager = RepoManager()
            with manager.prepare_for_analysis(pr_folder) as ctx:
                result = await checker.check(ctx.codebase_path, ctx.changed_files)
        """
        ctx = None
        try:
            ctx = self.clone_from_pr_export(pr_folder, use_temp=use_temp)
            logger.info(f"Prepared PR #{ctx.pr_number} for analysis: {ctx.codebase_path}")
            yield ctx
        finally:
            if ctx:
                self.cleanup(ctx)
    
    @contextmanager  
    def prepare_from_info(
        self,
        repo_url: str,
        head_branch: str,
        pr_number: int,
        repo_full_name: str,
        base_branch: str,
        changed_files: list[str],
    ):
        """
        Context manager for PR analysis from explicit parameters.
        
        Usage:
            with manager.prepare_from_info(repo_url, branch, ...) as ctx:
                result = await checker.check(ctx.codebase_path, ctx.changed_files)
        """
        ctx = None
        try:
            ctx = self.clone_for_pr(
                repo_url=repo_url,
                head_branch=head_branch,
                pr_number=pr_number,
                repo_full_name=repo_full_name,
                base_branch=base_branch,
                changed_files=changed_files,
                use_temp=True,
            )
            yield ctx
        finally:
            if ctx:
                self.cleanup(ctx)
