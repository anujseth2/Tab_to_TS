"""
Abstract Visualization Model - Framework-Agnostic Schemas

=============================================================================
WHAT THIS MODULE DOES:
=============================================================================
This module defines the "universal language" for describing visualizations.
These are pure data structures with NO logic - they serve as the CONTRACT
between different visualization systems.

The flow is:
    Tableau → [translate] → ChartIntent → [generate] → Muze

By having this middle layer, we can:
• Add new input formats (PowerBI, Looker) without changing output generation
• Add new output formats (D3.js, ECharts) without changing input parsing

=============================================================================
KEY CONCEPTS:
=============================================================================
• ChartIntent    - Complete description of what visualization to create
• ChartType      - Type of chart (bar, line, scatter, etc.)
• Encoding       - How a field maps to a visual property (x, y, color, size)
• Field          - A data field (dimension or measure)
• AggregationType - How to aggregate measures (SUM, AVG, COUNT, etc.)

=============================================================================
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# -----------------------------------------------------------------------------
# ENUMS
# These define the allowed values for various properties
# -----------------------------------------------------------------------------

class ChartType(Enum):
    """
    Types of charts/visualizations we support.
    
    These are generic chart types that can be mapped from Tableau mark types
    and to various visualization libraries.
    """
    BAR = "bar"              # Vertical bars
    BAR_HORIZONTAL = "bar_horizontal"  # Horizontal bars
    LINE = "line"            # Line chart
    AREA = "area"            # Area chart
    SCATTER = "scatter"      # Scatter plot (circles)
    PIE = "pie"              # Pie chart
    DONUT = "donut"          # Donut chart
    HEATMAP = "heatmap"      # Heat map / matrix
    TREEMAP = "treemap"      # Treemap
    TEXT = "text"            # Text/table
    MAP = "map"              # Geographic map
    HISTOGRAM = "histogram"  # Histogram (binned data)
    BOX_PLOT = "box_plot"    # Box and whisker plot
    UNKNOWN = "unknown"      # Fallback for unsupported types


class AggregationType(Enum):
    """
    Types of aggregations for measure fields.
    
    These correspond to standard SQL/Tableau aggregations.
    """
    NONE = "none"            # No aggregation (used for dimensions)
    SUM = "sum"              # Sum of values
    AVG = "avg"              # Average/mean
    COUNT = "count"          # Count of records
    COUNTD = "countd"        # Count distinct
    MIN = "min"              # Minimum value
    MAX = "max"              # Maximum value
    MEDIAN = "median"        # Median value
    STDEV = "stdev"          # Standard deviation
    VAR = "var"              # Variance
    ATTR = "attr"            # Attribute (returns value if unique)
    
    @classmethod
    def from_tableau(cls, tableau_agg: Optional[str]) -> "AggregationType":
        """
        Convert a Tableau aggregation string to our enum.
        
        Args:
            tableau_agg: Tableau aggregation like "sum", "avg", "none"
            
        Returns:
            Corresponding AggregationType
        """
        if not tableau_agg:
            return cls.NONE
            
        mapping = {
            "sum": cls.SUM,
            "avg": cls.AVG,
            "count": cls.COUNT,
            "countd": cls.COUNTD,
            "min": cls.MIN,
            "max": cls.MAX,
            "median": cls.MEDIAN,
            "stdev": cls.STDEV,
            "var": cls.VAR,
            "attr": cls.ATTR,
            "none": cls.NONE,
        }
        return mapping.get(tableau_agg.lower(), cls.NONE)


class FieldRole(Enum):
    """
    The role of a field in visualization.
    
    In data visualization, there's a fundamental distinction:
    • Dimensions - categorical fields used for grouping (Region, Category)
    • Measures   - numeric fields that can be aggregated (Sales, Profit)
    """
    DIMENSION = "dimension"  # Categorical field for grouping
    MEASURE = "measure"      # Numeric field for aggregation


class EncodingChannel(Enum):
    """
    Visual channels that data can be encoded to.
    
    These are the "slots" where you can place fields in a visualization.
    """
    X = "x"                  # X-axis (horizontal position)
    Y = "y"                  # Y-axis (vertical position)
    COLOR = "color"          # Color/hue
    SIZE = "size"            # Size of marks
    SHAPE = "shape"          # Shape of marks
    LABEL = "label"          # Text labels
    DETAIL = "detail"        # Level of detail (creates more marks)
    TOOLTIP = "tooltip"      # Tooltip information
    ROW = "row"              # Row facet (small multiples)
    COLUMN = "column"        # Column facet (small multiples)


class SortOrder(Enum):
    """
    Sort order for fields.
    """
    ASCENDING = "ascending"
    DESCENDING = "descending"
    NONE = "none"


# -----------------------------------------------------------------------------
# DATA CLASSES
# These are the core structures that describe a visualization
# -----------------------------------------------------------------------------

@dataclass
class Field:
    """
    Represents a data field used in a visualization.
    
    A field can be either a dimension (categorical) or a measure (numeric).
    Measures typically have an aggregation applied.
    
    Attributes:
        name: The field name (e.g., "Sales", "Category")
        role: Whether this is a dimension or measure
        data_type: The data type (string, integer, real, date, datetime, boolean)
        aggregation: How to aggregate this field (for measures)
        source_name: Original name in the source system (if different from name)
        calculation: Formula if this is a calculated field
    """
    name: str
    role: FieldRole
    data_type: str = "string"
    aggregation: AggregationType = AggregationType.NONE
    source_name: Optional[str] = None
    calculation: Optional[str] = None
    
    @property
    def is_measure(self) -> bool:
        """Returns True if this field is a measure."""
        return self.role == FieldRole.MEASURE
    
    @property
    def is_dimension(self) -> bool:
        """Returns True if this field is a dimension."""
        return self.role == FieldRole.DIMENSION
    
    @property
    def display_name(self) -> str:
        """
        Returns a human-readable display name.
        
        For aggregated measures, includes the aggregation: "SUM(Sales)"
        """
        if self.is_measure and self.aggregation != AggregationType.NONE:
            return f"{self.aggregation.value.upper()}({self.name})"
        return self.name


@dataclass
class Encoding:
    """
    Represents how a field is mapped to a visual channel.
    
    For example:
    - Field "Category" → X-axis channel
    - Field "Sales" with SUM → Y-axis channel
    - Field "Region" → Color channel
    
    Attributes:
        channel: The visual channel (x, y, color, size, etc.)
        field: The data field being encoded
        sort: Optional sort order
    """
    channel: EncodingChannel
    field: Field
    sort: SortOrder = SortOrder.NONE


@dataclass
class Filter:
    """
    Represents a filter applied to the visualization.
    
    Attributes:
        field: The field being filtered
        filter_type: Type of filter (categorical, range, etc.)
        values: For categorical filters, the selected values
        min_value: For range filters, the minimum value
        max_value: For range filters, the maximum value
        include: If True, include these values; if False, exclude them
    """
    field: Field
    filter_type: str = "categorical"  # "categorical", "range", "top_n"
    values: Optional[List[Any]] = None
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    include: bool = True


@dataclass
class ChartIntent:
    """
    Complete description of a visualization intent.
    
    This is the main schema that captures everything needed to recreate
    a visualization in any target library (Muze, D3, ECharts, etc.).
    
    Attributes:
        name: Name of the visualization
        chart_type: Type of chart (bar, line, scatter, etc.)
        encodings: List of field → channel mappings
        filters: List of filters applied
        title: Optional title for the chart
        subtitle: Optional subtitle
        data_source: Name of the data source
        orientation: For bar charts, 'horizontal' or 'vertical'
        stacked: Whether bars/areas should be stacked
        normalized: Whether to show as percentages (normalized to 100%)
        show_labels: Whether to show data labels on marks
        metadata: Any additional metadata as key-value pairs
    """
    name: str
    chart_type: ChartType
    encodings: List[Encoding] = field(default_factory=list)
    filters: List[Filter] = field(default_factory=list)
    title: Optional[str] = None
    subtitle: Optional[str] = None
    data_source: Optional[str] = None
    orientation: str = "vertical"  # "vertical" or "horizontal"
    stacked: bool = False
    normalized: bool = False
    show_labels: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------
    
    def get_encoding(self, channel: EncodingChannel) -> Optional[Encoding]:
        """
        Get the encoding for a specific channel.
        
        Args:
            channel: The channel to look for (X, Y, COLOR, etc.)
            
        Returns:
            The Encoding if found, None otherwise
        """
        for enc in self.encodings:
            if enc.channel == channel:
                return enc
        return None
    
    def get_encodings_by_channel(self, channel: EncodingChannel) -> List[Encoding]:
        """
        Get all encodings for a specific channel.
        
        Some channels (like DETAIL) can have multiple fields.
        
        Args:
            channel: The channel to look for
            
        Returns:
            List of Encodings for that channel (may be empty)
        """
        return [enc for enc in self.encodings if enc.channel == channel]
    
    @property
    def x_field(self) -> Optional[Field]:
        """Convenience property to get the X-axis field."""
        enc = self.get_encoding(EncodingChannel.X)
        return enc.field if enc else None
    
    @property
    def y_field(self) -> Optional[Field]:
        """Convenience property to get the Y-axis field."""
        enc = self.get_encoding(EncodingChannel.Y)
        return enc.field if enc else None
    
    @property
    def color_field(self) -> Optional[Field]:
        """Convenience property to get the color field."""
        enc = self.get_encoding(EncodingChannel.COLOR)
        return enc.field if enc else None
    
    @property
    def dimensions(self) -> List[Field]:
        """Get all dimension fields used in encodings."""
        # Use a dict to deduplicate by field name while preserving order
        seen = {}
        for enc in self.encodings:
            if enc.field.is_dimension and enc.field.name not in seen:
                seen[enc.field.name] = enc.field
        return list(seen.values())
    
    @property
    def measures(self) -> List[Field]:
        """Get all measure fields used in encodings."""
        # Use a dict to deduplicate by field name while preserving order
        seen = {}
        for enc in self.encodings:
            if enc.field.is_measure and enc.field.name not in seen:
                seen[enc.field.name] = enc.field
        return list(seen.values())


# -----------------------------------------------------------------------------
# FACTORY FUNCTIONS
# Convenient ways to create common field types
# -----------------------------------------------------------------------------

def dimension(name: str, data_type: str = "string") -> Field:
    """
    Create a dimension field.
    
    Example:
        category = dimension("Category")
        order_date = dimension("Order Date", data_type="date")
    """
    return Field(
        name=name,
        role=FieldRole.DIMENSION,
        data_type=data_type,
        aggregation=AggregationType.NONE
    )


def measure(name: str, aggregation: AggregationType = AggregationType.SUM, 
            data_type: str = "real") -> Field:
    """
    Create a measure field with aggregation.
    
    Example:
        sales = measure("Sales")  # SUM(Sales) by default
        avg_profit = measure("Profit", AggregationType.AVG)
    """
    return Field(
        name=name,
        role=FieldRole.MEASURE,
        data_type=data_type,
        aggregation=aggregation
    )


# -----------------------------------------------------------------------------
# SUMMARY FUNCTION
# -----------------------------------------------------------------------------

def get_chart_intent_summary(intent: ChartIntent) -> str:
    """
    Generate a human-readable summary of a ChartIntent.
    
    Useful for debugging and understanding what a visualization describes.
    """
    lines = [
        f"Chart: {intent.name}",
        f"  Type: {intent.chart_type.value}",
        f"  Orientation: {intent.orientation}",
    ]
    
    if intent.title:
        lines.append(f"  Title: {intent.title}")
    
    lines.append(f"  Encodings:")
    for enc in intent.encodings:
        lines.append(f"    {enc.channel.value}: {enc.field.display_name}")
    
    if intent.filters:
        lines.append(f"  Filters: {len(intent.filters)}")
        for f in intent.filters:
            lines.append(f"    {f.field.name}: {f.filter_type}")
    
    if intent.stacked:
        lines.append(f"  Stacked: Yes")
    
    return '\n'.join(lines)


# -----------------------------------------------------------------------------
# MODULE TEST
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("Abstract Viz Model - Schemas")
    print("=" * 50)
    print("\nThis module defines framework-agnostic visualization schemas:")
    print("  • ChartIntent - Complete visualization description")
    print("  • ChartType   - Types of charts (bar, line, etc.)")
    print("  • Encoding    - Field → Visual channel mapping")
    print("  • Field       - Dimension or measure field")
    print("\nExample usage:")
    print("  category = dimension('Category')")
    print("  sales = measure('Sales', AggregationType.SUM)")
    print("  intent = ChartIntent(")
    print("      name='Sales by Category',")
    print("      chart_type=ChartType.BAR,")
    print("      encodings=[")
    print("          Encoding(EncodingChannel.X, category),")
    print("          Encoding(EncodingChannel.Y, sales)")
    print("      ]")
    print("  )")
