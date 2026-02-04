"""
Generic to Muze Generator (LLM-Powered)

=============================================================================
WHAT THIS MODULE DOES:
=============================================================================
This module takes a ChartIntent (our generic visualization description) and
generates Muze code using an LLM (Large Language Model).

The LLM approach is used because:
- Many possible combinations of chart types, encodings, layers
- Handles edge cases like labels, stacking, orientations
- Adapts to Muze API nuances automatically

Output Format:
- HTML: The container structure
- CSS: Styling for the chart
- JavaScript: The Muze visualization code (LLM-generated)

=============================================================================
"""

import os
import json
import hashlib
import random
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from viz_model import (
    ChartIntent,
    ChartType,
    AggregationType,
    EncodingChannel,
    Field,
    Encoding,
    FieldRole,
    get_chart_intent_summary
)

# Try to import OpenAI - gracefully handle if not installed
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None


# -----------------------------------------------------------------------------
# MUZE DOCUMENTATION FOR LLM CONTEXT
# This comprehensive documentation helps the LLM generate correct Muze code
# -----------------------------------------------------------------------------

MUZE_DOCUMENTATION = '''
# Muze JavaScript Library Documentation (v2.0 - WebAssembly)

## Overview
Muze is a composable visualization library that uses a grammar-based approach.
It creates visualizations by composing layers, encoding data to visual properties.
Muze 2.0 uses WebAssembly and requires async/await patterns.

## Basic Structure (IMPORTANT - Async Pattern)

```javascript
(async function() {
    // Initialize Muze environment
    const env = await muze();
    const DataModel = await muze.DataModel.onReady();
    
    // Define schema
    const schema = [
        { name: 'Category', type: 'dimension' },
        { name: 'Sales', type: 'measure', defAggFn: 'sum' }
    ];
    
    // Define data
    const data = [
        { Category: 'A', Sales: 100 },
        { Category: 'B', Sales: 200 }
    ];
    
    // Create DataModel
    const formattedData = await DataModel.loadData(data, schema);
    const dm = new DataModel(formattedData);
    
    // Create visualization
    const canvas = env.canvas();
    canvas
        .data(dm)
        .rows(['Sales'])        // Y-axis fields (measures typically)
        .columns(['Category'])  // X-axis fields (dimensions typically)
        .layers([{ mark: 'bar' }])
        .title('Sales by Category')
        .mount('#chart-container');
})();
```

## Key Methods

### .data(dataModel)
Sets the DataModel for the visualization.

### .rows(fields)
Array of field names for the Y-axis / rows.
- For vertical bar charts: put measures here
- For horizontal bar charts: put dimensions here
Example: `.rows(['Sales'])` or `.rows(['Category'])`

### .columns(fields)
Array of field names for the X-axis / columns.
- For vertical bar charts: put dimensions here
- For horizontal bar charts: put measures here
Example: `.columns(['Category', 'Region'])`

### .color(field)
Field for color encoding. Creates colored/grouped marks.
Example: `.color('Region')`

### .size(field)
Field for size encoding (mainly for scatter plots).
Example: `.size('Profit')`

### .detail(fields)
Array of fields for additional detail (creates more marks without visual encoding).
Example: `.detail(['Customer ID'])`

### .layers(layerConfig)
Define visualization layers (marks). This is where you specify chart type.

Available marks: 'bar', 'line', 'point', 'area', 'arc', 'text', 'tick'

**Simple layer:**
```javascript
.layers([{ mark: 'bar' }])
```

**Line chart with points and labels:**
```javascript
.layers([
    { mark: 'line' },
    { mark: 'point' },
    { 
        mark: 'text',
        encoding: {
            text: { field: 'Sales' }
        }
    }
])
```

**Stacked bar chart:**
```javascript
.layers([{
    mark: 'bar',
    transform: { type: 'stack' }
}])
```

### .config(options)
Configuration options for the chart including axes, legend, etc.

```javascript
.config({
    axes: {
        x: { 
            name: 'Category',
            tickFormat: (v) => v.substring(0, 10)  // Truncate long labels
        },
        y: { 
            name: 'Sales ($)',
            tickFormat: (v) => '$' + v.toLocaleString()
        }
    },
    legend: {
        color: { show: true, position: 'right' }
    },
    interaction: {
        tooltip: { enable: true }
    }
})
```

### .title(text, config)
Set chart title.
Example: `.title('Sales by Category', { align: 'center' })`

### .mount(selector)
Mount the chart to a DOM element. Always call last.
Example: `.mount('#chart-container')`

## Chart Type Examples

### Bar Chart (Vertical)
```javascript
canvas
    .data(dm)
    .rows(['Sales'])      // Measure on Y
    .columns(['Category']) // Dimension on X
    .layers([{ mark: 'bar' }])
    .mount('#chart-container');
```

### Bar Chart (Horizontal)
```javascript
canvas
    .data(dm)
    .rows(['Category'])    // Dimension on Y
    .columns(['Sales'])    // Measure on X
    .layers([{ mark: 'bar' }])
    .mount('#chart-container');
```

### Line Chart with Data Labels
```javascript
canvas
    .data(dm)
    .rows(['Sales'])
    .columns(['Month'])
    .layers([
        { mark: 'line' },
        { mark: 'point' },
        { mark: 'text', encoding: { text: { field: 'Sales' } } }
    ])
    .mount('#chart-container');
```

### Scatter Plot
```javascript
canvas
    .data(dm)
    .rows(['Profit'])
    .columns(['Sales'])
    .color('Category')
    .size('Quantity')
    .layers([{ mark: 'point' }])
    .mount('#chart-container');
```

### Grouped Bar Chart
```javascript
canvas
    .data(dm)
    .rows(['Sales'])
    .columns(['Category'])
    .color('Region')  // Creates groups
    .layers([{ mark: 'bar' }])
    .mount('#chart-container');
```

### Stacked Bar Chart
```javascript
canvas
    .data(dm)
    .rows(['Sales'])
    .columns(['Category'])
    .color('Region')
    .layers([{
        mark: 'bar',
        transform: { type: 'stack' }
    }])
    .mount('#chart-container');
```

### Area Chart
```javascript
canvas
    .data(dm)
    .rows(['Sales'])
    .columns(['Date'])
    .layers([{ mark: 'area' }])
    .mount('#chart-container');
```

### Pie/Donut Chart
```javascript
canvas
    .data(dm)
    .rows(['Sales'])
    .columns(['Category'])
    .layers([{ mark: 'arc' }])
    .config({
        // For donut, add innerRadius
    })
    .mount('#chart-container');
```

## Schema Definition

Each field in the schema needs:
- `name`: Field name (string) - must match data keys exactly
- `type`: Either 'dimension' or 'measure'
- `defAggFn`: Default aggregation for measures ('sum', 'avg', 'count', 'min', 'max')

```javascript
const schema = [
    { name: 'Region', type: 'dimension' },
    { name: 'Category', type: 'dimension' },
    { name: 'Sales', type: 'measure', defAggFn: 'sum' },
    { name: 'Profit', type: 'measure', defAggFn: 'sum' }
];
```

## Important Notes

1. **Async Required**: Always wrap in async IIFE: `(async function() { ... })();`
2. **DataModel Loading**: Use `await DataModel.loadData(data, schema)` before `new DataModel()`
3. **Field Names**: Must match exactly between schema, data, and chart methods
4. **Mount Last**: Always call `.mount()` as the final method
5. **Measures on Rows**: For typical vertical charts, put measures on rows (Y-axis)
6. **Labels**: Add a text layer for data labels on charts
'''


# -----------------------------------------------------------------------------
# OUTPUT DATA STRUCTURE
# Separate code blocks for Muze Studio
# -----------------------------------------------------------------------------

@dataclass
class MuzeCodeOutput:
    """
    Output structure containing separate HTML, CSS, and JavaScript blocks.
    
    This format is designed for ThoughtSpot Muze Studio ingestion.
    """
    html: str
    css: str
    javascript: str
    sample_data: List[Dict[str, Any]] = field(default_factory=list)
    schema: List[Dict[str, str]] = field(default_factory=list)
    
    def get_combined_html(self, height: int = 500) -> str:
        """Get a combined HTML page for preview purposes."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Muze Visualization Preview</title>
    <link href="https://cdn.jsdelivr.net/npm/@chartshq/muze@2.0.0/dist/muze.css" rel="stylesheet">
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: {height}px !important;
            min-height: {height}px !important;
            background: #fafafa;
            overflow: hidden;
        }}
        #chart-container {{
            width: 100%;
            height: {height}px !important;
            min-height: {height}px !important;
            padding: 16px;
            box-sizing: border-box;
            background: white;
        }}
        /* Force Muze canvas to fill container */
        .muze-canvas-container,
        .muze-canvas-container > div,
        .muze-layout-container {{
            width: 100% !important;
            height: 100% !important;
        }}
        .loading {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #666;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        .error {{
            color: #dc3545;
            padding: 20px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div id="chart-container">
        <div class="loading" id="loading-msg">Loading Muze visualization...</div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/@chartshq/muze@2.0.0/dist/muze.js"></script>
    <script>
{self.javascript}
    </script>
</body>
</html>"""


# -----------------------------------------------------------------------------
# SAMPLE DATA GENERATION
# -----------------------------------------------------------------------------

SAMPLE_DIMENSION_VALUES = {
    "category": ["Electronics", "Furniture", "Office Supplies", "Technology", "Clothing"],
    "sub-category": ["Phones", "Chairs", "Storage", "Tables", "Binders", "Machines", "Accessories"],
    "region": ["North", "South", "East", "West", "Central"],
    "segment": ["Consumer", "Corporate", "Home Office", "Enterprise"],
    "product": ["Product A", "Product B", "Product C", "Product D", "Product E"],
    "city": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
    "state": ["California", "Texas", "Florida", "New York", "Illinois"],
    "country": ["USA", "Canada", "UK", "Germany", "France"],
    "month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "quarter": ["Q1", "Q2", "Q3", "Q4"],
    "year": ["2021", "2022", "2023", "2024"],
    "ship mode": ["Standard Class", "Second Class", "First Class", "Same Day"],
    "order priority": ["Low", "Medium", "High", "Critical"],
    "default": ["Category A", "Category B", "Category C", "Category D", "Category E"]
}

MEASURE_KEYWORDS = ["sales", "profit", "revenue", "cost", "price", "quantity", "amount",
                   "discount", "margin", "total", "sum", "avg", "count", "value", "rate"]
BIN_KEYWORDS = ["bin", "bucket", "range", "group"]


def _is_bin_field(field_name: str) -> bool:
    name_lower = field_name.lower()
    return any(kw in name_lower for kw in BIN_KEYWORDS)


def _is_measure_like(field_name: str) -> bool:
    name_lower = field_name.lower()
    return any(kw in name_lower for kw in MEASURE_KEYWORDS)


def _get_dimension_values(field_name: str, count: int = 5) -> List[str]:
    name_lower = field_name.lower()
    
    if _is_bin_field(field_name):
        if _is_measure_like(field_name):
            step = 1000
            return [f"{i*step}-{(i+1)*step}" for i in range(count)]
        else:
            return [f"Bin {i+1}" for i in range(count)]
    
    for key, values in SAMPLE_DIMENSION_VALUES.items():
        if key in name_lower:
            return values[:count]
    
    if any(kw in name_lower for kw in ["date", "time", "day", "week"]):
        return ["2023-01", "2023-02", "2023-03", "2023-04", "2023-05"][:count]
    
    return [f"{field_name} {i+1}" for i in range(count)]


def _get_measure_value(field_name: str) -> float:
    name_lower = field_name.lower()
    
    if "price" in name_lower or "cost" in name_lower:
        return round(random.uniform(10, 500), 2)
    elif "quantity" in name_lower or "count" in name_lower:
        return random.randint(1, 100)
    elif "profit" in name_lower:
        return round(random.uniform(-100, 500), 2)
    elif "percent" in name_lower or "rate" in name_lower:
        return round(random.uniform(0, 100), 2)
    elif "sales" in name_lower or "revenue" in name_lower:
        return round(random.uniform(100, 10000), 2)
    else:
        return round(random.uniform(50, 1000), 2)


def generate_sample_data(intent: ChartIntent, row_count: int = 20) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """Generate sample data based on the ChartIntent's fields."""
    dimensions = {}
    measures = {}
    bins = {}
    
    for enc in intent.encodings:
        f = enc.field
        field_name = f.name
        
        if field_name in dimensions or field_name in measures or field_name in bins:
            continue
        
        if _is_bin_field(field_name):
            bins[field_name] = f
        elif f.is_measure:
            measures[field_name] = f
        elif _is_measure_like(field_name) and not _is_bin_field(field_name):
            measures[field_name] = f
        else:
            dimensions[field_name] = f
    
    schema = []
    for name in dimensions:
        schema.append({"name": name, "type": "dimension"})
    for name in bins:
        schema.append({"name": name, "type": "dimension"})
    for name, f in measures.items():
        agg = f.aggregation.value if f.aggregation != AggregationType.NONE else "sum"
        schema.append({"name": name, "type": "measure", "defAggFn": agg})
    
    dim_values = {name: _get_dimension_values(name) for name in dimensions}
    bin_values = {name: _get_dimension_values(name) for name in bins}
    
    data = []
    all_categorical = {**dimensions, **bins}
    
    if all_categorical:
        cat_names = list(all_categorical.keys())
        all_cat_values = {**dim_values, **bin_values}
        
        for i in range(row_count):
            row = {}
            for cat_name in cat_names:
                values = all_cat_values[cat_name]
                row[cat_name] = values[i % len(values)]
            for measure_name in measures:
                row[measure_name] = _get_measure_value(measure_name)
            data.append(row)
    else:
        for i in range(row_count):
            row = {measure_name: _get_measure_value(measure_name) for measure_name in measures}
            data.append(row)
    
    return data, schema


# -----------------------------------------------------------------------------
# LLM-BASED CODE GENERATION
# -----------------------------------------------------------------------------

@dataclass
class LLMConfig:
    """Configuration for LLM-based code generation."""
    model: str = "gpt-4"
    temperature: float = 0.2
    max_tokens: int = 3000
    api_key: Optional[str] = None


def _build_llm_prompt(
    intent: ChartIntent,
    sample_data: List[Dict[str, Any]],
    schema: List[Dict[str, str]]
) -> str:
    """Build the prompt for the LLM to generate Muze JavaScript code."""
    
    # Build encoding description
    encodings_desc = []
    for enc in intent.encodings:
        channel = enc.channel.value.upper()
        role = "measure" if enc.field.is_measure else "dimension"
        agg = f" ({enc.field.aggregation.value})" if enc.field.is_measure and enc.field.aggregation != AggregationType.NONE else ""
        encodings_desc.append(f"  - {channel}: {enc.field.name} [{role}{agg}]")
    
    encodings_text = "\n".join(encodings_desc) if encodings_desc else "  (no encodings)"
    
    # Show sample data
    sample_preview = json.dumps(sample_data[:5], indent=2)
    schema_json = json.dumps(schema, indent=2)
    
    # Check for labels
    has_labels = any(enc.channel == EncodingChannel.LABEL for enc in intent.encodings)
    label_fields = [enc.field.name for enc in intent.encodings if enc.channel == EncodingChannel.LABEL]
    label_fields_str = ", ".join(label_fields) if label_fields else "None"
    
    prompt = f"""Generate Muze JavaScript code for the following visualization.

## Chart Specification
- **Name**: {intent.name}
- **Chart Type**: {intent.chart_type.value}
- **Orientation**: {intent.orientation}
- **Stacked**: {intent.stacked}
- **Show Labels**: {has_labels or intent.show_labels}
- **Label Fields**: {label_fields_str}
- **Title**: {intent.title or intent.name}

## Encodings (field → visual channel)
{encodings_text}

## Schema Definition
```json
{schema_json}
```

## Sample Data (first 5 rows of {len(sample_data)} total)
```json
{sample_preview}
```

## Requirements
1. Generate COMPLETE, EXECUTABLE Muze JavaScript code
2. Use the async pattern: `(async function() {{ ... }})();`
3. Include proper error handling with try-catch
4. Use the EXACT field names from the schema
5. Add a text layer for data labels if Show Labels is true
6. For line charts, add point markers AND text labels for values
7. Mount to '#chart-container'
8. Include a loading message hide function

## Output Format
Return ONLY the JavaScript code. No markdown, no explanations.
Start with: (async function() {{
"""
    
    return prompt


def _generate_with_llm(
    intent: ChartIntent,
    sample_data: List[Dict[str, Any]],
    schema: List[Dict[str, str]],
    config: Optional[LLMConfig] = None
) -> str:
    """Generate Muze JavaScript code using OpenAI LLM."""
    
    if not OPENAI_AVAILABLE:
        raise RuntimeError("OpenAI package not installed. Install with: pip install openai")
    
    config = config or LLMConfig()
    api_key = config.api_key or os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        raise RuntimeError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
    
    # Build prompt
    user_prompt = _build_llm_prompt(intent, sample_data, schema)
    
    # Create client and make request
    client = OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model=config.model,
        messages=[
            {
                "role": "system",
                "content": f"""You are an expert in the Muze JavaScript visualization library.
Your task is to generate clean, working Muze code based on chart specifications.

{MUZE_DOCUMENTATION}

IMPORTANT RULES:
1. Always use async/await pattern with IIFE
2. Always include error handling
3. For line charts, add point markers and text labels
4. Use exact field names from the provided schema
5. Return ONLY JavaScript code, no markdown formatting"""
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=config.temperature,
        max_tokens=config.max_tokens
    )
    
    code = response.choices[0].message.content
    
    # Clean up code (remove markdown if present)
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        lines = lines[1:]  # Remove opening ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # Remove closing ```
        code = "\n".join(lines)
    
    return code


# -----------------------------------------------------------------------------
# TEMPLATE-BASED FALLBACK
# Used when LLM is unavailable
# -----------------------------------------------------------------------------

def _generate_with_template(
    intent: ChartIntent,
    sample_data: List[Dict[str, Any]],
    schema: List[Dict[str, str]]
) -> str:
    """Generate Muze code using templates (fallback when LLM unavailable)."""
    
    rows_fields = []
    cols_fields = []
    color_field = None
    size_field = None
    label_field = None
    
    for enc in intent.encodings:
        field_name = enc.field.name
        if enc.channel == EncodingChannel.X:
            cols_fields.append(field_name)
        elif enc.channel == EncodingChannel.Y:
            rows_fields.append(field_name)
        elif enc.channel == EncodingChannel.COLOR:
            color_field = field_name
        elif enc.channel == EncodingChannel.SIZE:
            size_field = field_name
        elif enc.channel == EncodingChannel.LABEL:
            label_field = field_name
    
    # Determine mark type
    mark_mapping = {
        ChartType.BAR: "bar",
        ChartType.BAR_HORIZONTAL: "bar",
        ChartType.LINE: "line",
        ChartType.AREA: "area",
        ChartType.SCATTER: "point",
        ChartType.PIE: "arc",
        ChartType.TEXT: "text",
    }
    mark = mark_mapping.get(intent.chart_type, "bar")
    
    data_str = json.dumps(sample_data, indent=2)
    schema_str = json.dumps(schema, indent=2)
    title = intent.title or intent.name
    
    # Build layers
    # Determine if we need labels
    show_labels = intent.show_labels or label_field is not None
    # Use explicit label field, or fall back to first measure (Y field)
    text_field = label_field or (rows_fields[0] if rows_fields else None)
    
    if intent.chart_type == ChartType.LINE:
        if show_labels and text_field:
            layers_str = f"""[
            {{ mark: 'line' }},
            {{ mark: 'point' }},
            {{ mark: 'text', encoding: {{ text: {{ field: '{text_field}' }} }} }}
        ]"""
        else:
            layers_str = """[
            { mark: 'line' },
            { mark: 'point' }
        ]"""
    elif show_labels and text_field:
        # Add text layer for labels on bar, area, scatter, etc.
        layers_str = f"""[
            {{ mark: '{mark}' }},
            {{ mark: 'text', encoding: {{ text: {{ field: '{text_field}' }} }} }}
        ]"""
    else:
        layers_str = f"[{{ mark: '{mark}' }}]"
    
    code = f"""(async function() {{
    try {{
        const hideLoading = () => {{
            const el = document.getElementById('loading-msg');
            if (el) el.style.display = 'none';
        }};
        
        const env = await muze();
        const DataModel = await muze.DataModel.onReady();
        
        const schema = {schema_str};
        const data = {data_str};
        
        const formattedData = await DataModel.loadData(data, schema);
        const dm = new DataModel(formattedData);
        
        hideLoading();
        
        const canvas = env.canvas();
        canvas
            .data(dm)
            .rows({json.dumps(rows_fields)})
            .columns({json.dumps(cols_fields)})"""
    
    if color_field:
        code += f"\n            .color('{color_field}')"
    if size_field:
        code += f"\n            .size('{size_field}')"
    
    code += f"""
            .layers({layers_str})
            .title('{title}')
            .mount('#chart-container');
    }} catch (error) {{
        console.error('Muze error:', error);
        document.getElementById('chart-container').innerHTML = 
            '<div style=\"color:red;padding:20px;\">Error: ' + error.message + '</div>';
    }}
}})();"""
    
    return code


# -----------------------------------------------------------------------------
# CACHING LAYER
# -----------------------------------------------------------------------------

@dataclass
class CacheEntry:
    output: MuzeCodeOutput
    created_at: datetime
    source: str
    hit_count: int = 0


class MuzeCodeCache:
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def _create_cache_key(self, intent: ChartIntent, use_llm: bool) -> str:
        key_parts = [
            intent.name,
            intent.chart_type.value,
            intent.orientation,
            str(intent.stacked),
            str(intent.show_labels),
            str(use_llm),
        ]
        for enc in sorted(intent.encodings, key=lambda e: e.channel.value):
            key_parts.append(f"{enc.channel.value}:{enc.field.name}")
        return hashlib.sha256("|".join(key_parts).encode()).hexdigest()[:16]
    
    def get(self, intent: ChartIntent, use_llm: bool) -> Optional[MuzeCodeOutput]:
        key = self._create_cache_key(intent, use_llm)
        if key in self._cache:
            self._hits += 1
            self._cache[key].hit_count += 1
            return self._cache[key].output
        self._misses += 1
        return None
    
    def set(self, intent: ChartIntent, output: MuzeCodeOutput, use_llm: bool, source: str) -> None:
        if len(self._cache) >= self._max_size:
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
            del self._cache[oldest]
        key = self._create_cache_key(intent, use_llm)
        self._cache[key] = CacheEntry(output=output, created_at=datetime.now(), source=source)
    
    def clear(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(self._hits / total * 100, 1) if total > 0 else 0
        }


_code_cache = MuzeCodeCache()

def get_cache() -> MuzeCodeCache:
    return _code_cache

def clear_cache() -> None:
    _code_cache.clear()

def get_cache_stats() -> Dict[str, Any]:
    return _code_cache.get_stats()


# -----------------------------------------------------------------------------
# STATIC CODE GENERATION
# -----------------------------------------------------------------------------

def _generate_html() -> str:
    return """<div id="chart-container"></div>"""


def _generate_css() -> str:
    return """html, body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
}

#chart-container {
    width: 100%;
    height: 100%;
    min-height: 450px;
    padding: 10px;
    box-sizing: border-box;
}

.muze-chart {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.muze-canvas-container {
    width: 100% !important;
    height: 100% !important;
}"""


# -----------------------------------------------------------------------------
# MAIN GENERATION FUNCTION
# -----------------------------------------------------------------------------

def generate_muze_code(
    intent: ChartIntent,
    sample_data: Optional[List[Dict[str, Any]]] = None,
    use_cache: bool = True,
    use_llm: bool = True,
    row_count: int = 20,
    llm_config: Optional[LLMConfig] = None
) -> MuzeCodeOutput:
    """
    Generate Muze code from a ChartIntent.
    
    Uses LLM (GPT-4) by default for flexible, accurate code generation.
    Falls back to template-based generation if LLM fails.
    
    Args:
        intent: The ChartIntent describing the visualization
        sample_data: Optional pre-existing sample data
        use_cache: If True, check/populate cache
        use_llm: If True, use LLM for code generation (recommended)
        row_count: Number of sample data rows to generate
        llm_config: Optional LLM configuration
        
    Returns:
        MuzeCodeOutput containing separate HTML, CSS, and JavaScript
    """
    # Check cache
    if use_cache:
        cached = _code_cache.get(intent, use_llm)
        if cached is not None:
            return cached
    
    # Generate sample data if not provided
    if sample_data is None:
        sample_data, schema = generate_sample_data(intent, row_count)
    else:
        schema = []
        seen = set()
        for enc in intent.encodings:
            f = enc.field
            if f.name not in seen:
                seen.add(f.name)
                if f.is_dimension:
                    schema.append({"name": f.name, "type": "dimension"})
                else:
                    agg = f.aggregation.value if f.aggregation != AggregationType.NONE else "sum"
                    schema.append({"name": f.name, "type": "measure", "defAggFn": agg})
    
    # Generate JavaScript
    source = "template"
    if use_llm:
        try:
            javascript = _generate_with_llm(intent, sample_data, schema, llm_config)
            source = "llm"
        except Exception as e:
            print(f"LLM generation failed ({e}), falling back to template")
            javascript = _generate_with_template(intent, sample_data, schema)
    else:
        javascript = _generate_with_template(intent, sample_data, schema)
    
    # Create output
    output = MuzeCodeOutput(
        html=_generate_html(),
        css=_generate_css(),
        javascript=javascript,
        sample_data=sample_data,
        schema=schema
    )
    
    # Cache
    if use_cache:
        _code_cache.set(intent, output, use_llm, source)
    
    return output


def generate_muze_code_batch(
    intents: List[ChartIntent],
    use_cache: bool = True,
    use_llm: bool = True
) -> Dict[str, MuzeCodeOutput]:
    """Generate Muze code for multiple ChartIntents."""
    return {intent.name: generate_muze_code(intent, use_cache=use_cache, use_llm=use_llm) 
            for intent in intents}


# Legacy compatibility
def generate_muze_code_string(intent: ChartIntent, sample_data: Optional[List[Dict[str, Any]]] = None) -> str:
    return generate_muze_code(intent, sample_data).javascript


# -----------------------------------------------------------------------------
# MODULE INFO
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("Generic to Muze Generator (LLM-Powered)")
    print("=" * 50)
    print(f"\nOpenAI available: {OPENAI_AVAILABLE}")
    print("\nUsage:")
    print("  output = generate_muze_code(intent, use_llm=True)")
    print("  print(output.javascript)")
