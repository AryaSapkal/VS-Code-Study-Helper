"""
ML Wrapper to handle import issues
"""
import sys
import os
from pathlib import Path

# Add ML directory to path
ml_path = Path(__file__).parent.parent / "ml"
sys.path.insert(0, str(ml_path))

try:
    # Import ML components
    from models import StuckPredictor
    from features import get_feature_names
    import numpy as np
    import pandas as pd
    from pathlib import Path
    import joblib
    import json
    from typing import Dict, Any, Optional
    
    class StuckDetector:
        """Wrapper for ML stuck detection with correct imports"""
        
        def __init__(self):
            self.model_path = ml_path / "models" / "stuck_predictor_v1.pkl"
            
            # Create directories
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load or create model
            if self.model_path.exists():
                self.model = StuckPredictor.load(str(self.model_path))
                print(f"✓ Loaded model from {self.model_path}")
            else:
                print("⚠ No existing model found. Training initial model...")
                self._train_initial_model()
        
        def _train_initial_model(self):
            """Train initial model with very aggressive threshold for maximum hint coverage"""
            # Create model with very low threshold to catch all potentially stuck students
            self.model = StuckPredictor(model_type='random_forest', threshold=0.35)
            
            # Dummy training data
            feature_names = get_feature_names()
            n_features = len(feature_names)
            
            # Generate training data heavily biased toward catching stuck students
            X_dummy = pd.DataFrame([
                # Very clearly NOT stuck - only the most obviously productive cases
                [15, 20, 0.02, 1.5, 0, 0.05, 5, 30] + [0.05] * (n_features - 8),  # super productive
                
                # Everything else should trigger hints - err on side of helping
                [60, 10, 0.3, 2.0, 1, 0.3, 50, 20] + [0.3] * (n_features - 8),   # might be stuck
                [90, 8, 0.4, 2.5, 2, 0.4, 80, 15] + [0.4] * (n_features - 8),    # probably stuck  
                [120, 6, 0.5, 2.8, 3, 0.5, 100, 12] + [0.5] * (n_features - 8),  # likely stuck
                [150, 5, 0.6, 3.0, 4, 0.6, 130, 10] + [0.6] * (n_features - 8),  # definitely stuck
                [200, 4, 0.7, 3.2, 5, 0.7, 180, 8] + [0.7] * (n_features - 8),   # very stuck
                [300, 3, 0.8, 3.5, 6, 0.8, 280, 6] + [0.8] * (n_features - 8),   # extremely stuck
                [500, 2, 0.9, 4.0, 8, 0.9, 480, 3] + [0.9] * (n_features - 8),   # super stuck
            ], columns=feature_names)
            
            y_dummy = pd.Series([0, 1, 1, 1, 1, 1, 1, 1])  # not stuck x1, stuck x7 (maximum false positives!)
            
            self.model.fit(X_dummy, y_dummy)
            self.model.save(str(self.model_path))
            print(f"✓ Initial model trained and saved to {self.model_path}")
        
        def _fill_defaults(self, signals: Dict[str, float]) -> Dict[str, float]:
            """Fill missing signals with default values"""
            feature_names = get_feature_names()
            filled = signals.copy()
            
            for name in feature_names:
                if name not in filled:
                    filled[name] = 0.0
            
            return filled
        
        def predict_full(self, signals: Dict[str, float]) -> Dict[str, Any]:
            """Get full prediction with enhanced confidence analysis"""
            signals = self._fill_defaults(signals)
            
            # Convert signals dict to numpy array for model
            feature_names = get_feature_names()
            features = np.array([signals[name] for name in feature_names])
            
            # Get enhanced prediction
            prediction = self.model.predict_single(features)
            
            return prediction
        
        def log_feedback(self, signals: Dict[str, float], was_stuck: bool, helpful: Optional[bool] = None):
            """Log feedback for model retraining"""
            try:
                # Create feedback directory if it doesn't exist
                feedback_dir = Path(__file__).parent / "feedback_data"
                feedback_dir.mkdir(exist_ok=True)
                
                feedback_file = feedback_dir / "training_feedback.json"
                
                # Load existing feedback
                if feedback_file.exists():
                    with open(feedback_file, 'r') as f:
                        feedback_data = json.load(f)
                else:
                    feedback_data = {"entries": []}
                
                # Add new feedback entry
                entry = {
                    "timestamp": pd.Timestamp.now().isoformat(),
                    "signals": signals,
                    "was_stuck": was_stuck,
                    "helpful": helpful
                }
                feedback_data["entries"].append(entry)
                
                # Save updated feedback
                with open(feedback_file, 'w') as f:
                    json.dump(feedback_data, f, indent=2)
                
                print(f"✓ Logged feedback entry. Total entries: {len(feedback_data['entries'])}")
                
            except Exception as e:
                print(f"❌ Error logging feedback: {e}")
        
        def retrain_if_needed(self, force: bool = False):
            """Retrain model if enough feedback has been collected (100+ entries)"""
            try:
                feedback_file = Path(__file__).parent / "feedback_data" / "training_feedback.json"
                
                if not feedback_file.exists():
                    print("No feedback data available for retraining")
                    return False
                
                with open(feedback_file, 'r') as f:
                    feedback_data = json.load(f)
                
                entries = feedback_data.get("entries", [])
                
                if len(entries) < 100 and not force:
                    print(f"Not enough feedback for retraining ({len(entries)}/100 entries)")
                    return False
                
                print(f"🔄 Starting model retraining with {len(entries)} feedback entries...")
                
                # Prepare training data from feedback
                feature_names = get_feature_names()
                X_feedback = []
                y_feedback = []
                
                for entry in entries:
                    # Extract features in correct order
                    signals = entry["signals"]
                    features = [signals.get(name, 0.0) for name in feature_names]
                    X_feedback.append(features)
                    y_feedback.append(1 if entry["was_stuck"] else 0)
                
                if len(X_feedback) == 0:
                    print("No valid feedback data for retraining")
                    return False
                
                # Convert to DataFrame/Series
                X_new = pd.DataFrame(X_feedback, columns=feature_names)
                y_new = pd.Series(y_feedback)
                
                # Retrain the model
                print(f"Training with {len(X_new)} samples...")
                self.model.fit(X_new, y_new)
                
                # Save retrained model
                self.model.save(str(self.model_path))
                
                # Archive used feedback data
                archive_file = feedback_file.parent / f"archived_feedback_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json"
                feedback_file.rename(archive_file)
                
                print(f"✅ Model retrained successfully with {len(entries)} entries")
                print(f"📁 Feedback data archived to {archive_file.name}")
                
                return True
                
            except Exception as e:
                print(f"❌ Error during retraining: {e}")
                raise e
        
        def _count_feedback(self):
            """Count total feedback entries available"""
            try:
                feedback_file = Path(__file__).parent / "feedback_data" / "training_feedback.json"
                if not feedback_file.exists():
                    return 0
                
                with open(feedback_file, 'r') as f:
                    feedback_data = json.load(f)
                
                return len(feedback_data.get("entries", []))
            except Exception:
                return 0
        
        def _load_recent_feedback(self, limit: int = 50):
            """Load recent feedback entries for analysis"""
            try:
                feedback_file = Path(__file__).parent / "feedback_data" / "training_feedback.json"
                if not feedback_file.exists():
                    return []
                
                with open(feedback_file, 'r') as f:
                    feedback_data = json.load(f)
                
                entries = feedback_data.get("entries", [])
                return entries[-limit:] if len(entries) > limit else entries
            except Exception:
                return []

    ML_AVAILABLE = True
    print("✅ ML wrapper system loaded successfully")
    
except Exception as e:
    ML_AVAILABLE = False
    
    class FallbackStuckDetector:  # Dummy class for fallback
        def __init__(self): pass
        def predict_full(self, signals): return {"stuck": False, "confidence": 0.0}
        def log_feedback(self, signals, was_stuck, helpful=None): pass
        def retrain_if_needed(self, force=False): return False
        def _count_feedback(self): return 0
        def _load_recent_feedback(self, limit=50): return []
    
    StuckDetector = FallbackStuckDetector
    print(f"❌ ML wrapper failed to load: {e}")