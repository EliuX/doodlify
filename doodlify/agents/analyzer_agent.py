"""
Analyzer agent using Haystack AI for codebase analysis.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Set, Optional
from openai import OpenAI


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
        
        # Find all relevant files
        frontend_files = self._find_frontend_files(repo_path, sources)
        
        # Analyze files
        image_files = self._find_image_files(frontend_files)
        text_files = self._find_text_files(frontend_files)
        
        # If selector provided, find files using that selector
        selector_matches = []
        if selector:
            selector_matches = self._find_files_with_selector(
                frontend_files,
                selector
            )
        
        # Use AI to provide intelligent analysis
        ai_analysis = self._ai_analyze_structure(
            repo_path,
            frontend_files[:20],  # Limit to first 20 files for analysis
            project_description,
            selector
        )
        
        return {
            "files_of_interest": selector_matches if selector_matches else image_files + text_files,
            "image_files": image_files,
            "text_files": text_files,
            "selectors_found": self._extract_selectors_from_files(frontend_files),
            "notes": ai_analysis
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
                continue
            
            for ext in frontend_extensions:
                files.extend(search_path.rglob(f"*{ext}"))
        
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
        
        prompt = f"""
Analyze this frontend project to identify what elements should be customized for special events.

Project Description: {project_description}
{f"Target Selector: {selector}" if selector else "No specific selector provided."}

Sample Files:
{chr(10).join(file_samples[:5])}

Provide insights on:
1. What type of frontend framework is used (React, Vue, Static HTML, etc.)
2. Where are the main visual elements located (hero images, banners, logos)
3. What files would be best to modify for event customization
4. Any special considerations for this project

Respond in JSON format with keys: framework, visual_elements_location, priority_files, considerations
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a code analysis expert. Respond in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            response_text = response.choices[0].message.content.strip()
            
            # Try to parse as JSON, otherwise return as text
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {"analysis": response_text}
        except Exception as e:
            return {"error": str(e), "analysis": "AI analysis unavailable"}
