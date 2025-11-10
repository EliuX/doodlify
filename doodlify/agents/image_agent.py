"""
Image decoration agent using OpenAI's image editing API.
"""

import base64
from pathlib import Path
from typing import Optional
from openai import OpenAI
from PIL import Image
import io


class ImageAgent:
    """Handles image transformations for events using OpenAI."""

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def generate_prompt(self, event_name: str, event_description: str, image_context: str = "") -> str:
        """Generate a prompt for image transformation based on event."""
        base_prompt = f"""
        Generate a new version of the image that adapts it for {event_name}.
        {event_description}

        Instructions:
        - Ensure the result is professional and high-quality
        - Maintain the style, core composition and subject matter of the original image
        - Add thematic elements related to {event_name} or replace the existing ones
        - Use colors and visual elements that evoke the theme
        - The background without content is transparent.
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

        prompt = self.generate_prompt(
            event_name, event_description, image_context)

        # Call OpenAI image edit API (leave size as default 'auto')
        with open(image_path, 'rb') as f:
            result = self.client.images.edit(
                model="gpt-image-1",
                image=f,
                prompt=prompt,
                background="auto"
            )

        # Get base64 encoded image
        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        # Harmonize output size with original if needed (and possible)
        image_bytes = self._harmonize_output_size(image_path, image_bytes)

        # Save to output path if provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(image_bytes)

        return image_bytes

    def _harmonize_output_size(self, source_path: Path, image_bytes: bytes) -> bytes:
        """Ensure the output image matches the original size when possible.

        - If sizes match: return bytes unchanged.
        - If sizes differ but aspect ratio matches (within a small tolerance), resize to the
          original canvas using high-quality resampling, preserving transparency.
        - Otherwise: log a warning and return bytes unchanged.
        """
        try:
            with Image.open(source_path) as _orig:
                o_w, o_h = _orig.size
                orig_has_alpha = 'A' in _orig.getbands()
            with Image.open(io.BytesIO(image_bytes)) as _out:
                n_w, n_h = _out.size
                # Fast path: identical
                if (n_w, n_h) == (o_w, o_h):
                    return image_bytes

                # Check aspect ratio closeness
                def _ratio(w, h):
                    return float(w) / float(h) if h else 0.0

                r_orig = _ratio(o_w, o_h)
                r_new = _ratio(n_w, n_h)
                if abs(r_orig - r_new) <= 1e-3:
                    # Resize to exact original canvas
                    result_img = _out.convert("RGBA")
                    resized = result_img.resize((o_w, o_h), Image.LANCZOS)
                    # Ensure transparency is preserved when present
                    if not orig_has_alpha and 'A' not in resized.getbands():
                        # No alpha to enforce; keep as is
                        pass
                    # Serialize as PNG (to keep alpha)
                    buf = io.BytesIO()
                    resized.save(buf, format='PNG')
                    fixed_bytes = buf.getvalue()
                    print(
                        f"ℹ️  ImageAgent: resized output from {n_w}x{n_h} to match original {o_w}x{o_h} for {source_path.name}"
                    )
                    return fixed_bytes
                else:
                    print(
                        f"⚠️  ImageAgent: output size {n_w}x{n_h} aspect ratio differs from original {o_w}x{o_h} for {source_path.name}"
                    )
                    return image_bytes
        except Exception:
            # If any step fails, return original bytes
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
