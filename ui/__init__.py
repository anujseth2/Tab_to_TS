"""
UI Package - User Interface

=============================================================================
WHAT THIS PACKAGE DOES:
=============================================================================
This package provides the web-based user interface for Tab_to_TS.

1. streamlit_app.py - A web application built with Streamlit that allows users to:
                      • Upload a Tableau file (.twbx or .twb)
                      • See a preview of the worksheets found
                      • Select which worksheets to convert
                      • View the generated Muze visualization
                      • Download the generated HTML/JavaScript

=============================================================================
WHAT IS STREAMLIT?
=============================================================================
Streamlit is a Python library that makes it easy to create web apps.
Instead of writing HTML/CSS/JavaScript, you write Python code like:

    import streamlit as st
    
    st.title("My App")
    uploaded_file = st.file_uploader("Upload a file")
    st.button("Convert")

And Streamlit automatically creates a beautiful web interface!

=============================================================================
LAYER 6 (Part 2) of our architecture
=============================================================================
"""

# The Streamlit app is run directly, not imported
# To run: streamlit run ui/streamlit_app.py

# Expose the app path for convenience
from pathlib import Path
STREAMLIT_APP_PATH = Path(__file__).parent / "streamlit_app.py"
