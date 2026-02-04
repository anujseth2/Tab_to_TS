"""
Tests Package - Automated Testing

=============================================================================
WHAT THIS PACKAGE DOES:
=============================================================================
This package contains all the automated tests for Tab_to_TS.

Automated tests are like a "checklist" that the computer runs to make sure
everything is working correctly. They help us:
• Catch bugs early before users see them
• Make sure new changes don't break existing features
• Document how each module is supposed to work

=============================================================================
TEST FILES:
=============================================================================
• test_extractor.py        - Tests for extracting .twbx files
• test_xml_parser.py       - Tests for parsing Tableau XML
• test_schemas.py          - Tests for our data models
• test_tableau_to_generic.py - Tests for Tableau → ChartIntent conversion
• test_generic_to_muze.py  - Tests for ChartIntent → Muze code generation

=============================================================================
HOW TO RUN TESTS:
=============================================================================
From the project root directory, run:

    pytest tests/ -v

The -v flag means "verbose" - it shows more details about each test.

=============================================================================
SAMPLE DATA:
=============================================================================
The tests/sample_data/ folder contains sample Tableau files for testing.
These are real .twbx and .twb files that we use to verify our code works.
=============================================================================
"""

# Test discovery is automatic with pytest - no imports needed here
