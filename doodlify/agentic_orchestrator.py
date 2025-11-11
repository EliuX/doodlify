"""
Agentic Orchestrator using Haystack's Agent framework.
Replaces imperative orchestration with autonomous agent decision-making.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
import os

from haystack import Pipeline
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.tools import ToolInvoker
from haystack.dataclasses import ChatMessage
from haystack.tools import Toolset
from haystack.utils import Secret

from doodlify.config_manager import ConfigManager
from doodlify.models import EventLock
from doodlify.agents.haystack_tools import (
    analyze_codebase_tool,
    process_images_tool
)
from doodlify.agents.github_mcp_tools import GitHubMCPTools
from doodlify.git_agent import GitAgent


class AgenticOrchestrator:
    """
    Agentic orchestrator using Haystack's agent framework.
    
    Instead of imperative step-by-step execution, this orchestrator:
    - Defines available tools for the AI agent
    - Lets the agent decide which tools to call and when
    - Handles complex workflows autonomously
    - Adapts to different scenarios without hardcoded logic
    """
    
    def __init__(
        self,
        config_manager: ConfigManager,
        github_token: str,
        openai_api_key: str,
        repo_name: str
    ):
        """
        Initialize the agentic orchestrator.
        
        Args:
            config_manager: Configuration manager
            github_token: GitHub Personal Access Token
            openai_api_key: OpenAI API key
            repo_name: GitHub repository name (owner/repo)
        """
        self.config_manager = config_manager
        self.github_token = github_token
        self.openai_api_key = openai_api_key
        self.repo_name = repo_name
        
        # Set OpenAI API key for tools
        os.environ['OPENAI_API_KEY'] = openai_api_key
        
        # Initialize GitHub MCP tools
        self.github_tools = GitHubMCPTools(github_token)
        
        # Initialize Git agent for local operations
        repo_url = f"https://github.com/{repo_name}.git"
        self.git_agent = GitAgent(repo_url)
        
        # Create agent pipeline
        self._setup_agent_pipeline()
    
    def _setup_agent_pipeline(self):
        """Set up the Haystack agent pipeline with available tools."""
        
        # Create toolset with wrapped agent tools
        # These are thin wrappers around the same agents used in assistant mode
        self.toolset = Toolset(tools=[
            analyze_codebase_tool,
            process_images_tool,
        ])
        
        # Create chat generator with tool support
        self.chat_generator = OpenAIChatGenerator(
            api_key=Secret.from_token(self.openai_api_key),
            model="gpt-5",
            generation_kwargs={"temperature": 0.3},
            tools=self.toolset
        )
        
        # Create tool invoker
        self.tool_invoker = ToolInvoker(tools=self.toolset)
        
        # Build the agent pipeline
        self.pipeline = Pipeline()
        self.pipeline.add_component("chat_generator", self.chat_generator)
        self.pipeline.add_component("tool_invoker", self.tool_invoker)
        
        # Connect components
        self.pipeline.connect("chat_generator.replies", "tool_invoker.messages")
    
    def analyze(self, report_all: bool = False) -> bool:
        """
        Analyze phase: Let the agent analyze the codebase once (project-wide).
        
        Args:
            report_all: Whether to report all suggestions
        
        Returns:
            True if successful
        """
        print("\n" + "=" * 60)
        print("🔍 ANALYZE PHASE (Agentic)")
        print("=" * 60)
        
        try:
            config = self.config_manager.config
            
            # Clone/update repository
            target_branch = getattr(config.project, 'targetBranch', 'main')
            self.git_agent.clone_or_update(branch=target_branch)
            
            # Check if global analysis already exists
            lock = self.config_manager.load_lock()
            if lock.global_analysis and not report_all:
                print("✓ Global analysis already performed.")
                print(f"  - Images: {len(lock.global_analysis.image_files or [])}")
                print(f"  - Text files: {len(lock.global_analysis.text_files or [])}")
                print(f"  - Files of interest: {len(lock.global_analysis.files_of_interest or [])}")
                return True
            
            print("\n🔍 Performing global codebase analysis...")
            
            # Create agent conversation for analysis
            system_message = f"""You are an expert frontend analyzer for event-themed website transformations.

Your goal: Analyze the codebase ONCE for all events and identify:
1. Image files that could be transformed for event themes
2. Text/i18n files that may need adaptation
3. CSS/style files where colors could be changed
4. Improvement suggestions for better event readiness

Project: {config.project.name}
Description: {config.project.description}

Use the analyze_codebase tool to perform a comprehensive project analysis."""
            
            messages = [
                ChatMessage.from_system(system_message),
                ChatMessage.from_user(f"Analyze the repository at {self.git_agent.repo_path} for event-themed modifications.")
            ]
            
            # Run agent pipeline
            result = self.pipeline.run({
                "chat_generator": {"messages": messages}
            })
            
            # Extract analysis from tool results
            tool_results = result.get("tool_invoker", {}).get("tool_messages", [])
            
            if tool_results:
                # Store global analysis results
                import ast
                analysis_data = tool_results[0].tool_call_result.result
                
                # Convert string representation to dict if needed
                if isinstance(analysis_data, str):
                    analysis_data = ast.literal_eval(analysis_data)
                
                from doodlify.models import AnalysisResult
                analysis = AnalysisResult(**analysis_data)
                self.config_manager.update_global_analysis(analysis)
                
                print(f"  ✓ Global analysis complete")
                print(f"    - Images: {len(analysis.image_files or [])}")
                print(f"    - Text files: {len(analysis.text_files or [])}")
                print(f"    - Files of interest: {len(analysis.files_of_interest or [])}")
            
            print("\n✓ Analyze phase completed!")
            return True
            
        except Exception as e:
            print(f"\n✗ Analyze phase failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def process(
        self,
        event_id: Optional[str] = None,
        only: Optional[List[str]] = None,
        force: bool = False,
        styles_only: bool = False
    ) -> bool:
        """
        Process phase: Let the agent autonomously handle event processing.
        
        Args:
            event_id: Specific event ID to process
            only: List of specific files to process
            force: Force reprocess even if backups exist
            styles_only: Process only CSS/SCSS/SASS/LESS files (skip images and text)
        
        Returns:
            True if successful
        """
        print("\n" + "=" * 60)
        print("⚙️  PROCESS PHASE (Agentic)")
        print("=" * 60)
        
        try:
            # Determine which events to process
            if event_id:
                event = self.config_manager.get_event_lock(event_id)
                if not event:
                    print(f"Event not found: {event_id}")
                    return False
                events_to_process = [event]
            else:
                events_to_process = self.config_manager.get_unprocessed_active_events()
            
            if not events_to_process:
                print("No events to process.")
                return True
            
            print(f"Processing {len(events_to_process)} event(s)...\n")
            
            if styles_only:
                print("🎨 Styles-only mode: Processing CSS/SCSS/SASS/LESS files only\n")
            
            for event in events_to_process:
                success = self._process_event_agentic(event, only=only, force=force, styles_only=styles_only)
                if not success:
                    print(f"✗ Failed to process event: {event.name}")
                    return False
            
            print("\n✓ Process phase completed!")
            return True
            
        except Exception as e:
            print(f"\n✗ Process phase failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _process_event_agentic(
        self,
        event: EventLock,
        only: Optional[List[str]] = None,
        force: bool = False,
        styles_only: bool = False
    ) -> bool:
        """
        Process a single event using agentic approach.
        
        The agent autonomously decides:
        - Which files to transform
        - In what order to process them
        - How to handle errors and retries
        - When to commit changes
        
        Args:
            styles_only: Process only CSS/SCSS/SASS/LESS files (skip images and text)
        """
        print(f"\n{'=' * 60}")
        print(f"🎨 Processing: {event.name} (Agent-driven)")
        print(f"{'=' * 60}")
        
        try:
            # Get global analysis
            lock = self.config_manager.load_lock()
            analysis = lock.global_analysis if lock else None
            if not analysis:
                print("  ⚠️  No global analysis found. Run analyze phase first.")
                return False
            
            # Clone/update repository first
            config = self.config_manager.config
            target_branch = getattr(config.project, 'targetBranch', 'main')
            self.git_agent.clone_or_update(branch=target_branch)
            
            # Create event branch
            branch_prefix = getattr(config.defaults, 'branchPrefix', 'feature/event/')
            event_branch = f"{branch_prefix}{event.branch}"
            
            print(f"📂 Creating branch: {event_branch}")
            self.git_agent.create_branch(event_branch, from_branch=target_branch)
            
            # Prepare analysis data
            image_files = analysis.image_files or []
            text_files = analysis.text_files or []
            palette = analysis.notes.get('palette', []) if analysis.notes else []
            sources = getattr(config.project, 'sources', []) or []
            
            if only:
                # Filter to only specified files
                image_files = [f for f in image_files if f in only]
                text_files = [f for f in text_files if f in only]
            
            # Create agent conversation for processing
            system_message = f"""You are an autonomous agent responsible for transforming a website for an event theme.
                Event: {event.name}
                Description: {event.description}
                Repository: {self.git_agent.repo_path}
                
                Analysis Results:
                - {len(image_files)} image files identified for transformation
                - {len(text_files)} text/i18n files to adapt  
                - Color palette: {palette}
                
                Your mission:
                Transform ALL the images for this event using the process_images_tool.
                
                Image files to transform:
                {chr(10).join(f'- {img}' for img in image_files[:10])}{'...' if len(image_files) > 10 else ''}
                
                Call process_images_tool with:
                - repo_path: "{self.git_agent.repo_path}"
                - image_files: {image_files}
                - event_name: "{event.name}"
                - event_description: "{event.description}"
                - sources: {sources}
                - palette: {palette}
                
                Complete this transformation now."""
            
            messages = [
                ChatMessage.from_system(system_message),
                ChatMessage.from_user("Transform all the images for this event theme.")
            ]
            
            # Run agent - let it call tools once
            result = self.pipeline.run({
                "chat_generator": {"messages": messages}
            })
            
            # Get results
            replies = result.get("chat_generator", {}).get("replies", [])
            tool_results = result.get("tool_invoker", {}).get("tool_messages", [])
            
            # Check if tools were called and show results
            if tool_results:
                print(f"  ✓ Agent called {len(tool_results)} tool(s)")
                for tool_msg in tool_results:
                    if hasattr(tool_msg, 'tool_call_result'):
                        tool_name = tool_msg.tool_call_result.origin.tool_name
                        result = tool_msg.tool_call_result.result
                        print(f"    - {tool_name}")
                        
                        # Parse result if it's a string
                        import ast
                        if isinstance(result, str):
                            try:
                                result = ast.literal_eval(result)
                            except:
                                pass
                        
                        if isinstance(result, dict):
                            if 'total' in result:
                                print(f"      📊 Total: {result['total']}, Successful: {result.get('successful', 0)}, Failed: {result.get('failed', 0)}")
                            if 'results' in result and result.get('failed', 0) > 0:
                                # Show first few failures
                                failures = [r for r in result['results'] if r['status'] != 'success'][:3]
                                for fail in failures:
                                    print(f"      ⚠️  {fail['file']}: {fail.get('reason') or fail.get('error', 'unknown')}")
            
            # For now, we process in a single pass - the agent makes its tool calls
            # and we rely on those transformations being applied
            print(f"\n  ✓ Agent completed processing")
            
            # Commit changes
            print("\n💾 Committing changes...")
            try:
                commit_sha = self.git_agent.commit_changes(
                    f"feat: Apply {event.name} theme transformations\n\nAutomatically generated by Doodlify agentic orchestrator"
                )
                print(f"✓ Committed: {commit_sha[:8]}")
                
                self.config_manager.update_event_progress(
                    event.id,
                    status="processed",
                    branch=event_branch,
                    commit_sha=commit_sha
                )
            except ValueError as e:
                if "No changes to commit" in str(e):
                    print("⚠️  No changes were made")
                else:
                    raise
            
            print(f"\n✓ Event processed successfully: {event.name}")
            return True
            
        except Exception as e:
            print(f"\n✗ Event processing failed: {e}")
            import traceback
            traceback.print_exc()
            
            self.config_manager.update_event_progress(
                event.id,
                status="error",
                error=str(e)
            )
            return False
    
    def push(self) -> bool:
        """
        Push phase: Push branches and create PRs using MCP.
        
        Returns:
            True if successful
        """
        print("\n" + "=" * 60)
        print("🚀 PUSH PHASE (Agentic with MCP)")
        print("=" * 60)
        
        try:
            config = self.config_manager.config
            owner, repo = self.repo_name.split('/')
            target_branch = getattr(config.project, 'targetBranch', 'main')
            
            # Get processed but not pushed events
            events = self.config_manager.get_processed_unpushed_events()
            
            if not events:
                print("No events to push.")
                return True
            
            print(f"Pushing {len(events)} event(s)...\n")
            
            for event in events:
                print(f"\n📤 {event.name}")
                
                # Push branch using MCP
                if event.branch:
                    print(f"  Pushing branch: {event.branch}")
                    self.git_agent.push_branch(event.branch)
                    
                    # Create PR using MCP
                    pr_title = f"🎨 {event.name}: Event Theme Transformation"
                    pr_body = f"""## Event: {event.name}

{event.description}

### Changes
- Transformed images for event theme
- Updated text/i18n content
- Applied event color palette

**Start Date:** {event.startDate}
**End Date:** {event.endDate}

---
*Automatically generated by Doodlify Agentic Orchestrator*
"""
                    
                    pr_result = self.github_tools.create_pull_request(
                        owner=owner,
                        repo=repo,
                        title=pr_title,
                        head=event.branch,
                        base=target_branch,
                        body=pr_body
                    )
                    
                    pr_url = pr_result.get('html_url', '')
                    print(f"  ✓ PR created: {pr_url}")
                    
                    self.config_manager.update_event_progress(
                        event.id,
                        pr_url=pr_url
                    )
            
            print("\n✓ Push phase completed!")
            return True
            
        except Exception as e:
            print(f"\n✗ Push phase failed: {e}")
            import traceback
            traceback.print_exc()
            return False
