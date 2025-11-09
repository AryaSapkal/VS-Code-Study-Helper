#!/usr/bin/env python3
"""
Quick test to verify ML model import and initialization
"""

import sys
from pathlib import Path

# Add ML directory to path
backend_dir = Path(__file__).parent
ml_path = backend_dir.parent / "ml"

print(f"🔍 Backend dir: {backend_dir}")
print(f"🔍 ML path: {ml_path}")
print(f"🔍 ML path exists: {ml_path.exists()}")

if ml_path.exists():
    print(f"📁 Files in ML: {list(ml_path.iterdir())}")
    
    sys.path.insert(0, str(ml_path))
    print(f"🐍 Python path: {sys.path[:3]}")
    
    try:
        from blackbox import StuckDetector
        print("✅ blackbox import successful")
        
        detector = StuckDetector()
        print("✅ StuckDetector created successfully")
        
        # Test prediction
        test_signals = {
            "edit_events": 5,
            "idle_time_total": 300,
            "error_events": 2,
            "backspace_ratio": 0.5
        }
        
        result = detector.predict(test_signals)
        print(f"🎯 Test prediction: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ ML directory not found")