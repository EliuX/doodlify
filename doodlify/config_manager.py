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
    """Manages configuration and lock files."""

    def __init__(self, config_path: str = "config.json", lock_path: Optional[str] = None):
        self.config_path = Path(config_path)
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

    def load_config(self) -> Config:
        """Load and validate configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding="utf-8") as f:
            data = json.load(f)

        self._config = Config(**data)
        return self._config

    def load_lock(self) -> ConfigLock:
        """Load lock file or create from config if doesn't exist."""
        if self.lock_path.exists():
            with open(self.lock_path, 'r', encoding="utf-8") as f:
                data = json.load(f)
            self._lock = ConfigLock(**data)
        else:
            # Create lock from config
            if not self._config:
                self.load_config()

            event_locks = [
                EventLock(
                    **event.model_dump(),
                    progress=EventProgress(status="pending"),
                    analysis=None,
                    last_executed=None,
                )
                for event in self._config.events
            ]

            self._lock = ConfigLock(
                project=self._config.project,
                defaults=self._config.defaults,
                events=event_locks,
                global_analysis=None,
            )
            self.save_lock()

        return self._lock

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
        """Save lock file to disk."""
        if not self._lock:
            raise ValueError("No lock data to save")

        self._lock.last_updated = datetime.utcnow().isoformat()

        # Ensure parent exists if lock_path includes directories
        lock_parent = self.lock_path.parent
        if lock_parent and not lock_parent.exists():
            lock_parent.mkdir(parents=True, exist_ok=True)

        with open(self.lock_path, 'w', encoding="utf-8") as f:
            json.dump(self._lock.model_dump(), f, indent=2)

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
        """Point lock_path to the workspace repo lock if it exists.

        This ensures commands that don't instantiate the orchestrator (e.g., `status`)
        still read the same lock file that `process`/`analyze` wrote under the cloned repo.

        Args:
            repo_name: "owner/repo" or just "repo". If None or invalid, no-op.
            workspace_dir: Root directory where the repo was cloned.
        """
        try:
            if not repo_name:
                return
            repo_basename = repo_name.split('/')[-1]
            # Derive file name from current config (e.g., config.json -> config-lock.json)
            stem = self.config_path.name
            if stem.endswith(".json"):
                base = stem[:-5]
                derived = f"{base}-lock.json"
            else:
                derived = f"{stem}-lock.json"
            candidate = Path(workspace_dir) / repo_basename / derived
            if candidate.exists():
                self.lock_path = candidate
        except Exception:
            # Non-fatal; fall back to existing lock_path
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