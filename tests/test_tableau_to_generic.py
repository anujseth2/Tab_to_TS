"""
Tests for the Tableau to Generic Translator

=============================================================================
HOW TO RUN THESE TESTS:
=============================================================================
From the project root directory (Tab_to_TS/), run:

    PYTHONPATH=. pytest tests/test_tableau_to_generic.py -v

=============================================================================
WHAT THESE TESTS VERIFY:
=============================================================================
1. Mark type mapping works correctly
2. Shelf fields are converted to proper encodings
3. Orientation detection works
4. Full worksheet translation produces valid ChartIntent
=============================================================================
"""

import pytest
from pathlib import Path

from twbx.xml_parser import (
    ParsedWorkbook,
    TableauWorksheet,
    TableauDatasource,
    TableauColumn,
    ShelfField
)

from translators.tableau_to_generic import (
    translate_worksheet,
    translate_workbook,
    translate_tableau_file,
    _map_mark_type,
    _convert_shelf_field_to_field,
    _detect_orientation
)

from viz_model import (
    ChartType,
    AggregationType,
    FieldRole,
    EncodingChannel,
    ChartIntent
)


# -----------------------------------------------------------------------------
# TEST FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture
def sample_datasource():
    """Create a sample datasource with columns."""
    ds = TableauDatasource(
        name="TestData",
        caption="Test Data"
    )
    
    ds.columns["[Category]"] = TableauColumn(
        name="[Category]",
        caption="Category",
        role="dimension",
        datatype="string"
    )
    
    ds.columns["[Sales]"] = TableauColumn(
        name="[Sales]",
        caption="Sales",
        role="measure",
        datatype="real"
    )
    
    ds.columns["[Profit]"] = TableauColumn(
        name="[Profit]",
        caption="Profit",
        role="measure",
        datatype="real"
    )
    
    ds.columns["[Region]"] = TableauColumn(
        name="[Region]",
        caption="Region",
        role="dimension",
        datatype="string"
    )
    
    return {"TestData": ds}


@pytest.fixture
def bar_chart_worksheet():
    """Create a sample bar chart worksheet."""
    return TableauWorksheet(
        name="Sales by Category",
        mark_type="Bar",
        rows=[
            ShelfField(
                datasource="TestData",
                field_name="Category",
                aggregation="none",
                field_type="nk",
                raw="[TestData].[none:Category:nk]"
            )
        ],
        columns=[
            ShelfField(
                datasource="TestData",
                field_name="Sales",
                aggregation="sum",
                field_type="qk",
                raw="[TestData].[sum:Sales:qk]"
            )
        ],
        datasource_dependencies=["TestData"]
    )


@pytest.fixture
def horizontal_bar_worksheet():
    """Create a horizontal bar chart worksheet (measure on columns)."""
    return TableauWorksheet(
        name="Horizontal Bars",
        mark_type="Bar",
        rows=[
            ShelfField(
                datasource="TestData",
                field_name="Category",
                aggregation="none",
                field_type="nk",
                raw="[TestData].[none:Category:nk]"
            )
        ],
        columns=[
            ShelfField(
                datasource="TestData",
                field_name="Sales",
                aggregation="sum",
                field_type="qk",
                raw="[TestData].[sum:Sales:qk]"
            )
        ],
        datasource_dependencies=["TestData"]
    )


@pytest.fixture
def line_chart_worksheet():
    """Create a sample line chart worksheet."""
    return TableauWorksheet(
        name="Sales Trend",
        mark_type="Line",
        rows=[
            ShelfField(
                datasource="TestData",
                field_name="Sales",
                aggregation="sum",
                field_type="qk",
                raw="[TestData].[sum:Sales:qk]"
            )
        ],
        columns=[
            ShelfField(
                datasource="TestData",
                field_name="Order Date",
                aggregation="none",
                field_type="ok",
                raw="[TestData].[none:Order Date:ok]"
            )
        ],
        color=[
            ShelfField(
                datasource="TestData",
                field_name="Region",
                aggregation="none",
                field_type="nk",
                raw="[TestData].[none:Region:nk]"
            )
        ],
        datasource_dependencies=["TestData"]
    )


@pytest.fixture
def sample_twbx_path():
    """Path to the sample .twbx file."""
    path = Path(__file__).parent / "sample_data" / "test.twbx"
    if not path.exists():
        pytest.skip("Sample .twbx file not found")
    return path


# -----------------------------------------------------------------------------
# TESTS FOR MARK TYPE MAPPING
# -----------------------------------------------------------------------------

class TestMarkTypeMapping:
    """Tests for Tableau mark type to ChartType conversion."""
    
    def test_bar_mapping(self):
        """Test Bar mark maps to BAR."""
        assert _map_mark_type("Bar") == ChartType.BAR
        assert _map_mark_type("bar") == ChartType.BAR
    
    def test_line_mapping(self):
        """Test Line mark maps to LINE."""
        assert _map_mark_type("Line") == ChartType.LINE
    
    def test_circle_mapping(self):
        """Test Circle mark maps to SCATTER."""
        assert _map_mark_type("Circle") == ChartType.SCATTER
        assert _map_mark_type("Square") == ChartType.SCATTER
    
    def test_area_mapping(self):
        """Test Area mark maps to AREA."""
        assert _map_mark_type("Area") == ChartType.AREA
    
    def test_pie_mapping(self):
        """Test Pie mark maps to PIE."""
        assert _map_mark_type("Pie") == ChartType.PIE
    
    def test_unknown_mapping(self):
        """Test unknown marks map to UNKNOWN."""
        assert _map_mark_type("SomeNewType") == ChartType.UNKNOWN
        assert _map_mark_type(None) == ChartType.UNKNOWN


# -----------------------------------------------------------------------------
# TESTS FOR FIELD CONVERSION
# -----------------------------------------------------------------------------

class TestFieldConversion:
    """Tests for converting Tableau shelf fields to generic fields."""
    
    def test_convert_dimension_field(self, sample_datasource):
        """Test converting a dimension field."""
        shelf_field = ShelfField(
            datasource="TestData",
            field_name="Category",
            aggregation="none",
            field_type="nk",
            raw="[TestData].[none:Category:nk]"
        )
        
        field = _convert_shelf_field_to_field(shelf_field, sample_datasource)
        
        assert field.name == "Category"
        assert field.role == FieldRole.DIMENSION
        assert field.aggregation == AggregationType.NONE
    
    def test_convert_measure_field(self, sample_datasource):
        """Test converting a measure field with aggregation."""
        shelf_field = ShelfField(
            datasource="TestData",
            field_name="Sales",
            aggregation="sum",
            field_type="qk",
            raw="[TestData].[sum:Sales:qk]"
        )
        
        field = _convert_shelf_field_to_field(shelf_field, sample_datasource)
        
        assert field.name == "Sales"
        assert field.role == FieldRole.MEASURE
        assert field.aggregation == AggregationType.SUM
        assert field.display_name == "SUM(Sales)"
    
    def test_convert_avg_aggregation(self, sample_datasource):
        """Test converting field with AVG aggregation."""
        shelf_field = ShelfField(
            datasource="TestData",
            field_name="Profit",
            aggregation="avg",
            field_type="qk",
            raw="[TestData].[avg:Profit:qk]"
        )
        
        field = _convert_shelf_field_to_field(shelf_field, sample_datasource)
        
        assert field.aggregation == AggregationType.AVG
        assert field.display_name == "AVG(Profit)"


# -----------------------------------------------------------------------------
# TESTS FOR ORIENTATION DETECTION
# -----------------------------------------------------------------------------

class TestOrientationDetection:
    """Tests for chart orientation detection."""
    
    def test_horizontal_bar_detection(self, sample_datasource):
        """Test detection of horizontal bars (measure on columns)."""
        # Measure on columns = horizontal bars
        cols = [
            ShelfField(
                datasource="TestData",
                field_name="Sales",
                aggregation="sum",
                field_type="qk",
                raw="[TestData].[sum:Sales:qk]"
            )
        ]
        rows = [
            ShelfField(
                datasource="TestData",
                field_name="Category",
                aggregation="none",
                field_type="nk",
                raw="[TestData].[none:Category:nk]"
            )
        ]
        
        orientation = _detect_orientation(rows, cols, ChartType.BAR, sample_datasource)
        assert orientation == "horizontal"
    
    def test_vertical_bar_detection(self, sample_datasource):
        """Test detection of vertical bars (measure on rows)."""
        # Measure on rows = vertical bars
        cols = [
            ShelfField(
                datasource="TestData",
                field_name="Category",
                aggregation="none",
                field_type="nk",
                raw="[TestData].[none:Category:nk]"
            )
        ]
        rows = [
            ShelfField(
                datasource="TestData",
                field_name="Sales",
                aggregation="sum",
                field_type="qk",
                raw="[TestData].[sum:Sales:qk]"
            )
        ]
        
        orientation = _detect_orientation(rows, cols, ChartType.BAR, sample_datasource)
        assert orientation == "vertical"
    
    def test_non_bar_charts_vertical(self, sample_datasource):
        """Test that non-bar charts default to vertical."""
        orientation = _detect_orientation([], [], ChartType.LINE, sample_datasource)
        assert orientation == "vertical"


# -----------------------------------------------------------------------------
# TESTS FOR WORKSHEET TRANSLATION
# -----------------------------------------------------------------------------

class TestWorksheetTranslation:
    """Tests for full worksheet translation."""
    
    def test_translate_bar_chart(self, bar_chart_worksheet, sample_datasource):
        """Test translating a bar chart worksheet."""
        intent = translate_worksheet(bar_chart_worksheet, sample_datasource)
        
        assert intent.name == "Sales by Category"
        assert intent.chart_type in [ChartType.BAR, ChartType.BAR_HORIZONTAL]
        assert len(intent.encodings) == 2
    
    def test_translate_line_chart(self, line_chart_worksheet, sample_datasource):
        """Test translating a line chart worksheet."""
        intent = translate_worksheet(line_chart_worksheet, sample_datasource)
        
        assert intent.name == "Sales Trend"
        assert intent.chart_type == ChartType.LINE
        
        # Should have X, Y, and COLOR encodings
        assert intent.x_field is not None
        assert intent.y_field is not None
        assert intent.color_field is not None
        assert intent.color_field.name == "Region"
    
    def test_intent_has_title(self, bar_chart_worksheet, sample_datasource):
        """Test that translated intent has a title."""
        intent = translate_worksheet(bar_chart_worksheet, sample_datasource)
        
        assert intent.title == "Sales by Category"
    
    def test_intent_has_datasource(self, bar_chart_worksheet, sample_datasource):
        """Test that datasource is captured."""
        intent = translate_worksheet(bar_chart_worksheet, sample_datasource)
        
        assert intent.data_source == "TestData"


# -----------------------------------------------------------------------------
# TESTS FOR WORKBOOK TRANSLATION
# -----------------------------------------------------------------------------

class TestWorkbookTranslation:
    """Tests for translating entire workbooks."""
    
    def test_translate_workbook(self, bar_chart_worksheet, sample_datasource):
        """Test translating a workbook with multiple worksheets."""
        workbook = ParsedWorkbook(
            version="18.1",
            datasources=sample_datasource,
            worksheets=[bar_chart_worksheet]
        )
        
        intents = translate_workbook(workbook)
        
        assert len(intents) == 1
        assert intents[0].name == "Sales by Category"


# -----------------------------------------------------------------------------
# TESTS WITH REAL FILE
# -----------------------------------------------------------------------------

class TestRealFileTranslation:
    """Tests using the actual sample .twbx file."""
    
    def test_translate_real_file(self, sample_twbx_path):
        """Test translating a real Tableau file."""
        intents = translate_tableau_file(str(sample_twbx_path))
        
        # Should produce at least one intent
        assert len(intents) >= 1
        
        # Each intent should be valid
        for intent in intents:
            assert isinstance(intent, ChartIntent)
            assert intent.name is not None
            assert intent.chart_type is not None
    
    def test_real_file_has_encodings(self, sample_twbx_path):
        """Test that real file produces intents with encodings."""
        intents = translate_tableau_file(str(sample_twbx_path))
        
        # At least one intent should have encodings
        has_encodings = any(len(intent.encodings) > 0 for intent in intents)
        assert has_encodings


# -----------------------------------------------------------------------------
# RUN TESTS
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
