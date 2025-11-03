"""
Git operations agent for local repository management.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List
import git
from git import Repo


class GitAgent:
    """Handles local Git repository operations."""
    
    def __init__(self, repo_url: str, workspace_dir: str = ".doodlify-workspace"):
        self.repo_url = repo_url
        self.workspace_dir = Path(workspace_dir)
        self.repo: Optional[Repo] = None
        self.repo_path: Optional[Path] = None
    
    def clone_or_update(self, branch: str = "main") -> Path:
        """Clone repository or update if already exists."""
        # Extract repo name from URL
        repo_name = self.repo_url.split('/')[-1].replace('.git', '')
        self.repo_path = self.workspace_dir / repo_name
        
        if self.repo_path.exists():
            # Repository exists, update it
            self.repo = Repo(self.repo_path)
            origin = self.repo.remotes.origin
            origin.fetch()
            
            # Checkout and pull the specified branch
            if branch in self.repo.heads:
                self.repo.heads[branch].checkout()
            else:
                # Try to checkout remote branch
                if f"origin/{branch}" in [ref.name for ref in self.repo.refs]:
                    self.repo.git.checkout('-b', branch, f'origin/{branch}')
                else:
                    # Branch doesn't exist, use default
                    self.repo.heads[self.repo.active_branch.name].checkout()
            
            origin.pull()
        else:
            # Clone repository
            self.workspace_dir.mkdir(parents=True, exist_ok=True)
            self.repo = Repo.clone_from(
                self.repo_url,
                self.repo_path,
                branch=branch
            )
        
        return self.repo_path
    
    def create_branch(self, branch_name: str, from_branch: str = "main") -> None:
        """Create a new branch from specified base branch."""
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        
        # Ensure we're on the from_branch and it's up to date
        if from_branch in self.repo.heads:
            self.repo.heads[from_branch].checkout()
        else:
            self.repo.git.checkout('-b', from_branch, f'origin/{from_branch}')
        
        origin = self.repo.remotes.origin
        origin.pull()
        
        # Create new branch
        if branch_name in self.repo.heads:
            # Branch exists, checkout
            self.repo.heads[branch_name].checkout()
        else:
            # Create new branch
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
    
    def commit_changes(self, message: str, files: Optional[List[str]] = None) -> str:
        """Commit changes to the current branch."""
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        
        if files:
            # Add specific files
            for file in files:
                self.repo.index.add([file])
        else:
            # Add all changes
            self.repo.git.add(A=True)
        
        if self.repo.is_dirty() or self.repo.untracked_files:
            commit = self.repo.index.commit(message)
            return commit.hexsha
        else:
            raise ValueError("No changes to commit")
    
    def push_branch(self, branch_name: str, force: bool = False) -> None:
        """Push branch to remote."""
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        
        origin = self.repo.remotes.origin
        if force:
            origin.push(branch_name, force=True)
        else:
            origin.push(branch_name)
    
    def get_file_path(self, relative_path: str) -> Path:
        """Get absolute path to a file in the repository."""
        if not self.repo_path:
            raise RuntimeError("Repository not initialized")
        return self.repo_path / relative_path
    
    def list_files(self, pattern: str = "*", directory: str = "") -> List[Path]:
        """List files in repository matching pattern."""
        if not self.repo_path:
            raise RuntimeError("Repository not initialized")
        
        search_path = self.repo_path / directory if directory else self.repo_path
        return list(search_path.rglob(pattern))
    
    def get_current_branch(self) -> str:
        """Get name of current branch."""
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        return self.repo.active_branch.name
    
    def file_exists(self, relative_path: str) -> bool:
        """Check if file exists in repository."""
        if not self.repo_path:
            raise RuntimeError("Repository not initialized")
        return (self.repo_path / relative_path).exists()
    
    def read_file(self, relative_path: str) -> str:
        """Read file content from repository."""
        file_path = self.get_file_path(relative_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def write_file(self, relative_path: str, content: str) -> None:
        """Write content to file in repository."""
        file_path = self.get_file_path(relative_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def backup_file(self, relative_path: str) -> str:
        """Create a backup of a file before modifying it."""
        file_path = self.get_file_path(relative_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        
        # Create backup with .original extension
        backup_path = file_path.with_suffix(file_path.suffix + '.original')
        shutil.copy2(file_path, backup_path)
        
        return str(backup_path.relative_to(self.repo_path))
    
    def cleanup(self) -> None:
        """Clean up local repository."""
        if self.repo_path and self.repo_path.exists():
            shutil.rmtree(self.repo_path)
