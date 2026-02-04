"""
Tests for the Abstract Viz Model Schemas

=============================================================================
HOW TO RUN THESE TESTS:
=============================================================================
From the project root directory (Tab_to_TS/), run:

    PYTHONPATH=. pytest tests/test_schemas.py -v

=============================================================================
WHAT THESE TESTS VERIFY:
=============================================================================
1. Enum values are correct
2. Field creation and properties work
3. Encoding and ChartIntent work correctly
4. Factory functions create proper objects
=============================================================================
"""

import pytest

from viz_model import (
    ChartType,
    AggregationType,
    FieldRole,
    EncodingChannel,
    SortOrder,
    Field,
    Encoding,
    Filter,
    ChartIntent,
    dimension,
    measure,
    get_chart_intent_summary
)


# -----------------------------------------------------------------------------
# TESTS FOR ENUMS
# -----------------------------------------------------------------------------

class TestEnums:
    """Tests for enum definitions."""
    
    def test_chart_type_values(self):
        """Test that ChartType has expected values."""
        assert ChartType.BAR.value == "bar"
        assert ChartType.LINE.value == "line"
        assert ChartType.SCATTER.value == "scatter"
        assert ChartType.PIE.value == "pie"
    
    def test_aggregation_type_values(self):
        """Test that AggregationType has expected values."""
        assert AggregationType.SUM.value == "sum"
        assert AggregationType.AVG.value == "avg"
        assert AggregationType.COUNT.value == "count"
        assert AggregationType.NONE.value == "none"
    
    def test_aggregation_from_tableau(self):
        """Test conversion from Tableau aggregation strings."""
        assert AggregationType.from_tableau("sum") == AggregationType.SUM
        assert AggregationType.from_tableau("SUM") == AggregationType.SUM
        assert AggregationType.from_tableau("avg") == AggregationType.AVG
        assert AggregationType.from_tableau("none") == AggregationType.NONE
        assert AggregationType.from_tableau(None) == AggregationType.NONE
        assert AggregationType.from_tableau("unknown") == AggregationType.NONE
    
    def test_field_role_values(self):
        """Test that FieldRole has expected values."""
        assert FieldRole.DIMENSION.value == "dimension"
        assert FieldRole.MEASURE.value == "measure"
    
    def test_encoding_channel_values(self):
        """Test that EncodingChannel has expected values."""
        assert EncodingChannel.X.value == "x"
        assert EncodingChannel.Y.value == "y"
        assert EncodingChannel.COLOR.value == "color"
        assert EncodingChannel.SIZE.value == "size"


# -----------------------------------------------------------------------------
# TESTS FOR FIELD
# -----------------------------------------------------------------------------

class TestField:
    """Tests for the Field dataclass."""
    
    def test_create_dimension_field(self):
        """Test creating a dimension field."""
        field = Field(
            name="Category",
            role=FieldRole.DIMENSION,
            data_type="string"
        )
        
        assert field.name == "Category"
        assert field.is_dimension == True
        assert field.is_measure == False
        assert field.display_name == "Category"
    
    def test_create_measure_field(self):
        """Test creating a measure field with aggregation."""
        field = Field(
            name="Sales",
            role=FieldRole.MEASURE,
            data_type="real",
            aggregation=AggregationType.SUM
        )
        
        assert field.name == "Sales"
        assert field.is_measure == True
        assert field.is_dimension == False
        assert field.display_name == "SUM(Sales)"
    
    def test_measure_without_aggregation(self):
        """Test measure field with no aggregation."""
        field = Field(
            name="Value",
            role=FieldRole.MEASURE,
            aggregation=AggregationType.NONE
        )
        
        assert field.display_name == "Value"
    
    def test_field_with_calculation(self):
        """Test field with a calculation formula."""
        field = Field(
            name="Profit Ratio",
            role=FieldRole.MEASURE,
            calculation="[Profit] / [Sales]"
        )
        
        assert field.calculation == "[Profit] / [Sales]"


# -----------------------------------------------------------------------------
# TESTS FOR FACTORY FUNCTIONS
# -----------------------------------------------------------------------------

class TestFactoryFunctions:
    """Tests for the convenience factory functions."""
    
    def test_dimension_factory(self):
        """Test the dimension() factory function."""
        field = dimension("Category")
        
        assert field.name == "Category"
        assert field.role == FieldRole.DIMENSION
        assert field.data_type == "string"
        assert field.aggregation == AggregationType.NONE
    
    def test_dimension_with_type(self):
        """Test dimension with specified data type."""
        field = dimension("Order Date", data_type="date")
        
        assert field.data_type == "date"
    
    def test_measure_factory(self):
        """Test the measure() factory function."""
        field = measure("Sales")
        
        assert field.name == "Sales"
        assert field.role == FieldRole.MEASURE
        assert field.aggregation == AggregationType.SUM  # Default
        assert field.data_type == "real"
    
    def test_measure_with_aggregation(self):
        """Test measure with specified aggregation."""
        field = measure("Profit", aggregation=AggregationType.AVG)
        
        assert field.aggregation == AggregationType.AVG
        assert field.display_name == "AVG(Profit)"


# -----------------------------------------------------------------------------
# TESTS FOR ENCODING
# -----------------------------------------------------------------------------

class TestEncoding:
    """Tests for the Encoding dataclass."""
    
    def test_create_encoding(self):
        """Test creating an encoding."""
        field = dimension("Category")
        encoding = Encoding(
            channel=EncodingChannel.X,
            field=field
        )
        
        assert encoding.channel == EncodingChannel.X
        assert encoding.field.name == "Category"
        assert encoding.sort == SortOrder.NONE
    
    def test_encoding_with_sort(self):
        """Test encoding with sort order."""
        field = measure("Sales")
        encoding = Encoding(
            channel=EncodingChannel.Y,
            field=field,
            sort=SortOrder.DESCENDING
        )
        
        assert encoding.sort == SortOrder.DESCENDING


# -----------------------------------------------------------------------------
# TESTS FOR CHART INTENT
# -----------------------------------------------------------------------------

class TestChartIntent:
    """Tests for the ChartIntent dataclass."""
    
    def test_create_simple_chart(self):
        """Test creating a simple bar chart."""
        category = dimension("Category")
        sales = measure("Sales")
        
        intent = ChartIntent(
            name="Sales by Category",
            chart_type=ChartType.BAR,
            encodings=[
                Encoding(EncodingChannel.X, category),
                Encoding(EncodingChannel.Y, sales)
            ]
        )
        
        assert intent.name == "Sales by Category"
        assert intent.chart_type == ChartType.BAR
        assert len(intent.encodings) == 2
    
    def test_get_encoding(self):
        """Test getting encoding by channel."""
        category = dimension("Category")
        sales = measure("Sales")
        
        intent = ChartIntent(
            name="Test",
            chart_type=ChartType.BAR,
            encodings=[
                Encoding(EncodingChannel.X, category),
                Encoding(EncodingChannel.Y, sales)
            ]
        )
        
        x_enc = intent.get_encoding(EncodingChannel.X)
        assert x_enc is not None
        assert x_enc.field.name == "Category"
        
        color_enc = intent.get_encoding(EncodingChannel.COLOR)
        assert color_enc is None
    
    def test_convenience_properties(self):
        """Test x_field, y_field, color_field properties."""
        category = dimension("Category")
        sales = measure("Sales")
        region = dimension("Region")
        
        intent = ChartIntent(
            name="Test",
            chart_type=ChartType.BAR,
            encodings=[
                Encoding(EncodingChannel.X, category),
                Encoding(EncodingChannel.Y, sales),
                Encoding(EncodingChannel.COLOR, region)
            ]
        )
        
        assert intent.x_field.name == "Category"
        assert intent.y_field.name == "Sales"
        assert intent.color_field.name == "Region"
    
    def test_dimensions_and_measures(self):
        """Test getting all dimensions and measures."""
        category = dimension("Category")
        region = dimension("Region")
        sales = measure("Sales")
        
        intent = ChartIntent(
            name="Test",
            chart_type=ChartType.BAR,
            encodings=[
                Encoding(EncodingChannel.X, category),
                Encoding(EncodingChannel.Y, sales),
                Encoding(EncodingChannel.COLOR, region)
            ]
        )
        
        assert len(intent.dimensions) == 2
        assert len(intent.measures) == 1
    
    def test_chart_with_options(self):
        """Test chart with additional options."""
        intent = ChartIntent(
            name="Stacked Bar",
            chart_type=ChartType.BAR,
            orientation="horizontal",
            stacked=True,
            title="Sales Analysis",
            subtitle="By Region"
        )
        
        assert intent.orientation == "horizontal"
        assert intent.stacked == True
        assert intent.title == "Sales Analysis"
        assert intent.subtitle == "By Region"
    
    def test_chart_summary(self):
        """Test that summary generation works."""
        category = dimension("Category")
        sales = measure("Sales")
        
        intent = ChartIntent(
            name="Sales Chart",
            chart_type=ChartType.BAR,
            encodings=[
                Encoding(EncodingChannel.X, category),
                Encoding(EncodingChannel.Y, sales)
            ],
            title="My Chart"
        )
        
        summary = get_chart_intent_summary(intent)
        assert "Sales Chart" in summary
        assert "bar" in summary
        assert "Category" in summary
        assert "SUM(Sales)" in summary


# -----------------------------------------------------------------------------
# TESTS FOR FILTER
# -----------------------------------------------------------------------------

class TestFilter:
    """Tests for the Filter dataclass."""
    
    def test_create_categorical_filter(self):
        """Test creating a categorical filter."""
        field = dimension("Region")
        filter = Filter(
            field=field,
            filter_type="categorical",
            values=["East", "West"]
        )
        
        assert filter.field.name == "Region"
        assert filter.values == ["East", "West"]
        assert filter.include == True
    
    def test_create_range_filter(self):
        """Test creating a range filter."""
        field = measure("Sales")
        filter = Filter(
            field=field,
            filter_type="range",
            min_value=100,
            max_value=1000
        )
        
        assert filter.filter_type == "range"
        assert filter.min_value == 100
        assert filter.max_value == 1000


# -----------------------------------------------------------------------------
# RUN TESTS
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
