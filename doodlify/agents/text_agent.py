"""
Text decoration agent for i18n and content adaptation.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from openai import OpenAI


class TextAgent:
    """Handles text content transformations for events."""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def generate_adaptation_prompt(
        self,
        original_text: str,
        event_name: str,
        event_description: str,
        context: str = ""
    ) -> str:
        """Generate a prompt for text adaptation."""
        prompt = f"""
You are adapting website text content for a special event: {event_name}.

Event Description: {event_description}

Original text: "{original_text}"

{f"Context: {context}" if context else ""}

Instructions:
- Adapt the text to reflect the event theme while maintaining the core message
- Keep the tone professional and appropriate
- Maintain the same language as the original
- Keep the text length similar to the original
- Only output the adapted text, nothing else

Adapted text:"""
        return prompt.strip()
    
    def adapt_text(
        self,
        text: str,
        event_name: str,
        event_description: str,
        context: str = ""
    ) -> str:
        """
        Adapt a single text string for an event.
        
        Args:
            text: Original text to adapt
            event_name: Name of the event
            event_description: Description of the event
            context: Additional context about the text
            
        Returns:
            Adapted text
        """
        prompt = self.generate_adaptation_prompt(text, event_name, event_description, context)
        
        response = self.client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are a professional copywriter specializing in event-themed content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        adapted_text = response.choices[0].message.content.strip()
        # Remove quotes if present
        if adapted_text.startswith('"') and adapted_text.endswith('"'):
            adapted_text = adapted_text[1:-1]
        
        return adapted_text
    
    def adapt_i18n_file(
        self,
        file_path: Path,
        event_name: str,
        event_description: str,
        output_path: Optional[Path] = None,
        keys_to_adapt: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Adapt an i18n JSON file for an event.
        
        Args:
            file_path: Path to the i18n JSON file
            event_name: Name of the event
            event_description: Description of the event
            output_path: Optional path to save adapted content
            keys_to_adapt: Optional list of specific keys to adapt (None = adapt all)
            
        Returns:
            Dictionary with adapted content
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        adapted_content = self._adapt_nested_dict(
            content,
            event_name,
            event_description,
            keys_to_adapt
        )
        
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(adapted_content, f, indent=2, ensure_ascii=False)
        
        return adapted_content
    
    def _adapt_nested_dict(
        self,
        data: Dict[str, Any],
        event_name: str,
        event_description: str,
        keys_to_adapt: Optional[List[str]] = None,
        current_path: str = ""
    ) -> Dict[str, Any]:
        """Recursively adapt nested dictionary values."""
        result = {}
        
        for key, value in data.items():
            full_path = f"{current_path}.{key}" if current_path else key
            
            if isinstance(value, dict):
                # Recursively handle nested dictionaries
                result[key] = self._adapt_nested_dict(
                    value,
                    event_name,
                    event_description,
                    keys_to_adapt,
                    full_path
                )
            elif isinstance(value, str):
                # Check if we should adapt this key
                should_adapt = (
                    keys_to_adapt is None or
                    key in keys_to_adapt or
                    full_path in keys_to_adapt
                )
                
                if should_adapt and len(value) > 3:  # Don't adapt very short strings
                    try:
                        adapted = self.adapt_text(
                            value,
                            event_name,
                            event_description,
                            context=f"Key: {full_path}"
                        )
                        result[key] = adapted
                        print(f"  Adapted: {full_path}")
                    except Exception as e:
                        print(f"  Failed to adapt {full_path}: {e}")
                        result[key] = value
                else:
                    result[key] = value
            else:
                # Keep non-string values as is
                result[key] = value
        
        return result
    
    def find_i18n_files(self, repo_path: Path) -> List[Path]:
        """
        Find internationalization files in a repository.
        
        Common patterns:
        - **/i18n/**/*.json
        - **/locales/**/*.json
        - **/lang/**/*.json
        - **/messages.json
        - **/translations/**/*.json
        """
        patterns = [
            "**/i18n/**/*.json",
            "**/locales/**/*.json",
            "**/lang/**/*.json",
            "**/messages.json",
            "**/translations/**/*.json"
        ]
        
        i18n_files = []
        for pattern in patterns:
            i18n_files.extend(repo_path.glob(pattern))
        
        # Remove duplicates
        return list(set(i18n_files))
    
    def should_adapt_key(self, key: str) -> bool:
        """Determine if a key should be adapted based on its name."""
        # Skip keys that are likely technical or structural
        skip_patterns = ['id', 'key', 'code', 'url', 'path', 'api', 'endpoint']
        key_lower = key.lower()
        
        for pattern in skip_patterns:
            if pattern in key_lower:
                return False
        
        # Prioritize keys that are likely user-facing
        priority_patterns = ['title', 'description', 'message', 'text', 'label', 'heading', 'greeting']
        for pattern in priority_patterns:
            if pattern in key_lower:
                return True
        
        return True
