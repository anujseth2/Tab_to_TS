"""
Viz Model Package - Abstract Visualization Model

=============================================================================
WHAT THIS PACKAGE DOES:
=============================================================================
This package defines the "universal language" for describing charts.

Think of it like a translation dictionary:
- Tableau calls it "Rows shelf" → We call it "Y-axis encoding"
- Tableau calls it "Columns shelf" → We call it "X-axis encoding"
- Tableau calls it "Color shelf" → We call it "Color encoding"

This package contains ONLY data structures (schemas), NO logic.
It's the CONTRACT between Tableau world and Muze world.

=============================================================================
KEY CONCEPTS:
=============================================================================
• ChartIntent    - What the user wants to visualize (chart type, data, encodings)
• MeasureField   - A numeric field that can be aggregated (SUM, AVG, COUNT, etc.)
• DimensionField - A categorical field used for grouping (Region, Category, etc.)
• Encoding       - How a field maps to a visual property (x-axis, color, size, etc.)

=============================================================================
LAYER 3 of our architecture
=============================================================================
"""

# Import and expose the schema classes
from .schemas import (
    # Enums
    ChartType,
    AggregationType,
    FieldRole,
    EncodingChannel,
    SortOrder,
    # Data classes
    Field,
    Encoding,
    Filter,
    ChartIntent,
    # Factory functions
    dimension,
    measure,
    # Utilities
    get_chart_intent_summary
)
