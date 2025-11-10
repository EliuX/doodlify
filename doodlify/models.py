"""
Data models for configuration and state management.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    """Project metadata configuration."""
    name: str = Field(..., description="Name of the project")
    description: str = Field(..., description="Description of the project for AI agents")
    sources: List[str] = Field(default_factory=list, description="Subpaths to limit agent analysis")
    targetBranch: Optional[str] = Field(None, description="Target branch for PRs")
    timeZone: str = Field(
        default="America/Montreal",
        description="EST timezone (e.g., 'America/Montreal') used to compute active event dates"
    )


class DefaultsConfig(BaseModel):
    """Default configuration for events."""
    selector: Optional[str] = Field(None, description="CSS selector for elements to modify")
    branchPrefix: Optional[str] = Field(None, description="Prefix for event branch names")
    useEventColorPalette: Optional[bool] = Field(
        default=False,
        description=(
            "If true, use a preset palette for the event (e.g., Christmas, Halloween) "
            "instead of the app's extracted palette."
        ),
    )
    reportSuggestions: Dict[str, bool] = Field(
        default_factory=lambda: {
            # Optional by default
            "i18n": False,
            # Core suggestions enabled by default
            "css_variables": True,
            "data_attrs": True,
            "svg_usage": True,
            "global_css": True,
            "marker_styles": True,
            "favicon_variants": True,
            "favicon_establish": True,
            "og_variants": True,
            "og_add": True,
            "selectors_guidance": True,
            "ai_considerations": True,
        },
        description=(
            "Boolean map controlling which suggestions should be filed as GitHub issues. "
            "Keys correspond to analyzer suggestion keys."
        ),
    )


class EventConfig(BaseModel):
    """Event configuration."""
    id: str = Field(..., description="Unique identifier/slug for the event")
    name: str = Field(..., description="Public name of the event")
    description: str = Field(..., description="Description to provide context to agents")
    startDate: str = Field(..., description="Event start date (YYYY-MM-DD)")
    endDate: str = Field(..., description="Event end date (YYYY-MM-DD)")
    branch: str = Field(..., description="Branch name for this event")
    useEventColorPalette: Optional[bool] = Field(
        default=None,
        description=(
            "Override defaults.useEventColorPalette for this event; if true, use preset event palette."
        ),
    )


class Config(BaseModel):
    """Main configuration schema."""
    project: ProjectConfig
    defaults: DefaultsConfig
    events: List[EventConfig]


class AnalysisResult(BaseModel):
    """Results from codebase analysis."""
    files_of_interest: List[str] = Field(default_factory=list, description="Files identified for modification")
    image_files: List[str] = Field(default_factory=list, description="Image files to potentially modify")
    text_files: List[str] = Field(default_factory=list, description="Text/i18n files to potentially modify")
    selectors_found: List[str] = Field(default_factory=list, description="CSS selectors found in the code")
    notes: Dict[str, Any] = Field(default_factory=dict, description="Additional analysis notes")
    improvement_suggestions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of improvement suggestions detected during analysis (title, body, labels)"
    )
    analyzed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class EventProgress(BaseModel):
    """Progress tracking for an event."""
    status: str = Field(..., description="Status: pending, analyzing, processing, completed, failed")
    analyzed: bool = Field(default=False, description="Whether analysis has been completed")
    processed: bool = Field(default=False, description="Whether processing has been completed")
    pushed: bool = Field(default=False, description="Whether changes have been pushed")
    branch_created: bool = Field(default=False, description="Whether branch has been created")
    pr_created: bool = Field(default=False, description="Whether PR has been created")
    pr_url: Optional[str] = Field(None, description="URL of the created PR")
    commit_sha: Optional[str] = Field(None, description="SHA of the commit")
    modified_files: List[str] = Field(default_factory=list, description="List of files modified")
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[str] = Field(None, description="When processing started")
    completed_at: Optional[str] = Field(None, description="When processing completed")
    file_status: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Per-file processing status keyed by repo-relative path. "
            "Each value is a dict: {status: processed|unsupported|missing|skipped, updated_at: ISO8601, details?: str}."
        ),
    )


class EventLock(EventConfig):
    """Extended event configuration with lock data."""
    progress: EventProgress = Field(default_factory=lambda: EventProgress(status="pending"))
    analysis: Optional[AnalysisResult] = Field(None, description="Analysis results for this event")
    last_executed: Optional[str] = Field(None, description="Last execution timestamp")


class ConfigLock(BaseModel):
    """Lock file schema with execution state."""
    project: ProjectConfig
    defaults: DefaultsConfig
    events: List[EventLock]
    global_analysis: Optional[AnalysisResult] = Field(None, description="Global analysis results")
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    reported_suggestions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Suggestions already reported to GitHub (to avoid duplicates). Each item contains title, fingerprint, issue_number."
    )