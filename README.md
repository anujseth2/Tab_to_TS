# Tab_to_TS

**Tableau to Muze Visualization Converter**

A multi-layered tool for converting Tableau workbooks (.twbx) to Muze JavaScript visualizations.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: EXTRACTION (twbx/extractor, twbx/xml_parser)          │
│  • Unzip .twbx → Parse XML → Raw Tableau structures             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: TABLEAU MODEL (twbx/models)                           │
│  • TableauWorksheet, TableauDatasource representations          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: ABSTRACT VIZ MODEL (viz_model/schemas)                │
│  • ChartIntent, MeasureField, Encoding - Framework agnostic     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: TABLEAU → GENERIC TRANSLATOR                          │
│  (translators/tableau_to_generic)                               │
│  • Maps Tableau shelves/marks to generic encodings              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5: GENERIC → MUZE GENERATOR (translators/generic_to_muze)│
│  • LLM-powered Muze JavaScript code generation                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 6: RENDERING (muze/html_embed + ui/streamlit_app)        │
│  • HTML embedding + Streamlit interface                         │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Run the Streamlit app
streamlit run ui/streamlit_app.py

# Or use programmatically
python main.py path/to/workbook.twbx
```

## Project Structure

```
Tab_to_TS/
├── requirements.txt
├── README.md
├── main.py
├── twbx/                    # Layer 1 & 2
│   ├── extractor.py
│   ├── xml_parser.py
│   └── models.py
├── viz_model/               # Layer 3
│   └── schemas.py
├── translators/             # Layer 4 & 5
│   ├── tableau_to_generic.py
│   └── generic_to_muze.py
├── muze/                    # Layer 6 (part 1)
│   └── html_embed.py
├── ui/                      # Layer 6 (part 2)
│   └── streamlit_app.py
└── tests/
    └── sample_data/
```

## Development

Run tests:
```bash
pytest tests/ -v
```

## License

MIT
