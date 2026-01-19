#!/usr/bin/env python3
"""
InterView AI - Main Entry Point.

Usage:
    python main.py          # Run the Streamlit dashboard
    python main.py --cli    # Run in CLI mode (for testing)
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path


def setup_python_path():
    """Add project root to Python path."""
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def create_data_directories():
    """Ensure required data directories exist."""
    project_root = Path(__file__).parent
    
    dirs = [
        project_root / "data" / "resumes",
        project_root / "data" / "session_logs",
    ]
    
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)


def run_streamlit():
    """Launch the Streamlit dashboard."""
    import subprocess
    
    dashboard_path = Path(__file__).parent / "src" / "ui" / "dashboard.py"
    
    # Run streamlit
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_path),
        "--server.port=8501",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ])


async def run_cli_demo():
    """Run a quick CLI demo for testing."""
    setup_python_path()
    
    from src.core.config import configure_logging
    from src.app.orchestrator import create_orchestrator
    from src.infra.utils.pdf_parser import _mock_resume_text
    
    configure_logging()
    logger = logging.getLogger(__name__)
    
    print("\n" + "=" * 60)
    print("🎙️  InterView AI - CLI Demo")
    print("=" * 60 + "\n")
    
    # Create orchestrator
    orchestrator = create_orchestrator()
    
    # Mock data
    resume = _mock_resume_text()
    jd = "Backend Developer with Python and database experience."
    
    print("📄 Resume loaded (mock)")
    print("📋 Job Description:", jd)
    print("\n" + "-" * 60 + "\n")
    
    try:
        # Start session
        session_id = await orchestrator.start_session(resume, jd)
        print(f"🚀 Session started: {session_id}\n")
        
        # Get first question
        question = await orchestrator.get_next_question()
        print(f"🎯 Question: {question}\n")
        
        # Simulate answer
        answer = input("💬 Your answer (or press Enter for mock): ").strip()
        if not answer:
            answer = (
                "In my Flask project, I used PostgreSQL with SQLAlchemy ORM. "
                "The main challenge was handling N+1 query issues, which I solved "
                "by implementing eager loading with joinedload(). Um, this improved "
                "query performance by like 60 percent."
            )
            print(f"   (Using mock answer)")
        
        print("\n⏳ Processing...")
        
        # Analyze answer
        from src.app.coaching import AudioCoach
        coach = AudioCoach()
        
        duration = len(answer.split()) / 2.5  # ~150 WPM estimate
        feedback = coach.get_coaching_feedback(answer, duration)
        
        print(f"\n📊 Coaching Feedback:")
        print(f"   Volume: {feedback.volume_status}")
        print(f"   Pace: {feedback.pace_status} ({feedback.words_per_minute:.0f} WPM)")
        print(f"   Filler words: {feedback.filler_count}")
        print(f"   Alert: {feedback.primary_alert}")
        
        # Evaluate with Gemini
        evaluation = await orchestrator._gemini.evaluate_answer(question, answer)
        
        print(f"\n⭐ Evaluation:")
        print(f"   Technical: {evaluation.technical_accuracy}/10")
        print(f"   Clarity: {evaluation.clarity}/10")
        print(f"   Depth: {evaluation.depth}/10")
        print(f"   Average: {evaluation.average_score:.1f}/10")
        print(f"\n   💡 Tip: {evaluation.improvement_tip}")
        print(f"   👍 Good: {evaluation.positive_note}")
        
        # End session
        summary = await orchestrator.end_session()
        print("\n" + "=" * 60)
        print("🏁 Session Complete!")
        print(f"   Duration: {summary.get('duration_minutes', 0):.1f} min")
        print(f"   Questions: {summary.get('total_questions', 0)}")
        print("=" * 60 + "\n")
        
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        print("   Make sure GEMINI_API_KEY is set in .env")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="InterView AI - Real-Time Career Coach"
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in CLI mode instead of Streamlit",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    
    args = parser.parse_args()
    
    # Setup
    setup_python_path()
    create_data_directories()
    
    # Set debug mode
    if args.debug:
        os.environ["LOG_LEVEL"] = "DEBUG"
    
    # Run
    if args.cli:
        asyncio.run(run_cli_demo())
    else:
        print("\n🚀 Starting InterView AI Dashboard...")
        print("   Open http://localhost:8501 in your browser\n")
        run_streamlit()


if __name__ == "__main__":
    main()
