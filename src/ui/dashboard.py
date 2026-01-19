"""
InterView AI - Streamlit Dashboard.

The main user interface for the AI interview coach.
Features:
- Resume upload and job description input
- Real-time interview simulation
- Coaching HUD with live metrics
- Session summary and feedback
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import streamlit as st

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_settings, configure_logging
from src.core.domain.models import InterviewState, CoachingAlertLevel
from src.app.orchestrator import InterviewOrchestrator
from src.infra.utils.pdf_parser import extract_from_bytes


# Configure logging
configure_logging()
logger = logging.getLogger(__name__)


# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="InterView AI - Real-Time Career Coach",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# CUSTOM CSS
# =============================================================================

st.markdown("""
<style>
    /* Main container styling */
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    /* Coaching HUD */
    .coaching-hud {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #0f3460;
    }
    
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #a0a0a0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Alert styling */
    .alert-ok {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-weight: 600;
    }
    
    .alert-warning {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-weight: 600;
        animation: pulse 1.5s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    
    /* Question card */
    .question-card {
        background: linear-gradient(135deg, #232526 0%, #414345 100%);
        border-radius: 15px;
        padding: 2rem;
        margin: 1.5rem 0;
        border-left: 4px solid #667eea;
    }
    
    .question-text {
        font-size: 1.3rem;
        line-height: 1.6;
        color: #ffffff;
    }
    
    /* Transcript area */
    .transcript-area {
        background: #1a1a2e;
        border-radius: 10px;
        padding: 1rem;
        min-height: 100px;
        border: 1px solid #0f3460;
        font-family: 'Courier New', monospace;
    }
    
    /* Score display */
    .score-circle {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2rem;
        font-weight: 700;
        margin: 0 auto;
    }
    
    .score-good { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .score-mid { background: linear-gradient(135deg, #f5af19 0%, #f12711 100%); }
    .score-low { background: linear-gradient(135deg, #f5576c 0%, #f093fb 100%); }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Initialize Streamlit session state variables."""
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = InterviewOrchestrator()
    
    if "interview_started" not in st.session_state:
        st.session_state.interview_started = False
    
    if "resume_text" not in st.session_state:
        st.session_state.resume_text = ""
    
    if "job_description" not in st.session_state:
        st.session_state.job_description = ""
    
    if "current_question" not in st.session_state:
        st.session_state.current_question = ""
    
    if "transcript" not in st.session_state:
        st.session_state.transcript = ""
    
    if "coaching_feedback" not in st.session_state:
        st.session_state.coaching_feedback = None
    
    if "evaluation" not in st.session_state:
        st.session_state.evaluation = None
    
    if "session_stats" not in st.session_state:
        st.session_state.session_stats = {}
    
    if "messages" not in st.session_state:
        st.session_state.messages = []


init_session_state()


# =============================================================================
# SIDEBAR - SETUP
# =============================================================================

with st.sidebar:
    st.markdown("## 📄 Interview Setup")
    
    # Resume upload
    st.markdown("### Resume")
    uploaded_file = st.file_uploader(
        "Upload your resume (PDF)",
        type=["pdf"],
        help="Upload your resume to personalize the interview questions",
    )
    
    if uploaded_file is not None:
        try:
            resume_bytes = uploaded_file.read()
            st.session_state.resume_text = extract_from_bytes(resume_bytes, uploaded_file.name)
            st.success(f"✅ Resume loaded: {len(st.session_state.resume_text)} characters")
        except Exception as e:
            st.error(f"❌ Failed to parse resume: {e}")
    
    # Job description
    st.markdown("### Job Description")
    st.session_state.job_description = st.text_area(
        "Paste the job description",
        value=st.session_state.job_description,
        height=150,
        placeholder="Paste the full job description here...",
    )
    
    # Settings
    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    
    settings = get_settings()
    st.info(f"Whisper Model: {settings.WHISPER_MODEL}")
    st.info(f"WPM Range: {settings.WPM_SLOW}-{settings.WPM_FAST}")
    
    # API Key check
    if not settings.GEMINI_API_KEY:
        st.error("⚠️ GEMINI_API_KEY not set in .env")


# =============================================================================
# MAIN HEADER
# =============================================================================

st.markdown('<h1 class="main-header">🎙️ InterView AI</h1>', unsafe_allow_html=True)
st.markdown(
    '<p style="text-align: center; color: #888; margin-bottom: 2rem;">Your Real-Time AI Career Coach</p>',
    unsafe_allow_html=True,
)


# =============================================================================
# INTERVIEW CONTROLS
# =============================================================================

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if not st.session_state.interview_started:
        # Check if ready to start
        ready = bool(st.session_state.resume_text and st.session_state.job_description)
        
        if st.button(
            "🎬 Start Interview",
            use_container_width=True,
            disabled=not ready,
            type="primary",
        ):
            # Start the interview
            orchestrator = st.session_state.orchestrator
            
            with st.spinner("🚀 Starting interview..."):
                try:
                    # Run async function
                    session_id = asyncio.run(
                        orchestrator.start_session(
                            st.session_state.resume_text,
                            st.session_state.job_description,
                        )
                    )
                    
                    # Get first question
                    question = asyncio.run(orchestrator.get_next_question())
                    st.session_state.current_question = question
                    st.session_state.interview_started = True
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Failed to start interview: {e}")
        
        if not ready:
            st.warning("📋 Please upload your resume and add a job description to start.")
    
    else:
        if st.button("🛑 End Interview", use_container_width=True, type="secondary"):
            orchestrator = st.session_state.orchestrator
            
            with st.spinner("Generating summary..."):
                try:
                    summary = asyncio.run(orchestrator.end_session())
                    st.session_state.session_stats = summary
                    st.session_state.interview_started = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Error ending session: {e}")


# =============================================================================
# INTERVIEW AREA
# =============================================================================

if st.session_state.interview_started:
    
    # Coaching HUD
    st.markdown('<div class="coaching-hud">', unsafe_allow_html=True)
    
    hud_cols = st.columns(4)
    
    feedback = st.session_state.coaching_feedback
    
    with hud_cols[0]:
        wpm = feedback.words_per_minute if feedback else 0
        st.metric("📊 Words/Min", f"{wpm:.0f}")
    
    with hud_cols[1]:
        fillers = feedback.filler_count if feedback else 0
        st.metric("🗣️ Filler Words", fillers)
    
    with hud_cols[2]:
        stats = st.session_state.orchestrator.get_session_stats()
        questions = stats.get("questions_asked", 0)
        st.metric("❓ Questions", questions)
    
    with hud_cols[3]:
        avg_score = stats.get("average_score", 0)
        st.metric("⭐ Avg Score", f"{avg_score:.1f}/10")
    
    # Alert banner
    if feedback and feedback.primary_alert:
        alert_class = "alert-ok" if feedback.alert_level == CoachingAlertLevel.OK else "alert-warning"
        st.markdown(
            f'<div class="{alert_class}">{feedback.primary_alert}</div>',
            unsafe_allow_html=True,
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Current Question
    st.markdown('<div class="question-card">', unsafe_allow_html=True)
    st.markdown(f"**🎯 Current Question:**")
    st.markdown(f'<p class="question-text">{st.session_state.current_question}</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Audio input section
    st.markdown("### 🎤 Your Answer")
    
    # Use streamlit-webrtc for audio recording (simplified version)
    st.info("💡 Click the button below and speak your answer clearly.")
    
    # Simple text input fallback (for demo/testing)
    answer_text = st.text_area(
        "Type your answer (or use voice):",
        placeholder="Speak or type your answer here...",
        height=100,
        key="answer_input",
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 Submit Answer", use_container_width=True, type="primary"):
            if answer_text.strip():
                orchestrator = st.session_state.orchestrator
                
                with st.spinner("🔄 Processing your answer..."):
                    try:
                        # For text input, we create mock audio processing
                        # In production, this would use actual audio bytes
                        from src.app.coaching import AudioCoach
                        import numpy as np
                        
                        coach = AudioCoach()
                        duration = len(answer_text.split()) / 2.5  # Estimate ~150 WPM
                        
                        # Get coaching feedback directly
                        coaching = coach.get_coaching_feedback(
                            text=answer_text,
                            duration_seconds=duration,
                            audio_data=None,
                        )
                        st.session_state.coaching_feedback = coaching
                        
                        # Evaluate with Gemini
                        evaluation = asyncio.run(
                            orchestrator._gemini.evaluate_answer(
                                question=st.session_state.current_question,
                                answer=answer_text,
                            )
                        )
                        st.session_state.evaluation = evaluation
                        st.session_state.transcript = answer_text
                        
                        # Update context
                        if orchestrator._question_context:
                            orchestrator._question_context.add_exchange(
                                st.session_state.current_question,
                                answer_text,
                            )
                        
                        st.success("✅ Answer processed!")
                        
                    except Exception as e:
                        st.error(f"Error processing answer: {e}")
            else:
                st.warning("Please enter your answer first.")
    
    with col2:
        if st.button("➡️ Next Question", use_container_width=True):
            orchestrator = st.session_state.orchestrator
            
            with st.spinner("Generating next question..."):
                try:
                    question = asyncio.run(orchestrator.get_next_question())
                    st.session_state.current_question = question
                    st.session_state.transcript = ""
                    st.session_state.evaluation = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    # Evaluation display
    if st.session_state.evaluation:
        st.markdown("---")
        st.markdown("### 📊 Answer Evaluation")
        
        eval_obj = st.session_state.evaluation
        
        eval_cols = st.columns(4)
        
        with eval_cols[0]:
            st.metric("🎯 Technical", f"{eval_obj.technical_accuracy}/10")
        with eval_cols[1]:
            st.metric("💡 Clarity", f"{eval_obj.clarity}/10")
        with eval_cols[2]:
            st.metric("📚 Depth", f"{eval_obj.depth}/10")
        with eval_cols[3]:
            st.metric("✅ Complete", f"{eval_obj.completeness}/10")
        
        if eval_obj.positive_note:
            st.success(f"👍 **Strength:** {eval_obj.positive_note}")
        
        if eval_obj.improvement_tip:
            st.info(f"💡 **Tip:** {eval_obj.improvement_tip}")


# =============================================================================
# SESSION SUMMARY (after interview ends)
# =============================================================================

if not st.session_state.interview_started and st.session_state.session_stats:
    st.markdown("---")
    st.markdown("## 📋 Interview Summary")
    
    stats = st.session_state.session_stats
    
    summary_cols = st.columns(5)
    
    with summary_cols[0]:
        st.metric("⏱️ Duration", f"{stats.get('duration_minutes', 0)} min")
    with summary_cols[1]:
        st.metric("❓ Questions", stats.get("total_questions", 0))
    with summary_cols[2]:
        st.metric("⭐ Avg Score", f"{stats.get('average_score', 0):.1f}/10")
    with summary_cols[3]:
        st.metric("📊 Avg WPM", f"{stats.get('average_wpm', 0):.0f}")
    with summary_cols[4]:
        st.metric("🗣️ Fillers", stats.get("total_filler_words", 0))
    
    st.balloons()
    st.success("🎉 Great job completing the interview! Review your metrics above.")


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.markdown(
    '<p style="text-align: center; color: #666; font-size: 0.8rem;">'
    'InterView AI | Built with Streamlit, Gemini, and Whisper | '
    '<a href="https://github.com" style="color: #667eea;">GitHub</a>'
    '</p>',
    unsafe_allow_html=True,
)
