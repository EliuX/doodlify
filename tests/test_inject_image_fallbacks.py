"""
Unit tests for _inject_image_fallbacks logic.
"""

import re
import pytest


def inject_onerror_attribute(html: str, image_name: str, backup_name: str, force_rewrite: bool = False) -> str:
    """
    Inject onerror attribute into img tags.
    
    Args:
        html: HTML content
        image_name: Name of the image file (e.g., 'hero.png')
        backup_name: Name of the backup file (e.g., 'hero.original.png')
        force_rewrite: If True, removes existing onerror and rewrites it
    
    Returns:
        Modified HTML content
    """
    new_html = html
    
    if force_rewrite:
        # Remove existing onerror attributes
        # Strategy: Match the entire img tag and extract only the attributes we want to keep
        full_tag_pattern = re.compile(
            rf"<img([^>]*src=(?:'|\")(?:[^'\"]*{re.escape(image_name)})['\"][^>]*)>",
            re.IGNORECASE | re.DOTALL
        )
        
        def remove_onerror(m):
            tag_content = m.group(1)
            # Extract all attributes except onerror
            # Split by attribute boundaries and filter out onerror
            attrs = []
            # Match attributes: name="value" or name='value'
            attr_pattern = re.compile(r'(\s+\w+(?:-\w+)*\s*=\s*[\'"][^\'"]*[\'"])', re.IGNORECASE)
            for attr_match in attr_pattern.finditer(tag_content):
                attr = attr_match.group(1)
                if not re.search(r'onerror\s*=', attr, re.IGNORECASE):
                    attrs.append(attr)
            return f"<img{''.join(attrs)} />"
        
        new_html = full_tag_pattern.sub(remove_onerror, new_html)
    
    # Match <img ... src="...name..."> - be specific about the image name
    # Use word boundary or path separator to avoid matching partial names
    pattern = re.compile(
        rf"(<img[^>]*?src=(?:'|\")(?:[^'\"]*/)?\b{re.escape(image_name)}\b['\"][^>]*?)(\s*/?\s*>)",
        re.IGNORECASE | re.DOTALL
    )
    
    def _inject(m):
        tag_start = m.group(1)
        closing = m.group(2)
        # If already has onerror, skip (unless force_rewrite removed it above)
        if not force_rewrite and re.search(r"onerror=", tag_start, re.IGNORECASE):
            return m.group(0)
        # Normalize closing: remove extra whitespace, keep / if present, add space before >
        normalized_closing = " />" if "/" in closing else ">"
        return tag_start + f" onerror=\"this.onerror=null;this.src='{backup_name}'\"" + normalized_closing
    
    return pattern.sub(_inject, new_html)


class TestInjectImageFallbacks:
    """Test cases for injecting onerror attributes into img tags."""
    
    def test_simple_img_tag(self):
        """Test injection into a simple img tag."""
        html = '<img src="images/hero.png" alt="Hero">'
        result = inject_onerror_attribute(html, "hero.png", "hero.original.png")
        assert 'onerror="this.onerror=null;this.src=\'hero.original.png\'"' in result
        assert result == '<img src="images/hero.png" alt="Hero" onerror="this.onerror=null;this.src=\'hero.original.png\'">'
    
    def test_self_closing_img_tag(self):
        """Test injection into a self-closing img tag."""
        html = '<img src="images/hero.png" alt="Hero" />'
        result = inject_onerror_attribute(html, "hero.png", "hero.original.png")
        assert 'onerror="this.onerror=null;this.src=\'hero.original.png\'"' in result
        assert result == '<img src="images/hero.png" alt="Hero" onerror="this.onerror=null;this.src=\'hero.original.png\'" />'
    
    def test_multiline_img_tag(self):
        """Test injection into a multiline img tag."""
        html = '''<img
  class="img-fluid"
  src="images/hero.png"
  alt="Hero"
/>'''
        result = inject_onerror_attribute(html, "hero.png", "hero.original.png")
        assert 'onerror="this.onerror=null;this.src=\'hero.original.png\'"' in result
        # Should normalize the closing to " />"
        assert 'onerror="this.onerror=null;this.src=\'hero.original.png\'" />' in result
    
    def test_multiline_img_tag_with_separated_slash(self):
        """Test injection into a multiline img tag with slash on separate line."""
        html = '''<img
  class="img-fluid"
  src="images/hero-ecommerce-construction.png"
  alt="eCommerce construction"
  />'''
        result = inject_onerror_attribute(html, "hero-ecommerce-construction.png", "hero-ecommerce-construction.original.png")
        assert 'onerror="this.onerror=null;this.src=\'hero-ecommerce-construction.original.png\'"' in result
        assert 'onerror="this.onerror=null;this.src=\'hero-ecommerce-construction.original.png\'" />' in result
        # Should not have malformed output like "/ onerror=..."
        assert '/ onerror=' not in result
    
    def test_skip_existing_onerror(self):
        """Test that existing onerror is not duplicated."""
        html = '<img src="images/hero.png" alt="Hero" onerror="handleError()">'
        result = inject_onerror_attribute(html, "hero.png", "hero.original.png")
        # Should not modify - already has onerror
        assert result == html
    
    def test_force_rewrite_existing_onerror(self):
        """Test that force_rewrite replaces existing onerror."""
        html = '<img src="images/hero.png" alt="Hero" onerror="oldHandler()">'
        result = inject_onerror_attribute(html, "hero.png", "hero.original.png", force_rewrite=True)
        assert 'onerror="this.onerror=null;this.src=\'hero.original.png\'"' in result
        assert 'oldHandler()' not in result
    
    def test_force_rewrite_malformed_onerror(self):
        """Test that force_rewrite fixes malformed onerror attributes."""
        # This is the actual broken case from the codebase
        html = '''<img
  class="img-fluid"
  src="images/hero-ecommerce-construction.png"
  alt="eCommerce construction"
/ onerror="this.onerror=null;this.src='hero-ecommerce-construction.original.png'">'''
        
        result = inject_onerror_attribute(html, "hero-ecommerce-construction.png", "hero-ecommerce-construction.original.png", force_rewrite=True)
        
        # Should fix the malformed tag
        assert '/ onerror=' not in result
        assert 'onerror="this.onerror=null;this.src=\'hero-ecommerce-construction.original.png\'" />' in result
    
    def test_multiple_img_tags(self):
        """Test injection into multiple img tags."""
        html = '''
        <img src="images/hero.png" alt="Hero">
        <img src="images/logo.png" alt="Logo">
        '''
        result = inject_onerror_attribute(html, "hero.png", "hero.original.png")
        # Should only inject into the hero.png tag
        # Count img tags with onerror attribute (not the string "onerror=" which appears twice: once as attribute, once in the handler)
        assert result.count('<img') == 2
        assert result.count('src="images/hero.png"') == 1
        assert result.count('src="images/logo.png"') == 1
        # Only hero.png should have the onerror attribute
        assert 'hero.original.png' in result
        assert 'logo.original.png' not in result
        # Verify logo.png tag doesn't have onerror attribute
        logo_line = [line for line in result.split('\n') if 'logo.png' in line][0]
        assert ' onerror=' not in logo_line
    
    def test_img_tag_with_single_quotes(self):
        """Test injection into img tag with single quotes."""
        html = "<img src='images/hero.png' alt='Hero'>"
        result = inject_onerror_attribute(html, "hero.png", "hero.original.png")
        assert 'onerror="this.onerror=null;this.src=\'hero.original.png\'"' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
