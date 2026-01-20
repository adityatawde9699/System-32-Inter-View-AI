"""
InterView AI - Session Repository.

JSON-based session persistence for crash resistance.
Serializes InterviewSession to disk after every turn,
allowing the server to be stateless and crash-resistant.

Usage:
    repo = SessionRepository()
    
    # Save after each answer
    repo.save(session)
    
    # Restore on server restart
    session = repo.load(session_id)
    
    # Clean up old sessions
    repo.delete(session_id)
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.core.domain.models import (
    InterviewSession,
    InterviewState,
    InterviewExchange,
    AnswerEvaluation,
    CoachingFeedback,
    CoachingAlertLevel,
)

logger = logging.getLogger(__name__)


class SessionRepository:
    """
    JSON-based session persistence.
    
    Stores session state as JSON files in a data directory,
    enabling crash recovery and server restarts without data loss.
    """
    
    def __init__(self, data_dir: str = "data/sessions"):
        """
        Initialize repository with data directory.
        
        Args:
            data_dir: Directory to store session JSON files
        """
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Session repository initialized at: {self._data_dir}")
    
    def _session_path(self, session_id: str) -> Path:
        """Get file path for a session ID."""
        # Sanitize session_id to prevent path traversal
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        return self._data_dir / f"{safe_id}.json"
    
    def save(self, session: InterviewSession) -> None:
        """
        Serialize session to JSON file.
        
        Called after every answer submission to persist state.
        Uses atomic write pattern to prevent corruption.
        
        Args:
            session: InterviewSession to persist
        """
        data = self._session_to_dict(session)
        path = self._session_path(session.session_id)
        temp_path = path.with_suffix('.json.tmp')
        
        try:
            # Write to temp file first (atomic write pattern)
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Rename temp to final (atomic on most filesystems)
            temp_path.replace(path)
            
            logger.debug(f"Saved session {session.session_id} ({len(session.exchanges)} exchanges)")
            
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    def load(self, session_id: str) -> Optional[InterviewSession]:
        """
        Load session from JSON file.
        
        Args:
            session_id: Session ID to load
            
        Returns:
            InterviewSession if found, None otherwise
        """
        path = self._session_path(session_id)
        
        if not path.exists():
            logger.debug(f"Session {session_id} not found on disk")
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            session = self._dict_to_session(data)
            logger.info(f"Loaded session {session_id} from disk ({len(session.exchanges)} exchanges)")
            return session
            
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
    def delete(self, session_id: str) -> bool:
        """
        Delete session file.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()
            logger.info(f"Deleted session file: {session_id}")
            return True
        return False
    
    def list_sessions(self) -> list[str]:
        """
        List all stored session IDs.
        
        Returns:
            List of session IDs (without .json extension)
        """
        return [p.stem for p in self._data_dir.glob("*.json")]
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        Delete session files older than max_age_hours.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
            
        Returns:
            Number of sessions cleaned up
        """
        count = 0
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        
        for path in self._data_dir.glob("*.json"):
            if path.stat().st_mtime < cutoff:
                path.unlink()
                count += 1
                logger.info(f"Cleaned up old session file: {path.stem}")
        
        return count
    
    # -------------------------------------------------------------------------
    # Serialization Helpers
    # -------------------------------------------------------------------------
    
    def _session_to_dict(self, session: InterviewSession) -> dict:
        """Convert session to serializable dict."""
        return {
            "version": 1,  # Schema version for future migrations
            "session_id": session.session_id,
            "state": session.state.value,
            "resume_text": session.resume_text,
            "job_description": session.job_description,
            "current_question": session.current_question,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "total_questions_asked": session.total_questions_asked,
            "total_filler_words": session.total_filler_words,
            "average_wpm": session.average_wpm,
            "exchanges": [self._exchange_to_dict(ex) for ex in session.exchanges],
        }
    
    def _exchange_to_dict(self, exchange: InterviewExchange) -> dict:
        """Convert exchange to serializable dict."""
        return {
            "question": exchange.question,
            "answer": exchange.answer,
            "duration_seconds": exchange.answer_duration_seconds,
            "timestamp": exchange.timestamp.isoformat(),
            "evaluation": self._evaluation_to_dict(exchange.evaluation) if exchange.evaluation else None,
            "coaching": self._coaching_to_dict(exchange.coaching_feedback) if exchange.coaching_feedback else None,
        }
    
    def _evaluation_to_dict(self, evaluation: AnswerEvaluation) -> dict:
        """Convert evaluation to serializable dict."""
        return {
            "technical_accuracy": evaluation.technical_accuracy,
            "clarity": evaluation.clarity,
            "depth": evaluation.depth,
            "completeness": evaluation.completeness,
            "improvement_tip": evaluation.improvement_tip,
            "positive_note": evaluation.positive_note,
        }
    
    def _coaching_to_dict(self, coaching: CoachingFeedback) -> dict:
        """Convert coaching feedback to serializable dict."""
        return {
            "volume_status": coaching.volume_status,
            "pace_status": coaching.pace_status,
            "filler_count": coaching.filler_count,
            "words_per_minute": coaching.words_per_minute,
            "primary_alert": coaching.primary_alert,
            "alert_level": coaching.alert_level.value,
        }
    
    def _dict_to_session(self, data: dict) -> InterviewSession:
        """Reconstruct session from dict."""
        session = InterviewSession(
            session_id=data["session_id"],
            state=InterviewState(data.get("state", "idle")),
            resume_text=data.get("resume_text", ""),
            job_description=data.get("job_description", ""),
            current_question=data.get("current_question", ""),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            total_questions_asked=data.get("total_questions_asked", 0),
            total_filler_words=data.get("total_filler_words", 0),
            average_wpm=data.get("average_wpm", 0.0),
        )
        
        # Reconstruct exchanges
        for ex_data in data.get("exchanges", []):
            evaluation = self._dict_to_evaluation(ex_data.get("evaluation"))
            coaching = self._dict_to_coaching(ex_data.get("coaching"))
            
            exchange = InterviewExchange(
                question=ex_data["question"],
                answer=ex_data["answer"],
                answer_duration_seconds=ex_data.get("duration_seconds", 0),
                evaluation=evaluation,
                coaching_feedback=coaching,
                timestamp=datetime.fromisoformat(ex_data["timestamp"]) if ex_data.get("timestamp") else datetime.now(),
            )
            session.exchanges.append(exchange)
        
        return session
    
    def _dict_to_evaluation(self, data: Optional[dict]) -> Optional[AnswerEvaluation]:
        """Reconstruct evaluation from dict."""
        if not data:
            return None
        
        return AnswerEvaluation(
            technical_accuracy=data.get("technical_accuracy", 0),
            clarity=data.get("clarity", 0),
            depth=data.get("depth", 0),
            completeness=data.get("completeness", 0),
            improvement_tip=data.get("improvement_tip", ""),
            positive_note=data.get("positive_note", ""),
        )
    
    def _dict_to_coaching(self, data: Optional[dict]) -> Optional[CoachingFeedback]:
        """Reconstruct coaching feedback from dict."""
        if not data:
            return None
        
        return CoachingFeedback(
            volume_status=data.get("volume_status", "OK"),
            pace_status=data.get("pace_status", "OK"),
            filler_count=data.get("filler_count", 0),
            words_per_minute=data.get("words_per_minute", 0.0),
            primary_alert=data.get("primary_alert", ""),
            alert_level=CoachingAlertLevel(data.get("alert_level", "ok")),
        )
