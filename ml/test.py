#!/usr/bin/env python3
"""Test ML model predictions"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from blackbox import StuckDetector

def test_ml_model():
    print("Testing ML Model\n")
    
    detector = StuckDetector()
    
    # Test Case 1: Obviously stuck (repeated errors)
    stuck_signals = {
        'error_events': 15,
        'error_repeat_count': 10,
        'error_persistence': 0.9,
        'idle_time_total': 60,
        'backspace_ratio': 0.8
    }
    
    result = detector.is_stuck(stuck_signals)
    prob = detector.get_stuck_probability(stuck_signals)
    
    print(f"Test 1 - Repeated Errors:")
    print(f"  Prediction: {'STUCK ✓' if result else 'NOT STUCK ✗'}")
    print(f"  Probability: {prob:.2%}")
    assert result == True, "Should predict stuck for repeated errors"
    
    # Test Case 2: Obviously productive
    productive_signals = {
        'edit_velocity': 10,
        'error_events': 1,
        'run_attempt_count': 5,
        'idle_time_total': 10
    }
    
    result = detector.is_stuck(productive_signals)
    prob = detector.get_stuck_probability(productive_signals)
    
    print(f"\nTest 2 - Productive:")
    print(f"  Prediction: {'STUCK ✗' if result else 'NOT STUCK ✓'}")
    print(f"  Probability: {prob:.2%}")
    assert result == False, "Should predict not stuck for productive coding"
    
    print("\nAll tests passed!")

if __name__ == "__main__":
    test_ml_model()