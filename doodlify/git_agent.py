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
            # If there are local changes, stash them before any checkout/pull
            try:
                if self.repo.is_dirty(untracked_files=True) or bool(self.repo.untracked_files):
                    self.repo.git.stash('push', '-u', '-m', 'doodlify: pre-update stash')
            except Exception:
                # Non-fatal; continue and allow ff-only/rebase logic to handle
                pass
            origin = self.repo.remotes.origin
            origin.fetch()
            
            # Checkout and pull the specified branch (fast-forward only)
            if branch in self.repo.heads:
                self.repo.heads[branch].checkout()
            else:
                # Try to checkout remote branch
                if f"origin/{branch}" in [ref.name for ref in self.repo.refs]:
                    self.repo.git.checkout('-b', branch, f'origin/{branch}')
                else:
                    # Branch doesn't exist, use default
                    self.repo.heads[self.repo.active_branch.name].checkout()
            # Fast-forward only to avoid auto-merges/divergence prompts
            try:
                self.repo.git.pull('--ff-only', 'origin', branch)
            except Exception:
                # If ff-only fails (diverged), rebase onto remote as a safe default
                try:
                    self.repo.git.fetch('origin', branch)
                    self.repo.git.rebase(f'origin/{branch}')
                except Exception:
                    # Leave as-is; orchestrator may handle stashing/conflicts
                    pass
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
        
        # Ensure any local modifications are stashed before switching branches
        try:
            if self.repo.is_dirty(untracked_files=True) or bool(self.repo.untracked_files):
                self.repo.git.stash('push', '-u', '-m', 'doodlify: pre-create-branch stash')
        except Exception:
            # Non-fatal; branch checkout may still succeed
            pass

        # Ensure we're on the from_branch and it's up to date
        if from_branch in self.repo.heads:
            self.repo.heads[from_branch].checkout()
        else:
            self.repo.git.checkout('-b', from_branch, f'origin/{from_branch}')
        
        # Fast-forward only to latest remote for base branch
        try:
            self.repo.git.pull('--ff-only', 'origin', from_branch)
        except Exception:
            try:
                self.repo.git.fetch('origin', from_branch)
                self.repo.git.rebase(f'origin/{from_branch}')
            except Exception:
                pass
        
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
    
    def find_file(self, path_str: str, sources: Optional[List[str]] = None) -> Path:
        """Find file in repository.
        
        Attempts resolution in this order:
        - <repo>/<normalized>
        - <repo>/<source>/<normalized>
        - <repo>/<source>/web-ui/src/<normalized>
        - <repo>/web-ui/src/<normalized>
        - <repo>/public/<normalized>
        - <repo>/<source>/public/<normalized>
        - rglob for the normalized subpath
        - rglob for the filename only
        """
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        
        normalized = path_str.strip().lstrip('/').lstrip('./')
        candidates = []
        
        # 0) Repo-root direct
        candidates.append(self.repo_path / normalized)

        if sources:
            for s in sources:
                # Normalize source root
                s_norm = str(s).strip().lstrip('./')
                candidates.append(self.repo_path / s_norm / normalized)
                # Also try nested web-ui/src under each source
                candidates.append(self.repo_path / s_norm / 'web-ui' / 'src' / normalized)
                # Also try public roots under each source
                candidates.append(self.repo_path / s_norm / 'public' / normalized)
        
        # 4) Heuristic: common UI root if present
        ui_root = self.repo_path / 'web-ui' / 'src'
        if ui_root.exists():
            candidates.append(ui_root / normalized)
        # 4b) Heuristic: common public root if present at repo root
        public_root = self.repo_path / 'public'
        if public_root.exists():
            candidates.append(public_root / normalized)
        
        # 5) Fallback: attempt rglob by normalized subpath, then by filename
        try:
            # Exact subpath search (e.g., images/foo.png anywhere)
            for hit in self.repo_path.rglob(normalized):
                if hit.is_file():
                    return hit
        except Exception:
            pass
        try:
            # Filename-only search as last resort
            name = Path(normalized).name
            for hit in self.repo_path.rglob(name):
                if hit.is_file():
                    return hit
        except Exception:
            pass

        for c in candidates:
            try:
                if c.exists():
                    return c
            except Exception:
                continue
        # Return first candidate even if it doesn't exist; caller will handle
        return candidates[0] if candidates else (self.repo_path / normalized)
    
    def push_branch(self, branch_name: str, force: bool = False) -> None:
        """Push branch to remote."""
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        
        origin = self.repo.remotes.origin
        if force:
            origin.push(branch_name, force=True)
        else:
            origin.push(branch_name)

    def stash_push(self, message: str = 'doodlify-auto') -> bool:
        """Stash local changes (including untracked) if any. Returns True if stashed."""
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        dirty = self.repo.is_dirty(untracked_files=True) or bool(self.repo.untracked_files)
        if dirty:
            try:
                self.repo.git.stash('push', '-u', '-m', message)
                return True
            except Exception:
                return False
        return False

    def stash_apply(self) -> bool:
        """Apply the most recent stash. Returns True if applied without error."""
        if not self.repo:
            raise RuntimeError("Repository not initialized")
        try:
            self.repo.git.stash('apply')
            return True
        except Exception:
            return False
    
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
        
        # Create backup using new scheme: <name>.original.<ext>
        backup_path = self.get_backup_path(file_path)
        shutil.copy2(file_path, backup_path)
        return str(backup_path.relative_to(self.repo_path))
    
    # -------- Backup path utilities (new scheme with backward compatibility) --------
    def get_backup_path(self, file_path: Path) -> Path:
        """Return backup path using new scheme: <name>.original.<ext>.
        If there is no suffix, append `.original` at the end.
        """
        if file_path.suffix:
            # e.g., hero.png -> hero.original.png
            return file_path.with_name(f"{file_path.stem}.original{file_path.suffix}")
        # No suffix: fallback to append .original
        return file_path.with_name(file_path.name + '.original')
    
    def get_legacy_backup_path(self, file_path: Path) -> Path:
        """Legacy backup scheme: <name>.<ext>.original (kept for compatibility)."""
        return file_path.with_suffix(file_path.suffix + '.original')
    
    def resolve_existing_backup(self, file_path: Path) -> Optional[Path]:
        """Return an existing backup path only if it matches the new scheme.
        New scheme: <name>.original.<ext>
        Legacy backups (<name>.<ext>.original) are intentionally ignored.
        """
        new_path = self.get_backup_path(file_path)
        if new_path.exists():
            return new_path
        return None

    def cleanup(self) -> None:
        """Clean up local repository."""
        if self.repo_path and self.repo_path.exists():
            shutil.rmtree(self.repo_path)
