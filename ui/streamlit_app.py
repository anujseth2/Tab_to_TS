"""
Tab_to_TS Streamlit Application

=============================================================================
WHAT THIS APP DOES:
=============================================================================
This is the main user interface for Tab_to_TS - Tableau to ThoughtSpot
Liveboard converter. It provides a web-based interface where users can:

1. Upload a Tableau workbook (.twbx or .twb)
2. See the worksheets found in the workbook
3. Select which worksheets to convert
4. View the generated Muze visualization preview
5. Copy/download the separate HTML, CSS, and JavaScript code blocks

=============================================================================
HOW TO RUN:
=============================================================================
From the project root directory:

    PYTHONPATH=/path/to/Tab_to_TS streamlit run ui/streamlit_app.py

=============================================================================
"""

import streamlit as st
import streamlit.components.v1 as components
import sys
import os
import time
from pathlib import Path
import tempfile
import json

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import our modules
from twbx import get_workbook_xml, parse_workbook, get_workbook_summary
from translators import translate_workbook, generate_muze_code, get_cache_stats, clear_cache
from translators.generic_to_muze import MuzeCodeOutput
from viz_model import get_chart_intent_summary


# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Tab_to_TS - Tableau to ThoughtSpot Converter",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# -----------------------------------------------------------------------------
# CUSTOM STYLING
# -----------------------------------------------------------------------------

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 16px;
        margin: 16px 0;
    }
    
    .info-box {
        background-color: #e7f3ff;
        border: 1px solid #b3d9ff;
        border-radius: 8px;
        padding: 16px;
        margin: 16px 0;
    }
    
    .code-section {
        background: #1e1e1e;
        border-radius: 8px;
        margin: 8px 0;
    }
    
    .code-header {
        background: #2d2d2d;
        padding: 8px 16px;
        border-radius: 8px 8px 0 0;
        color: #e0e0e0;
        font-weight: 600;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .copy-hint {
        font-size: 0.8rem;
        color: #888;
        font-style: italic;
    }
    
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 20px;
        color: white;
        text-align: center;
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
    }
    
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------

if 'workbook' not in st.session_state:
    st.session_state.workbook = None
if 'intents' not in st.session_state:
    st.session_state.intents = []
if 'generated_outputs' not in st.session_state:
    st.session_state.generated_outputs = {}
if 'uploaded_filename' not in st.session_state:
    st.session_state.uploaded_filename = None


# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## ⚙️ Settings")
    
    # Generation settings
    st.markdown("### Generation")
    
    use_llm = st.checkbox(
        "🤖 Use LLM (GPT-4)",
        value=True,
        help="Use OpenAI GPT-4 for intelligent code generation. Handles complex chart configurations automatically."
    )
    
    if use_llm:
        # Check if API key is set (Streamlit secrets or env var)
        api_key = None
        try:
            api_key = st.secrets.get("OPENAI_API_KEY")
            if api_key:
                # Set as env var so generate_muze_code can use it
                os.environ["OPENAI_API_KEY"] = api_key
        except Exception:
            pass
        
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
        
        if api_key:
            st.success("✅ OpenAI API key found")
        else:
            st.warning("⚠️ Set OPENAI_API_KEY in secrets or environment")
    
    sample_rows = st.slider(
        "Sample Data Rows",
        min_value=5,
        max_value=50,
        value=20,
        step=5,
        help="Number of sample data rows to generate for preview"
    )
    
    use_cache = st.checkbox(
        "Use Cache",
        value=True,
        help="Cache generated code to avoid redundant API calls."
    )
    
    # Display settings
    st.markdown("### Display")
    chart_height = st.slider(
        "Chart Height (px)",
        min_value=300,
        max_value=800,
        value=500,
        step=50
    )
    
    # Cache stats
    st.markdown("### 📊 Cache Stats")
    stats = get_cache_stats()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Cached", stats['size'])
    with col2:
        st.metric("Hit Rate", f"{stats['hit_rate_percent']}%")
    
    if st.button("Clear Cache"):
        clear_cache()
        st.success("Cache cleared!")
        st.rerun()
    
    # About
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    **Tab_to_TS** converts Tableau workbooks 
    to ThoughtSpot Liveboards using Muze.
    
    Output: Separate HTML, CSS, and JavaScript
    code blocks for Muze Studio ingestion.
    """)


# -----------------------------------------------------------------------------
# MAIN CONTENT
# -----------------------------------------------------------------------------

# Header
st.markdown('<p class="main-header">📊 Tab_to_TS</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Convert Tableau Workbooks to ThoughtSpot Liveboards (Muze)</p>', unsafe_allow_html=True)

# File uploader
st.markdown("### 1️⃣ Upload Tableau Workbook")

uploaded_file = st.file_uploader(
    "Choose a .twbx or .twb file",
    type=['twbx', 'twb'],
    help="Upload a Tableau Packaged Workbook (.twbx) or Workbook (.twb) file"
)

if uploaded_file is not None:
    # Check if it's a new file
    if uploaded_file.name != st.session_state.uploaded_filename:
        st.session_state.uploaded_filename = uploaded_file.name
        st.session_state.workbook = None
        st.session_state.intents = []
        st.session_state.generated_outputs = {}
        
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        # Parse the workbook
        with st.spinner("Parsing Tableau workbook..."):
            try:
                xml_content = get_workbook_xml(tmp_path)
                st.session_state.workbook = parse_workbook(xml_content)
                st.session_state.intents = translate_workbook(st.session_state.workbook)
                st.success(f"✅ Successfully parsed: **{uploaded_file.name}**")
            except Exception as e:
                st.error(f"❌ Error parsing file: {str(e)}")
                st.session_state.workbook = None
    
    # Display workbook info
    if st.session_state.workbook is not None:
        workbook = st.session_state.workbook
        
        st.markdown("### 2️⃣ Workbook Overview")
        
        # Stats row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Worksheets", len(workbook.worksheets))
        with col2:
            st.metric("Datasources", len(workbook.datasources))
        with col3:
            st.metric("Parameters", len(workbook.parameters))
        with col4:
            st.metric("Version", workbook.version or "Unknown")
        
        # Expandable workbook details
        with st.expander("📋 Workbook Details", expanded=False):
            st.text(get_workbook_summary(workbook))
        
        # Worksheet selection
        st.markdown("### 3️⃣ Select Worksheets to Convert")
        
        if len(st.session_state.intents) == 0:
            st.warning("No worksheets found in this workbook.")
        else:
            # Create tabs for each worksheet
            worksheet_names = [intent.name for intent in st.session_state.intents]
            tabs = st.tabs(worksheet_names)
            
            for i, (tab, intent) in enumerate(zip(tabs, st.session_state.intents)):
                with tab:
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.markdown("#### Chart Details")
                        st.markdown(f"""
                        - **Chart Type:** `{intent.chart_type.value}`
                        - **Orientation:** `{intent.orientation}`
                        - **Encodings:** {len(intent.encodings)}
                        - **Filters:** {len(intent.filters)}
                        """)
                        
                        # Show encodings
                        st.markdown("**Encodings:**")
                        for enc in intent.encodings:
                            role_icon = "📊" if enc.field.is_measure else "🏷️"
                            st.markdown(f"- {enc.channel.value}: `{enc.field.display_name}` {role_icon}")
                    
                    with col2:
                        st.markdown("#### Actions")
                        
                        # Generate button
                        if st.button(f"🔄 Generate Muze Code", key=f"gen_{i}"):
                            spinner_msg = "Generating Muze code with LLM..." if use_llm else "Generating Muze code..."
                            with st.spinner(spinner_msg):
                                try:
                                    output = generate_muze_code(
                                        intent,
                                        use_cache=use_cache,
                                        use_llm=use_llm,
                                        row_count=sample_rows
                                    )
                                    st.session_state.generated_outputs[intent.name] = output
                                    source = "LLM (GPT-4)" if use_llm else "Template"
                                    st.success(f"✅ Code generated using {source}!")
                                except Exception as e:
                                    st.error(f"❌ Generation failed: {str(e)}")
                    
                    # Show generated code and preview
                    if intent.name in st.session_state.generated_outputs:
                        output: MuzeCodeOutput = st.session_state.generated_outputs[intent.name]
                        
                        st.markdown("---")
                        
                        # Code, Preview, and Data tabs
                        code_tab, preview_tab, data_tab, download_tab = st.tabs([
                            "📝 Code Blocks", 
                            "👁️ Preview", 
                            "📊 Sample Data",
                            "💾 Download"
                        ])
                        
                        with code_tab:
                            st.markdown("##### Separate code blocks for Muze Studio")
                            st.markdown('<p class="copy-hint">💡 Click the copy icon in each code block to copy to clipboard</p>', unsafe_allow_html=True)
                            
                            # HTML Block
                            st.markdown("**HTML**")
                            st.code(output.html, language="html")
                            
                            # CSS Block
                            st.markdown("**CSS**")
                            st.code(output.css, language="css")
                            
                            # JavaScript Block
                            st.markdown("**JavaScript**")
                            st.code(output.javascript, language="javascript")
                        
                        with preview_tab:
                            st.markdown("##### Live Preview")
                            
                            try:
                                # Use combined HTML for preview
                                preview_height = max(chart_height, 300)
                                preview_html = output.get_combined_html(height=preview_height)
                                # Add unique timestamp to force fresh render every time
                                unique_marker = f"<!-- render:{time.time()}:height:{preview_height} -->"
                                preview_html_with_marker = preview_html.replace(
                                    "</body>", 
                                    f"{unique_marker}</body>"
                                )
                                components.html(preview_html_with_marker, height=preview_height + 50, scrolling=False)
                            except Exception as e:
                                st.error(f"Preview error: {str(e)}")
                                st.info("The chart may still work when the code is used in Muze Studio.")
                        
                        with data_tab:
                            st.markdown("##### Generated Sample Data")
                            st.markdown(f"**Schema:** {len(output.schema)} fields | **Rows:** {len(output.sample_data)}")
                            
                            # Show schema
                            st.markdown("**Schema Definition:**")
                            st.json(output.schema)
                            
                            # Show sample data (as table if possible)
                            st.markdown("**Sample Data:**")
                            if output.sample_data:
                                st.dataframe(output.sample_data, use_container_width=True)
                        
                        with download_tab:
                            st.markdown("##### Download Options")
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.download_button(
                                    label="📥 Download HTML",
                                    data=output.html,
                                    file_name=f"{intent.name.replace(' ', '_')}_html.html",
                                    mime="text/html"
                                )
                            
                            with col2:
                                st.download_button(
                                    label="📥 Download CSS",
                                    data=output.css,
                                    file_name=f"{intent.name.replace(' ', '_')}_styles.css",
                                    mime="text/css"
                                )
                            
                            with col3:
                                st.download_button(
                                    label="📥 Download JavaScript",
                                    data=output.javascript,
                                    file_name=f"{intent.name.replace(' ', '_')}_chart.js",
                                    mime="text/javascript"
                                )
                            
                            st.markdown("---")
                            
                            # Combined HTML download
                            st.download_button(
                                label="📥 Download Complete HTML (for testing)",
                                data=output.get_combined_html(),
                                file_name=f"{intent.name.replace(' ', '_')}_complete.html",
                                mime="text/html",
                                help="Downloads a complete HTML file that can be opened directly in a browser"
                            )
                            
                            # JSON export with all data
                            export_data = {
                                "chart_name": intent.name,
                                "chart_type": intent.chart_type.value,
                                "html": output.html,
                                "css": output.css,
                                "javascript": output.javascript,
                                "schema": output.schema,
                                "sample_data": output.sample_data
                            }
                            st.download_button(
                                label="📥 Download JSON (all data)",
                                data=json.dumps(export_data, indent=2),
                                file_name=f"{intent.name.replace(' ', '_')}_export.json",
                                mime="application/json",
                                help="Downloads all code blocks and data in JSON format"
                            )

else:
    # No file uploaded - show instructions
    st.markdown("""
    <div class="info-box">
        <h4>👋 Welcome to Tab_to_TS!</h4>
        <p>Convert your Tableau workbooks to ThoughtSpot Liveboards using Muze visualizations.</p>
        <p>To get started:</p>
        <ol>
            <li>Upload a Tableau workbook file (.twbx or .twb) using the uploader above</li>
            <li>Review the worksheets found in your workbook</li>
            <li>Click "Generate Muze Code" for each worksheet you want to convert</li>
            <li>Preview the visualization with generated sample data</li>
            <li>Copy the separate HTML, CSS, and JavaScript blocks to Muze Studio</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    
    # Demo section
    st.markdown("### 🎯 How It Works")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        #### 1. Extract
        Upload your Tableau workbook. We'll parse:
        - Worksheets
        - Datasources
        - Encodings
        - Mark types
        """)
    
    with col2:
        st.markdown("""
        #### 2. Translate
        Convert Tableau concepts:
        - Rows → Y-axis
        - Columns → X-axis
        - Marks → Chart type
        """)
    
    with col3:
        st.markdown("""
        #### 3. Generate
        Create Muze code:
        - HTML container
        - CSS styling
        - JavaScript chart
        - Sample data
        """)
    
    with col4:
        st.markdown("""
        #### 4. Export
        Get separate blocks:
        - Copy to Muze Studio
        - Download files
        - JSON export
        """)


# -----------------------------------------------------------------------------
# FOOTER
# -----------------------------------------------------------------------------

st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #888; font-size: 0.9rem;'>"
    "Tab_to_TS v0.2.0 | Tableau to ThoughtSpot Converter | "
    "<a href='https://muze-studio.vercel.app/' target='_blank'>Muze Studio</a>"
    "</p>",
    unsafe_allow_html=True
)
