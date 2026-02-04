"""
Tests for the Tableau XML Parser Module

=============================================================================
HOW TO RUN THESE TESTS:
=============================================================================
From the project root directory (Tab_to_TS/), run:

    PYTHONPATH=. pytest tests/test_xml_parser.py -v

=============================================================================
WHAT THESE TESTS VERIFY:
=============================================================================
1. Can we parse workbook XML and extract structure?
2. Are datasources and columns extracted correctly?
3. Are worksheets and their properties extracted correctly?
4. Does the parser handle edge cases gracefully?
=============================================================================
"""

import pytest
from pathlib import Path

from twbx.xml_parser import (
    parse_workbook,
    get_worksheet_summary,
    get_workbook_summary,
    ParsedWorkbook,
    TableauWorksheet,
    TableauDatasource,
    TableauColumn,
    ShelfField,
    _parse_single_field,
    _parse_shelf_fields
)


# -----------------------------------------------------------------------------
# TEST FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture
def minimal_workbook_xml():
    """
    A minimal valid Tableau workbook XML for testing.
    Contains one datasource and one worksheet.
    """
    return '''<?xml version='1.0' encoding='utf-8' ?>
<workbook version='18.1'>
  <preferences />
  <datasources>
    <datasource name='TestData' caption='Test Data' inline='true'>
      <column name='[Category]' caption='Category' role='dimension' datatype='string' />
      <column name='[Sales]' caption='Sales' role='measure' datatype='real' />
      <column name='[Profit]' role='measure' datatype='real'>
        <calculation formula='[Sales] * 0.2' />
      </column>
    </datasource>
    <datasource name='Parameters' inline='true'>
      <column name='[Parameter 1]' caption='Top N' role='measure' datatype='integer'>
        <calculation class='tableau' formula='10' />
      </column>
    </datasource>
  </datasources>
  <worksheets>
    <worksheet name='Sales by Category'>
      <table>
        <rows>[TestData].[none:Category:nk]</rows>
        <cols>[TestData].[sum:Sales:qk]</cols>
        <pane>
          <mark class='Bar' />
          <encodings>
            <color column='[TestData].[none:Category:nk]' />
          </encodings>
        </pane>
      </table>
      <datasource-dependencies datasource='TestData' />
    </worksheet>
  </worksheets>
</workbook>
'''


@pytest.fixture
def sample_twbx_path():
    """Path to the sample .twbx file in the test data folder."""
    path = Path(__file__).parent / "sample_data" / "test.twbx"
    if not path.exists():
        pytest.skip("Sample .twbx file not found in tests/sample_data/")
    return path


# -----------------------------------------------------------------------------
# TESTS FOR FIELD PARSING HELPERS
# -----------------------------------------------------------------------------

class TestFieldParsing:
    """Tests for the field string parsing functions."""
    
    def test_parse_simple_field(self):
        """Test parsing a simple field without aggregation."""
        result = _parse_single_field("[TestData].[none:Category:nk]")
        
        assert result is not None
        assert result.datasource == "TestData"
        assert result.field_name == "Category"
        assert result.aggregation == "none"
        assert result.field_type == "nk"
    
    def test_parse_aggregated_field(self):
        """Test parsing a field with SUM aggregation."""
        result = _parse_single_field("[TestData].[sum:Sales:qk]")
        
        assert result is not None
        assert result.datasource == "TestData"
        assert result.field_name == "Sales"
        assert result.aggregation == "sum"
        assert result.field_type == "qk"
        assert result.is_measure == True
    
    def test_parse_parameter_field(self):
        """Test parsing a parameter field (simpler format)."""
        result = _parse_single_field("[Parameters].[Parameter 1]")
        
        assert result is not None
        assert result.datasource == "Parameters"
        assert result.field_name == "Parameter 1"
    
    def test_display_name_with_aggregation(self):
        """Test that display_name includes aggregation for measures."""
        result = _parse_single_field("[TestData].[sum:Sales:qk]")
        
        assert result.display_name == "SUM(Sales)"
    
    def test_display_name_without_aggregation(self):
        """Test that display_name is just the field name for dimensions."""
        result = _parse_single_field("[TestData].[none:Category:nk]")
        
        assert result.display_name == "Category"
    
    def test_parse_shelf_fields_multiple(self):
        """Test parsing multiple fields on a shelf."""
        shelf_text = "[DS].[none:A:nk] [DS].[sum:B:qk]"
        results = _parse_shelf_fields(shelf_text)
        
        assert len(results) == 2
        assert results[0].field_name == "A"
        assert results[1].field_name == "B"


# -----------------------------------------------------------------------------
# TESTS FOR DATASOURCE PARSING
# -----------------------------------------------------------------------------

class TestDatasourceParsing:
    """Tests for datasource extraction."""
    
    def test_parse_datasources(self, minimal_workbook_xml):
        """Test that datasources are extracted correctly."""
        workbook = parse_workbook(minimal_workbook_xml)
        
        assert len(workbook.datasources) == 2
        assert "TestData" in workbook.datasources
        assert "Parameters" in workbook.datasources
    
    def test_datasource_columns(self, minimal_workbook_xml):
        """Test that columns are extracted from datasources."""
        workbook = parse_workbook(minimal_workbook_xml)
        ds = workbook.datasources["TestData"]
        
        assert len(ds.columns) == 3
        assert "[Category]" in ds.columns
        assert "[Sales]" in ds.columns
        assert "[Profit]" in ds.columns
    
    def test_column_properties(self, minimal_workbook_xml):
        """Test that column properties are extracted correctly."""
        workbook = parse_workbook(minimal_workbook_xml)
        ds = workbook.datasources["TestData"]
        
        category_col = ds.columns["[Category]"]
        assert category_col.caption == "Category"
        assert category_col.role == "dimension"
        assert category_col.datatype == "string"
        assert category_col.display_name == "Category"
        
        sales_col = ds.columns["[Sales]"]
        assert sales_col.role == "measure"
        assert sales_col.datatype == "real"
    
    def test_calculated_field(self, minimal_workbook_xml):
        """Test that calculated fields include their formula."""
        workbook = parse_workbook(minimal_workbook_xml)
        ds = workbook.datasources["TestData"]
        
        profit_col = ds.columns["[Profit]"]
        assert profit_col.calculation == "[Sales] * 0.2"
    
    def test_parameters_extracted(self, minimal_workbook_xml):
        """Test that parameters are extracted separately."""
        workbook = parse_workbook(minimal_workbook_xml)
        
        assert len(workbook.parameters) == 1
        assert workbook.parameters[0].caption == "Top N"


# -----------------------------------------------------------------------------
# TESTS FOR WORKSHEET PARSING
# -----------------------------------------------------------------------------

class TestWorksheetParsing:
    """Tests for worksheet extraction."""
    
    def test_parse_worksheets(self, minimal_workbook_xml):
        """Test that worksheets are extracted."""
        workbook = parse_workbook(minimal_workbook_xml)
        
        assert len(workbook.worksheets) == 1
        assert workbook.worksheets[0].name == "Sales by Category"
    
    def test_worksheet_mark_type(self, minimal_workbook_xml):
        """Test that mark type is extracted."""
        workbook = parse_workbook(minimal_workbook_xml)
        ws = workbook.worksheets[0]
        
        assert ws.mark_type == "Bar"
    
    def test_worksheet_rows_columns(self, minimal_workbook_xml):
        """Test that rows and columns shelves are extracted."""
        workbook = parse_workbook(minimal_workbook_xml)
        ws = workbook.worksheets[0]
        
        assert len(ws.rows) == 1
        assert ws.rows[0].field_name == "Category"
        
        assert len(ws.columns) == 1
        assert ws.columns[0].field_name == "Sales"
        assert ws.columns[0].aggregation == "sum"
    
    def test_worksheet_color_encoding(self, minimal_workbook_xml):
        """Test that color encoding is extracted."""
        workbook = parse_workbook(minimal_workbook_xml)
        ws = workbook.worksheets[0]
        
        assert len(ws.color) == 1
        assert ws.color[0].field_name == "Category"
    
    def test_datasource_dependencies(self, minimal_workbook_xml):
        """Test that datasource dependencies are tracked."""
        workbook = parse_workbook(minimal_workbook_xml)
        ws = workbook.worksheets[0]
        
        assert "TestData" in ws.datasource_dependencies


# -----------------------------------------------------------------------------
# TESTS FOR WORKBOOK PARSING
# -----------------------------------------------------------------------------

class TestWorkbookParsing:
    """Tests for overall workbook parsing."""
    
    def test_version_extracted(self, minimal_workbook_xml):
        """Test that workbook version is extracted."""
        workbook = parse_workbook(minimal_workbook_xml)
        
        assert workbook.version == "18.1"
    
    def test_summary_generation(self, minimal_workbook_xml):
        """Test that summary functions work without errors."""
        workbook = parse_workbook(minimal_workbook_xml)
        
        # Should not raise any errors
        summary = get_workbook_summary(workbook)
        assert "Sales by Category" in summary
        assert "Bar" in summary
        
        ws_summary = get_worksheet_summary(workbook.worksheets[0])
        assert "Category" in ws_summary


# -----------------------------------------------------------------------------
# TESTS WITH REAL TABLEAU FILE
# -----------------------------------------------------------------------------

class TestRealTableauFile:
    """Tests using the actual sample .twbx file."""
    
    def test_parse_real_twbx(self, sample_twbx_path):
        """Test parsing a real Tableau file."""
        from twbx import get_workbook_xml
        
        xml_content = get_workbook_xml(sample_twbx_path)
        workbook = parse_workbook(xml_content)
        
        # Basic checks
        assert workbook.version is not None
        assert len(workbook.worksheets) >= 1
    
    def test_real_file_has_datasources(self, sample_twbx_path):
        """Test that real file has datasources with columns."""
        from twbx import get_workbook_xml
        
        xml_content = get_workbook_xml(sample_twbx_path)
        workbook = parse_workbook(xml_content)
        
        # Should have at least one datasource with columns
        has_columns = any(
            len(ds.columns) > 0 
            for ds in workbook.datasources.values()
        )
        assert has_columns, "Expected at least one datasource with columns"
    
    def test_real_worksheet_has_mark_type(self, sample_twbx_path):
        """Test that real worksheet has a mark type."""
        from twbx import get_workbook_xml
        
        xml_content = get_workbook_xml(sample_twbx_path)
        workbook = parse_workbook(xml_content)
        
        # At least one worksheet should have a mark type
        has_mark = any(ws.mark_type for ws in workbook.worksheets)
        assert has_mark, "Expected at least one worksheet with a mark type"


# -----------------------------------------------------------------------------
# RUN TESTS
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
