"""
InterView AI - API Routes.

FastAPI router with all interview endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from src.api.schemas import (
    StartSessionRequest,
    SubmitAnswerRequest,
    SessionResponse,
    QuestionResponse,
    AnswerResultResponse,
    CoachingFeedbackResponse,
    EvaluationResponse,
    SessionStatsResponse,
)
from src.app.orchestrator import InterviewOrchestrator
from src.app.coaching import AudioCoach
from src.infra.utils.pdf_parser import extract_from_bytes


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["interview"])

# Global orchestrator instance (in production, use dependency injection)
_orchestrator: InterviewOrchestrator | None = None


def get_orchestrator() -> InterviewOrchestrator:
    """Get or create the orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = InterviewOrchestrator()
    return _orchestrator


# =============================================================================
# Session Management
# =============================================================================

@router.post("/session/start", response_model=SessionResponse)
async def start_session(request: StartSessionRequest):
    """Start a new interview session."""
    try:
        orchestrator = get_orchestrator()
        
        session_id = await orchestrator.start_session(
            resume_text=request.resume_text,
            job_description=request.job_description,
        )
        
        return SessionResponse(
            session_id=session_id,
            status="started",
            message="Interview session started. Ready for first question.",
        )
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/end", response_model=SessionStatsResponse)
async def end_session():
    """End the current interview session."""
    try:
        orchestrator = get_orchestrator()
        
        if not orchestrator.session:
            raise HTTPException(status_code=400, detail="No active session")
        
        summary = await orchestrator.end_session()
        
        return SessionStatsResponse(
            session_id=summary.get("session_id", ""),
            questions_asked=summary.get("total_questions", 0),
            duration_minutes=summary.get("duration_minutes", 0),
            average_score=summary.get("average_score", 0),
            average_wpm=summary.get("average_wpm", 0),
            total_fillers=summary.get("total_filler_words", 0),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to end session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/stats", response_model=SessionStatsResponse)
async def get_session_stats():
    """Get current session statistics."""
    orchestrator = get_orchestrator()
    
    if not orchestrator.session:
        raise HTTPException(status_code=400, detail="No active session")
    
    stats = orchestrator.get_session_stats()
    
    return SessionStatsResponse(
        session_id=orchestrator.session.session_id,
        questions_asked=stats.get("questions_asked", 0),
        duration_minutes=stats.get("duration_minutes", 0),
        average_score=stats.get("average_score", 0),
        average_wpm=stats.get("average_wpm", 0),
        total_fillers=stats.get("total_fillers", 0),
    )


# =============================================================================
# Interview Flow
# =============================================================================

@router.get("/question/next", response_model=QuestionResponse)
async def get_next_question():
    """Get the next interview question."""
    try:
        orchestrator = get_orchestrator()
        
        if not orchestrator.session:
            raise HTTPException(status_code=400, detail="No active session. Start a session first.")
        
        question = await orchestrator.get_next_question()
        
        return QuestionResponse(
            session_id=orchestrator.session.session_id,
            question_number=orchestrator.session.total_questions_asked,
            question_text=question,
            total_questions=10,  # Max questions
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/answer/submit", response_model=AnswerResultResponse)
async def submit_answer(request: SubmitAnswerRequest):
    """Submit an answer and get evaluation."""
    try:
        orchestrator = get_orchestrator()
        
        if not orchestrator.session:
            raise HTTPException(status_code=400, detail="No active session")
        
        # Create coaching feedback from text
        coach = AudioCoach()
        coaching = coach.get_coaching_feedback(
            text=request.answer_text,
            duration_seconds=request.duration_seconds,
            audio_data=None,
        )
        
        # Evaluate with Gemini
        evaluation = await orchestrator._gemini.evaluate_answer(
            question=orchestrator.session.current_question,
            answer=request.answer_text,
        )
        
        # Update context
        if orchestrator._question_context:
            orchestrator._question_context.add_exchange(
                orchestrator.session.current_question,
                request.answer_text,
            )
        
        return AnswerResultResponse(
            session_id=request.session_id,
            transcript=request.answer_text,
            coaching=CoachingFeedbackResponse(
                volume_status=coaching.volume_status,
                pace_status=coaching.pace_status,
                filler_count=coaching.filler_count,
                words_per_minute=coaching.words_per_minute,
                primary_alert=coaching.primary_alert,
                alert_level=coaching.alert_level.value,
            ),
            evaluation=EvaluationResponse(
                technical_accuracy=evaluation.technical_accuracy,
                clarity=evaluation.clarity,
                depth=evaluation.depth,
                completeness=evaluation.completeness,
                average_score=evaluation.average_score,
                improvement_tip=evaluation.improvement_tip,
                positive_note=evaluation.positive_note,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process answer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# File Upload
# =============================================================================

@router.post("/upload/resume")
async def upload_resume(file: UploadFile = File(...)):
    """Upload and parse a resume PDF."""
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        contents = await file.read()
        text = extract_from_bytes(contents, file.filename)
        
        return {
            "filename": file.filename,
            "text_length": len(text),
            "text_content": text,
            "status": "success",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to parse resume: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
async def health_check():
    """API health check."""
    return {"status": "healthy", "service": "InterView AI"}
