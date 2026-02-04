"""
Tab_to_TS - Tableau to Muze Visualization Converter

=============================================================================
WHAT THIS FILE DOES:
=============================================================================
This is the main entry point (starting point) for the Tab_to_TS application.
When you run the program, this file is executed first.

It handles two ways to use the tool:
1. Command Line: python main.py my_dashboard.twbx
2. Web Interface: python main.py --ui (launches a browser-based interface)

=============================================================================
"""

# -----------------------------------------------------------------------------
# IMPORTS
# These are like "ingredients" we need from Python's library
# -----------------------------------------------------------------------------
import argparse    # Helps us read command-line arguments (what you type after "python main.py")
import sys         # Lets us interact with the system (like exiting the program)
from pathlib import Path  # Makes working with file paths easier and cleaner


def main():
    """
    Main function - This is where the program starts running.
    
    Think of this like a recipe:
    1. First, we read what the user wants to do (parse arguments)
    2. Then, we check if the input is valid (validation)
    3. Finally, we do the actual work (conversion)
    """
    
    # -------------------------------------------------------------------------
    # STEP 1: SET UP THE COMMAND-LINE INTERFACE
    # This defines what options the user can provide when running the program
    # -------------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Convert Tableau workbooks (.twbx) to Muze visualizations"
    )
    
    # The input file - the Tableau workbook the user wants to convert
    # Example: python main.py my_dashboard.twbx
    parser.add_argument(
        "input_file",
        type=str,
        nargs="?",  # This makes the argument optional (can be empty)
        help="Path to the .twbx file to convert"
    )
    
    # Output directory - where to save the generated Muze files
    # Example: python main.py my_dashboard.twbx -o ./output/
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output directory for generated files"
    )
    
    # UI flag - if provided, launches the web interface instead of command line
    # Example: python main.py --ui
    parser.add_argument(
        "--ui",
        action="store_true",  # This means: if --ui is present, set it to True
        help="Launch Streamlit UI instead of CLI"
    )
    
    # Actually read what the user typed
    args = parser.parse_args()
    
    # -------------------------------------------------------------------------
    # STEP 2: HANDLE WEB INTERFACE MODE
    # If user wants the web UI, we tell them how to launch it
    # -------------------------------------------------------------------------
    if args.ui:
        print("Streamlit UI not yet implemented.")
        print("When ready, use: streamlit run ui/streamlit_app.py")
        sys.exit(0)  # Exit with code 0 means "success, we're done"
    
    # -------------------------------------------------------------------------
    # STEP 3: VALIDATE THE INPUT
    # Make sure the user provided a valid file before we try to process it
    # -------------------------------------------------------------------------
    
    # Check: Did the user provide a file?
    if not args.input_file:
        print("No input file provided. Here's how to use this tool:\n")
        parser.print_help()  # Show the help message with all options
        sys.exit(1)  # Exit with code 1 means "something went wrong"
    
    # Convert the file path string to a Path object (easier to work with)
    input_path = Path(args.input_file)
    
    # Check: Does the file actually exist on the computer?
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        print("Please check the file path and try again.")
        sys.exit(1)
    
    # Check: Is it a valid Tableau file (.twbx or .twb)?
    # - .twbx = Packaged Workbook (a ZIP file containing .twb + data + images)
    # - .twb  = Workbook (just the XML definition, no embedded data)
    valid_extensions = [".twbx", ".twb"]
    if input_path.suffix.lower() not in valid_extensions:
        print(f"Error: Expected a .twbx or .twb file, but got: {input_path.suffix}")
        print("This tool works with Tableau Workbook (.twb) and Packaged Workbook (.twbx) files.")
        sys.exit(1)
    
    # Store the file type for later use in the pipeline
    is_packaged = input_path.suffix.lower() == ".twbx"
    
    # -------------------------------------------------------------------------
    # STEP 4: DO THE ACTUAL CONVERSION
    # This is where the magic happens (once we implement it!)
    # -------------------------------------------------------------------------
    file_type = "Packaged Workbook (.twbx)" if is_packaged else "Workbook (.twb)"
    print(f"Converting: {input_path}")
    print(f"File type: {file_type}")
    print("Conversion pipeline not yet implemented.")
    
    # TODO: The conversion pipeline will:
    # 1. Extract/Read the file:
    #    - For .twbx: Unzip the package and find the .twb inside
    #    - For .twb: Read the XML file directly
    # 2. Parse the Tableau XML to understand the visualizations
    # 3. Convert Tableau concepts to our generic format
    # 4. Generate Muze JavaScript code
    # 5. Create an HTML file that displays the visualization


# -----------------------------------------------------------------------------
# PROGRAM START POINT
# This is a Python convention - it means "only run main() if this file is 
# executed directly, not when it's imported by another file"
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
