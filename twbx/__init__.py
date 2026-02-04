"""
TWBX Package - Tableau File Extraction and Parsing

=============================================================================
WHAT THIS PACKAGE DOES:
=============================================================================
This package handles everything related to reading Tableau files:

1. extractor.py  - Opens .twbx files (which are ZIP archives) and extracts
                   the contents, including the .twb XML file inside

2. xml_parser.py - Reads the Tableau XML and extracts information about
                   worksheets, data sources, shelves (rows, columns, etc.)

3. models.py     - Defines data structures (like blueprints) that represent
                   Tableau concepts: TableauWorksheet, TableauDatasource, etc.

=============================================================================
LAYER 1 & 2 of our architecture
=============================================================================
"""

# Import and expose the extractor functions
from .extractor import (
    extract_workbook,
    get_workbook_xml,
    cleanup_temp_dir,
    ExtractionResult
)

# Import and expose the XML parser functions
from .xml_parser import (
    parse_workbook,
    get_worksheet_summary,
    get_workbook_summary,
    ParsedWorkbook,
    TableauWorksheet,
    TableauDatasource,
    TableauColumn,
    ShelfField
)

# When other modules are implemented, we'll add them here:
# from .models import ...
