"""
Tableau XML Parser

=============================================================================
WHAT THIS MODULE DOES:
=============================================================================
This module parses Tableau workbook XML and extracts structured information
about worksheets, datasources, and visualizations.

The XML structure in a Tableau workbook looks like:
    <workbook>
        <datasources>
            <datasource name="..." caption="...">
                <column name="..." caption="..." role="dimension" datatype="string"/>
            </datasource>
        </datasources>
        <worksheets>
            <worksheet name="Sales Dashboard">
                <table>
                    <rows>[datasource].[field:Field Name:qk]</rows>
                    <cols>[datasource].[field:Other Field:nk]</cols>
                    <pane>
                        <mark class="Bar"/>
                    </pane>
                </table>
            </worksheet>
        </worksheets>
    </workbook>

=============================================================================
MAIN FUNCTION:
=============================================================================
parse_workbook(xml_content) → Returns ParsedWorkbook with all extracted info

=============================================================================
"""

from lxml import etree
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import re


# -----------------------------------------------------------------------------
# DATA CLASSES
# These hold the parsed information in a clean, structured way
# -----------------------------------------------------------------------------

@dataclass
class TableauColumn:
    """
    Represents a column/field in a Tableau datasource.
    
    Attributes:
        name: Internal Tableau name (e.g., "[Sales]")
        caption: Display name shown to users (e.g., "Total Sales")
        role: Either "dimension" or "measure"
        datatype: Data type (string, integer, real, datetime, boolean)
        calculation: If this is a calculated field, the formula
    """
    name: str
    caption: Optional[str]
    role: str  # "dimension" or "measure"
    datatype: str
    calculation: Optional[str] = None
    
    @property
    def display_name(self) -> str:
        """Returns the caption if available, otherwise the cleaned name."""
        if self.caption:
            return self.caption
        # Clean up the internal name (remove brackets)
        return self.name.strip("[]")


@dataclass
class TableauDatasource:
    """
    Represents a datasource in a Tableau workbook.
    
    Attributes:
        name: Internal name used in the XML
        caption: Human-readable name shown in Tableau
        columns: Dictionary of column name → TableauColumn
        connection_type: Type of connection (e.g., "sqlproxy", "excel", "hyper")
    """
    name: str
    caption: Optional[str]
    columns: Dict[str, TableauColumn] = field(default_factory=dict)
    connection_type: Optional[str] = None
    
    @property
    def display_name(self) -> str:
        """Returns the caption if available, otherwise the name."""
        return self.caption or self.name


@dataclass
class ShelfField:
    """
    Represents a field placed on a shelf (rows, columns, color, etc.).
    
    Tableau encodes shelf fields as strings like:
        [datasource].[none:Field Name:qk]
        [datasource].[sum:Sales:qk]
    
    This class parses that into structured components.
    
    Attributes:
        datasource: Name of the datasource
        field_name: Name of the field
        aggregation: Aggregation type (sum, avg, none, etc.) or None
        field_type: Type indicator from Tableau (qk=quantitative, nk=nominal, ok=ordinal)
        raw: The original raw string from the XML
    """
    datasource: str
    field_name: str
    aggregation: Optional[str]
    field_type: Optional[str]
    raw: str
    
    @property
    def is_measure(self) -> bool:
        """Returns True if this appears to be a measure (aggregated field)."""
        return self.aggregation is not None and self.aggregation.lower() != "none"
    
    @property
    def display_name(self) -> str:
        """Returns a human-readable name for the field."""
        if self.aggregation and self.aggregation.lower() != "none":
            return f"{self.aggregation.upper()}({self.field_name})"
        return self.field_name


@dataclass 
class TableauWorksheet:
    """
    Represents a worksheet (visualization) in a Tableau workbook.
    
    Attributes:
        name: Name of the worksheet
        mark_type: Type of mark (Bar, Line, Circle, Square, etc.)
        rows: List of fields on the Rows shelf
        columns: List of fields on the Columns shelf
        color: List of fields on the Color shelf (in marks card)
        size: List of fields on the Size shelf (in marks card)
        label: List of fields on the Label shelf (in marks card)
        detail: List of fields on the Detail shelf (in marks card)
        tooltip: List of fields on the Tooltip shelf
        filters: List of fields used as filters
        datasource_dependencies: List of datasource names used by this worksheet
    """
    name: str
    mark_type: Optional[str] = None
    rows: List[ShelfField] = field(default_factory=list)
    columns: List[ShelfField] = field(default_factory=list)
    color: List[ShelfField] = field(default_factory=list)
    size: List[ShelfField] = field(default_factory=list)
    label: List[ShelfField] = field(default_factory=list)
    detail: List[ShelfField] = field(default_factory=list)
    tooltip: List[ShelfField] = field(default_factory=list)
    filters: List[ShelfField] = field(default_factory=list)
    datasource_dependencies: List[str] = field(default_factory=list)


@dataclass
class ParsedWorkbook:
    """
    The complete parsed representation of a Tableau workbook.
    
    Attributes:
        version: Tableau version that created this workbook
        datasources: Dictionary of datasource name → TableauDatasource
        worksheets: List of TableauWorksheet objects
        parameters: List of parameter columns (special datasource)
    """
    version: Optional[str]
    datasources: Dict[str, TableauDatasource] = field(default_factory=dict)
    worksheets: List[TableauWorksheet] = field(default_factory=list)
    parameters: List[TableauColumn] = field(default_factory=list)


# -----------------------------------------------------------------------------
# PARSING FUNCTIONS
# -----------------------------------------------------------------------------

def parse_workbook(xml_content: str) -> ParsedWorkbook:
    """
    Parse a Tableau workbook XML string into a structured ParsedWorkbook.
    
    This is the main entry point for parsing. It extracts all datasources,
    worksheets, and their configurations from the XML.
    
    Args:
        xml_content: The raw XML content of a .twb file (as a string)
        
    Returns:
        A ParsedWorkbook containing all extracted information
        
    Example:
        from twbx.extractor import get_workbook_xml
        from twbx.xml_parser import parse_workbook
        
        xml = get_workbook_xml("my_dashboard.twbx")
        workbook = parse_workbook(xml)
        
        for ws in workbook.worksheets:
            print(f"Worksheet: {ws.name}, Mark: {ws.mark_type}")
    """
    # Parse the XML
    root = etree.fromstring(xml_content.encode('utf-8'))
    
    # Extract workbook version
    version = root.get('version')
    
    # Create the result object
    result = ParsedWorkbook(version=version)
    
    # Parse datasources
    result.datasources, result.parameters = _parse_datasources(root)
    
    # Parse worksheets
    result.worksheets = _parse_worksheets(root)
    
    return result


def _parse_datasources(root: etree._Element) -> tuple:
    """
    Parse all datasources from the workbook XML.
    
    Note: Tableau workbooks may have multiple datasource elements with the same
    name/caption. We prefer 'inline=true' datasources as they contain the full
    column definitions. If we encounter a duplicate, we keep the one with more
    columns.
    
    Returns:
        Tuple of (datasources dict, parameters list)
    """
    datasources = {}
    parameters = []
    
    for ds_elem in root.findall('.//datasource'):
        ds_name = ds_elem.get('name', '')
        ds_caption = ds_elem.get('caption')
        is_inline = ds_elem.get('inline') == 'true'
        
        # Determine connection type
        connection = ds_elem.find('.//connection')
        connection_type = connection.get('class') if connection is not None else None
        
        # Create datasource object
        datasource = TableauDatasource(
            name=ds_name,
            caption=ds_caption,
            connection_type=connection_type
        )
        
        # Parse columns
        for col_elem in ds_elem.findall('.//column'):
            col_name = col_elem.get('name', '')
            col_caption = col_elem.get('caption')
            col_role = col_elem.get('role', 'dimension')
            col_datatype = col_elem.get('datatype', 'string')
            
            # Check for calculation formula
            calc_elem = col_elem.find('.//calculation')
            calculation = None
            if calc_elem is not None:
                calculation = calc_elem.get('formula')
            
            column = TableauColumn(
                name=col_name,
                caption=col_caption,
                role=col_role,
                datatype=col_datatype,
                calculation=calculation
            )
            
            datasource.columns[col_name] = column
            
            # If this is the Parameters datasource, also add to parameters list
            if ds_name == 'Parameters':
                parameters.append(column)
        
        # Only add/replace if this datasource has more columns than existing one
        # This handles cases where Tableau has duplicate datasource entries
        existing = datasources.get(ds_name)
        if existing is None or len(datasource.columns) > len(existing.columns):
            datasources[ds_name] = datasource
    
    return datasources, parameters


def _parse_worksheets(root: etree._Element) -> List[TableauWorksheet]:
    """
    Parse all worksheets from the workbook XML.
    """
    worksheets = []
    
    for ws_elem in root.findall('.//worksheet'):
        ws_name = ws_elem.get('name', 'Unnamed')
        
        worksheet = TableauWorksheet(name=ws_name)
        
        # Find the table element (contains visualization config)
        table_elem = ws_elem.find('.//table')
        if table_elem is not None:
            # Parse mark type from pane
            pane_elem = table_elem.find('.//pane')
            if pane_elem is not None:
                mark_elem = pane_elem.find('.//mark')
                if mark_elem is not None:
                    worksheet.mark_type = mark_elem.get('class')
                
                # Parse encodings from pane
                encodings_elem = pane_elem.find('.//encodings')
                if encodings_elem is not None:
                    worksheet.color = _parse_encoding_fields(encodings_elem, 'color')
                    worksheet.size = _parse_encoding_fields(encodings_elem, 'size')
                    worksheet.label = _parse_encoding_fields(encodings_elem, 'text')
                    worksheet.detail = _parse_encoding_fields(encodings_elem, 'lod')
            
            # Parse rows shelf
            rows_elem = table_elem.find('.//rows')
            if rows_elem is not None and rows_elem.text:
                worksheet.rows = _parse_shelf_fields(rows_elem.text)
            
            # Parse columns shelf
            cols_elem = table_elem.find('.//cols')
            if cols_elem is not None and cols_elem.text:
                worksheet.columns = _parse_shelf_fields(cols_elem.text)
        
        # Parse datasource dependencies
        for dep in ws_elem.findall('.//datasource-dependencies'):
            ds_name = dep.get('datasource')
            if ds_name:
                worksheet.datasource_dependencies.append(ds_name)
        
        # Parse filters
        for filter_elem in ws_elem.findall('.//filter'):
            col = filter_elem.get('column')
            if col:
                parsed = _parse_single_field(col)
                if parsed:
                    worksheet.filters.append(parsed)
        
        worksheets.append(worksheet)
    
    return worksheets


def _parse_shelf_fields(shelf_text: str) -> List[ShelfField]:
    """
    Parse a shelf text (rows/columns) into a list of ShelfField objects.
    
    Tableau encodes multiple fields on a shelf as space-separated entries.
    Each field looks like: [datasource].[aggregation:FieldName:type]
    """
    fields = []
    
    # Split by spaces, but be careful with field names that might contain spaces
    # Fields are enclosed in brackets, so we can split more carefully
    raw_fields = re.findall(r'\[[^\]]+\]\.\[[^\]]+\]', shelf_text)
    
    for raw in raw_fields:
        parsed = _parse_single_field(raw)
        if parsed:
            fields.append(parsed)
    
    return fields


def _parse_single_field(field_str: str) -> Optional[ShelfField]:
    """
    Parse a single field string into a ShelfField object.
    
    Examples of field strings:
        [datasource].[none:Category:nk]
        [datasource].[sum:Sales:qk]
        [Parameters].[Parameter 1]
    """
    # Pattern: [datasource].[aggregation:field:type] or [datasource].[field]
    match = re.match(r'\[([^\]]+)\]\.\[([^\]]+)\]', field_str)
    
    if not match:
        return None
    
    datasource = match.group(1)
    field_part = match.group(2)
    
    # Try to parse the field part (may have aggregation:name:type format)
    parts = field_part.split(':')
    
    if len(parts) >= 3:
        # Format: aggregation:field_name:type
        aggregation = parts[0] if parts[0] else None
        field_name = parts[1]
        field_type = parts[2] if len(parts) > 2 else None
    elif len(parts) == 2:
        # Format: field_name:type or aggregation:field_name
        aggregation = None
        field_name = parts[0]
        field_type = parts[1]
    else:
        # Just the field name
        aggregation = None
        field_name = parts[0]
        field_type = None
    
    return ShelfField(
        datasource=datasource,
        field_name=field_name,
        aggregation=aggregation,
        field_type=field_type,
        raw=field_str
    )


def _parse_encoding_fields(encodings_elem: etree._Element, encoding_type: str) -> List[ShelfField]:
    """
    Parse fields from an encoding element (color, size, text, etc.).
    """
    fields = []
    
    for enc in encodings_elem.findall(f'.//{encoding_type}'):
        column = enc.get('column')
        if column:
            parsed = _parse_single_field(column)
            if parsed:
                fields.append(parsed)
    
    return fields


# -----------------------------------------------------------------------------
# UTILITY FUNCTIONS
# -----------------------------------------------------------------------------

def get_worksheet_summary(worksheet: TableauWorksheet) -> str:
    """
    Generate a human-readable summary of a worksheet.
    
    Useful for debugging and understanding what a worksheet contains.
    """
    lines = [
        f"Worksheet: {worksheet.name}",
        f"  Mark Type: {worksheet.mark_type or 'Unknown'}",
        f"  Rows: {', '.join(f.display_name for f in worksheet.rows) or 'None'}",
        f"  Columns: {', '.join(f.display_name for f in worksheet.columns) or 'None'}",
    ]
    
    if worksheet.color:
        lines.append(f"  Color: {', '.join(f.display_name for f in worksheet.color)}")
    if worksheet.size:
        lines.append(f"  Size: {', '.join(f.display_name for f in worksheet.size)}")
    if worksheet.filters:
        lines.append(f"  Filters: {', '.join(f.display_name for f in worksheet.filters)}")
    
    return '\n'.join(lines)


def get_workbook_summary(workbook: ParsedWorkbook) -> str:
    """
    Generate a human-readable summary of the entire workbook.
    """
    lines = [
        f"Tableau Workbook (version {workbook.version})",
        f"=" * 50,
        f"Datasources: {len(workbook.datasources)}",
    ]
    
    for name, ds in workbook.datasources.items():
        lines.append(f"  - {ds.display_name}: {len(ds.columns)} columns")
    
    lines.append(f"\nParameters: {len(workbook.parameters)}")
    for param in workbook.parameters:
        lines.append(f"  - {param.display_name}")
    
    lines.append(f"\nWorksheets: {len(workbook.worksheets)}")
    for ws in workbook.worksheets:
        lines.append(f"\n{get_worksheet_summary(ws)}")
    
    return '\n'.join(lines)


# -----------------------------------------------------------------------------
# MODULE TEST
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("Tableau XML Parser Module")
    print("=" * 50)
    print("\nThis module provides functions to parse Tableau XML:")
    print("  • parse_workbook(xml) - Parse XML into structured objects")
    print("  • get_worksheet_summary(ws) - Get human-readable worksheet summary")
    print("  • get_workbook_summary(wb) - Get human-readable workbook summary")
    print("\nRun the tests with: pytest tests/test_xml_parser.py -v")
