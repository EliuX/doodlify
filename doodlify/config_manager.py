"""
Configuration and lock file management.
"""

import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from .models import Config, ConfigLock, EventLock, EventProgress, AnalysisResult


class ConfigManager:
    """Manages configuration and lock files.
    
    Supports two modes:
    - config.json: lock stored in .doodlify-workspace/config-lock.json keyed by repo folder name
    - event.manifest.json: lock stored in repo root as event.manifest-lock.json (committed)
    """

    def __init__(self, config_path: str = "config.json", lock_path: Optional[str] = None, repo_path: Optional[Path] = None):
        self.config_path = Path(config_path)
        self.repo_path = repo_path  # Set by orchestrator after clone
        # Derive lock file name if not explicitly provided
        if lock_path is None:
            # Replace extension with -lock.json, e.g., config.json -> config-lock.json, event.manifest.json -> event.manifest-lock.json
            stem = self.config_path.name
            if stem.endswith(".json"):
                base = stem[:-5]
                derived = f"{base}-lock.json"
            else:
                derived = f"{stem}-lock.json"
            self.lock_path = Path(derived)
        else:
            self.lock_path = Path(lock_path)
        self._config: Optional[Config] = None
        self._lock: Optional[ConfigLock] = None
        self._tz: Optional[ZoneInfo] = None
        self._is_manifest_mode = False  # Set during load_config

    def load_config(self) -> Config:
        """Load and validate configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding="utf-8") as f:
            data = json.load(f)

        self._config = Config(**data)
        # Detect mode: event.manifest.json means in-repo lock
        self._is_manifest_mode = self.config_path.name.startswith("event.manifest")
        return self._config

    def load_lock(self) -> ConfigLock:
        """Load lock file or create from config if doesn't exist.
        
        For config.json: reads from .doodlify-workspace/config-lock.json[repo_folder]
        For event.manifest.json: reads from <repo>/event.manifest-lock.json
        """
        if not self._config:
            self.load_config()

        # Determine actual lock path based on mode
        if self._is_manifest_mode:
            # In-repo lock at repo root
            if self.repo_path:
                self.lock_path = self.repo_path / "event.manifest-lock.json"
            else:
                # Fallback if repo_path not set yet
                self.lock_path = Path("event.manifest-lock.json")
        else:
            # Workspace lock keyed by repo folder
            self.lock_path = Path(".doodlify-workspace") / "config-lock.json"

        if self.lock_path.exists():
            with open(self.lock_path, 'r', encoding="utf-8") as f:
                raw = json.load(f)
            
            if self._is_manifest_mode:
                # Single-root payload
                self._lock = ConfigLock(**raw)
            else:
                # Map keyed by repo folder name
                repo_key = self.repo_path.name if self.repo_path else "default"
                data = raw.get(repo_key)
                if not data:
                    # Initialize entry for this repo
                    self._lock = self._create_new_lock()
                    raw[repo_key] = self._lock.model_dump()
                    self.lock_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(self.lock_path, 'w', encoding="utf-8") as wf:
                        json.dump(raw, wf, indent=2)
                else:
                    self._lock = ConfigLock(**data)
        else:
            # Create new lock
            self._lock = self._create_new_lock()
            self.save_lock()

        return self._lock
    
    def _create_new_lock(self) -> ConfigLock:
        """Create a new lock from current config."""
        event_locks = [
            EventLock(
                **event.model_dump(),
                progress=EventProgress(status="pending"),
                analysis=None,
                last_executed=None,
            )
            for event in self._config.events
        ]
        return ConfigLock(
            project=self._config.project,
            defaults=self._config.defaults,
            events=event_locks,
            global_analysis=None,
        )

    def apply_overrides(self, overrides: dict) -> None:
        """Apply partial overrides to the current config (e.g., from repo manifest).

        Only known top-level keys (project, defaults, events) are considered. Unknown keys are ignored.
        Lock mirrors (project/defaults) are also updated to stay consistent for later phases.
        """
        if not self._config:
            self.load_config()
        data = self._config.model_dump()
        # Merge shallowly for project/defaults; replace events if provided
        if "project" in overrides and isinstance(overrides["project"], dict):
            data["project"].update(overrides["project"])
        if "defaults" in overrides and isinstance(overrides["defaults"], dict):
            data["defaults"].update(overrides["defaults"])
        if "events" in overrides and isinstance(overrides["events"], list):
            data["events"] = overrides["events"]

        # Re-validate into Config
        self._config = Config(**data)

        # Update lock mirrors
        if not self._lock:
            self.load_lock()
        self._lock.project = self._config.project
        self._lock.defaults = self._config.defaults
        self.save_lock()

    def save_lock(self) -> None:
        """Save lock file to disk.
        
        For config.json: updates the repo entry in .doodlify-workspace/config-lock.json
        For event.manifest.json: writes to <repo>/event.manifest-lock.json
        """
        if not self._lock:
            raise ValueError("No lock data to save")

        self._lock.last_updated = datetime.utcnow().isoformat()

        # Ensure parent exists
        lock_parent = self.lock_path.parent
        if lock_parent and not lock_parent.exists():
            lock_parent.mkdir(parents=True, exist_ok=True)

        if self._is_manifest_mode:
            # Single-root payload for manifest mode
            with open(self.lock_path, 'w', encoding="utf-8") as f:
                json.dump(self._lock.model_dump(), f, indent=2)
        else:
            # Map keyed by repo folder for config mode
            repo_key = self.repo_path.name if self.repo_path else "default"
            raw = {}
            if self.lock_path.exists():
                try:
                    with open(self.lock_path, 'r', encoding="utf-8") as f:
                        raw = json.load(f) or {}
                except Exception:
                    raw = {}
            raw[repo_key] = self._lock.model_dump()
            with open(self.lock_path, 'w', encoding="utf-8") as f:
                json.dump(raw, f, indent=2)

    def get_event_lock(self, event_id: str) -> Optional[EventLock]:
        """Get lock data for a specific event."""
        if not self._lock:
            self.load_lock()

        for event in self._lock.events:
            if event.id == event_id:
                return event
        return None

    def update_event_progress(self, event_id: str, **kwargs) -> None:
        """Update progress for an event."""
        event_lock = self.get_event_lock(event_id)
        if not event_lock:
            raise ValueError(f"Event not found: {event_id}")

        for key, value in kwargs.items():
            if hasattr(event_lock.progress, key):
                setattr(event_lock.progress, key, value)

        self.save_lock()

    def update_event_analysis(self, event_id: str, analysis: AnalysisResult) -> None:
        """Update analysis results for an event."""
        event_lock = self.get_event_lock(event_id)
        if not event_lock:
            raise ValueError(f"Event not found: {event_id}")

        event_lock.analysis = analysis
        event_lock.progress.analyzed = True
        self.save_lock()

    def update_global_analysis(self, analysis: AnalysisResult) -> None:
        """Update global analysis results."""
        if not self._lock:
            self.load_lock()

        self._lock.global_analysis = analysis
        self.save_lock()

    def clear_event(self, event_id: str) -> None:
        """Clear lock data for a specific event."""
        event_lock = self.get_event_lock(event_id)
        if not event_lock:
            raise ValueError(f"Event not found: {event_id}")

        # Reset progress
        event_lock.progress = EventProgress(status="pending")
        event_lock.analysis = None
        event_lock.last_executed = None

        self.save_lock()

    def clear_all(self) -> None:
        """Clear all lock data."""
        if self.lock_path.exists():
            os.remove(self.lock_path)
        self._lock = None

    def get_active_events(self) -> list[EventLock]:
        """Get events that are currently active based on date range."""
        if not self._lock:
            self.load_lock()

        tz = self.get_project_timezone();
        if tz is None:
            # Fallback to UTC when timezone is missing or invalid
            today = datetime.utcnow().date()
        else:
            today = datetime.now(tz).date()

        active_events = []

        for event in self._lock.events:
            start_date = datetime.strptime(event.startDate, "%Y-%m-%d").date()
            end_date = datetime.strptime(event.endDate, "%Y-%m-%d").date()

            if start_date <= today <= end_date:
                active_events.append(event)

        return active_events
    
    def get_project_timezone(self) -> ZoneInfo:
        if self._tz:
            return self._tz
        
        tz_name = None
        try:
            tz_name = getattr(self._lock.project, "timeZone", None)
        except Exception:
            tz_name = None 
        try:
            if tz_name:
                self._tz = ZoneInfo(tz_name)
        except Exception:
            self._tz = None
        return self._tz

    def get_unprocessed_active_events(self) -> list[EventLock]:
        """Get active events that haven't been processed yet."""
        active_events = self.get_active_events()
        return [e for e in active_events if not e.progress.processed]

    def align_lock_with_workspace(self, repo_name: Optional[str], workspace_dir: str = ".doodlify-workspace") -> None:
        """Align lock_path based on mode.
        
        For config.json: .doodlify-workspace/config-lock.json (keyed by repo folder)
        For event.manifest.json: <repo>/event.manifest-lock.json (in-repo, committed)
        
        Args:
            repo_name: "owner/repo" or just "repo". Used to derive repo folder name.
            workspace_dir: Root directory where the repo was cloned.
        """
        try:
            if not repo_name:
                return
            repo_basename = repo_name.split('/')[-1]
            
            if self._is_manifest_mode:
                # In-repo lock
                self.repo_path = Path(workspace_dir) / repo_basename
                self.lock_path = self.repo_path / "event.manifest-lock.json"
            else:
                # Workspace lock
                self.repo_path = Path(workspace_dir) / repo_basename
                self.lock_path = Path(workspace_dir) / "config-lock.json"
        except Exception:
            pass

    @property
    def config(self) -> Config:
        """Get current config."""
        if not self._config:
            self.load_config()
        return self._config

    @property
    def lock(self) -> ConfigLock:
        """Get current lock."""
        if not self._lock:
            self.load_lock()
        return self._lock