"""
Muze HTML Embedding

=============================================================================
WHAT THIS MODULE DOES:
=============================================================================
This module creates complete HTML pages that embed Muze visualizations.

It takes generated Muze JavaScript code and wraps it in an HTML template
that includes:
- Muze library loaded from CDN
- Proper container elements
- Styling for the visualization
- Error handling

The output is a standalone HTML file that can be:
- Displayed in Streamlit using st.components.v1.html()
- Saved as a file and opened in a browser
- Embedded in other web pages

=============================================================================
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass


# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------

@dataclass
class EmbedConfig:
    """
    Configuration for HTML embedding.
    
    Attributes:
        width: Width of the chart container (CSS value)
        height: Height of the chart container (CSS value)
        muze_cdn_url: URL to load Muze library from
        theme: Color theme ('light' or 'dark')
        background_color: Background color of the page
        font_family: Font family for text
        show_error_details: If True, show detailed error messages
    """
    width: str = "100%"
    height: str = "500px"
    muze_cdn_url: str = "https://cdn.jsdelivr.net/npm/@chartshq/muze@2.0.0/dist/muze.js"
    muze_css_url: str = "https://cdn.jsdelivr.net/npm/@chartshq/muze@2.0.0/dist/muze.css"
    theme: str = "light"
    background_color: str = "#ffffff"
    font_family: str = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
    show_error_details: bool = True


# -----------------------------------------------------------------------------
# HTML TEMPLATES
# -----------------------------------------------------------------------------

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: {font_family};
            background-color: {background_color};
            padding: 20px;
        }}
        
        .chart-wrapper {{
            width: {width};
            margin: 0 auto;
        }}
        
        .chart-title {{
            font-size: 1.5rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 16px;
            text-align: center;
        }}
        
        #chart-container {{
            width: 100%;
            height: {height};
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
            background: #fafafa;
        }}
        
        .loading {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #666;
            font-size: 1rem;
        }}
        
        .error {{
            display: none;
            padding: 20px;
            background: #fee;
            border: 1px solid #fcc;
            border-radius: 8px;
            color: #c00;
            margin-top: 10px;
        }}
        
        .error.visible {{
            display: block;
        }}
        
        .error-title {{
            font-weight: 600;
            margin-bottom: 8px;
        }}
        
        .error-details {{
            font-family: monospace;
            font-size: 0.85rem;
            white-space: pre-wrap;
            background: #fff;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
        }}
        
        /* Dark theme */
        .theme-dark {{
            background-color: #1a1a2e;
        }}
        
        .theme-dark .chart-title {{
            color: #eee;
        }}
        
        .theme-dark #chart-container {{
            background: #16213e;
            border-color: #0f3460;
        }}
        
        .theme-dark .loading {{
            color: #aaa;
        }}
    </style>
</head>
<body class="{theme_class}">
    <div class="chart-wrapper">
        {title_html}
        <div id="chart-container">
            <div class="loading" id="loading">Loading visualization...</div>
        </div>
        <div class="error" id="error">
            <div class="error-title">Error rendering chart</div>
            <div class="error-details" id="error-details"></div>
        </div>
    </div>

    <!-- Load Muze library -->
    <link href="{muze_css_url}" rel="stylesheet">
    <script src="{muze_cdn_url}"></script>
    
    <script>
        // Wait for Muze to load and run the chart
        (async function() {{
            const maxWait = 15000; // 15 seconds
            const startTime = Date.now();
            
            function showError(error) {{
                document.getElementById('loading').style.display = 'none';
                const errorDiv = document.getElementById('error');
                const errorDetails = document.getElementById('error-details');
                errorDiv.classList.add('visible');
                errorDetails.textContent = {show_error_details} ? 
                    error.message + '\\n\\n' + (error.stack || '') : 
                    'An error occurred while rendering the chart.';
                console.error('Muze Error:', error);
            }}
            
            // Wait for muze to be defined
            while (typeof muze === 'undefined') {{
                if (Date.now() - startTime > maxWait) {{
                    showError(new Error('Timeout: Muze library failed to load'));
                    return;
                }}
                await new Promise(r => setTimeout(r, 100));
            }}
            
            try {{
                // Muze 2.0 uses WebAssembly and async initialization
                const viz = await muze();
                const DataModel = await muze.DataModel.onReady();
                
                // Hide loading message
                document.getElementById('loading').style.display = 'none';
                
                // Create a wrapper that provides viz object for the chart code
                const runChart = async (muze, DataModel) => {{
                    {chart_code}
                }};
                
                await runChart(viz, DataModel);
            }} catch (error) {{
                showError(error);
            }}
        }})();
    </script>
</body>
</html>
'''


MINIMAL_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ margin: 0; padding: 0; }}
        #chart-container {{ width: 100%; height: {height}; }}
    </style>
</head>
<body>
    <div id="chart-container"></div>
    <script src="{muze_cdn_url}"></script>
    <script>
        (function checkMuze() {{
            if (typeof viz !== 'undefined') {{
                try {{ {chart_code} }} catch(e) {{ console.error(e); }}
            }} else {{ setTimeout(checkMuze, 100); }}
        }})();
    </script>
</body>
</html>
'''


# -----------------------------------------------------------------------------
# MAIN FUNCTIONS
# -----------------------------------------------------------------------------

def create_html_page(
    muze_code: str,
    title: Optional[str] = None,
    config: Optional[EmbedConfig] = None
) -> str:
    """
    Create a complete HTML page with embedded Muze visualization.
    
    This creates a full HTML document with proper styling, the Muze library,
    and the generated chart code.
    
    Args:
        muze_code: The generated Muze JavaScript code
        title: Optional title to display above the chart
        config: Embedding configuration
        
    Returns:
        Complete HTML document as a string
        
    Example:
        code = generate_muze_code(intent)
        html = create_html_page(code, title="Sales Dashboard")
        
        # Save to file
        with open("chart.html", "w") as f:
            f.write(html)
        
        # Or display in Streamlit
        import streamlit as st
        st.components.v1.html(html, height=600)
    """
    config = config or EmbedConfig()
    
    # Build theme class
    theme_class = f"theme-{config.theme}" if config.theme != "light" else ""
    
    # Build title HTML
    title_html = f'<div class="chart-title">{title}</div>' if title else ""
    
    # Build the HTML
    html = HTML_TEMPLATE.format(
        title=title or "Muze Visualization",
        font_family=config.font_family,
        background_color=config.background_color,
        width=config.width,
        height=config.height,
        theme_class=theme_class,
        title_html=title_html,
        muze_cdn_url=config.muze_cdn_url,
        muze_css_url=config.muze_css_url,
        chart_code=muze_code,
        show_error_details="true" if config.show_error_details else "false"
    )
    
    return html


def create_minimal_html(
    muze_code: str,
    height: str = "500px",
    muze_cdn_url: str = "https://cdn.jsdelivr.net/npm/@viz/muze@latest/dist/muze.js"
) -> str:
    """
    Create a minimal HTML page for embedding in iframes or Streamlit.
    
    This creates a stripped-down HTML document without extra styling,
    ideal for embedding inside other pages.
    
    Args:
        muze_code: The generated Muze JavaScript code
        height: Height of the chart
        muze_cdn_url: URL to Muze CDN
        
    Returns:
        Minimal HTML document as a string
    """
    return MINIMAL_TEMPLATE.format(
        height=height,
        muze_cdn_url=muze_cdn_url,
        chart_code=muze_code
    )


def create_multi_chart_page(
    charts: List[Dict[str, Any]],
    page_title: str = "Dashboard",
    config: Optional[EmbedConfig] = None
) -> str:
    """
    Create an HTML page with multiple charts.
    
    Args:
        charts: List of dicts with 'code', 'title', and optional 'width' keys
        page_title: Title of the page
        config: Embedding configuration
        
    Returns:
        Complete HTML document with multiple charts
        
    Example:
        charts = [
            {"code": code1, "title": "Sales", "width": "50%"},
            {"code": code2, "title": "Profit", "width": "50%"}
        ]
        html = create_multi_chart_page(charts, "My Dashboard")
    """
    config = config or EmbedConfig()
    
    # Build individual chart divs and scripts
    chart_divs = []
    chart_scripts = []
    
    for i, chart in enumerate(charts):
        container_id = f"chart-container-{i}"
        width = chart.get("width", "100%")
        title = chart.get("title", f"Chart {i+1}")
        code = chart.get("code", "")
        
        # Replace the default container ID with our unique one
        modified_code = code.replace("#chart-container", f"#{container_id}")
        modified_code = modified_code.replace("'#chart-container'", f"'#{container_id}'")
        
        chart_divs.append(f'''
        <div class="chart-cell" style="width: {width};">
            <div class="chart-title">{title}</div>
            <div id="{container_id}" style="height: {config.height};"></div>
        </div>
        ''')
        
        chart_scripts.append(f'''
        try {{
            {modified_code}
        }} catch(e) {{
            document.getElementById('{container_id}').innerHTML = 
                '<div style="color: red; padding: 20px;">Error: ' + e.message + '</div>';
        }}
        ''')
    
    # Build the complete HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{page_title}</title>
    <style>
        body {{
            font-family: {config.font_family};
            background-color: {config.background_color};
            padding: 20px;
            margin: 0;
        }}
        
        .page-title {{
            font-size: 2rem;
            font-weight: 600;
            color: #333;
            text-align: center;
            margin-bottom: 24px;
        }}
        
        .charts-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
        }}
        
        .chart-cell {{
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 16px;
            box-sizing: border-box;
        }}
        
        .chart-title {{
            font-size: 1.2rem;
            font-weight: 500;
            color: #333;
            margin-bottom: 12px;
        }}
    </style>
</head>
<body>
    <div class="page-title">{page_title}</div>
    <div class="charts-grid">
        {''.join(chart_divs)}
    </div>
    
    <script src="{config.muze_cdn_url}"></script>
    <script>
        (function checkMuze() {{
            if (typeof viz !== 'undefined' && viz.muze && viz.DataModel) {{
                {''.join(chart_scripts)}
            }} else {{
                setTimeout(checkMuze, 100);
            }}
        }})();
    </script>
</body>
</html>
'''
    
    return html


def save_html_file(html: str, file_path: str) -> str:
    """
    Save HTML content to a file.
    
    Args:
        html: HTML content to save
        file_path: Path to save the file
        
    Returns:
        The absolute path of the saved file
    """
    from pathlib import Path
    
    path = Path(file_path)
    path.write_text(html, encoding='utf-8')
    
    return str(path.absolute())


# -----------------------------------------------------------------------------
# STREAMLIT INTEGRATION
# -----------------------------------------------------------------------------

def get_streamlit_component_html(
    muze_code: str,
    height: int = 500,
    title: Optional[str] = None
) -> str:
    """
    Get HTML suitable for st.components.v1.html().
    
    This returns HTML optimized for Streamlit embedding, using the minimal
    template for better performance.
    
    Args:
        muze_code: The generated Muze JavaScript code
        height: Height in pixels (for Streamlit's height parameter)
        title: Optional title to display
        
    Returns:
        HTML string for Streamlit
        
    Example:
        import streamlit as st
        import streamlit.components.v1 as components
        
        html = get_streamlit_component_html(code, height=500)
        components.html(html, height=520)  # Add 20px for padding
    """
    if title:
        # Use full template with title
        config = EmbedConfig(height=f"{height}px")
        return create_html_page(muze_code, title=title, config=config)
    else:
        # Use minimal template for better performance
        return create_minimal_html(muze_code, height=f"{height}px")


# -----------------------------------------------------------------------------
# MODULE TEST
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("Muze HTML Embedding Module")
    print("=" * 50)
    print("\nThis module creates HTML pages with embedded Muze charts:")
    print("  • create_html_page(code) - Full HTML with styling")
    print("  • create_minimal_html(code) - Minimal HTML for embedding")
    print("  • create_multi_chart_page(charts) - Dashboard with multiple charts")
    print("  • get_streamlit_component_html(code) - Optimized for Streamlit")
    print("  • save_html_file(html, path) - Save to file")
