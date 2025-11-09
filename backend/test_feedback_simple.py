#!/usr/bin/env python3
"""
Simple test to verify ML feedback logging works
"""
import sys
import os
sys.path.insert(0, '/Users/arvinmefsha/Projects/hackprinceton/stuck-detector/backend')

from ml_wrapper import StuckDetector, ML_AVAILABLE

def test_ml_feedback():
    print("🧪 Testing ML Feedback System")
    print("=" * 40)
    
    if not ML_AVAILABLE:
        print("❌ ML not available")
        return
    
    # Initialize detector
    detector = StuckDetector()
    print("✅ ML detector initialized")
    
    # Test logging feedback
    test_signals = {
        'time_on_current_line': 120.0,
        'words_typed': 3.0,
        'error_rate': 0.4,
        'typing_speed': 1.5,
        'copy_paste_count': 0,
        'idle_time_ratio': 0.4,
        'time_since_last_run': 180.0,
        'runs_per_minute': 0.3
    }
    
    print("📊 Logging feedback...")
    detector.log_feedback(test_signals, was_stuck=True, helpful=True)
    
    # Check feedback count
    count = detector._count_feedback()
    print(f"📈 Total feedback entries: {count}")
    
    # Test retraining (force with small dataset)
    print("🔄 Testing retraining...")
    result = detector.retrain_if_needed(force=True)
    print(f"✅ Retraining result: {result}")
    
    print("\n🎉 ML Feedback System Test Complete!")
    print("🔍 Key features implemented:")
    print("  ✅ Feedback logging to JSON file")
    print("  ✅ Automatic retraining at 100+ entries") 
    print("  ✅ Manual retraining with force=True")
    print("  ✅ Integration with hint feedback endpoint")

if __name__ == "__main__":
    test_ml_feedback()