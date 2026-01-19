"""
Pytest configuration and fixtures for InterView AI tests.
"""

import os
import sys
from pathlib import Path

import pytest


# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_root_path():
    """Return the project root directory."""
    return project_root


@pytest.fixture
def sample_resume_text():
    """Sample resume text for testing."""
    return """
John Doe
Software Engineer
john.doe@email.com | github.com/johndoe

EXPERIENCE

Software Engineer Intern - Tech Company (2024)
- Built REST APIs with Flask
- Implemented PostgreSQL database layer
- Wrote comprehensive unit tests

EDUCATION

B.Tech in Computer Science - University (2021-2025)
GPA: 3.8/4.0

SKILLS

Python, Flask, PostgreSQL, Docker, Git
    """.strip()


@pytest.fixture
def sample_job_description():
    """Sample job description for testing."""
    return """
Backend Developer

About the Role:
We are looking for a talented backend developer to join our team.

Requirements:
- 2+ years Python experience
- SQL database knowledge
- REST API design experience
- Version control with Git

Responsibilities:
- Design and implement scalable APIs
- Write clean, testable code
- Participate in code reviews
    """.strip()


@pytest.fixture
def mock_audio_bytes():
    """Mock audio bytes for testing (minimal WAV header)."""
    # This is a minimal valid WAV header
    return bytes([
        0x52, 0x49, 0x46, 0x46,  # "RIFF"
        0x24, 0x00, 0x00, 0x00,  # File size
        0x57, 0x41, 0x56, 0x45,  # "WAVE"
        0x66, 0x6D, 0x74, 0x20,  # "fmt "
        0x10, 0x00, 0x00, 0x00,  # Chunk size
        0x01, 0x00,              # Audio format (PCM)
        0x01, 0x00,              # Num channels (mono)
        0x80, 0x3E, 0x00, 0x00,  # Sample rate (16000)
        0x00, 0x7D, 0x00, 0x00,  # Byte rate
        0x02, 0x00,              # Block align
        0x10, 0x00,              # Bits per sample (16)
        0x64, 0x61, 0x74, 0x61,  # "data"
        0x00, 0x00, 0x00, 0x00,  # Data size
    ])


# Configure async tests
@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
