"""
Tests for the Muze HTML Embedding Module

=============================================================================
HOW TO RUN THESE TESTS:
=============================================================================
From the project root directory (Tab_to_TS/), run:

    PYTHONPATH=. pytest tests/test_html_embed.py -v

=============================================================================
WHAT THESE TESTS VERIFY:
=============================================================================
1. HTML templates are generated correctly
2. Configuration options are applied
3. Multi-chart pages work
4. Streamlit integration works
=============================================================================
"""

import pytest
from pathlib import Path
import tempfile

from muze.html_embed import (
    create_html_page,
    create_minimal_html,
    create_multi_chart_page,
    save_html_file,
    get_streamlit_component_html,
    EmbedConfig
)


# -----------------------------------------------------------------------------
# TEST FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture
def sample_muze_code():
    """Sample Muze JavaScript code for testing."""
    return '''const { muze, DataModel } = viz;

const schema = [
    { name: 'Category', type: 'dimension' },
    { name: 'Sales', type: 'measure', defAggFn: 'sum' }
];

const data = [
    { Category: 'A', Sales: 100 },
    { Category: 'B', Sales: 200 }
];

const dm = new DataModel(data, schema);

muze()
    .data(dm)
    .rows(['Sales'])
    .columns(['Category'])
    .layers([{ mark: 'bar' }])
    .title('Test Chart')
    .mount('#chart-container');
'''


# -----------------------------------------------------------------------------
# TESTS FOR BASIC HTML GENERATION
# -----------------------------------------------------------------------------

class TestHtmlGeneration:
    """Tests for HTML page generation."""
    
    def test_create_html_page(self, sample_muze_code):
        """Test creating a complete HTML page."""
        html = create_html_page(sample_muze_code, title="Test Chart")
        
        # Check basic structure
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        
        # Check title is included
        assert "Test Chart" in html
        
        # Check Muze CDN is loaded
        assert "muze.js" in html
        
        # Check chart code is embedded
        assert "Category" in html
        assert "Sales" in html
    
    def test_create_minimal_html(self, sample_muze_code):
        """Test creating minimal HTML."""
        html = create_minimal_html(sample_muze_code)
        
        # Should be valid HTML
        assert "<!DOCTYPE html>" in html
        assert "#chart-container" in html
        
        # Should be smaller than full template
        full_html = create_html_page(sample_muze_code)
        assert len(html) < len(full_html)
    
    def test_html_has_chart_container(self, sample_muze_code):
        """Test that HTML has the chart container element."""
        html = create_html_page(sample_muze_code)
        
        assert 'id="chart-container"' in html
    
    def test_html_has_loading_indicator(self, sample_muze_code):
        """Test that HTML has a loading indicator."""
        html = create_html_page(sample_muze_code)
        
        assert "loading" in html.lower()
    
    def test_html_has_error_handling(self, sample_muze_code):
        """Test that HTML has error handling."""
        html = create_html_page(sample_muze_code)
        
        assert "error" in html.lower()
        assert "catch" in html  # JavaScript try/catch


# -----------------------------------------------------------------------------
# TESTS FOR CONFIGURATION
# -----------------------------------------------------------------------------

class TestEmbedConfig:
    """Tests for embedding configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = EmbedConfig()
        
        assert config.width == "100%"
        assert config.height == "500px"
        assert config.theme == "light"
        assert "muze.js" in config.muze_cdn_url
    
    def test_custom_height(self, sample_muze_code):
        """Test custom height configuration."""
        config = EmbedConfig(height="800px")
        html = create_html_page(sample_muze_code, config=config)
        
        assert "800px" in html
    
    def test_custom_theme(self, sample_muze_code):
        """Test dark theme configuration."""
        config = EmbedConfig(theme="dark")
        html = create_html_page(sample_muze_code, config=config)
        
        assert "theme-dark" in html
    
    def test_custom_background(self, sample_muze_code):
        """Test custom background color."""
        config = EmbedConfig(background_color="#f0f0f0")
        html = create_html_page(sample_muze_code, config=config)
        
        assert "#f0f0f0" in html


# -----------------------------------------------------------------------------
# TESTS FOR MULTI-CHART PAGES
# -----------------------------------------------------------------------------

class TestMultiChartPage:
    """Tests for multi-chart dashboard pages."""
    
    def test_create_multi_chart_page(self, sample_muze_code):
        """Test creating a page with multiple charts."""
        charts = [
            {"code": sample_muze_code, "title": "Chart 1"},
            {"code": sample_muze_code, "title": "Chart 2"}
        ]
        
        html = create_multi_chart_page(charts, page_title="Dashboard")
        
        # Check page title
        assert "Dashboard" in html
        
        # Check both chart titles
        assert "Chart 1" in html
        assert "Chart 2" in html
        
        # Check multiple containers
        assert "chart-container-0" in html
        assert "chart-container-1" in html
    
    def test_multi_chart_with_widths(self, sample_muze_code):
        """Test multi-chart page with custom widths."""
        charts = [
            {"code": sample_muze_code, "title": "Left", "width": "50%"},
            {"code": sample_muze_code, "title": "Right", "width": "50%"}
        ]
        
        html = create_multi_chart_page(charts)
        
        assert "50%" in html


# -----------------------------------------------------------------------------
# TESTS FOR FILE SAVING
# -----------------------------------------------------------------------------

class TestFileSaving:
    """Tests for saving HTML to files."""
    
    def test_save_html_file(self, sample_muze_code):
        """Test saving HTML to a file."""
        html = create_html_page(sample_muze_code, title="Test")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test_chart.html"
            
            result_path = save_html_file(html, str(file_path))
            
            # File should exist
            assert file_path.exists()
            
            # Content should match
            saved_content = file_path.read_text(encoding='utf-8')
            assert saved_content == html
            
            # Return path should be absolute
            assert Path(result_path).is_absolute()


# -----------------------------------------------------------------------------
# TESTS FOR STREAMLIT INTEGRATION
# -----------------------------------------------------------------------------

class TestStreamlitIntegration:
    """Tests for Streamlit-specific functionality."""
    
    def test_get_streamlit_component_html(self, sample_muze_code):
        """Test getting HTML for Streamlit components."""
        html = get_streamlit_component_html(sample_muze_code, height=500)
        
        # Should be valid HTML
        assert "<!DOCTYPE html>" in html
        assert "#chart-container" in html
    
    def test_streamlit_html_with_title(self, sample_muze_code):
        """Test Streamlit HTML with title uses full template."""
        html = get_streamlit_component_html(
            sample_muze_code, 
            height=500, 
            title="My Chart"
        )
        
        assert "My Chart" in html
    
    def test_streamlit_html_without_title(self, sample_muze_code):
        """Test Streamlit HTML without title uses minimal template."""
        html = get_streamlit_component_html(sample_muze_code, height=500)
        
        # Should still work but be more minimal
        assert "<!DOCTYPE html>" in html


# -----------------------------------------------------------------------------
# TESTS FOR CODE EMBEDDING
# -----------------------------------------------------------------------------

class TestCodeEmbedding:
    """Tests for JavaScript code embedding."""
    
    def test_code_is_embedded(self, sample_muze_code):
        """Test that the Muze code is properly embedded."""
        html = create_html_page(sample_muze_code)
        
        # Key parts of the code should be present
        assert "const { muze, DataModel } = viz;" in html
        assert "const schema = [" in html
        assert ".mount('#chart-container')" in html
    
    def test_special_characters_handled(self):
        """Test that special characters in code are handled."""
        code_with_special = '''const x = "test's value";
const y = '<div>HTML</div>';
muze().mount('#chart-container');'''
        
        # Should not raise an error
        html = create_html_page(code_with_special)
        
        assert "<!DOCTYPE html>" in html


# -----------------------------------------------------------------------------
# RUN TESTS
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
