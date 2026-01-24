"""
InterView AI - API Routes.

FastAPI router with all interview endpoints.
Includes rate limiting to prevent abuse and Gemini credit drain.
"""

import logging
from typing import Dict
from datetime import datetime, timedelta

import numpy as np
from fastapi import APIRouter, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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
from src.app.coaching import AudioCoach, audio_bytes_to_numpy
from src.infra.utils.pdf_parser import extract_from_bytes
from src.core.domain.models import InterviewExchange
from src.infra.persistence.repository import SessionRepository
from src.infra.firebase_service import firebase_service  # <--- Added Import
from src.core.config import get_settings


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["interview"])

# Rate limiting: 100 requests per hour per IP, with stricter limits on expensive endpoints
limiter = Limiter(key_func=get_remote_address)

# Session-based orchestrator storage for multi-user support
sessions: Dict[str, InterviewOrchestrator] = {}

# Session timestamps for cleanup
session_created: Dict[str, datetime] = {}

SESSION_TIMEOUT_HOURS = 2  # Cleanup sessions older than this

# Session persistence repository
session_repo = SessionRepository()


@router.get("/config")
async def get_config() -> Dict:
    """
    Serve Firebase configuration to frontend.
    
    This endpoint ensures frontend & backend configuration are synchronized
    and credentials are managed from a single source (.env file).
    """
    settings = get_settings()
    
    return {
        "firebase": {
            "apiKey": settings.FIREBASE_API_KEY,
            "authDomain": settings.FIREBASE_AUTH_DOMAIN,
            "projectId": settings.FIREBASE_PROJECT_ID,
            "storageBucket": settings.FIREBASE_STORAGE_BUCKET,
            "messagingSenderId": settings.FIREBASE_MESSAGING_SENDER_ID,
            "appId": settings.FIREBASE_APP_ID,
            "measurementId": settings.FIREBASE_MEASUREMENT_ID,
        }
    }


def get_orchestrator(session_id: str) -> InterviewOrchestrator:
    """
    Get orchestrator for a specific session.
    
    Attempts to restore from disk if not found in memory (handles server restarts).
    """
    logger.debug(f"Looking up session: {session_id}, available: {list(sessions.keys())}")
    
    if session_id not in sessions:
        # Try to restore from persisted session
        persisted_session = session_repo.load(session_id)
        if persisted_session:
            logger.info(f"Restoring session {session_id} from disk")
            orchestrator = InterviewOrchestrator()
            orchestrator._session = persisted_session
            
            # Reconstruct QuestionContext from session data
            from src.core.domain.models import QuestionContext
            orchestrator._question_context = QuestionContext(
                resume_text=persisted_session.resume_text,
                job_description=persisted_session.job_description,
            )
            # Replay previous exchanges to rebuild context
            for exchange in persisted_session.exchanges:
                orchestrator._question_context.add_exchange(
                    exchange.question,
                    exchange.answer,
                )
            
            sessions[session_id] = orchestrator
            session_created[session_id] = datetime.now()
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    
    return sessions[session_id]


def cleanup_stale_sessions() -> int:
    """
    Remove sessions older than SESSION_TIMEOUT_HOURS.
    Returns the number of sessions cleaned up.
    Call this periodically or on each request.
    """
    if not session_created:
        return 0
    
    now = datetime.now()
    cutoff = now - timedelta(hours=SESSION_TIMEOUT_HOURS)
    stale_sessions = [
        sid for sid, created in session_created.items()
        if created < cutoff
    ]
    
    for sid in stale_sessions:
        sessions.pop(sid, None)
        session_created.pop(sid, None)
        logger.info(f"Cleaned up stale session: {sid}")
    
    return len(stale_sessions)


def get_active_session_count() -> int:
    """Get count of active sessions for monitoring."""
    return len(sessions)


# =============================================================================
# Session Management
# =============================================================================

@router.post("/session/start", response_model=SessionResponse)
async def start_session(request: StartSessionRequest):
    """Start a new interview session."""
    try:
        # Cleanup stale sessions periodically
        cleanup_stale_sessions()
        
        # Create new orchestrator for this session
        orchestrator = InterviewOrchestrator()
        
        session_id = await orchestrator.start_session(
            resume_text=request.resume_text,
            job_description=request.job_description,
        )
        
        # Store in sessions dict for multi-user support
        sessions[session_id] = orchestrator
        session_created[session_id] = datetime.now()
        
        # Persist session immediately for crash resistance
        session_repo.save(orchestrator.session)
        
        logger.info(f"Started session {session_id}. Active sessions: {len(sessions)}")
        
        return SessionResponse(
            session_id=session_id,
            status="started",
            message="Interview session started. Ready for first question.",
        )
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/end", response_model=SessionStatsResponse)
async def end_session(
    request: Request,
    session_id: str = Query(..., description="Session ID to end"),
):
    """
    End the current interview session.
    
    Securely extracts user email from Firebase ID Token in Authorization header.
    """
    try:
        orchestrator = get_orchestrator(session_id)
        
        if not orchestrator.session:
            raise HTTPException(status_code=400, detail="No active session")
        
        summary = await orchestrator.end_session()
        
        # Secure Email Handling
        user_email = None
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                from firebase_admin import auth
                decoded_token = auth.verify_id_token(token)
                user_email = decoded_token.get("email")
                logger.info(f"✅ Verified user email from token: {user_email}")
            except Exception as e:
                logger.warning(f"❌ Failed to verify token: {e}")
        
        # Send email report via Firebase (if valid email found)
        if user_email:
            logger.info(f"📧 Sending interview report to {user_email}")
            success = firebase_service.send_interview_report(user_email, summary)
            if not success:
                logger.warning("Failed to queue email report (check firebase_service logs)")
        else:
            logger.info("ℹ️ No authenticated user email found, skipping report email.")

        # Clean up session from dict
        sessions.pop(session_id, None)
        
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
async def get_session_stats(session_id: str = Query(..., description="Session ID")):
    """Get current session statistics."""
    orchestrator = get_orchestrator(session_id)
    
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
@limiter.limit("30/hour")  # 30 questions per hour (3-4 questions per session is typical)
async def get_next_question(
    request: Request,
    session_id: str = Query(..., description="Session ID")
):
    """Get the next interview question. Rate-limited to prevent LLM abuse."""
    try:
        orchestrator = get_orchestrator(session_id)
        
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
@limiter.limit("30/hour")  # 30 answers per hour (matches question limit)
async def submit_answer(request: Request, answer_request: SubmitAnswerRequest):
    """Submit an answer and get evaluation. Rate-limited to prevent LLM abuse."""
    try:
        orchestrator = get_orchestrator(answer_request.session_id)
        
        if not orchestrator.session:
            raise HTTPException(status_code=400, detail="No active session")
        
        # Create coaching feedback from text
        coach = AudioCoach()
        coaching = coach.get_coaching_feedback(
            text=answer_request.answer_text,
            duration_seconds=answer_request.duration_seconds,
            audio_data=None,
        )
        
        # Evaluate with Gemini
        evaluation = await orchestrator._gemini.evaluate_answer(
            question=orchestrator.session.current_question,
            answer=answer_request.answer_text,
        )
        
        # Record the exchange in session
        exchange = InterviewExchange(
            question=orchestrator.session.current_question,
            answer=answer_request.answer_text,
            answer_duration_seconds=answer_request.duration_seconds,
            evaluation=evaluation,
            coaching_feedback=coaching,
        )
        orchestrator.session.add_exchange(exchange)
        
        # Update question context for next question generation
        if orchestrator._question_context:
            orchestrator._question_context.add_exchange(
                orchestrator.session.current_question,
                answer_request.answer_text,
            )
        
        # Persist session to disk for crash resistance
        session_repo.save(orchestrator.session)
        
        return AnswerResultResponse(
            session_id=answer_request.session_id,
            transcript=answer_request.answer_text,
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


@router.post("/answer/audio", response_model=AnswerResultResponse)
async def submit_audio_answer(
    session_id: str = Query(..., description="Session ID"),
    audio: UploadFile = File(..., description="Audio file (WebM, WAV, MP3, etc.)"),
):
    """
    Submit an audio answer for transcription and evaluation.
    
    This endpoint:
    1. Receives audio file from the frontend
    2. Transcribes using Whisper (STT)
    3. Analyzes delivery with AudioCoach
    4. Evaluates content with Gemini
    
    Requires ffmpeg installed for WebM/non-WAV formats.
    """
    try:
        orchestrator = get_orchestrator(session_id)
        
        if not orchestrator.session:
            raise HTTPException(status_code=400, detail="No active session")
        
        # Read audio bytes
        audio_bytes = await audio.read()
        
        if len(audio_bytes) < 1000:
            raise HTTPException(status_code=400, detail="Audio file too small or empty")
        
        logger.info(f"Received audio: {len(audio_bytes)} bytes, type: {audio.content_type}")
        
        # Process through orchestrator (Whisper + Coach + Gemini)
        transcript, coaching, evaluation = await orchestrator.process_answer(
            audio_bytes=audio_bytes,
            sample_rate=16000,
        )
        
        # Persist session to disk for crash resistance
        session_repo.save(orchestrator.session)
        
        return AnswerResultResponse(
            session_id=session_id,
            transcript=transcript,
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
        logger.error(f"Failed to process audio answer: {e}")
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


# =============================================================================
# WebSocket Audio Streaming
# =============================================================================

@router.websocket("/ws/audio/{session_id}")
async def websocket_audio(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time audio streaming and coaching.
    
    Receives audio chunks from the frontend, analyzes volume in real-time,
    and sends coaching feedback back to the client.
    """
    await websocket.accept()
    
    # Validate session exists
    if session_id not in sessions:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    # Create per-connection coach instance
    coach = AudioCoach()
    logger.info(f"WebSocket connected for session: {session_id}")
    
    try:
        while True:
            # Receive audio chunk as bytes (WebM format from browser)
            data = await websocket.receive_bytes()
            
            # Convert to numpy for analysis
            # Note: audio_bytes_to_numpy uses pydub which can handle WebM with ffmpeg
            import asyncio
            audio_np = await asyncio.to_thread(audio_bytes_to_numpy, data)
            
            if audio_np.size > 0:
                # Analyze volume in real-time
                volume_alert = coach.analyze_volume(audio_np)
                
                # Calculate RMS for visualization
                rms = float(np.sqrt(np.mean(audio_np.astype(np.float32) ** 2)))
                
                # Send feedback back to UI
                await websocket.send_json({
                    "type": "coaching",
                    "volume_alert": volume_alert,
                    "volume_level": rms,
                    "is_speaking": rms > 0.02
                })
            else:
                # Send minimal response for empty/invalid audio
                await websocket.send_json({
                    "type": "coaching",
                    "volume_alert": "OK",
                    "volume_level": 0.0,
                    "is_speaking": False
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await websocket.close(code=1011, reason=str(e))


# =============================================================================
# Report Download
# =============================================================================

@router.get("/session/report/{session_id}/download")
async def download_report(session_id: str):
    """
    Generate and download a PDF report for the interview session.
    """
    try:
        from fpdf import FPDF
        import tempfile
        import os
        from fastapi.responses import FileResponse
        
        orchestrator = get_orchestrator(session_id)
        if not orchestrator.session:
            # Try to load from disk if not active
            try:
                # This logic is duplicated from get_orchestrator but robust
                pass 
            except:
                 raise HTTPException(status_code=404, detail="Session not found")
        
        stats = orchestrator.get_session_stats()
        session = orchestrator.session
        
        # Create PDF
        class ReportPDF(FPDF):
            def header(self):
                self.set_font('Arial', 'B', 16)
                self.cell(0, 10, 'InterView AI - Session Report', 0, 1, 'C')
                self.ln(5)
                
            def footer(self):
                self.set_y(-15)
                self.set_font('Arial', 'I', 8)
                self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

        pdf = ReportPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Stats Section
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Session Statistics", 0, 1)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1)
        pdf.cell(0, 8, f"Duration: {stats.get('duration_minutes', 0)} minutes", 0, 1)
        pdf.cell(0, 8, f"Questions Asked: {stats.get('questions_asked', 0)}", 0, 1)
        pdf.cell(0, 8, f"Average Score: {stats.get('average_score', 0)}/10", 0, 1)
        pdf.cell(0, 8, f"Words Per Minute: {stats.get('average_wpm', 0)}", 0, 1)
        pdf.ln(10)
        
        # Q&A Transcript
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Interview Transcript", 0, 1)
        pdf.set_font("Arial", size=11)
        
        for i, exchange in enumerate(session.exchanges):
            pdf.set_font("Arial", 'B', 11)
            # Handle unicode characters broadly by replacing or ignoring
            q_text = f"Q{i+1}: {exchange.question}".encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 7, q_text)
            
            pdf.set_font("Arial", '', 11)
            a_text = f"A: {exchange.answer}".encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 7, a_text)
            
            # Feedback
            pdf.set_font("Arial", 'I', 10)
            fb_text = f"Feedback: Tech={exchange.evaluation.technical_accuracy}/10, Clarity={exchange.evaluation.clarity}/10".encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 6, fb_text)
            if exchange.evaluation.improvement_tip:
                 tip = f"Tip: {exchange.evaluation.improvement_tip}".encode('latin-1', 'replace').decode('latin-1')
                 pdf.multi_cell(0, 6, tip)
            
            pdf.ln(5)
            
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf.output(temp_file.name)
        
        return FileResponse(
            temp_file.name, 
            media_type='application/pdf', 
            filename=f"interview_report_{session_id}.pdf"
        )
        
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))
