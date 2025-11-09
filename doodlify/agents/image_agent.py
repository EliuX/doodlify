"""
Image decoration agent using OpenAI's image editing API.
"""

import base64
from pathlib import Path
from typing import Optional
from openai import OpenAI


class ImageAgent:
    """Handles image transformations for events using OpenAI."""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def generate_prompt(self, event_name: str, event_description: str, image_context: str = "") -> str:
        """Generate a prompt for image transformation based on event."""
        base_prompt = f"""
Generate a new flat 2D illustration version of the image that adapts it for {event_name}.
{event_description}

Instructions:
- Maintain the core composition and subject matter of the original image
- Add thematic elements related to {event_name}
- Keep the style consistent with the original
- Use colors and visual elements that evoke the theme
- Ensure the result is professional and high-quality
- PRESERVE any existing transparency (alpha channel) exactly as in the original
- Do NOT introduce a checkerboard or solid fill where transparency exists
- Do NOT flatten the image; keep transparent pixels transparent
"""
        
        if image_context:
            base_prompt += f"\n\nContext about this image: {image_context}"
        
        return base_prompt.strip()
    
    def transform_image(
        self,
        image_path: Path,
        event_name: str,
        event_description: str,
        output_path: Optional[Path] = None,
        image_context: str = ""
    ) -> bytes:
        """
        Transform an image for a specific event.
        
        Args:
            image_path: Path to the input image
            event_name: Name of the event
            event_description: Description of the event for context
            output_path: Optional path to save the transformed image
            image_context: Additional context about the image's purpose
            
        Returns:
            Image bytes of the transformed image
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        prompt = self.generate_prompt(event_name, event_description, image_context)
        
        # Call OpenAI image edit API
        with open(image_path, 'rb') as f:
            result = self.client.images.edit(
                model="gpt-image-1",
                image=f,
                prompt=prompt
            )
        
        # Get base64 encoded image
        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)
        
        # Save to output path if provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(image_bytes)
        
        return image_bytes
    
    def is_supported_format(self, file_path: Path) -> bool:
        """Check if image format is supported."""
        supported_extensions = {'.png', '.jpg', '.jpeg', '.webp'}
        return file_path.suffix.lower() in supported_extensions
    
    def batch_transform(
        self,
        image_paths: list[Path],
        event_name: str,
        event_description: str,
        output_dir: Optional[Path] = None
    ) -> dict[str, bytes]:
        """
        Transform multiple images for an event.
        
        Args:
            image_paths: List of image paths to transform
            event_name: Name of the event
            event_description: Description of the event
            output_dir: Optional directory to save transformed images
            
        Returns:
            Dictionary mapping original paths to transformed image bytes
        """
        results = {}
        
        for image_path in image_paths:
            if not self.is_supported_format(image_path):
                print(f"Skipping unsupported format: {image_path}")
                continue
            
            output_path = None
            if output_dir:
                output_path = output_dir / image_path.name
            
            try:
                image_bytes = self.transform_image(
                    image_path,
                    event_name,
                    event_description,
                    output_path
                )
                results[str(image_path)] = image_bytes
                print(f"✓ Transformed: {image_path.name}")
            except Exception as e:
                print(f"✗ Failed to transform {image_path.name}: {e}")
                results[str(image_path)] = None
        
        return results
