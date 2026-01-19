"""
InterView AI - API Request/Response Schemas.

Pydantic models for API validation.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# =============================================================================
# Request Schemas
# =============================================================================

class StartSessionRequest(BaseModel):
    """Request to start a new interview session."""
    resume_text: str = Field(..., min_length=50, description="Extracted resume text")
    job_description: str = Field(..., min_length=20, description="Target job description")


class SubmitAnswerRequest(BaseModel):
    """Request to submit an answer (text-based for now)."""
    session_id: str
    answer_text: str = Field(..., min_length=1, description="Candidate's answer")
    duration_seconds: float = Field(default=10.0, ge=0, description="Time taken to answer")


class UploadResumeRequest(BaseModel):
    """Resume text after extraction."""
    filename: str
    text_content: str


# =============================================================================
# Response Schemas
# =============================================================================

class SessionResponse(BaseModel):
    """Response after starting a session."""
    session_id: str
    status: str
    message: str


class QuestionResponse(BaseModel):
    """Response containing an interview question."""
    session_id: str
    question_number: int
    question_text: str
    total_questions: int


class CoachingFeedbackResponse(BaseModel):
    """Real-time coaching feedback."""
    volume_status: str
    pace_status: str
    filler_count: int
    words_per_minute: float
    primary_alert: str
    alert_level: str


class EvaluationResponse(BaseModel):
    """Answer evaluation from AI."""
    technical_accuracy: int
    clarity: int
    depth: int
    completeness: int
    average_score: float
    improvement_tip: str
    positive_note: str


class AnswerResultResponse(BaseModel):
    """Complete response after submitting an answer."""
    session_id: str
    transcript: str
    coaching: CoachingFeedbackResponse
    evaluation: EvaluationResponse


class SessionStatsResponse(BaseModel):
    """Session statistics."""
    session_id: str
    questions_asked: int
    duration_minutes: float
    average_score: float
    average_wpm: float
    total_fillers: int


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
