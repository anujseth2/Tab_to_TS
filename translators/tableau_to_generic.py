"""
Tableau to Generic Translator

=============================================================================
WHAT THIS MODULE DOES:
=============================================================================
This module translates Tableau-specific concepts into our generic
visualization model (ChartIntent).

The translation involves:
1. Mark Type → ChartType (Bar → BAR, Line → LINE, etc.)
2. Rows/Columns shelves → X/Y encodings (with orientation detection)
3. Color/Size/Detail shelves → corresponding encodings
4. Aggregation parsing (sum:Sales:qk → SUM)

=============================================================================
KEY INSIGHT: ORIENTATION DETECTION
=============================================================================
In Tableau:
- Rows shelf = vertical axis (Y)
- Columns shelf = horizontal axis (X)

But for bar charts, the orientation depends on where the measure is:
- Measure on Columns + Dimension on Rows = Horizontal bars
- Measure on Rows + Dimension on Columns = Vertical bars (default)

We detect this automatically and set the orientation accordingly.

=============================================================================
"""

from typing import List, Optional, Dict
from dataclasses import dataclass

# Import Tableau models
from twbx.xml_parser import (
    ParsedWorkbook,
    TableauWorksheet,
    TableauDatasource,
    TableauColumn,
    ShelfField
)

# Import generic visualization model
from viz_model import (
    ChartType,
    AggregationType,
    FieldRole,
    EncodingChannel,
    Field,
    Encoding,
    Filter,
    ChartIntent,
    dimension,
    measure
)


# -----------------------------------------------------------------------------
# MARK TYPE MAPPING
# Maps Tableau mark types to our generic ChartType
# -----------------------------------------------------------------------------

MARK_TYPE_MAPPING: Dict[str, ChartType] = {
    # Standard marks
    "bar": ChartType.BAR,
    "line": ChartType.LINE,
    "area": ChartType.AREA,
    "circle": ChartType.SCATTER,
    "square": ChartType.SCATTER,
    "shape": ChartType.SCATTER,
    "text": ChartType.TEXT,
    "pie": ChartType.PIE,
    "polygon": ChartType.MAP,
    "map": ChartType.MAP,
    "ganttbar": ChartType.BAR,
    
    # Automatic mark (Tableau decides based on data)
    "automatic": ChartType.BAR,  # Default to bar
    
    # Fallback
    None: ChartType.UNKNOWN,
}


def _map_mark_type(tableau_mark: Optional[str]) -> ChartType:
    """
    Convert Tableau mark type to generic ChartType.
    
    Args:
        tableau_mark: Tableau mark type string (e.g., "Bar", "Line")
        
    Returns:
        Corresponding ChartType enum value
    """
    if tableau_mark is None:
        return ChartType.UNKNOWN
    
    # Normalize to lowercase
    mark_lower = tableau_mark.lower()
    
    return MARK_TYPE_MAPPING.get(mark_lower, ChartType.UNKNOWN)


# -----------------------------------------------------------------------------
# FIELD CONVERSION
# Convert Tableau ShelfField to generic Field
# -----------------------------------------------------------------------------

def _convert_shelf_field_to_field(
    shelf_field: ShelfField,
    datasources: Dict[str, TableauDatasource]
) -> Field:
    """
    Convert a Tableau ShelfField to a generic Field.
    
    This looks up the field in the datasource to get additional metadata
    like data type and whether it's a calculated field.
    
    Args:
        shelf_field: The Tableau shelf field
        datasources: Dictionary of datasources from the workbook
        
    Returns:
        A generic Field object
    """
    # Determine role based on aggregation
    # If there's an aggregation (other than 'none'), it's likely a measure
    has_aggregation = (
        shelf_field.aggregation is not None and 
        shelf_field.aggregation.lower() != "none"
    )
    
    # Also check field type indicator (qk = quantitative, nk = nominal)
    is_quantitative = shelf_field.field_type == "qk" if shelf_field.field_type else False
    
    # Determine role
    if has_aggregation or is_quantitative:
        role = FieldRole.MEASURE
    else:
        role = FieldRole.DIMENSION
    
    # Parse aggregation type
    agg_type = AggregationType.from_tableau(shelf_field.aggregation)
    
    # Try to look up the field in the datasource for more info
    data_type = "string"
    calculation = None
    
    ds = datasources.get(shelf_field.datasource)
    if ds:
        # Try different name formats
        possible_names = [
            f"[{shelf_field.field_name}]",
            shelf_field.field_name,
        ]
        
        for name in possible_names:
            if name in ds.columns:
                col = ds.columns[name]
                data_type = col.datatype
                calculation = col.calculation
                # Use the column's role if available
                if col.role == "measure":
                    role = FieldRole.MEASURE
                elif col.role == "dimension":
                    role = FieldRole.DIMENSION
                break
    
    return Field(
        name=shelf_field.field_name,
        role=role,
        data_type=data_type,
        aggregation=agg_type if role == FieldRole.MEASURE else AggregationType.NONE,
        source_name=shelf_field.raw,
        calculation=calculation
    )


def _convert_shelf_to_encodings(
    shelf_fields: List[ShelfField],
    channel: EncodingChannel,
    datasources: Dict[str, TableauDatasource]
) -> List[Encoding]:
    """
    Convert a list of shelf fields to encodings for a specific channel.
    
    Args:
        shelf_fields: List of Tableau shelf fields
        channel: The encoding channel to assign
        datasources: Dictionary of datasources
        
    Returns:
        List of Encoding objects
    """
    encodings = []
    
    for shelf_field in shelf_fields:
        field = _convert_shelf_field_to_field(shelf_field, datasources)
        encoding = Encoding(channel=channel, field=field)
        encodings.append(encoding)
    
    return encodings


# -----------------------------------------------------------------------------
# ORIENTATION DETECTION
# Determine if a bar chart should be horizontal or vertical
# -----------------------------------------------------------------------------

def _detect_orientation(
    rows_fields: List[ShelfField],
    cols_fields: List[ShelfField],
    chart_type: ChartType,
    datasources: Dict[str, TableauDatasource]
) -> str:
    """
    Detect the orientation of a chart based on field placement.
    
    For bar charts:
    - If measure is on Columns (X-axis), bars are horizontal
    - If measure is on Rows (Y-axis), bars are vertical
    
    Args:
        rows_fields: Fields on the Rows shelf
        cols_fields: Fields on the Columns shelf
        chart_type: The type of chart
        datasources: Dictionary of datasources
        
    Returns:
        "horizontal" or "vertical"
    """
    # Only relevant for bar charts
    if chart_type not in [ChartType.BAR, ChartType.BAR_HORIZONTAL]:
        return "vertical"
    
    # Check if columns has measures (would make horizontal bars)
    cols_has_measure = False
    for sf in cols_fields:
        field = _convert_shelf_field_to_field(sf, datasources)
        if field.is_measure:
            cols_has_measure = True
            break
    
    # Check if rows has measures
    rows_has_measure = False
    for sf in rows_fields:
        field = _convert_shelf_field_to_field(sf, datasources)
        if field.is_measure:
            rows_has_measure = True
            break
    
    # If measure is on columns and dimension on rows → horizontal
    if cols_has_measure and not rows_has_measure:
        return "horizontal"
    
    # Default to vertical
    return "vertical"


# -----------------------------------------------------------------------------
# MAIN TRANSLATION FUNCTION
# -----------------------------------------------------------------------------

def translate_worksheet(
    worksheet: TableauWorksheet,
    datasources: Dict[str, TableauDatasource]
) -> ChartIntent:
    """
    Translate a single Tableau worksheet to a ChartIntent.
    
    This is the main function for converting a Tableau visualization
    to our generic format.
    
    Args:
        worksheet: The parsed Tableau worksheet
        datasources: Dictionary of datasources from the workbook
        
    Returns:
        A ChartIntent representing the visualization
        
    Example:
        from twbx import get_workbook_xml, parse_workbook
        from translators import translate_worksheet
        
        xml = get_workbook_xml("dashboard.twbx")
        workbook = parse_workbook(xml)
        
        for ws in workbook.worksheets:
            intent = translate_worksheet(ws, workbook.datasources)
            print(f"{ws.name}: {intent.chart_type.value}")
    """
    # Map the mark type
    chart_type = _map_mark_type(worksheet.mark_type)
    
    # Detect orientation
    orientation = _detect_orientation(
        worksheet.rows,
        worksheet.columns,
        chart_type,
        datasources
    )
    
    # Update chart type for horizontal bars
    if chart_type == ChartType.BAR and orientation == "horizontal":
        chart_type = ChartType.BAR_HORIZONTAL
    
    # Build encodings list
    encodings: List[Encoding] = []
    
    # In Tableau:
    # - Columns shelf → X-axis (horizontal)
    # - Rows shelf → Y-axis (vertical)
    # But for horizontal bar charts, we might want to swap this conceptually
    
    # Convert columns to X encodings
    x_encodings = _convert_shelf_to_encodings(
        worksheet.columns,
        EncodingChannel.X,
        datasources
    )
    encodings.extend(x_encodings)
    
    # Convert rows to Y encodings
    y_encodings = _convert_shelf_to_encodings(
        worksheet.rows,
        EncodingChannel.Y,
        datasources
    )
    encodings.extend(y_encodings)
    
    # Convert color shelf
    color_encodings = _convert_shelf_to_encodings(
        worksheet.color,
        EncodingChannel.COLOR,
        datasources
    )
    encodings.extend(color_encodings)
    
    # Convert size shelf
    size_encodings = _convert_shelf_to_encodings(
        worksheet.size,
        EncodingChannel.SIZE,
        datasources
    )
    encodings.extend(size_encodings)
    
    # Convert label shelf
    label_encodings = _convert_shelf_to_encodings(
        worksheet.label,
        EncodingChannel.LABEL,
        datasources
    )
    encodings.extend(label_encodings)
    
    # Convert detail shelf
    detail_encodings = _convert_shelf_to_encodings(
        worksheet.detail,
        EncodingChannel.DETAIL,
        datasources
    )
    encodings.extend(detail_encodings)
    
    # Convert filters
    filters: List[Filter] = []
    for shelf_field in worksheet.filters:
        field = _convert_shelf_field_to_field(shelf_field, datasources)
        filter_obj = Filter(field=field, filter_type="categorical")
        filters.append(filter_obj)
    
    # Determine primary datasource
    data_source = None
    if worksheet.datasource_dependencies:
        data_source = worksheet.datasource_dependencies[0]
    elif encodings:
        # Use datasource from first encoding
        first_field = encodings[0].field
        if first_field.source_name:
            # Extract datasource from source_name like "[DS].[field]"
            import re
            match = re.match(r'\[([^\]]+)\]', first_field.source_name)
            if match:
                data_source = match.group(1)
    
    # Create the ChartIntent
    return ChartIntent(
        name=worksheet.name,
        chart_type=chart_type,
        encodings=encodings,
        filters=filters,
        title=worksheet.name,  # Use worksheet name as default title
        data_source=data_source,
        orientation=orientation,
        stacked=False,  # Would need more analysis to detect stacking
        normalized=False,
        show_labels=len(label_encodings) > 0
    )


def translate_workbook(workbook: ParsedWorkbook) -> List[ChartIntent]:
    """
    Translate all worksheets in a Tableau workbook to ChartIntents.
    
    Args:
        workbook: The parsed Tableau workbook
        
    Returns:
        List of ChartIntent objects, one per worksheet
        
    Example:
        from twbx import get_workbook_xml, parse_workbook
        from translators import translate_workbook
        
        xml = get_workbook_xml("dashboard.twbx")
        workbook = parse_workbook(xml)
        intents = translate_workbook(workbook)
        
        for intent in intents:
            print(f"{intent.name}: {intent.chart_type.value}")
    """
    intents = []
    
    for worksheet in workbook.worksheets:
        intent = translate_worksheet(worksheet, workbook.datasources)
        intents.append(intent)
    
    return intents


# -----------------------------------------------------------------------------
# CONVENIENCE FUNCTION
# One-step translation from file to ChartIntents
# -----------------------------------------------------------------------------

def translate_tableau_file(file_path: str) -> List[ChartIntent]:
    """
    Translate a Tableau file directly to ChartIntents.
    
    This is a convenience function that combines extraction, parsing,
    and translation into a single call.
    
    Args:
        file_path: Path to a .twbx or .twb file
        
    Returns:
        List of ChartIntent objects
        
    Example:
        from translators import translate_tableau_file
        
        intents = translate_tableau_file("my_dashboard.twbx")
        for intent in intents:
            print(f"{intent.name}: {intent.chart_type.value}")
    """
    from twbx import get_workbook_xml, parse_workbook
    
    xml_content = get_workbook_xml(file_path)
    workbook = parse_workbook(xml_content)
    return translate_workbook(workbook)


# -----------------------------------------------------------------------------
# MODULE TEST
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("Tableau to Generic Translator")
    print("=" * 50)
    print("\nThis module translates Tableau worksheets to ChartIntents:")
    print("  • translate_worksheet(ws, ds) - Translate single worksheet")
    print("  • translate_workbook(wb) - Translate all worksheets")
    print("  • translate_tableau_file(path) - One-step file translation")
    print("\nRun the tests with: pytest tests/test_tableau_to_generic.py -v")
