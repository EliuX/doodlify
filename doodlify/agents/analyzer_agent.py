"""
Analyzer agent using Haystack AI for codebase analysis.
"""

import re
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Set, Optional
from openai import OpenAI

# Configure logging for analyzer visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AnalyzerAgent:
    """Analyzes frontend codebases to identify elements for decoration."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
    
    def analyze_codebase(
        self,
        repo_path: Path,
        sources: List[str],
        selector: Optional[str] = None,
        project_description: str = ""
    ) -> Dict[str, any]:
        """
        Analyze codebase to identify files and elements for decoration.
        
        Args:
            repo_path: Path to the repository
            sources: List of source directories to analyze
            selector: Optional CSS selector to match elements
            project_description: Description of the project
            
        Returns:
            Analysis results including files to modify
        """
        print("🔍 Analyzing codebase...")
        logger.info(f"Starting codebase analysis for repository: {repo_path}")
        logger.info(f"Source directories to scan: {sources if sources else ['entire repository']}")
        
        # Find all relevant files
        frontend_files = self._find_frontend_files(repo_path, sources)
        logger.info(f"Found {len(frontend_files)} frontend files across all source directories")
        
        # Analyze files
        image_files = self._find_image_files(frontend_files)
        logger.info(f"Discovered {len(image_files)} image files/references")
        
        text_files = self._find_text_files(frontend_files)
        logger.info(f"Found {len(text_files)} i18n/text files")
        
        # If selector provided, find files using that selector
        selector_matches = []
        if selector:
            logger.info(f"Searching for files matching CSS selector: {selector}")
            selector_matches = self._find_files_with_selector(
                frontend_files,
                selector
            )
            logger.info(f"Found {len(selector_matches)} files matching selector '{selector}'")
        
        # Use AI to provide intelligent analysis
        logger.info(f"Running AI analysis on sample of {min(20, len(frontend_files))} files")
        ai_analysis = self._ai_analyze_structure(
            repo_path,
            frontend_files[:20],  # Limit to first 20 files for analysis
            project_description,
            selector
        )
        logger.info("AI analysis completed")
        
        # Lightweight heuristics to guide suggestions
        logger.info("Running heuristic analysis to detect project features...")
        has_css_vars = self._detect_css_variables(frontend_files)
        logger.info(f"CSS variables detected: {has_css_vars}")
        
        has_event_data_attrs = self._detect_data_attributes(frontend_files)
        logger.info(f"Event data attributes detected: {has_event_data_attrs}")
        
        svg_count = self._count_svg_assets(frontend_files)
        logger.info(f"SVG assets found: {svg_count}")
        
        has_global_css = self._detect_global_styles(frontend_files)
        logger.info(f"Global CSS files detected: {has_global_css}")
        
        has_marker_styles = self._detect_marker_styles(frontend_files)
        logger.info(f"CSS marker styles detected: {has_marker_styles}")
        
        has_favicon = self._detect_favicon_assets(frontend_files)
        logger.info(f"Favicon assets detected: {has_favicon}")
        
        has_og_image = self._detect_og_image(frontend_files)
        logger.info(f"Open Graph image meta tags detected: {has_og_image}")

        ctx = {
            "image_files": image_files,
            "text_files": text_files,
            "selector": selector,
            "ai_analysis": ai_analysis,
            "has_css_vars": has_css_vars,
            "has_event_data_attrs": has_event_data_attrs,
            "svg_count": svg_count,
            "has_global_css": has_global_css,
            "has_marker_styles": has_marker_styles,
            "has_favicon": has_favicon,
            "has_og_image": has_og_image,
        }

        logger.info("Building improvement suggestions based on analysis...")
        suggestions = self._build_improvement_suggestions(ctx)
        logger.info(f"Generated {len(suggestions)} improvement suggestions")

        # Normalize to repo-root relative paths so sources only guide discovery
        norm_images = self._normalize_paths(repo_path, sources, image_files)
        norm_texts = self._normalize_paths(repo_path, sources, text_files)
        norm_selectors = self._normalize_paths(repo_path, sources, selector_matches if selector_matches else [])

        return {
            "files_of_interest": norm_selectors if selector_matches else (norm_images + norm_texts),
            "image_files": norm_images,
            "text_files": norm_texts,
            "selectors_found": self._extract_selectors_from_files(frontend_files),
            "notes": ai_analysis,
            "improvement_suggestions": suggestions,
        }
    
    def _find_frontend_files(self, repo_path: Path, sources: List[str]) -> List[Path]:
        """Find all frontend-related files in specified sources."""
        frontend_extensions = {
            '.tsx', '.ts', '.jsx', '.js',
            '.vue', '.svelte',
            '.html', '.htm',
            '.css', '.scss', '.sass', '.less'
        }
        
        files = []
        search_paths = [repo_path / src for src in sources] if sources else [repo_path]
        
        for search_path in search_paths:
            if not search_path.exists():
                logger.warning(f"Source directory does not exist: {search_path}")
                continue
            
            logger.info(f"Scanning directory: {search_path}")
            path_files = []
            for ext in frontend_extensions:
                ext_files = list(search_path.rglob(f"*{ext}"))
                path_files.extend(ext_files)
            
            logger.info(f"Found {len(path_files)} frontend files in {search_path}")
            files.extend(path_files)
        
        # Filter out node_modules, build, dist, etc.
        exclude_patterns = ['node_modules', 'dist', 'build', '.next', 'out', 'coverage', '.git']
        filtered_files = [
            f for f in files
            if not any(pattern in str(f) for pattern in exclude_patterns)
        ]
        
        return filtered_files
    
    def _find_image_files(self, files: List[Path]) -> List[str]:
        """Extract paths to image files referenced in the codebase."""
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico'}
        image_files = []
        
        for file_path in files:
            if file_path.suffix.lower() in image_extensions:
                image_files.append(str(file_path))
            else:
                # Look for image references in code
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    # Find image paths in imports, src attributes, etc.
                    image_patterns = [
                        r'["\']([^"\']*\.(?:png|jpg|jpeg|gif|svg|webp|ico))["\']',
                        r'url\(["\']?([^"\'()]*\.(?:png|jpg|jpeg|gif|svg|webp|ico))["\']?\)',
                    ]
                    for pattern in image_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        image_files.extend(matches)
                except Exception:
                    continue
        
        return list(set(image_files))
    
    def _find_text_files(self, files: List[Path]) -> List[str]:
        """Find text/i18n files for adaptation."""
        i18n_patterns = ['i18n', 'locales', 'lang', 'translations', 'messages.json']
        text_files = []
        
        for file_path in files:
            # Check if file path contains i18n patterns
            if any(pattern in str(file_path).lower() for pattern in i18n_patterns):
                if file_path.suffix == '.json':
                    text_files.append(str(file_path))
        
        return text_files
    
    def _find_files_with_selector(self, files: List[Path], selector: str) -> List[str]:
        """Find files that contain elements matching the CSS selector."""
        matching_files = []
        
        # Parse selector to extract class names, IDs, and tag names
        selector_parts = self._parse_selector(selector)
        
        for file_path in files:
            if file_path.suffix.lower() not in {'.tsx', '.jsx', '.html', '.vue', '.svelte'}:
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Check if any selector part matches in the file
                if self._selector_matches_content(content, selector_parts):
                    matching_files.append(str(file_path))
            except Exception:
                continue
        
        return matching_files
    
    def _parse_selector(self, selector: str) -> Dict[str, List[str]]:
        """Parse CSS selector into components."""
        parts = {
            'classes': re.findall(r'\.([a-zA-Z0-9_-]+)', selector),
            'ids': re.findall(r'#([a-zA-Z0-9_-]+)', selector),
            'tags': re.findall(r'\b([a-z]+)\b(?![a-zA-Z])', selector)
        }
        return parts
    
    def _selector_matches_content(self, content: str, selector_parts: Dict[str, List[str]]) -> bool:
        """Check if content contains elements matching selector parts."""
        # Check for class names
        for class_name in selector_parts['classes']:
            patterns = [
                rf'className=["\'](?:[^"\']*\s)?{class_name}(?:\s[^"\']*)?["\']',
                rf'class=["\'](?:[^"\']*\s)?{class_name}(?:\s[^"\']*)?["\']',
            ]
            if any(re.search(pattern, content) for pattern in patterns):
                return True
        
        # Check for IDs
        for id_name in selector_parts['ids']:
            if re.search(rf'id=["\'](?:[^"\']*\s)?{id_name}(?:\s[^"\']*)?["\']', content):
                return True
        
        # Check for tag names (less specific)
        for tag in selector_parts['tags']:
            if re.search(rf'<{tag}[\s>]', content, re.IGNORECASE):
                return True
        
        return False

    def _detect_favicon_assets(self, files: List[Path]) -> bool:
        candidates = {"favicon.ico", "favicon.png", "apple-touch-icon.png", "apple-touch-icon-precomposed.png"}
        for p in files:
            name = p.name.lower()
            if name in candidates:
                return True
        return False

    def _detect_og_image(self, files: List[Path]) -> bool:
        for p in files:
            if p.suffix.lower() not in {'.html', '.htm'}:
                continue
            try:
                txt = p.read_text(encoding='utf-8', errors='ignore').lower()
                if 'property="og:image"' in txt or "property='og:image'" in txt or "og:image" in txt:
                    return True
            except Exception:
                continue
        return False
    
    def _extract_selectors_from_files(self, files: List[Path]) -> List[str]:
        """Extract common CSS selectors from files."""
        selectors = set()
        
        for file_path in files[:50]:  # Limit to first 50 files
            if file_path.suffix.lower() not in {'.tsx', '.jsx', '.html', '.vue'}:
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Extract class names
                class_matches = re.findall(r'className=["\']([^"\']+)["\']', content)
                class_matches += re.findall(r'class=["\']([^"\']+)["\']', content)
                
                for classes in class_matches:
                    for cls in classes.split():
                        if cls and len(cls) > 2:
                            selectors.add(f".{cls}")
                
                # Extract IDs
                id_matches = re.findall(r'id=["\']([^"\']+)["\']', content)
                for id_val in id_matches:
                    if id_val and len(id_val) > 2:
                        selectors.add(f"#{id_val}")
            except Exception:
                continue
        
        return sorted(list(selectors))[:50]  # Return top 50 selectors
    
    def _ai_analyze_structure(
        self,
        repo_path: Path,
        sample_files: List[Path],
        project_description: str,
        selector: Optional[str]
    ) -> Dict[str, any]:
        """Use AI to analyze project structure and provide insights."""
        # Prepare sample of file contents
        file_samples = []
        for file_path in sample_files[:10]:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                file_samples.append(f"File: {file_path.name}\n{content[:500]}...")
            except Exception:
                continue
        
        prompt = (
            "Analyze this frontend project to identify what elements should be customized for special events.\n\n"
            f"Project Description: {project_description}\n"
            f"{('Target Selector: ' + selector) if selector else 'No specific selector provided.'}\n\n"
            "Sample Files (names and excerpts):\n"
            f"{chr(10).join(file_samples[:5])}\n\n"
            "Return STRICT JSON with the following keys ONLY:\n"
            "{{\n"
            "  \"framework\": \"one of: React|Vue|Svelte|Static HTML|Next.js|Nuxt|Unknown\",\n"
            "  \"visual_elements_location\": \"string\",\n"
            "  \"priority_files\": [\"relative/path/one.ext\", \"relative/path/two.ext\"],\n"
            "  \"considerations\": \"short actionable considerations specific to the project (<= 5 sentences)\",\n"
            "  \"evidence\": [\n"
            "    {{\n"
            "      \"path\": \"relative/path/from/repo/root\",\n"
            "      \"reason\": \"why this path supports your consideration\",\n"
            "      \"snippet\": \"a short exact snippet from that file supporting the claim (if available)\"\n"
            "    }}\n"
            "  ]\n"
            "}}\n\n"
            "Rules:\n"
            "- Do NOT invent paths. Only include paths you are confident about.\n"
            "- Prefer citing files shown in the sample above or common entrypoints (app/, src/, public/).\n"
            "- Keep \"considerations\" project-specific, not generic.\n"
        )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a code analysis expert. Respond ONLY with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=900
            )
            response_text = response.choices[0].message.content.strip()

            # Parse JSON; if invalid, return error wrapper
            try:
                parsed = json.loads(response_text)
            except json.JSONDecodeError:
                return {"error": "invalid_json", "raw": response_text, "analysis": "AI analysis unavailable"}

            # Validate evidence: check files exist and optional snippet present in content
            evidence = parsed.get("evidence") or []
            validated: List[Dict[str, str]] = []
            for ev in evidence[:10]:  # limit validation cost
                try:
                    ev_path = ev.get("path")
                    if not ev_path:
                        continue
                    full = (repo_path / ev_path).resolve()
                    if not full.exists() or not full.is_file():
                        continue
                    ev_copy = {"path": ev_path, "reason": ev.get("reason", "")}
                    snippet = ev.get("snippet")
                    if snippet:
                        try:
                            txt = full.read_text(encoding='utf-8', errors='ignore')
                            if snippet in txt:
                                ev_copy["snippet_match"] = True
                            else:
                                ev_copy["snippet_match"] = False
                        except Exception:
                            ev_copy["snippet_match"] = False
                    validated.append(ev_copy)
                except Exception:
                    continue

            # Compute a simple confidence: fraction of validated evidence out of provided
            denom = max(1, len(evidence))
            confidence = round(min(1.0, len(validated) / denom), 2)

            parsed["evidence_validated"] = validated
            parsed["confidence"] = confidence
            return parsed
        except Exception as e:
            return {"error": str(e), "analysis": "AI analysis unavailable"}

    def _build_improvement_suggestions(self, ctx: Dict[str, any]) -> List[Dict[str, any]]:
        """Create optional, best-practice suggestions to improve adaptability.

        Context keys:
          - image_files: List[str]
          - text_files: List[str]
          - selector: Optional[str]
          - ai_analysis: Dict[str, any]
          - has_css_vars: bool
          - has_event_data_attrs: bool
          - svg_count: int
          - has_global_css: bool
          - has_marker_styles: bool
          - has_favicon: bool
          - has_og_image: bool
        """
        suggestions: List[Dict[str, any]] = []

        image_files = ctx.get("image_files", [])
        text_files = ctx.get("text_files", [])
        selector = ctx.get("selector")
        ai_analysis = ctx.get("ai_analysis", {})
        has_css_vars = bool(ctx.get("has_css_vars"))
        has_event_data_attrs = bool(ctx.get("has_event_data_attrs"))
        svg_count = int(ctx.get("svg_count", 0))
        has_global_css = bool(ctx.get("has_global_css"))
        has_marker_styles = bool(ctx.get("has_marker_styles"))
        has_favicon = bool(ctx.get("has_favicon"))
        has_og_image = bool(ctx.get("has_og_image"))

        # i18n is not required, but can help centralize copy
        if not text_files:
            logger.info("Creating suggestion: No i18n files found - recommending centralized text management")
            suggestions.append({
                "key": "i18n",
                "title": "Optional: Centralize user-facing copy in i18n files",
                "body": (
                    "No internationalization files were detected in scanned directories. While not required, keeping user-facing strings in i18n (e.g., `src/i18n/messages.json` or `locales/en/messages.json`) "
                    "can make text adaptations more consistent across events."
                ),
                "labels": ["enhancement", "i18n", "event-customization"],
            })

        # Avoid enforcing hero images; suggest alternative adaptation levers
        if not has_css_vars:
            logger.info("Creating suggestion: No CSS variables detected - recommending theme tokens")
            suggestions.append({
                "key": "css_variables",
                "title": "Add CSS variables for theme tokens (colors, spacing)",
                "body": (
                    "No CSS custom properties were detected in CSS files (e.g., `:root { --color-primary: ... }`). Defining theme tokens lets the tool adjust palettes "
                    "for events without relying on hero images."
                ),
                "labels": ["enhancement", "css", "theming"],
            })

        if not has_event_data_attrs and not selector:
            logger.info("Creating suggestion: No event data attributes or selector found - recommending element marking")
            suggestions.append({
                "key": "data_attrs",
                "title": "Add data attributes to mark adaptable elements",
                "body": (
                    "No event-specific data attributes found in HTML/JSX files and no selector provided. Consider annotating adaptable UI with attributes like `[data-event-adaptable]`, `[data-event-role='banner']`, or `[data-event-color]` "
                    "to help the analyzer and decorators target elements precisely."
                ),
                "labels": ["enhancement", "frontend", "event-customization"],
            })

        if svg_count == 0:
            logger.info("Creating suggestion: No SVG assets found - recommending SVG usage for recoloring")
            suggestions.append({
                "key": "svg_usage",
                "title": "Prefer SVG for logos/illustrations to enable recoloring",
                "body": (
                    "No SVG assets were detected in scanned directories. Using SVG for logos/illustrations enables clean recoloring and decorations during events."
                ),
                "labels": ["enhancement", "images", "svg"],
            })

        if not has_global_css:
            logger.info("Creating suggestion: No global CSS files found - recommending global stylesheet")
            suggestions.append({
                "key": "global_css",
                "title": "Ensure a global stylesheet or theme entrypoint exists",
                "body": (
                    "No global stylesheet detected in scanned files (e.g., `src/styles/global.css` or `app/globals.css`). A global stylesheet makes it easier to apply event-wide tweaks (palette, typography)."
                ),
                "labels": ["enhancement", "css", "theming"],
            })

        if not has_marker_styles:
            logger.info("Creating suggestion: No CSS marker styles found - recommending marker styling")
            suggestions.append({
                "key": "marker_styles",
                "title": "Style list markers (e.g., vignettes) to allow event variations",
                "body": (
                    "No `::marker` styles detected in CSS files. Adding list/bullet marker styles enables subtle event adaptations without layout changes."
                ),
                "labels": ["enhancement", "css"],
            })

        # Favicon / touch icons
        if has_favicon:
            logger.info("Creating suggestion: Favicon assets found - recommending event variants")
            suggestions.append({
                "key": "favicon_variants",
                "title": "Provide event-ready favicon/touch icon variants",
                "body": (
                    "Favicon assets detected in scanned files. Consider keeping event variants (e.g., `favicon-halloween.png`, `apple-touch-icon-xmas.png`) "
                    "and a small switch mechanism to apply seasonal icons. Keep changes subtle and non-intrusive."
                ),
                "labels": ["enhancement", "assets", "events"],
            })
        else:
            logger.info("Creating suggestion: No favicon assets found - recommending favicon establishment")
            suggestions.append({
                "key": "favicon_establish",
                "title": "Establish predictable favicon/touch icon assets",
                "body": (
                    "No favicon/touch icon assets were detected in scanned directories. Establishing predictable files (e.g., `public/favicon.png`, `public/apple-touch-icon.png`) "
                    "allows non-intrusive event variants to be swapped in."
                ),
                "labels": ["enhancement", "assets"],
            })

        # Open Graph social preview image
        if has_og_image:
            logger.info("Creating suggestion: Open Graph image found - recommending seasonal variants")
            suggestions.append({
                "key": "og_variants",
                "title": "Provide seasonal Open Graph social preview variants",
                "body": (
                    "An `og:image` meta tag was detected in HTML files. Consider providing seasonal social preview images (e.g., subtle hat or snow accents) "
                    "that can be swapped during events without intrusive UI changes."
                ),
                "labels": ["enhancement", "seo", "assets"],
            })
        else:
            logger.info("Creating suggestion: No Open Graph image found - recommending OG image addition")
            suggestions.append({
                "key": "og_add",
                "title": "Add Open Graph image meta for social sharing",
                "body": (
                    "No `og:image` meta tag was detected in HTML files. Adding one enables tasteful, non-intrusive seasonal variants for social sharing cards."
                ),
                "labels": ["enhancement", "seo"],
            })

        if not selector:
            logger.info("Creating suggestion: No selector provided - recommending CSS selectors for targeting")
            suggestions.append({
                "key": "selectors_guidance",
                "title": "Add CSS selectors or data-attributes to mark event-adaptable elements",
                "body": (
                    "No `defaults.selector` was provided in configuration. Adding selectors like `img.hero, .banner-image, [data-event-adaptable]` helps the analyzer "
                    "target the right UI elements and improves adaptation precision."
                ),
                "labels": ["enhancement", "frontend", "event-customization"],
            })

        # If AI analysis provided considerations WITH EVIDENCE, turn them into suggestions
        considerations = None
        evidence_validated: List[Dict[str, str]] = []
        confidence = 0.0
        if isinstance(ai_analysis, dict):
            considerations = ai_analysis.get("considerations")
            evidence_validated = ai_analysis.get("evidence_validated") or []
            try:
                confidence = float(ai_analysis.get("confidence") or 0.0)
            except Exception:
                confidence = 0.0

        # Thresholds
        min_evidence = 1
        min_conf = 0.6

        if (
            considerations and isinstance(considerations, str) and len(considerations) > 10
            and isinstance(evidence_validated, list) and len(evidence_validated) >= min_evidence
            and confidence >= min_conf
        ):
            logger.info(
                f"Creating suggestion: AI considerations (confidence={confidence}, evidence={len(evidence_validated)})"
            )
            suggestions.append({
                "key": "ai_considerations",
                "title": "Apply analyzer considerations to improve event readiness",
                "body": considerations,
                "labels": ["enhancement", "code-health"],
                "evidence": evidence_validated,
                "confidence": confidence,
            })
        else:
            if considerations:
                logger.info(
                    f"Skipping AI considerations due to insufficient evidence/confidence (confidence={confidence}, evidence={len(evidence_validated) if isinstance(evidence_validated, list) else 0})"
                )

        return suggestions

    def _detect_css_variables(self, files: List[Path]) -> bool:
        for p in files:
            if p.suffix.lower() not in {'.css', '.scss', '.sass', '.less'}:
                continue
            try:
                txt = p.read_text(encoding='utf-8', errors='ignore')
                if ":root" in txt and "--" in txt:
                    return True
            except Exception:
                continue
        return False

    def _detect_data_attributes(self, files: List[Path]) -> bool:
        patterns = ["data-event-adaptable", "data-event-role", "data-event-color"]
        for p in files:
            if p.suffix.lower() not in {'.tsx', '.jsx', '.html', '.vue', '.svelte'}:
                continue
            try:
                txt = p.read_text(encoding='utf-8', errors='ignore')
                if any(attr in txt for attr in patterns):
                    return True
            except Exception:
                continue
        return False

    def _count_svg_assets(self, files: List[Path]) -> int:
        count = 0
        for p in files:
            if p.suffix.lower() == '.svg':
                count += 1
        return count

    def _detect_global_styles(self, files: List[Path]) -> bool:
        candidates = ["global.css", "globals.css", "base.css", "theme.css"]
        for p in files:
            if p.suffix.lower() not in {'.css', '.scss', '.sass', '.less'}:
                continue
            if any(name in str(p).lower() for name in candidates):
                return True
        return False

    def _detect_marker_styles(self, files: List[Path]) -> bool:
        for p in files:
            if p.suffix.lower() not in {'.css', '.scss', '.sass', '.less'}:
                continue
            try:
                txt = p.read_text(encoding='utf-8', errors='ignore')
                if "::marker" in txt:
                    return True
            except Exception:
                continue
        return False

    # --- Path normalization helpers ---
    def _normalize_paths(self, repo_path: Path, sources: List[str], items: List[str]) -> List[str]:
        """Normalize a list of path-like items to repo-root relative strings.
        - If item is an absolute or repo-absolute path, convert to relative to repo_path.
        - If item is a web-style path (e.g., "/images/foo.png"), strip leading slash and try resolution under repo and sources.
        - If no candidate exists, return the normalized (slash-stripped) string to keep intent.
        """
        out: List[str] = []
        for raw in items:
            try:
                p = Path(str(raw))
                # Already a file path on disk
                if p.exists():
                    try:
                        rel = str(p.relative_to(repo_path))
                    except Exception:
                        # If it is under sources but not directly relative, try manual strip
                        rel = str(p).replace(str(repo_path) + os.sep, "") if str(p).startswith(str(repo_path)) else p.name
                    out.append(rel)
                    continue
                # Treat as repo-web or relative string
                candidate = self._resolve_repo_file(repo_path, sources, str(raw))
                if candidate and candidate.exists():
                    try:
                        out.append(str(candidate.relative_to(repo_path)))
                    except Exception:
                        out.append(candidate.name)
                else:
                    # Keep normalized intent without leading slash
                    out.append(str(raw).lstrip('/'))
            except Exception:
                out.append(str(raw).lstrip('/'))
        # De-duplicate while preserving order
        seen = set()
        deduped = []
        for s in out:
            if s not in seen:
                seen.add(s)
                deduped.append(s)
        return deduped

    def _resolve_repo_file(self, repo_path: Path, sources: List[str], raw_path: str) -> Path:
        """Resolve a path string to a file within the repo, trying common locations.
        Sources guide discovery; the returned path is always repo-root based if found.
        """
        normalized = str(raw_path or "").strip()
        if not normalized:
            return repo_path / ""
        # Strip leading slash from web paths
        normalized = normalized.lstrip('/')
        candidates: List[Path] = []
        # 1) Repo-root
        candidates.append(repo_path / normalized)
        # 2) Try each source root
        for s in (sources or []):
            s_norm = str(s).strip().lstrip('./')
            candidates.append(repo_path / s_norm / normalized)
        # 3) Heuristic UI root
        candidates.append(repo_path / 'web-ui' / 'src' / normalized)
        for c in candidates:
            try:
                if c.exists():
                    return c
            except Exception:
                continue
        return candidates[0]
