"""
Main orchestrator for the Doodlify workflow.
"""

import os
import json
import asyncio
import hashlib
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from .config_manager import ConfigManager
from .git_agent import GitAgent
from .agents import ImageAgent, TextAgent, AnalyzerAgent
from .agents.github_agent import GitHubAgent
from .models import EventLock, AnalysisResult
from haystack.dataclasses import ChatMessage


class Orchestrator:
    """Orchestrates the entire event decoration workflow."""
    
    def __init__(
        self,
        config_manager: ConfigManager,
        github_token: str,
        openai_api_key: str,
        repo_name: str,
        target_branch: Optional[str] = None,
        report_all_suggestions: bool = False,
    ):
        self.config_manager = config_manager
        self.github_token = github_token
        self.openai_api_key = openai_api_key
        self.repo_name = repo_name
        self.target_branch = target_branch
        self.report_all_suggestions = report_all_suggestions
        
        # Extract owner and repo from repo_name
        self.owner, self.repo = repo_name.split('/')
        
        # Initialize agents
        self.image_agent = ImageAgent(openai_api_key)
        self.text_agent = TextAgent(openai_api_key)
        self.analyzer_agent = AnalyzerAgent(openai_api_key)
        
        # Git agent will be initialized when needed
        self.git_agent: Optional[GitAgent] = None
    
    def analyze(self) -> bool:
        """
        Analyze phase: Check if project can be accessed and configuration is valid.
        
        Returns:
            True if analysis successful, False otherwise
        """
        print("=" * 60)
        print("📋 ANALYZE PHASE")
        print("=" * 60)
        
        try:
            # Load configuration
            config = self.config_manager.load_config()
            print(f"✓ Configuration loaded: {config.project.name}")
            
            # Check environment variables
            missing_vars = []
            if not self.github_token:
                missing_vars.append("GITHUB_PERSONAL_ACCESS_TOKEN")
            if not self.openai_api_key:
                missing_vars.append("OPENAI_API_KEY")
            if not self.repo_name:
                missing_vars.append("GITHUB_REPO_NAME")
            
            if missing_vars:
                print(f"✗ Missing environment variables: {', '.join(missing_vars)}")
                return False

            print(f"✓ Environment variables validated")
            
            # Initialize Git agent and clone/update repository
            repo_url = f"https://{self.github_token}@github.com/{self.repo_name}.git"
            self.git_agent = GitAgent(repo_url)
            
            base_branch = config.project.targetBranch or "main"
            repo_path = self.git_agent.clone_or_update(base_branch)
            print(f"✓ Repository cloned/updated at: {repo_path}")
            
            # Ensure the lock file is written inside the workspace repo directory
            # Keep the derived filename (e.g., config-lock.json or event.manifest-lock.json)
            try:
                derived_lock_name = self.config_manager.lock_path.name
                self.config_manager.lock_path = Path(repo_path) / derived_lock_name
            except Exception:
                pass
            
            # Optional: load repo-level manifest (event.manifest.json) to override config
            manifest_path = Path(repo_path) / "event.manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as mf:
                        overrides = json.load(mf)
                    self.config_manager.apply_overrides(overrides)
                    config = self.config_manager.config
                    print("✓ Applied repo manifest overrides from event.manifest.json")
                except Exception as me:
                    print(f"! Skipped manifest overrides due to error: {me}")
            
            # Perform global analysis if not already done
            lock = self.config_manager.load_lock()
            if not lock.global_analysis:
                print("\n🔍 Performing global codebase analysis...")
                analysis_result = self.analyzer_agent.analyze_codebase(
                    repo_path,
                    config.project.sources,
                    config.defaults.selector,
                    config.project.description
                )
                
                analysis = AnalysisResult(**analysis_result)
                self.config_manager.update_global_analysis(analysis)
                
                print(f"  ✓ Found {len(analysis.image_files)} image files")
                print(f"  ✓ Found {len(analysis.text_files)} text/i18n files")
                print(f"  ✓ Identified {len(analysis.files_of_interest)} files of interest")

                # Report improvement suggestions as GitHub issues (avoid duplicates)
                if analysis.improvement_suggestions:
                    print(f"\n📝 Reporting {len(analysis.improvement_suggestions)} improvement suggestion(s) to GitHub issues (deduped)...")
                    self._report_suggestions(analysis.improvement_suggestions)
            else:
                print("✓ Using cached global analysis")
            
            # Check active events
            active_events = self.config_manager.get_active_events()
            print(f"\n📅 Active events: {len(active_events)}")
            for event in active_events:
                status = event.progress.status
                print(f"  - {event.name} ({event.id}): {status}")
            
            print("\n✓ Analysis phase completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n✗ Analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def restore_files(self, event_id: str, files: List[str]) -> bool:
        """Restore selected files from their `.original` backups and reset their processed state.

        - Replaces the current file with the `.original` content
        - Removes the `.original` file
        - Marks file status as pending so it can be reprocessed
        """
        try:
            # Ensure repo is available
            cfg = self.config_manager.config
            if not self.git_agent:
                repo_url = f"https://{self.github_token}@github.com/{self.repo_name}.git"
                self.git_agent = GitAgent(repo_url)
                base_branch = cfg.project.targetBranch or "main"
                repo_path = self.git_agent.clone_or_update(base_branch)
                print(f"Repository ready at: {repo_path}")

                # Align lock path with workspace repo directory
                try:
                    derived_lock_name = self.config_manager.lock_path.name
                    self.config_manager.lock_path = Path(repo_path) / derived_lock_name
                except Exception:
                    pass
            
            # Normalize inputs
            targets = [str(Path(p).as_posix()).lstrip('/') for p in files]
            event_lock = self.config_manager.get_event_lock(event_id)
            if not event_lock:
                print(f"Event not found: {event_id}")
                return False

            sources = getattr(cfg.project, "sources", []) or []
            file_status = dict(getattr(event_lock.progress, "file_status", {}) or {})
            modified_files = set(event_lock.progress.modified_files or [])

            restored_any = False
            for rel in targets:
                full_path = self.git_agent.find_file(rel, sources=sources)
                try:
                    rel_path = str(full_path.relative_to(self.git_agent.repo_path))
                except Exception:
                    rel_path = rel

                backup_full = full_path.with_suffix(full_path.suffix + '.original')
                if not backup_full.exists():
                    print(f"  ⚠️  No backup to restore: {rel_path}")
                    continue

                try:
                    # Replace current with original, then remove .original
                    data = backup_full.read_bytes()
                    full_path.write_bytes(data)
                    backup_full.unlink()

                    # Update status and modified files
                    file_status[rel_path] = {"status": "pending", "updated_at": datetime.utcnow().isoformat()}
                    modified_files.discard(rel_path + '.original')
                    self.config_manager.update_event_progress(event_id, file_status=file_status, modified_files=sorted(modified_files))
                    print(f"  🔄 Restored from backup: {rel_path}")
                    restored_any = True
                except Exception as e:
                    print(f"  ✗ Failed to restore {rel_path}: {e}")

            return restored_any
        except Exception as e:
            print(f"\n✗ Restore failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _fingerprint(self, title: str, body: str) -> str:
        data = (title.strip() + "\n" + body.strip()).encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def _report_suggestions(self, suggestions: List[dict]) -> None:
        """Create GitHub issues for suggestions if not already reported."""
        lock = self.config_manager.lock
        reported = lock.reported_suggestions or []
        reported_fps = {item.get("fingerprint") for item in reported}

        # Initialize GitHub agent
        github_agent = GitHubAgent(self.github_token, self.openai_api_key)
        # Controls for suggestion reporting
        cfg = self.config_manager.config
        report_map = dict(getattr(cfg.defaults, "reportSuggestions", {}) or {})
        report_all = bool(self.report_all_suggestions)
        
        for s in suggestions:
            title = s.get("title") or "Improvement suggestion"
            body = s.get("body") or ""
            labels = s.get("labels") or ["enhancement"]
            fp = self._fingerprint(title, body)
            key = s.get("key")

            # Decide if this suggestion should be reported based on key map or report-all
            should_report = report_all or (report_map.get(key, True))
            if not should_report:
                print(f"- Skipping suggestion (disabled by defaults.reportSuggestions): {title}")
                print(f"  Key: {key or 'unknown'}  |  Value: false")
                continue

            # Additional guard for AI-driven suggestions: require evidence/confidence
            if key == "ai_considerations":
                conf = float(s.get("confidence") or 0.0)
                ev = s.get("evidence") or []
                if not ev or conf < 0.6:
                    print(f"- Skipping ai_considerations due to insufficient evidence/confidence: {title}")
                    print(f"  confidence={conf}, evidence_count={len(ev)} (need >=0.6 and >=1)")
                    continue

            # If reporting due to --report-all while map=false, mark as optional in logs
            if report_all and not report_map.get(key, True):
                print(f"- Filing OPTIONAL suggestion due to --report-all: {title}")
                print(f"  Key: {key or 'unknown'}  |  defaults.reportSuggestions[{key}] = false")
            else:
                print(f"- Filing suggestion as issue: {title}")
                print("  Reason: Enabled in defaults.reportSuggestions or default behavior.")

            if fp in reported_fps:
                continue

            # Use agent to handle issue creation with duplicate checking
            user_input = f"""
            Search for existing GitHub issues with title "{title}" in repository {self.owner}/{self.repo}.
            If no duplicate exists, create a new issue with title "{title}", body "{body}", and labels {labels}.
            
            Return JSON: {{"issue_number": <number>, "created": <true/false>}}
            """
            
            try:
                response = github_agent.run(messages=[ChatMessage.from_user(user_input)])
                
                # Extract issue number from agent response
                found_number = None
                if response and "messages" in response:
                    final_message = response["messages"][-1]
                    if hasattr(final_message, "content"):
                        # Try to extract issue number from response
                        import re
                        import json
                        try:
                            # Look for JSON in response
                            json_match = re.search(r'\{[^}]*"issue_number"[^}]*\}', final_message.content)
                            if json_match:
                                result = json.loads(json_match.group())
                                found_number = result.get("issue_number")
                        except:
                            # Fallback: look for issue number pattern
                            match = re.search(r'#(\d+)', final_message.content)
                            if match:
                                found_number = int(match.group(1))
                
                lock.reported_suggestions.append({
                    "title": title,
                    "fingerprint": fp,
                    "issue_number": found_number,
                    "reported_at": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                print(f"Warning: Failed to create issue via agent: {e}")
                continue

    def process(self, event_id: Optional[str] = None, only: Optional[List[str]] = None, force: bool = False) -> bool:
        """
        Process phase: Process all active unprocessed events.
        
        Returns:
            True if processing successful, False otherwise
        """
        print("\n" + "=" * 60)
        print("⚙️  PROCESS PHASE")
        print("=" * 60)
        
        try:
            # Ensure Git agent and repository are initialized for this run
            config = self.config_manager.config
            if not self.git_agent:
                repo_url = f"https://{self.github_token}@github.com/{self.repo_name}.git"
                self.git_agent = GitAgent(repo_url)
                base_branch = config.project.targetBranch or "main"
                repo_path = self.git_agent.clone_or_update(base_branch)
                print(f"Repository ready at: {repo_path}")

                # Ensure the lock file is written/read inside the workspace repo directory
                try:
                    derived_lock_name = self.config_manager.lock_path.name
                    self.config_manager.lock_path = Path(repo_path) / derived_lock_name
                except Exception:
                    pass

            # Determine events to process
            if event_id:
                lock = self.config_manager.lock
                events_to_process = [e for e in lock.events if e.id == event_id]
                if not events_to_process:
                    print(f"No event found with id: {event_id}")
                    return True
            else:
                # Default behavior: unprocessed & active
                events_to_process = self.config_manager.get_unprocessed_active_events()
            
            if not events_to_process:
                print("No unprocessed active events found.")
                return True
            
            print(f"Processing {len(events_to_process)} event(s)...\n")
            
            for event in events_to_process:
                success = self._process_event(event, only=only, force=force)
                if not success:
                    print(f"✗ Failed to process event: {event.name}")
                    return False
            
            print("\n✓ Process phase completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n✗ Process phase failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _process_event(self, event: EventLock, only: Optional[List[str]] = None, force: bool = False) -> bool:
        """Process a single event."""
        print(f"\n{'=' * 60}")
        print(f"🎨 Processing: {event.name}")
        print(f"{'=' * 60}")
        
        try:
            # Update status
            self.config_manager.update_event_progress(
                event.id,
                status="processing",
                started_at=datetime.utcnow().isoformat()
            )

            # Get configuration
            config = self.config_manager.config
            branch_prefix = config.defaults.branchPrefix or ""
            branch_name = f"{branch_prefix}{event.branch}"

            # Safeguard local work before updating base: stash changes
            stashed = False
            try:
                stashed = self.git_agent.stash_push('doodlify: pre-process stash')
            except Exception:
                stashed = False

            # Ensure base branch is up-to-date (ff-only) and create/checkout event branch
            print(f"📂 Creating branch: {branch_name}")
            base_branch = config.project.targetBranch or self.target_branch or "main"
            self.git_agent.create_branch(branch_name, base_branch)
            self.config_manager.update_event_progress(event.id, branch_created=True)

            # Re-apply stashed work onto the event branch (if any)
            if stashed:
                applied = self.git_agent.stash_apply()
                if not applied:
                    print("⚠️  Failed to apply stash automatically; please resolve manually if needed.")

            # Get analysis data
            analysis = None
            # If a focused file list was provided, avoid full analysis and use it directly
            if only:
                normalized_only = [str(Path(p).as_posix()).lstrip('/') for p in only]
                analysis = AnalysisResult(
                    files_of_interest=normalized_only,
                    image_files=[p for p in normalized_only if any(p.lower().endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.webp'))],
                    text_files=[p for p in normalized_only if p.lower().endswith('.json')],
                    selectors_found=[],
                    notes={},
                    improvement_suggestions=[],
                )
            else:
                analysis = event.analysis or self.config_manager.lock.global_analysis
                if not analysis:
                    analysis_result = self.analyzer_agent.analyze_codebase(
                        self.git_agent.repo_path,
                        config.project.sources,
                        config.defaults.selector,
                        config.project.description
                    )
                    analysis = AnalysisResult(**analysis_result)
                    self.config_manager.update_event_analysis(event.id, analysis)
            
            modified_files = []
            
            # Normalize "only" list to a set of repo-relative paths
            only_set: Optional[set] = None
            if only:
                only_set = set([str(Path(p).as_posix()).lstrip('/') for p in only])

            # Process image files (respect --only before logging)
            image_candidates = list(analysis.image_files or [])
            if only_set is not None:
                image_candidates = [p for p in image_candidates if (p in only_set or Path(p).name in only_set)]
            if image_candidates:
                print(f"\n🖼️  Processing {len(image_candidates)} image(s)...")
                image_files = self._process_images(event, image_candidates, only=only_set, force=force)
                modified_files.extend(image_files)
            
            # Process text files (respect --only before logging)
            text_candidates = list(analysis.text_files or [])
            if only_set is not None:
                text_candidates = [p for p in text_candidates if (p in only_set or Path(p).name in only_set)]
            if text_candidates:
                print(f"\n📝 Processing {len(text_candidates)} text file(s)...")
                text_files = self._process_texts(event, text_candidates, only=only_set, force=force)
                modified_files.extend(text_files)
            
            if not modified_files:
                print("⚠️  No files were modified")
                self.config_manager.update_event_progress(
                    event.id,
                    status="completed",
                    processed=True,
                    completed_at=datetime.utcnow().isoformat(),
                    error="No files were modified"
                )
                return True
            
            # Commit changes
            print(f"\n💾 Committing changes...")
            commit_message = self._generate_commit_message(event, modified_files)
            commit_sha = self.git_agent.commit_changes(commit_message, modified_files)
            
            print(f"✓ Committed: {commit_sha[:8]}")
            
            # Update progress
            self.config_manager.update_event_progress(
                event.id,
                status="completed",
                processed=True,
                commit_sha=commit_sha,
                modified_files=modified_files,
                completed_at=datetime.utcnow().isoformat()
            )
            
            # Update last executed marker on the event
            lock = self.config_manager.lock
            for e in lock.events:
                if e.id == event.id:
                    e.last_executed = datetime.utcnow().isoformat()
                    break
            self.config_manager.save_lock()
            
            print(f"\n✓ Event processed successfully: {event.name}")
            return True
            
        except Exception as e:
            print(f"\n✗ Failed to process event: {e}")
            self.config_manager.update_event_progress(
                event.id,
                status="failed",
                error=str(e)
            )
            import traceback
            traceback.print_exc()
            return False
    
    def _process_images(self, event: EventLock, image_paths: List[str], only: Optional[set] = None, force: bool = False) -> List[str]:
        """Process image files for an event."""
        modified = []
        
        # Use configured sources only to guide discovery (paths remain repo-root relative)
        config = self.config_manager.config
        sources = getattr(config.project, "sources", []) or []
        
        event_lock = self.config_manager.get_event_lock(event.id)
        file_status = dict(getattr(event_lock.progress, "file_status", {}) or {})
        
        for image_path_str in image_paths:
            # Resolve to an absolute path inside the repo (handles leading '/')
            full_path = self.git_agent.find_file(str(image_path_str), sources=sources)
            try:
                rel_path = str(full_path.relative_to(self.git_agent.repo_path))
            except Exception:
                rel_path = str(image_path_str).lstrip('/')
            
            # If an "only" filter is provided, skip files not in the set
            if only is not None and rel_path not in only:
                # Also try without leading directories if caller provided a shorter path
                short_rel = Path(rel_path).name
                if short_rel not in only:
                    continue

            # Skip if backup exists (idempotence via on-disk evidence) unless force
            backup_full = full_path.with_suffix(full_path.suffix + '.original')
            if backup_full.exists() and not force:
                print(f"  ⏭️  Skipping (backup exists): {rel_path}")
                # Optionally record as processed if not present
                if file_status.get(rel_path, {}).get("status") != "processed":
                    file_status[rel_path] = {"status": "processed", "updated_at": datetime.utcnow().isoformat()}
                    self.config_manager.update_event_progress(event.id, file_status=file_status)
                continue
            
            if not full_path.exists():
                print(f"  ⚠️  Skipping missing file: {rel_path}")
                # Log likely search locations for debugging
                try:
                    repo_root = self.git_agent.repo_path
                    searched = [str(repo_root / rel_path)]
                    for s in sources:
                        s_norm = str(s).strip().lstrip('./')
                        searched.append(str(repo_root / s_norm / rel_path))
                        searched.append(str(repo_root / s_norm / 'web-ui' / 'src' / rel_path))
                        searched.append(str(repo_root / s_norm / 'public' / rel_path))
                    searched.append(str(repo_root / 'web-ui' / 'src' / rel_path))
                    searched.append(str(repo_root / 'public' / rel_path))
                    print("    Tried:")
                    for loc in searched[:8]:
                        print(f"     - {loc}")
                except Exception:
                    pass
                file_status[rel_path] = {"status": "missing", "updated_at": datetime.utcnow().isoformat()}
                self.config_manager.update_event_progress(event.id, file_status=file_status)
                continue
            
            try:
                # Backup original
                backup_rel_path = self.git_agent.backup_file(rel_path)
                print(f"  📦 Backed up: {rel_path}")
                
                # Transform image in place
                self.image_agent.transform_image(
                    full_path,
                    event.name,
                    event.description,
                    output_path=full_path
                )
                
                modified.append(rel_path)
                modified.append(backup_rel_path)
                print(f"  ✓ Transformed: {rel_path}")
                
                file_status[rel_path] = {"status": "processed", "updated_at": datetime.utcnow().isoformat()}
                current_mod = set(event_lock.progress.modified_files or [])
                current_mod.update([rel_path, backup_rel_path])
                self.config_manager.update_event_progress(event.id, file_status=file_status, modified_files=sorted(current_mod))
                
            except Exception as e:
                print(f"  ✗ Failed to process {rel_path}: {e}")
                file_status[rel_path] = {"status": "skipped", "updated_at": datetime.utcnow().isoformat(), "details": str(e)}
                self.config_manager.update_event_progress(event.id, file_status=file_status)
        
        return modified
    
    def _process_texts(self, event: EventLock, text_paths: List[str], only: Optional[set] = None, force: bool = False) -> List[str]:
        """Process text/i18n files for an event."""
        modified = []
        
        # Use configured sources only to guide discovery (paths remain repo-root relative)
        config = self.config_manager.config
        sources = getattr(config.project, "sources", []) or []
        
        event_lock = self.config_manager.get_event_lock(event.id)
        file_status = dict(getattr(event_lock.progress, "file_status", {}) or {})
        
        for text_path_str in text_paths:
            full_path = self.git_agent.find_file(str(text_path_str), sources=sources)
            try:
                rel_path = str(full_path.relative_to(self.git_agent.repo_path))
            except Exception:
                rel_path = str(text_path_str).lstrip('/')
            
            # If an "only" filter is provided, skip files not in the set
            if only is not None and rel_path not in only:
                short_rel = Path(rel_path).name
                if short_rel not in only:
                    continue

            # Skip if backup exists (idempotence via on-disk evidence) unless force
            backup_full = full_path.with_suffix(full_path.suffix + '.original')
            if backup_full.exists() and not force:
                print(f"  ⏭️  Skipping (backup exists): {rel_path}")
                if file_status.get(rel_path, {}).get("status") != "processed":
                    file_status[rel_path] = {"status": "processed", "updated_at": datetime.utcnow().isoformat()}
                    self.config_manager.update_event_progress(event.id, file_status=file_status)
                continue
            
            if not full_path.exists():
                print(f"  ⚠️  Skipping missing file: {rel_path}")
                # Log likely search locations for debugging
                try:
                    repo_root = self.git_agent.repo_path
                    searched = [str(repo_root / rel_path)]
                    for s in sources:
                        s_norm = str(s).strip().lstrip('./')
                        searched.append(str(repo_root / s_norm / rel_path))
                        searched.append(str(repo_root / s_norm / 'web-ui' / 'src' / rel_path))
                        searched.append(str(repo_root / s_norm / 'public' / rel_path))
                    searched.append(str(repo_root / 'web-ui' / 'src' / rel_path))
                    searched.append(str(repo_root / 'public' / rel_path))
                    print("    Tried:")
                    for loc in searched[:8]:
                        print(f"     - {loc}")
                except Exception:
                    pass
                file_status[rel_path] = {"status": "missing", "updated_at": datetime.utcnow().isoformat()}
                self.config_manager.update_event_progress(event.id, file_status=file_status)
                continue
            
            try:
                # Backup original
                backup_rel_path = self.git_agent.backup_file(rel_path)
                print(f"  📦 Backed up: {rel_path}")
                
                # Adapt text file in place
                self.text_agent.adapt_i18n_file(
                    full_path,
                    event.name,
                    event.description,
                    output_path=full_path
                )
                
                modified.append(rel_path)
                modified.append(backup_rel_path)
                print(f"  ✓ Adapted: {rel_path}")
                
                file_status[rel_path] = {"status": "processed", "updated_at": datetime.utcnow().isoformat()}
                current_mod = set(event_lock.progress.modified_files or [])
                current_mod.update([rel_path, backup_rel_path])
                self.config_manager.update_event_progress(event.id, file_status=file_status, modified_files=sorted(current_mod))
                
            except Exception as e:
                print(f"  ✗ Failed to process {rel_path}: {e}")
                file_status[rel_path] = {"status": "skipped", "updated_at": datetime.utcnow().isoformat(), "details": str(e)}
                self.config_manager.update_event_progress(event.id, file_status=file_status)
        
        return modified
    
    def _generate_commit_message(self, event: EventLock, modified_files: List[str]) -> str:
        """Generate a descriptive commit message."""
        return f"""feat: Apply {event.name} theme customizations

Applied event-themed decorations for {event.name}
Event period: {event.startDate} to {event.endDate}

Modified files:
{chr(10).join(f'- {f}' for f in modified_files[:10])}
{f'... and {len(modified_files) - 10} more files' if len(modified_files) > 10 else ''}

Generated by Doodlify 🎨
"""
    
    async def push(self) -> bool:
        """
        Push phase: Push committed changes and create PRs.
        
        Returns:
            True if push successful, False otherwise
        """
        print("\n" + "=" * 60)
        print("🚀 PUSH PHASE")
        print("=" * 60)
        
        try:
            # Ensure Git agent and repository are initialized for this run
            cfg = self.config_manager.config
            if not self.git_agent:
                repo_url = f"https://{self.github_token}@github.com/{self.repo_name}.git"
                self.git_agent = GitAgent(repo_url)
                base_branch = cfg.project.targetBranch or "main"
                repo_path = self.git_agent.clone_or_update(base_branch)
                print(f"Repository ready at: {repo_path}")

            # Get events that are processed but not pushed
            lock = self.config_manager.lock
            events_to_push = [
                e for e in lock.events
                if e.progress.processed and not e.progress.pushed
            ]
            
            if not events_to_push:
                print("No events to push.")
                return True
            
            print(f"Pushing {len(events_to_push)} event(s)...\n")
            
            github_agent = GitHubAgent(self.github_token, self.openai_api_key)
            for event in events_to_push:
                success = self._push_event(event, github_agent)
                if not success:
                    print(f"✗ Failed to push event: {event.name}")
                    return False
            
            print("\n✓ Push phase completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n✗ Push phase failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _push_event(self, event: EventLock, github_agent: GitHubAgent) -> bool:
        """Push a single event's changes."""
        print(f"\n{'=' * 60}")
        print(f"🚀 Pushing: {event.name}")
        print(f"{'=' * 60}")
        
        try:
            config = self.config_manager.config
            branch_prefix = config.defaults.branchPrefix or ""
            branch_name = f"{branch_prefix}{event.branch}"
            
            # Push branch to remote
            print(f"📤 Pushing branch: {branch_name}")
            self.git_agent.push_branch(branch_name)
            
            # Create pull request
            print(f"📝 Creating pull request...")
            target_branch = config.project.targetBranch or "main"
            
            pr_title = f"🎨 {event.name} Theme Customizations"
            pr_body = self._generate_pr_description(event)
            
            # Use agent to create pull request
            user_input = f"""
            Search for existing GitHub issues with title "{pr_title}" in repository {self.owner}/{self.repo}.
            If no duplicate exists, create a new pull request with title "{pr_title}", body "{pr_body}", and head branch "{branch_name}".
            
            Return the pull request number as JSON: {{"pr_number": <number>}}
            """
            
            pr_response = github_agent.run(messages=[ChatMessage.from_user(user_input)])
            
            # Extract PR number from response
            pr_number = None
            if pr_response and "messages" in pr_response:
                final_message = pr_response["messages"][-1]
                if hasattr(final_message, "content"):
                    import re
                    import json
                    try:
                        # Look for JSON in response
                        json_match = re.search(r'\{[^}]*"pr_number"[^}]*\}', final_message.content)
                        if json_match:
                            result = json.loads(json_match.group())
                            pr_number = result.get("pr_number")
                    except:
                        # Fallback: look for issue number pattern
                        match = re.search(r'#(\d+)', final_message.content)
                        if match:
                            pr_number = int(match.group(1))
            
            pr_url = f"https://github.com/{self.owner}/{self.repo}/pull/{pr_number}" if pr_number else "Unknown"
            print(f"✓ Pull request created: {pr_url}")
            
            # Update progress
            self.config_manager.update_event_progress(
                event.id,
                pushed=True,
                pr_created=True,
                pr_url=pr_url
            )
            
            return True
            
        except Exception as e:
            print(f"\n✗ Failed to push event: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _generate_pr_description(self, event: EventLock) -> str:
        """Generate PR description."""
        return f"""## 🎨 {event.name} Theme Customizations

This PR applies event-themed decorations for **{event.name}**.

### Event Details
- **Event Period:** {event.startDate} to {event.endDate}
- **Description:** {event.description}

### Changes Applied
This automated customization includes:
- 🖼️ Image transformations with event-themed elements
- 📝 Text adaptations for event context
- 🎯 Selective modifications based on configured selectors

### Modified Files
{chr(10).join(f'- `{f}`' for f in event.progress.modified_files[:20])}
{f'... and {len(event.progress.modified_files) - 20} more files' if len(event.progress.modified_files) > 20 else ''}

### Review Notes
- Original files have been backed up with `.original` extension
- Changes can be easily reverted if needed
- All modifications maintain the original structure and functionality

---
*Generated automatically by [Doodlify](https://github.com/doodlify) 🎨*
*Event ID: `{event.id}`*
*Commit: `{event.progress.commit_sha[:8] if event.progress.commit_sha else 'N/A'}`*
"""
    
    def clear(self, event_id: Optional[str] = None) -> bool:
        """
        Clear phase: Clear lock data.
        
        Args:
            event_id: Optional event ID to clear. If None, clears all.
            
        Returns:
            True if successful
        """
        print("\n" + "=" * 60)
        print("🧹 CLEAR PHASE")
        print("=" * 60)
        
        try:
            if event_id:
                print(f"Clearing event: {event_id}")
                self.config_manager.clear_event(event_id)
                print(f"✓ Event {event_id} cleared")
            else:
                print("Clearing all lock data...")
                self.config_manager.clear_all()
                print("✓ All lock data cleared")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Clear failed: {e}")
            return False
