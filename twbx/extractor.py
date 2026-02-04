"""
Tableau File Extractor

=============================================================================
WHAT THIS MODULE DOES:
=============================================================================
This module handles opening and extracting Tableau workbook files.

• .twbx files - These are actually ZIP archives! Inside you'll find:
                - A .twb file (the actual workbook definition in XML)
                - Data extracts (.hyper or .tde files)
                - Images and other resources
                
• .twb files  - These are plain XML files, no extraction needed.

=============================================================================
MAIN FUNCTION:
=============================================================================
extract_workbook(file_path) → Returns the XML content of the workbook

=============================================================================
"""

import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Tuple, Optional, Union, List
from dataclasses import dataclass


# -----------------------------------------------------------------------------
# DATA CLASSES
# These are simple containers to hold our extraction results
# -----------------------------------------------------------------------------

@dataclass
class ExtractionResult:
    """
    Container for the results of extracting a Tableau file.
    
    Attributes:
        twb_content: The raw XML content of the workbook (.twb)
        twb_path: Path to the .twb file (useful for debugging)
        temp_dir: If we extracted a .twbx, this is the temp directory
                  containing extracted files (caller should clean up!)
        data_sources: List of paths to any data extract files found (.hyper, .tde)
        is_packaged: True if the original file was a .twbx, False if .twb
    """
    twb_content: str
    twb_path: Path
    temp_dir: Optional[Path]
    data_sources: List[str]
    is_packaged: bool


# -----------------------------------------------------------------------------
# MAIN EXTRACTION FUNCTION
# -----------------------------------------------------------------------------

def extract_workbook(file_path: Union[str, Path]) -> ExtractionResult:
    """
    Extract a Tableau workbook from a .twbx or .twb file.
    
    This is the main function you'll use. It handles both file types
    automatically and returns the XML content ready for parsing.
    
    Args:
        file_path: Path to a .twbx or .twb file
        
    Returns:
        ExtractionResult containing the workbook XML and metadata
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file is not a valid Tableau file
        zipfile.BadZipFile: If the .twbx file is corrupted
        
    Example:
        result = extract_workbook("my_dashboard.twbx")
        print(result.twb_content)  # The XML content
        
        # Don't forget to clean up temp files when done!
        if result.temp_dir:
            cleanup_temp_dir(result.temp_dir)
    """
    # Convert to Path object for easier handling
    file_path = Path(file_path)
    
    # -------------------------------------------------------------------------
    # VALIDATION: Make sure the file exists and is a valid type
    # -------------------------------------------------------------------------
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_extension = file_path.suffix.lower()
    
    if file_extension not in [".twbx", ".twb"]:
        raise ValueError(
            f"Invalid file type: {file_extension}. "
            f"Expected .twbx or .twb file."
        )
    
    # -------------------------------------------------------------------------
    # EXTRACTION: Handle each file type appropriately
    # -------------------------------------------------------------------------
    if file_extension == ".twbx":
        return _extract_twbx(file_path)
    else:
        return _extract_twb(file_path)


# -----------------------------------------------------------------------------
# PRIVATE HELPER FUNCTIONS
# These do the actual work, but users should call extract_workbook() instead
# -----------------------------------------------------------------------------

def _extract_twbx(file_path: Path) -> ExtractionResult:
    """
    Extract a .twbx (packaged workbook) file.
    
    A .twbx file is a ZIP archive containing:
    - One .twb file (the workbook XML)
    - Zero or more data extract files (.hyper, .tde)
    - Possibly images and other resources
    
    We extract everything to a temporary directory and return the results.
    """
    # Create a temporary directory to extract files into
    # We use a prefix so it's easy to identify our temp folders
    temp_dir = Path(tempfile.mkdtemp(prefix="tab_to_ts_"))
    
    try:
        # Open the .twbx file as a ZIP archive
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Extract all contents to our temp directory
            zip_ref.extractall(temp_dir)
        
        # Find the .twb file inside the extracted contents
        # There should be exactly one .twb file
        twb_files = list(temp_dir.rglob("*.twb"))
        
        if len(twb_files) == 0:
            raise ValueError(
                f"No .twb file found inside {file_path}. "
                f"This may be a corrupted or invalid .twbx file."
            )
        
        if len(twb_files) > 1:
            # This is unusual but possible - we'll use the first one
            # and log a warning
            print(f"Warning: Found multiple .twb files in {file_path}. Using: {twb_files[0]}")
        
        twb_path = twb_files[0]
        
        # Read the XML content from the .twb file
        twb_content = twb_path.read_text(encoding='utf-8')
        
        # Find any data extract files (.hyper or .tde)
        # These contain the actual data used by the workbook
        data_sources = []
        data_sources.extend(temp_dir.rglob("*.hyper"))  # Newer format
        data_sources.extend(temp_dir.rglob("*.tde"))    # Older format
        data_sources = [str(ds) for ds in data_sources]  # Convert to strings
        
        return ExtractionResult(
            twb_content=twb_content,
            twb_path=twb_path,
            temp_dir=temp_dir,
            data_sources=data_sources,
            is_packaged=True
        )
        
    except zipfile.BadZipFile:
        # Clean up the temp directory if extraction failed
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise zipfile.BadZipFile(
            f"Could not open {file_path} as a ZIP file. "
            f"The file may be corrupted."
        )
    except Exception as e:
        # Clean up on any other error too
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def _extract_twb(file_path: Path) -> ExtractionResult:
    """
    Read a .twb (workbook) file directly.
    
    A .twb file is just an XML file, so we simply read its contents.
    No extraction or temp directory needed.
    """
    # Read the XML content directly
    twb_content = file_path.read_text(encoding='utf-8')
    
    return ExtractionResult(
        twb_content=twb_content,
        twb_path=file_path,
        temp_dir=None,  # No temp directory for .twb files
        data_sources=[],  # .twb files don't contain embedded data
        is_packaged=False
    )


# -----------------------------------------------------------------------------
# CLEANUP FUNCTION
# Important: Call this when you're done to avoid filling up disk space!
# -----------------------------------------------------------------------------

def cleanup_temp_dir(temp_dir: Union[Path, str, None]) -> None:
    """
    Clean up a temporary directory created during extraction.
    
    Always call this when you're done processing a .twbx file!
    It's safe to call even if temp_dir is None (will do nothing).
    
    Args:
        temp_dir: The temp_dir from an ExtractionResult, or None
        
    Example:
        result = extract_workbook("dashboard.twbx")
        try:
            # ... do your processing ...
        finally:
            cleanup_temp_dir(result.temp_dir)
    """
    if temp_dir is None:
        return
    
    temp_dir = Path(temp_dir)
    
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


# -----------------------------------------------------------------------------
# CONVENIENCE FUNCTION
# For when you just want the XML and don't care about cleanup
# -----------------------------------------------------------------------------

def get_workbook_xml(file_path: Union[str, Path]) -> str:
    """
    Simple convenience function that extracts and returns just the XML content.
    
    This handles cleanup automatically, but you won't have access to
    data extract files. Use extract_workbook() if you need those.
    
    Args:
        file_path: Path to a .twbx or .twb file
        
    Returns:
        The XML content of the workbook as a string
        
    Example:
        xml_content = get_workbook_xml("my_dashboard.twbx")
        # Now parse the XML...
    """
    result = extract_workbook(file_path)
    
    try:
        return result.twb_content
    finally:
        # Always clean up temp files
        cleanup_temp_dir(result.temp_dir)


# -----------------------------------------------------------------------------
# MODULE TEST
# This runs when you execute this file directly: python extractor.py
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("Tableau Extractor Module")
    print("=" * 50)
    print("\nThis module provides functions to extract Tableau files:")
    print("  • extract_workbook(path) - Full extraction with metadata")
    print("  • get_workbook_xml(path) - Quick extraction, just the XML")
    print("  • cleanup_temp_dir(dir)  - Clean up temporary files")
    print("\nRun the tests with: pytest tests/test_extractor.py -v")
