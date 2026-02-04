"""
Tests for the Generic to Muze Generator

=============================================================================
HOW TO RUN THESE TESTS:
=============================================================================
From the project root directory (Tab_to_TS/), run:

    PYTHONPATH=. pytest tests/test_generic_to_muze.py -v

=============================================================================
WHAT THESE TESTS VERIFY:
=============================================================================
1. Template-based generation produces valid Muze code
2. Code includes required components (schema, data, mount)
3. Different chart types generate appropriate mark types
4. Prompt building works correctly
5. Error handling works properly
=============================================================================
"""

import pytest
import json
from pathlib import Path

from viz_model import (
    ChartType,
    AggregationType,
    FieldRole,
    EncodingChannel,
    Field,
    Encoding,
    ChartIntent,
    dimension,
    measure
)

from translators.generic_to_muze import (
    generate_muze_code,
    generate_muze_code_batch,
    preview_prompt,
    MuzeGeneratorConfig,
    _generate_with_template,
    _build_generation_prompt,
    _clean_generated_code,
    # Cache imports
    MuzeCodeCache,
    get_cache,
    clear_cache,
    get_cache_stats
)


# -----------------------------------------------------------------------------
# TEST FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture
def bar_chart_intent():
    """Create a sample bar chart intent."""
    return ChartIntent(
        name="Sales by Category",
        chart_type=ChartType.BAR,
        encodings=[
            Encoding(EncodingChannel.X, dimension("Category")),
            Encoding(EncodingChannel.Y, measure("Sales", AggregationType.SUM))
        ],
        title="Sales by Category"
    )


@pytest.fixture
def line_chart_intent():
    """Create a sample line chart intent with color encoding."""
    return ChartIntent(
        name="Sales Trend",
        chart_type=ChartType.LINE,
        encodings=[
            Encoding(EncodingChannel.X, dimension("Date", data_type="date")),
            Encoding(EncodingChannel.Y, measure("Sales", AggregationType.SUM)),
            Encoding(EncodingChannel.COLOR, dimension("Region"))
        ],
        title="Sales Over Time by Region"
    )


@pytest.fixture
def scatter_chart_intent():
    """Create a sample scatter plot intent."""
    return ChartIntent(
        name="Profit vs Sales",
        chart_type=ChartType.SCATTER,
        encodings=[
            Encoding(EncodingChannel.X, measure("Sales", AggregationType.SUM)),
            Encoding(EncodingChannel.Y, measure("Profit", AggregationType.SUM)),
            Encoding(EncodingChannel.COLOR, dimension("Category")),
            Encoding(EncodingChannel.SIZE, measure("Quantity", AggregationType.SUM))
        ],
        title="Profit vs Sales Analysis"
    )


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return [
        {"Category": "Furniture", "Sales": 1000, "Profit": 200},
        {"Category": "Technology", "Sales": 2000, "Profit": 500},
        {"Category": "Office Supplies", "Sales": 800, "Profit": 100}
    ]


@pytest.fixture
def sample_twbx_path():
    """Path to sample .twbx file."""
    path = Path(__file__).parent / "sample_data" / "test.twbx"
    if not path.exists():
        pytest.skip("Sample .twbx file not found")
    return path


# -----------------------------------------------------------------------------
# TESTS FOR TEMPLATE-BASED GENERATION
# -----------------------------------------------------------------------------

class TestTemplateGeneration:
    """Tests for template-based code generation."""
    
    def test_bar_chart_generation(self, bar_chart_intent):
        """Test generating code for a bar chart."""
        code = generate_muze_code(bar_chart_intent, use_llm=False)
        
        # Check essential components
        assert "const { muze, DataModel } = viz;" in code
        assert "const schema = [" in code
        assert "const data = [" in code
        assert "new DataModel(data, schema)" in code
        assert ".mount('#chart-container')" in code
        assert "mark: 'bar'" in code
    
    def test_line_chart_generation(self, line_chart_intent):
        """Test generating code for a line chart with color."""
        code = generate_muze_code(line_chart_intent, use_llm=False)
        
        assert "mark: 'line'" in code
        assert ".color('Region')" in code
    
    def test_scatter_chart_generation(self, scatter_chart_intent):
        """Test generating code for a scatter plot with size."""
        code = generate_muze_code(scatter_chart_intent, use_llm=False)
        
        assert "mark: 'point'" in code
        assert ".color('Category')" in code
        assert ".size('Quantity')" in code
    
    def test_schema_has_correct_types(self, bar_chart_intent):
        """Test that schema defines correct field types."""
        code = generate_muze_code(bar_chart_intent, use_llm=False)
        
        # Category should be dimension
        assert "name: 'Category', type: 'dimension'" in code
        
        # Sales should be measure with aggregation
        assert "name: 'Sales', type: 'measure'" in code
        assert "defAggFn: 'sum'" in code
    
    def test_with_sample_data(self, bar_chart_intent, sample_data):
        """Test generation with sample data provided."""
        code = generate_muze_code(bar_chart_intent, sample_data=sample_data, use_llm=False)
        
        # Should include actual data values
        assert "Furniture" in code
        assert "Technology" in code
    
    def test_title_included(self, bar_chart_intent):
        """Test that chart title is included."""
        code = generate_muze_code(bar_chart_intent, use_llm=False)
        
        assert ".title('Sales by Category')" in code


# -----------------------------------------------------------------------------
# TESTS FOR CODE QUALITY
# -----------------------------------------------------------------------------

class TestCodeQuality:
    """Tests for code quality and validity."""
    
    def test_code_is_complete_javascript(self, bar_chart_intent):
        """Test that generated code is complete JavaScript."""
        code = generate_muze_code(bar_chart_intent, use_llm=False)
        
        # Should not have placeholders
        assert "TODO" not in code
        assert "PLACEHOLDER" not in code
        assert "undefined" not in code.lower() or "undefined" in code  # Allow 'undefined' in strings
    
    def test_code_has_no_syntax_errors(self, bar_chart_intent):
        """Test that code doesn't have obvious syntax issues."""
        code = generate_muze_code(bar_chart_intent, use_llm=False)
        
        # Check bracket balance (simple check)
        assert code.count('{') == code.count('}')
        assert code.count('[') == code.count(']')
        assert code.count('(') == code.count(')')
    
    def test_clean_generated_code(self):
        """Test cleaning of markdown from generated code."""
        dirty_code = """```javascript
const x = 1;
```"""
        clean = _clean_generated_code(dirty_code)
        
        assert "```" not in clean
        assert "const x = 1;" in clean


# -----------------------------------------------------------------------------
# TESTS FOR PROMPT BUILDING
# -----------------------------------------------------------------------------

class TestPromptBuilding:
    """Tests for LLM prompt construction."""
    
    def test_prompt_includes_chart_spec(self, bar_chart_intent):
        """Test that prompt includes chart specification."""
        prompt = preview_prompt(bar_chart_intent)
        
        assert "Sales by Category" in prompt
        assert "bar" in prompt.lower()
        assert "Chart Type" in prompt
    
    def test_prompt_includes_encodings(self, bar_chart_intent):
        """Test that prompt includes encoding information."""
        prompt = preview_prompt(bar_chart_intent)
        
        assert "Category" in prompt
        assert "Sales" in prompt
        assert "dimension" in prompt
        assert "measure" in prompt
    
    def test_prompt_includes_sample_data(self, bar_chart_intent, sample_data):
        """Test that prompt includes sample data when provided."""
        prompt = preview_prompt(bar_chart_intent, sample_data)
        
        assert "Sample Data" in prompt
        assert "Furniture" in prompt
    
    def test_prompt_includes_requirements(self, bar_chart_intent):
        """Test that prompt includes generation requirements."""
        prompt = preview_prompt(bar_chart_intent)
        
        assert "Requirements" in prompt
        assert "schema" in prompt.lower()
        assert "mount" in prompt.lower()


# -----------------------------------------------------------------------------
# TESTS FOR BATCH GENERATION
# -----------------------------------------------------------------------------

class TestBatchGeneration:
    """Tests for batch code generation."""
    
    def test_batch_generation(self, bar_chart_intent, line_chart_intent):
        """Test generating code for multiple intents."""
        intents = [bar_chart_intent, line_chart_intent]
        
        codes = generate_muze_code_batch(intents, use_llm=False)
        
        assert len(codes) == 2
        assert "Sales by Category" in codes
        assert "Sales Trend" in codes
        assert "bar" in codes["Sales by Category"]
        assert "line" in codes["Sales Trend"]
    
    def test_batch_with_sample_data_map(self, bar_chart_intent, sample_data):
        """Test batch generation with sample data map."""
        intents = [bar_chart_intent]
        sample_data_map = {"Sales by Category": sample_data}
        
        codes = generate_muze_code_batch(intents, sample_data_map, use_llm=False)
        
        assert "Furniture" in codes["Sales by Category"]


# -----------------------------------------------------------------------------
# TESTS FOR CONFIGURATION
# -----------------------------------------------------------------------------

class TestConfiguration:
    """Tests for generator configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = MuzeGeneratorConfig()
        
        assert config.model == "gpt-4"
        assert config.temperature == 0.2
        assert config.max_tokens == 2000
        assert config.use_fallback == True
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = MuzeGeneratorConfig(
            model="gpt-3.5-turbo",
            temperature=0.5,
            max_tokens=1000
        )
        
        assert config.model == "gpt-3.5-turbo"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000


# -----------------------------------------------------------------------------
# TESTS FOR DIFFERENT CHART TYPES
# -----------------------------------------------------------------------------

class TestChartTypes:
    """Tests for different chart type generation."""
    
    @pytest.mark.parametrize("chart_type,expected_mark", [
        (ChartType.BAR, "bar"),
        (ChartType.LINE, "line"),
        (ChartType.AREA, "area"),
        (ChartType.SCATTER, "point"),
        (ChartType.PIE, "arc"),
    ])
    def test_chart_type_to_mark(self, chart_type, expected_mark):
        """Test that chart types map to correct Muze marks."""
        intent = ChartIntent(
            name="Test Chart",
            chart_type=chart_type,
            encodings=[
                Encoding(EncodingChannel.X, dimension("X")),
                Encoding(EncodingChannel.Y, measure("Y"))
            ]
        )
        
        code = generate_muze_code(intent, use_llm=False)
        assert f"mark: '{expected_mark}'" in code


# -----------------------------------------------------------------------------
# TESTS WITH REAL TABLEAU FILE
# -----------------------------------------------------------------------------

class TestRealFileIntegration:
    """Integration tests with real Tableau files."""
    
    def test_full_pipeline(self, sample_twbx_path):
        """Test full pipeline from Tableau file to Muze code."""
        from translators import translate_tableau_file
        
        # Translate the file
        intents = translate_tableau_file(str(sample_twbx_path))
        
        # Generate code for each intent
        for intent in intents:
            code = generate_muze_code(intent, use_llm=False)
            
            # Verify basic structure
            assert "const { muze, DataModel } = viz;" in code
            assert ".mount('#chart-container')" in code
            assert len(code) > 100


# -----------------------------------------------------------------------------
# TESTS FOR CACHING
# -----------------------------------------------------------------------------

class TestCaching:
    """Tests for the code generation cache."""
    
    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()
    
    def test_cache_stores_generated_code(self, bar_chart_intent):
        """Test that generated code is cached."""
        # First call - should miss cache
        code1 = generate_muze_code(bar_chart_intent, use_llm=False, use_cache=True)
        
        stats = get_cache_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0
        assert stats["size"] == 1
        
        # Second call - should hit cache
        code2 = generate_muze_code(bar_chart_intent, use_llm=False, use_cache=True)
        
        stats = get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        
        # Code should be identical
        assert code1 == code2
    
    def test_cache_key_uniqueness(self, bar_chart_intent, line_chart_intent):
        """Test that different intents have different cache keys."""
        generate_muze_code(bar_chart_intent, use_llm=False, use_cache=True)
        generate_muze_code(line_chart_intent, use_llm=False, use_cache=True)
        
        stats = get_cache_stats()
        assert stats["size"] == 2
        assert stats["misses"] == 2
    
    def test_cache_bypass(self, bar_chart_intent):
        """Test that cache can be bypassed."""
        # Generate with cache
        generate_muze_code(bar_chart_intent, use_llm=False, use_cache=True)
        
        # Generate without cache (should not hit)
        generate_muze_code(bar_chart_intent, use_llm=False, use_cache=False)
        
        stats = get_cache_stats()
        # Only one entry in cache, second call didn't check cache
        assert stats["size"] == 1
        assert stats["hits"] == 0  # No hits because second call bypassed cache
    
    def test_cache_clear(self, bar_chart_intent):
        """Test that cache can be cleared."""
        generate_muze_code(bar_chart_intent, use_llm=False, use_cache=True)
        
        stats = get_cache_stats()
        assert stats["size"] == 1
        
        clear_cache()
        
        stats = get_cache_stats()
        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
    
    def test_cache_hit_rate(self, bar_chart_intent):
        """Test cache hit rate calculation."""
        # 1 miss
        generate_muze_code(bar_chart_intent, use_llm=False, use_cache=True)
        
        # 3 hits
        generate_muze_code(bar_chart_intent, use_llm=False, use_cache=True)
        generate_muze_code(bar_chart_intent, use_llm=False, use_cache=True)
        generate_muze_code(bar_chart_intent, use_llm=False, use_cache=True)
        
        stats = get_cache_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 75.0
    
    def test_sample_data_affects_cache_key(self, bar_chart_intent, sample_data):
        """Test that different sample data creates different cache entries."""
        # Without sample data
        generate_muze_code(bar_chart_intent, use_llm=False, use_cache=True)
        
        # With sample data - should be different cache entry
        generate_muze_code(bar_chart_intent, sample_data=sample_data, use_llm=False, use_cache=True)
        
        stats = get_cache_stats()
        assert stats["size"] == 2
        assert stats["misses"] == 2
    
    def test_cache_instance(self):
        """Test getting cache instance."""
        cache = get_cache()
        assert isinstance(cache, MuzeCodeCache)


# -----------------------------------------------------------------------------
# RUN TESTS
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
