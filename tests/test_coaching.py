"""
Unit tests for the AudioCoach module.

Tests the zero-latency local audio analysis functionality.
"""

import numpy as np
import pytest

from src.app.coaching import AudioCoach, audio_bytes_to_numpy
from src.core.domain.models import CoachingAlertLevel


class TestAudioCoach:
    """Test suite for AudioCoach class."""
    
    @pytest.fixture
    def coach(self):
        """Create a fresh AudioCoach instance for each test."""
        return AudioCoach()
    
    # =========================================================================
    # Volume Analysis Tests
    # =========================================================================
    
    def test_volume_below_threshold_returns_speak_up(self, coach):
        """Low volume should trigger 'speak up' alert."""
        # Create very quiet audio (near silence)
        quiet_audio = np.array([0.001, 0.002, -0.001, 0.0015], dtype=np.float32)
        
        result = coach.analyze_volume(quiet_audio)
        
        assert "SPEAK UP" in result or "Speak Up" in result
    
    def test_volume_above_threshold_returns_ok(self, coach):
        """Normal volume should return OK."""
        # Create normal volume audio
        normal_audio = np.array([0.1, -0.15, 0.2, -0.1, 0.12], dtype=np.float32)
        
        result = coach.analyze_volume(normal_audio)
        
        assert result == "OK"
    
    def test_empty_audio_returns_ok(self, coach):
        """Empty audio array should return OK (not crash)."""
        empty_audio = np.array([], dtype=np.float32)
        
        result = coach.analyze_volume(empty_audio)
        
        assert result == "OK"
    
    # =========================================================================
    # Pace Analysis Tests
    # =========================================================================
    
    def test_pace_above_160_returns_slow_down(self, coach):
        """Speaking too fast (>160 WPM) should trigger slow down."""
        # 30 words in 10 seconds = 180 WPM
        text = " ".join(["word"] * 30)
        duration = 10.0
        
        result = coach.analyze_pace(text, duration)
        
        assert "SLOW DOWN" in result or "Slow Down" in result
    
    def test_pace_below_100_returns_pick_up(self, coach):
        """Speaking too slow (<100 WPM) should trigger pick up."""
        # 10 words in 10 seconds = 60 WPM
        text = " ".join(["word"] * 10)
        duration = 10.0
        
        result = coach.analyze_pace(text, duration)
        
        assert "PICK UP" in result or "Pick Up" in result
    
    def test_normal_pace_returns_ok(self, coach):
        """Normal pace (100-160 WPM) should return OK."""
        # 20 words in 10 seconds = 120 WPM
        text = " ".join(["word"] * 20)
        duration = 10.0
        
        result = coach.analyze_pace(text, duration)
        
        assert result == "OK"
    
    def test_zero_duration_returns_ok(self, coach):
        """Zero duration should return OK (avoid division by zero)."""
        result = coach.analyze_pace("hello world", 0.0)
        
        assert result == "OK"
    
    def test_empty_text_returns_ok(self, coach):
        """Empty text should return OK."""
        result = coach.analyze_pace("", 5.0)
        
        assert result == "OK"
    
    # =========================================================================
    # Filler Word Tests
    # =========================================================================
    
    def test_filler_word_counting_um(self, coach):
        """Should count 'um' occurrences."""
        text = "I think um that um we should um do this"
        
        count = coach.get_filler_count(text)
        
        assert count >= 3
    
    def test_filler_word_counting_like(self, coach):
        """Should count 'like' occurrences."""
        text = "It was like really like awesome like wow"
        
        count = coach.get_filler_count(text)
        
        assert count >= 3
    
    def test_filler_word_counting_you_know(self, coach):
        """Should count 'you know' phrase."""
        text = "So you know I was thinking you know about it"
        
        count = coach.get_filler_count(text)
        
        assert count >= 2
    
    def test_no_fillers_returns_zero(self, coach):
        """Text without fillers should return 0."""
        text = "I implemented a REST API using Flask and PostgreSQL"
        
        count = coach.get_filler_count(text)
        
        assert count == 0
    
    def test_empty_text_returns_zero_fillers(self, coach):
        """Empty text should return 0 fillers."""
        count = coach.get_filler_count("")
        
        assert count == 0
    
    # =========================================================================
    # Combined Feedback Tests
    # =========================================================================
    
    def test_get_coaching_feedback_returns_feedback_object(self, coach):
        """Should return a CoachingFeedback object."""
        text = "This is a sample answer with um some fillers"
        duration = 5.0
        
        feedback = coach.get_coaching_feedback(text, duration)
        
        assert feedback is not None
        assert hasattr(feedback, 'volume_status')
        assert hasattr(feedback, 'pace_status')
        assert hasattr(feedback, 'filler_count')
        assert hasattr(feedback, 'words_per_minute')
        assert hasattr(feedback, 'primary_alert')
        assert hasattr(feedback, 'alert_level')
    
    def test_feedback_calculates_wpm(self, coach):
        """Should correctly calculate words per minute."""
        text = "one two three four five six seven eight nine ten"  # 10 words
        duration = 5.0  # 5 seconds = 120 WPM
        
        feedback = coach.get_coaching_feedback(text, duration)
        
        assert 115 <= feedback.words_per_minute <= 125
    
    def test_feedback_with_audio_data(self, coach):
        """Should analyze audio when provided."""
        text = "Test answer"
        duration = 2.0
        audio = np.array([0.1, -0.1, 0.15, -0.05], dtype=np.float32)
        
        feedback = coach.get_coaching_feedback(text, duration, audio)
        
        assert feedback.volume_status in ["OK", "📣 SPEAK UP", "📣 Speak Up! Your voice is a bit quiet."]
    
    def test_feedback_high_fillers_triggers_warning(self, coach):
        """Many filler words should trigger a warning."""
        text = "Um so like you know I um think we should like um do this"
        duration = 10.0
        
        feedback = coach.get_coaching_feedback(text, duration)
        
        # Should have at least 5 fillers
        assert feedback.filler_count >= 5
    
    # =========================================================================
    # History and Reset Tests
    # =========================================================================
    
    def test_average_wpm_calculation(self, coach):
        """Should calculate average WPM across segments."""
        # Analyze multiple segments
        coach.analyze_pace("word " * 20, 10.0)  # 120 WPM
        coach.analyze_pace("word " * 25, 10.0)  # 150 WPM
        
        avg = coach.get_average_wpm()
        
        assert 130 <= avg <= 140
    
    def test_reset_clears_history(self, coach):
        """Reset should clear all history."""
        coach.analyze_pace("word " * 20, 10.0)
        coach.analyze_volume(np.array([0.1, 0.2], dtype=np.float32))
        
        coach.reset()
        
        assert coach.get_average_wpm() == 0.0
        assert coach.get_average_volume() == 0.0


class TestAudioBytesToNumpy:
    """Test audio conversion utility."""
    
    def test_returns_numpy_array(self):
        """Should return a numpy array."""
        # This would need actual WAV bytes to test properly
        # For now, test that it handles empty/invalid input gracefully
        result = audio_bytes_to_numpy(b"invalid data")
        
        assert isinstance(result, np.ndarray)
    
    def test_handles_empty_bytes(self):
        """Should handle empty bytes without crashing."""
        result = audio_bytes_to_numpy(b"")
        
        assert isinstance(result, np.ndarray)
        assert result.size == 0


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
