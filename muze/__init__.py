"""
Muze Package - HTML Embedding and Rendering

=============================================================================
WHAT THIS PACKAGE DOES:
=============================================================================
This package handles the final step: taking generated Muze JavaScript code
and embedding it into an HTML page that can be displayed.

1. html_embed.py - Creates a complete HTML page with:
                   • Muze library loaded from CDN
                   • The generated JavaScript code
                   • Proper styling and container elements
                   • Any required data embedded as JSON

=============================================================================
WHAT IS MUZE?
=============================================================================
Muze is a JavaScript library for creating data visualizations.
It's similar to D3.js but with a more declarative, grammar-based approach.

Example Muze code:
    muze()
        .data(data)
        .rows(['Sales'])
        .columns(['Category'])
        .mount('#chart-container');

=============================================================================
LAYER 6 (Part 1) of our architecture
=============================================================================
"""

# Import and expose the HTML embedding functions
from .html_embed import (
    create_html_page,
    create_minimal_html,
    create_multi_chart_page,
    save_html_file,
    get_streamlit_component_html,
    EmbedConfig
)
