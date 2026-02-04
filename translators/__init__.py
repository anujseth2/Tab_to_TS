"""
Translators Package - Conversion Logic

=============================================================================
WHAT THIS PACKAGE DOES:
=============================================================================
This package contains the "brains" that convert between different formats:

1. tableau_to_generic.py - Converts Tableau-specific concepts to our universal
                           visualization model (ChartIntent)
                           
                           Example mappings:
                           • Rows shelf → Y-axis encoding
                           • Columns shelf → X-axis encoding  
                           • Mark type "bar" → Chart type "bar"
                           • SUM(Sales) → MeasureField with SUM aggregation

2. generic_to_muze.py    - Takes the universal ChartIntent and generates
                           Muze code as separate HTML, CSS, and JavaScript
                           blocks for ThoughtSpot Muze Studio ingestion.

=============================================================================
OUTPUT FORMAT:
=============================================================================
The generator produces MuzeCodeOutput with:
• html       - The container HTML structure
• css        - CSS styling for the chart
• javascript - Muze visualization code
• sample_data - Generated sample data for preview
• schema     - Data schema definition

=============================================================================
"""

# Import and expose the Tableau to Generic translator
from .tableau_to_generic import (
    translate_worksheet,
    translate_workbook,
    translate_tableau_file
)

# Import and expose the Generic to Muze generator
from .generic_to_muze import (
    # Main generation function
    generate_muze_code,
    generate_muze_code_batch,
    
    # Output structure
    MuzeCodeOutput,
    
    # Sample data generation
    generate_sample_data,
    
    # LLM configuration
    LLMConfig,
    MUZE_DOCUMENTATION,
    
    # Cache management
    get_cache,
    clear_cache,
    get_cache_stats,
    MuzeCodeCache,
    CacheEntry,
    
    # Legacy compatibility
    generate_muze_code_string
)
