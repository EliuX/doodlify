"""
Configuration and lock file management.
"""

import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

from .models import Config, ConfigLock, EventLock, EventProgress, AnalysisResult


class ConfigManager:
    """Manages configuration and lock files."""
    
    def __init__(self, config_path: str = "config.json", lock_path: str = "config-lock.json"):
        self.config_path = Path(config_path)
        self.lock_path = Path(lock_path)
        self._config: Optional[Config] = None
        self._lock: Optional[ConfigLock] = None
    
    def load_config(self) -> Config:
        """Load and validate configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            data = json.load(f)
        
        self._config = Config(**data)
        return self._config
    
    def load_lock(self) -> ConfigLock:
        """Load lock file or create from config if doesn't exist."""
        if self.lock_path.exists():
            with open(self.lock_path, 'r') as f:
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
                    last_executed=None
                )
                for event in self._config.events
            ]
            
            self._lock = ConfigLock(
                project=self._config.project,
                defaults=self._config.defaults,
                events=event_locks,
                global_analysis=None
            )
            self.save_lock()
        
        return self._lock
    
    def save_lock(self) -> None:
        """Save lock file to disk."""
        if not self._lock:
            raise ValueError("No lock data to save")
        
        self._lock.last_updated = datetime.utcnow().isoformat()
        
        with open(self.lock_path, 'w') as f:
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
        
        today = datetime.utcnow().date()
        active_events = []
        
        for event in self._lock.events:
            start_date = datetime.strptime(event.startDate, "%Y-%m-%d").date()
            end_date = datetime.strptime(event.endDate, "%Y-%m-%d").date()
            
            if start_date <= today <= end_date:
                active_events.append(event)
        
        return active_events
    
    def get_unprocessed_active_events(self) -> list[EventLock]:
        """Get active events that haven't been processed yet."""
        active_events = self.get_active_events()
        return [e for e in active_events if not e.progress.processed]
    
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
