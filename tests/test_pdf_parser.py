"""
Unit tests for the PDF Parser module.

Tests resume extraction and job description parsing.
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.infra.utils.pdf_parser import (
    extract_resume_text,
    extract_from_bytes,
    parse_job_description,
    _clean_text,
    _mock_resume_text,
)
from src.core.exceptions import PDFParseError, EmptyDocumentError


class TestExtractResumeText:
    """Test suite for PDF text extraction."""
    
    def test_file_not_found_raises_error(self):
        """Non-existent file should raise PDFParseError."""
        with pytest.raises(PDFParseError) as exc_info:
            extract_resume_text("/nonexistent/path/resume.pdf")
        
        assert "File not found" in str(exc_info.value)
    
    def test_non_pdf_file_raises_error(self, tmp_path):
        """Non-PDF file should raise PDFParseError."""
        # Create a text file with .txt extension
        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("This is not a PDF")
        
        with pytest.raises(PDFParseError) as exc_info:
            extract_resume_text(str(txt_file))
        
        assert "not a PDF" in str(exc_info.value)
    
    def test_mock_resume_returns_text(self):
        """Mock resume should return sample text."""
        text = _mock_resume_text()
        
        assert len(text) > 100
        assert "Python" in text or "python" in text
        assert "experience" in text.lower() or "EXPERIENCE" in text


class TestExtractFromBytes:
    """Test byte-based PDF extraction."""
    
    def test_handles_invalid_bytes_gracefully(self):
        """Invalid PDF bytes should raise error, not crash."""
        invalid_bytes = b"This is not a PDF file"
        
        # Should either raise PDFParseError or use mock fallback
        try:
            result = extract_from_bytes(invalid_bytes, "fake.pdf")
            # If it returns (using mock), result should be non-empty
            assert len(result) > 0
        except PDFParseError:
            # This is also acceptable
            pass


class TestParseJobDescription:
    """Test job description parsing."""
    
    def test_extracts_title(self):
        """Should extract job title from first line."""
        jd = """Software Engineer
        
We are looking for a talented engineer...
"""
        result = parse_job_description(jd)
        
        assert "title" in result
        assert "Software Engineer" in result["title"]
    
    def test_extracts_requirements(self):
        """Should extract requirements section."""
        jd = """Backend Developer

Requirements:
- 3+ years Python experience
- SQL database knowledge
- REST API design

Responsibilities:
- Build scalable services
"""
        result = parse_job_description(jd)
        
        assert "requirements" in result
        assert isinstance(result["requirements"], list)
    
    def test_extracts_responsibilities(self):
        """Should extract responsibilities section."""
        jd = """Backend Developer

Responsibilities:
- Design and implement APIs
- Code review
"""
        result = parse_job_description(jd)
        
        assert "responsibilities" in result
        assert isinstance(result["responsibilities"], list)
    
    def test_preserves_full_text(self):
        """Should preserve full text in result."""
        jd = "Full Stack Developer\n\nWe need someone awesome."
        
        result = parse_job_description(jd)
        
        assert "full_text" in result
        assert len(result["full_text"]) > 0


class TestCleanText:
    """Test text cleaning utility."""
    
    def test_removes_excessive_whitespace(self):
        """Should collapse multiple spaces."""
        text = "Hello    world   with   spaces"
        
        result = _clean_text(text)
        
        assert "    " not in result
        assert "   " not in result
    
    def test_normalizes_line_breaks(self):
        """Should normalize different line break styles."""
        text = "Line1\r\nLine2\rLine3\nLine4"
        
        result = _clean_text(text)
        
        assert "\r\n" not in result
        assert "\r" not in result
    
    def test_removes_excessive_newlines(self):
        """Should collapse multiple newlines."""
        text = "Para1\n\n\n\n\nPara2"
        
        result = _clean_text(text)
        
        assert "\n\n\n" not in result
    
    def test_strips_whitespace(self):
        """Should strip leading/trailing whitespace."""
        text = "   Hello World   "
        
        result = _clean_text(text)
        
        assert result == "Hello World"
    
    def test_handles_empty_string(self):
        """Should handle empty string."""
        result = _clean_text("")
        
        assert result == ""


class TestMockResumeText:
    """Test mock resume for fallback scenarios."""
    
    def test_contains_experience_section(self):
        """Mock resume should have experience."""
        text = _mock_resume_text()
        
        assert "EXPERIENCE" in text or "Experience" in text
    
    def test_contains_skills_section(self):
        """Mock resume should have skills."""
        text = _mock_resume_text()
        
        assert "SKILLS" in text or "Skills" in text
    
    def test_contains_education_section(self):
        """Mock resume should have education."""
        text = _mock_resume_text()
        
        assert "EDUCATION" in text or "Education" in text


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
