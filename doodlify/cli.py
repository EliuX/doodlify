"""
Command-line interface for Doodlify.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from .config_manager import ConfigManager
from .orchestrator import Orchestrator
from .agentic_orchestrator import AgenticOrchestrator


# Load environment variables
load_dotenv()


def get_env_or_exit(var_name: str) -> str:
    """Get environment variable or exit with error."""
    value = os.getenv(var_name)
    if not value:
        click.echo(f"Error: {var_name} not set in environment", err=True)
        click.echo(
            f"Please set it in .env file or as environment variable", err=True)
        sys.exit(1)
    return value


def create_orchestrator(config_path: str, agentic: bool):
    """Create orchestrator instance based on mode."""
    github_token = get_env_or_exit('GITHUB_PERSONAL_ACCESS_TOKEN')
    openai_api_key = get_env_or_exit('OPENAI_API_KEY')
    repo_name = get_env_or_exit('GITHUB_REPO_NAME')
    
    config_manager = ConfigManager(config_path=config_path)
    
    if agentic:
        click.echo("🤖 Using Agentic Mode (Haystack + MCP)")
        return AgenticOrchestrator(
            config_manager=config_manager,
            github_token=github_token,
            openai_api_key=openai_api_key,
            repo_name=repo_name,
        )
    else:
        click.echo("⚙️  Using Imperative Mode (Classic)")
        return Orchestrator(
            config_manager=config_manager,
            github_token=github_token,
            openai_api_key=openai_api_key,
            repo_name=repo_name,
        )


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    Doodlify - Automated Event-Based Frontend Customization Tool

    A CLI tool that adapts frontend projects for special events using AI agents.
    """
    pass


@cli.command()
@click.option(
    '--config',
    default='config.json',
    help='Path to configuration file',
    type=click.Path(exists=True)
)
@click.option(
    '--report-all',
    is_flag=True,
    default=False,
    help='Report all suggestions (including those disabled in defaults.reportSuggestions)'
)
@click.option(
    '--agentic',
    is_flag=True,
    default=False,
    help='Use agentic mode (Haystack + MCP) instead of classic assistant mode'
)
def analyze(config: str, report_all: bool, agentic: bool):
    """
    Analyze the project and validate configuration.

    This phase checks if the project can be accessed, validates the configuration,
    and performs initial codebase analysis to identify files of interest.
    """
    try:
        # Initialize orchestrator
        orchestrator = create_orchestrator(config, agentic)
        
        if hasattr(orchestrator, 'report_all_suggestions'):
            orchestrator.report_all_suggestions = report_all

        # Run analysis
        success = orchestrator.analyze(report_all=report_all) if agentic else orchestrator.analyze()

        if success:
            click.echo("\n✅ Analysis completed successfully!")
            sys.exit(0)
        else:
            click.echo("\n❌ Analysis failed!", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--config',
    default='config.json',
    help='Path to configuration file',
    type=click.Path(exists=True)
)
@click.option(
    '--event-id',
    required=True,
    help='Event ID to operate on',
    type=str
)
@click.option(
    '--files',
    required=True,
    help='Comma-separated repo-relative file paths to restore from .original backups',
    type=str
)
def restore(config: str, event_id: str, files: str):
    """
    Restore selected files from their `.original` backups and clear their processed state.

    This is useful when you want to reprocess specific files without clearing the whole event.
    """
    try:
        # Env (only minimal vars needed for repo access)
        github_token = get_env_or_exit('GITHUB_PERSONAL_ACCESS_TOKEN')
        openai_api_key = get_env_or_exit('OPENAI_API_KEY')
        repo_name = get_env_or_exit('GITHUB_REPO_NAME')

        config_manager = ConfigManager(config_path=config)
        orchestrator = Orchestrator(
            config_manager=config_manager,
            github_token=github_token,
            openai_api_key=openai_api_key,
            repo_name=repo_name,
        )

        file_list = [p.strip() for p in files.split(',') if p.strip()]
        success = orchestrator.restore_files(event_id=event_id, files=file_list)

        if success:
            click.echo("\n✅ Restore completed successfully!")
            sys.exit(0)
        else:
            click.echo("\n❌ Restore failed!", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--config',
    default='config.json',
    help='Path to configuration file',
    type=click.Path(exists=True)
)
@click.option(
    '--event-id',
    default=None,
    help='Process a specific event ID (bypasses active/unprocessed filters)',
    type=str
)
@click.option(
    '--only',
    default=None,
    help='Comma-separated list of repo-relative files to process only',
    type=str
)
@click.option(
    '--force',
    is_flag=True,
    default=False,
    help='Force reprocess even if backups (.original) exist'
)
@click.option(
    '--agentic',
    is_flag=True,
    default=False,
    help='Use agentic mode (Haystack + MCP) instead of classic assistant mode'
)
def process(config: str, event_id: Optional[str], only: Optional[str], force: bool, agentic: bool):
    """
    Process all active unprocessed events.

    This phase processes events that are currently active (based on date range)
    and haven't been processed yet. It applies AI-based transformations to
    images and text files.
    """
    try:
        # Initialize orchestrator
        orchestrator = create_orchestrator(config, agentic)

        # Run processing
        only_list = None
        if only:
            only_list = [p.strip() for p in only.split(',') if p.strip()]
        success = orchestrator.process(event_id=event_id, only=only_list, force=force)

        if success:
            click.echo("\n✅ Processing completed successfully!")
            sys.exit(0)
        else:
            click.echo("\n❌ Processing failed!", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--config',
    default='config.json',
    help='Path to configuration file',
    type=click.Path(exists=True)
)
@click.option(
    '--agentic',
    is_flag=True,
    default=False,
    help='Use agentic mode (Haystack + MCP) instead of classic assistant mode'
)
def push(config: str, agentic: bool):
    """
    Push processed changes and create pull requests.

    This phase pushes branches with committed changes to GitHub and
    creates pull requests for review.
    """
    try:
        # Initialize orchestrator
        orchestrator = create_orchestrator(config, agentic)

        # Run push (async for classic, sync for agentic)
        if agentic:
            success = orchestrator.push()
        else:
            success = asyncio.run(orchestrator.push())

        if success:
            click.echo("\n✅ Push completed successfully!")
            sys.exit(0)
        else:
            click.echo("\n❌ Push failed!", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--config',
    default='config.json',
    help='Path to configuration file',
    type=click.Path(exists=True)
)
@click.option(
    '--event-id',
    help='Event ID to clear (clears all if not specified)',
    type=str
)
@click.confirmation_option(
    prompt='Are you sure you want to clear the lock data?'
)
def clear(config: str, event_id: Optional[str]):
    """
    Clear lock data for an event or all events.

    This removes the processing state from config-lock.json, allowing
    events to be processed again. Use with caution in CI/CD environments.
    """
    try:
        # Get environment variables (only those needed for basic operations)
        github_token = os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN', 'dummy')
        openai_api_key = os.getenv('OPENAI_API_KEY', 'dummy')
        repo_name = os.getenv('GITHUB_REPO_NAME', 'dummy/repo')

        # Initialize
        config_manager = ConfigManager(config_path=config)
        orchestrator = Orchestrator(
            config_manager=config_manager,
            github_token=github_token,
            openai_api_key=openai_api_key,
            repo_name=repo_name,
        )

        # Run clear
        success = orchestrator.clear(event_id=event_id)

        if success:
            click.echo("\n✅ Clear completed successfully!")
            sys.exit(0)
        else:
            click.echo("\n❌ Clear failed!", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--config',
    default='config.json',
    help='Path to configuration file',
    type=click.Path(exists=True)
)
@click.option(
    '--report-all',
    is_flag=True,
    default=False,
    help='Report all suggestions (including those disabled in defaults.reportSuggestions)'
)
def run(config: str, report_all: bool):
    """
    Run the complete workflow: analyze -> process -> push.

    This convenience command runs all three phases in sequence.
    Perfect for CI/CD automation.
    """
    try:
        # Get environment variables
        github_token = get_env_or_exit('GITHUB_PERSONAL_ACCESS_TOKEN')
        openai_api_key = get_env_or_exit('OPENAI_API_KEY')
        repo_name = get_env_or_exit('GITHUB_REPO_NAME')
        target_branch = os.getenv('GIT_BRANCH_CHANGES_TARGET')

        # Initialize
        config_manager = ConfigManager(config_path=config)
        orchestrator = Orchestrator(
            config_manager=config_manager,
            github_token=github_token,
            openai_api_key=openai_api_key,
            repo_name=repo_name,
            target_branch=target_branch,
            report_all_suggestions=report_all,
        )

        # Run analyze
        click.echo("Starting complete workflow...\n")
        if not orchestrator.analyze():
            click.echo("\n❌ Workflow failed at analyze phase!", err=True)
            sys.exit(1)

        # Run process
        if not orchestrator.process():
            click.echo("\n❌ Workflow failed at process phase!", err=True)
            sys.exit(1)

        # Run push
        if not asyncio.run(orchestrator.push()):
            click.echo("\n❌ Workflow failed at push phase!", err=True)
            sys.exit(1)

        click.echo("\n✅ Complete workflow finished successfully!")
        sys.exit(0)

    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--config',
    default='config.json',
    help='Path to configuration file',
    type=click.Path(exists=True)
)
def status(config: str):
    """
    Show status of events and their processing state.
    """
    try:
        config_manager = ConfigManager(config_path=config)
        # Load base config first
        config_manager.load_config()
        # Align lock path to the workspace repo so we read the same lock that process/analyze wrote
        repo_name = os.getenv('GITHUB_REPO_NAME')
        config_manager.align_lock_with_workspace(repo_name)
        # Now load the (possibly relocated) lock file
        lock = config_manager.load_lock()

        click.echo("=" * 60)
        click.echo(f"Project: {lock.project.name}")
        click.echo("=" * 60)

        active_events = config_manager.get_active_events()
        click.echo(f"\n📅 Active Events: {len(active_events)}")

        for event in lock.events:
            status_icon = "🟢" if event in active_events else "⚪"
            click.echo(f"\n{status_icon} {event.name} ({event.id})")
            click.echo(f"   Period: {event.startDate} to {event.endDate}")
            click.echo(f"   Status: {event.progress.status}")
            click.echo(
                f"   Analyzed: {'✓' if event.progress.analyzed else '✗'}")
            click.echo(
                f"   Processed: {'✓' if event.progress.processed else '✗'}")
            click.echo(f"   Pushed: {'✓' if event.progress.pushed else '✗'}")
            if event.progress.pr_url:
                click.echo(f"   PR: {event.progress.pr_url}")
            if event.progress.error:
                click.echo(f"   Error: {event.progress.error}")

        sys.exit(0)

    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
