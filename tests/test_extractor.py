"""
Tests for the Tableau Extractor Module

=============================================================================
HOW TO RUN THESE TESTS:
=============================================================================
From the project root directory (Tab_to_TS/), run:

    pytest tests/test_extractor.py -v

The -v flag shows verbose output with each test name and result.

=============================================================================
WHAT THESE TESTS VERIFY:
=============================================================================
1. Can we read a .twb file (plain XML)?
2. Can we extract a .twbx file (ZIP archive)?
3. Do we handle errors properly (missing files, invalid files)?
4. Is cleanup working correctly?
=============================================================================
"""

import pytest
import zipfile
import tempfile
from pathlib import Path

# Import the module we're testing
from twbx.extractor import (
    extract_workbook,
    get_workbook_xml,
    cleanup_temp_dir,
    ExtractionResult
)


# -----------------------------------------------------------------------------
# TEST FIXTURES
# Fixtures are reusable test data/setup that pytest manages for us
# -----------------------------------------------------------------------------

@pytest.fixture
def sample_twb_content():
    """
    A minimal valid Tableau workbook XML structure.
    This is what a real .twb file looks like (simplified).
    """
    return '''<?xml version='1.0' encoding='utf-8' ?>
<workbook source-build='2024.1.0' source-platform='win' version='18.1'>
  <preferences />
  <datasources>
    <datasource caption='Sample Data' name='federated.sample'>
      <connection class='federated' />
    </datasource>
  </datasources>
  <worksheets>
    <worksheet name='Sales Dashboard'>
      <table>
        <view />
      </table>
    </worksheet>
  </worksheets>
</workbook>
'''


@pytest.fixture
def sample_twb_file(sample_twb_content, tmp_path):
    """
    Creates a temporary .twb file for testing.
    
    tmp_path is a pytest fixture that provides a temporary directory
    that gets cleaned up automatically after the test.
    """
    twb_file = tmp_path / "test_workbook.twb"
    twb_file.write_text(sample_twb_content, encoding='utf-8')
    return twb_file


@pytest.fixture
def sample_twbx_file(sample_twb_content, tmp_path):
    """
    Creates a temporary .twbx file (ZIP containing a .twb) for testing.
    """
    # First create the .twb file
    twb_file = tmp_path / "test_workbook.twb"
    twb_file.write_text(sample_twb_content, encoding='utf-8')
    
    # Now create a .twbx file (which is just a ZIP)
    twbx_file = tmp_path / "test_workbook.twbx"
    
    with zipfile.ZipFile(twbx_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add the .twb file to the ZIP
        zf.write(twb_file, "test_workbook.twb")
    
    return twbx_file


@pytest.fixture
def sample_twbx_with_data(sample_twb_content, tmp_path):
    """
    Creates a .twbx file that also contains a fake data extract file.
    This simulates a real packaged workbook with embedded data.
    """
    # Create the .twb file
    twb_file = tmp_path / "test_workbook.twb"
    twb_file.write_text(sample_twb_content, encoding='utf-8')
    
    # Create a fake .hyper file (in reality these are database files)
    hyper_file = tmp_path / "Data" / "Extract.hyper"
    hyper_file.parent.mkdir(exist_ok=True)
    hyper_file.write_text("fake hyper data", encoding='utf-8')
    
    # Create the .twbx file
    twbx_file = tmp_path / "test_workbook.twbx"
    
    with zipfile.ZipFile(twbx_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(twb_file, "test_workbook.twb")
        zf.write(hyper_file, "Data/Extract.hyper")
    
    return twbx_file


# -----------------------------------------------------------------------------
# TESTS FOR .TWB FILES (Plain XML)
# -----------------------------------------------------------------------------

class TestTwbExtraction:
    """Tests for extracting .twb (plain XML) files."""
    
    def test_extract_twb_returns_content(self, sample_twb_file, sample_twb_content):
        """Test that we can read a .twb file and get its content."""
        result = extract_workbook(sample_twb_file)
        
        # Check that we got the right content
        assert result.twb_content == sample_twb_content
        
        # Check metadata
        assert result.is_packaged == False
        assert result.temp_dir is None  # No temp dir for .twb files
        assert result.data_sources == []  # No embedded data in .twb
    
    def test_get_workbook_xml_convenience(self, sample_twb_file, sample_twb_content):
        """Test the simple convenience function."""
        xml_content = get_workbook_xml(sample_twb_file)
        assert xml_content == sample_twb_content
    
    def test_twb_path_is_correct(self, sample_twb_file):
        """Test that the returned path matches the input path."""
        result = extract_workbook(sample_twb_file)
        assert result.twb_path == sample_twb_file


# -----------------------------------------------------------------------------
# TESTS FOR .TWBX FILES (ZIP Archives)
# -----------------------------------------------------------------------------

class TestTwbxExtraction:
    """Tests for extracting .twbx (packaged) files."""
    
    def test_extract_twbx_returns_content(self, sample_twbx_file, sample_twb_content):
        """Test that we can extract a .twbx file and get the XML content."""
        result = extract_workbook(sample_twbx_file)
        
        try:
            # Check that we got the right content
            assert result.twb_content == sample_twb_content
            
            # Check metadata
            assert result.is_packaged == True
            assert result.temp_dir is not None  # Should have a temp dir
            assert result.temp_dir.exists()  # Temp dir should exist
        finally:
            # Always clean up
            cleanup_temp_dir(result.temp_dir)
    
    def test_twbx_with_data_extracts(self, sample_twbx_with_data):
        """Test that we find data extract files (.hyper) in the package."""
        result = extract_workbook(sample_twbx_with_data)
        
        try:
            # Should find the .hyper file
            assert len(result.data_sources) == 1
            assert any("Extract.hyper" in ds for ds in result.data_sources)
        finally:
            cleanup_temp_dir(result.temp_dir)
    
    def test_get_workbook_xml_cleans_up(self, sample_twbx_file):
        """Test that get_workbook_xml cleans up temp files automatically."""
        # First, extract and note the temp dir location
        result = extract_workbook(sample_twbx_file)
        temp_dir = result.temp_dir
        cleanup_temp_dir(temp_dir)
        
        # Now use the convenience function
        xml_content = get_workbook_xml(sample_twbx_file)
        
        # Should get valid content
        assert "workbook" in xml_content
        # Note: We can't easily verify cleanup happened since we don't
        # have access to the temp_dir from the convenience function


# -----------------------------------------------------------------------------
# TESTS FOR ERROR HANDLING
# -----------------------------------------------------------------------------

class TestErrorHandling:
    """Tests for error handling and edge cases."""
    
    def test_file_not_found(self):
        """Test that we raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            extract_workbook("/nonexistent/path/file.twbx")
    
    def test_invalid_extension(self, tmp_path):
        """Test that we reject files with wrong extensions."""
        # Create a file with wrong extension
        bad_file = tmp_path / "test.xlsx"
        bad_file.write_text("not a tableau file", encoding='utf-8')
        
        with pytest.raises(ValueError) as exc_info:
            extract_workbook(bad_file)
        
        assert "Invalid file type" in str(exc_info.value)
    
    def test_corrupted_twbx(self, tmp_path):
        """Test that we handle corrupted ZIP files gracefully."""
        # Create a file that's not actually a ZIP
        bad_twbx = tmp_path / "corrupted.twbx"
        bad_twbx.write_text("this is not a zip file", encoding='utf-8')
        
        with pytest.raises(zipfile.BadZipFile):
            extract_workbook(bad_twbx)
    
    def test_twbx_without_twb(self, tmp_path):
        """Test error when .twbx doesn't contain a .twb file."""
        # Create a ZIP file without a .twb inside
        bad_twbx = tmp_path / "no_twb.twbx"
        
        with zipfile.ZipFile(bad_twbx, 'w') as zf:
            zf.writestr("some_other_file.txt", "not a workbook")
        
        with pytest.raises(ValueError) as exc_info:
            extract_workbook(bad_twbx)
        
        assert "No .twb file found" in str(exc_info.value)


# -----------------------------------------------------------------------------
# TESTS FOR CLEANUP
# -----------------------------------------------------------------------------

class TestCleanup:
    """Tests for the cleanup functionality."""
    
    def test_cleanup_removes_temp_dir(self, sample_twbx_file):
        """Test that cleanup_temp_dir actually removes the directory."""
        result = extract_workbook(sample_twbx_file)
        temp_dir = result.temp_dir
        
        # Temp dir should exist
        assert temp_dir.exists()
        
        # Clean up
        cleanup_temp_dir(temp_dir)
        
        # Now it should be gone
        assert not temp_dir.exists()
    
    def test_cleanup_handles_none(self):
        """Test that cleanup_temp_dir handles None gracefully."""
        # Should not raise any errors
        cleanup_temp_dir(None)
    
    def test_cleanup_handles_nonexistent_dir(self, tmp_path):
        """Test cleanup with a path that doesn't exist."""
        nonexistent = tmp_path / "does_not_exist"
        
        # Should not raise any errors
        cleanup_temp_dir(nonexistent)


# -----------------------------------------------------------------------------
# RUN TESTS
# This allows running tests directly with: python test_extractor.py
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
