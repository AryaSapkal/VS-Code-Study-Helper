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
    from typing import Dict, Any
    
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
            """Train initial model with some dummy data"""
            # Create minimal model with much higher threshold to reduce false positives
            self.model = StuckPredictor(model_type='random_forest', threshold=0.80)
            
            # Dummy training data
            feature_names = get_feature_names()
            n_features = len(feature_names)
            
            # Generate more conservative training data with clearer distinctions
            X_dummy = pd.DataFrame([
                # Clearly NOT stuck - normal productive coding
                [20, 15, 0.05, 1.0, 0, 0.1, 10, 25] + [0.1] * (n_features - 8),  # very productive
                [45, 20, 0.15, 1.8, 1, 0.2, 30, 40] + [0.2] * (n_features - 8),  # normal coding
                [60, 30, 0.25, 2.1, 1, 0.3, 50, 35] + [0.3] * (n_features - 8),  # thinking/reading
                
                # Clearly STUCK - obvious stuck patterns  
                [400, 8, 0.9, 3.5, 5, 0.8, 350, 5] + [0.9] * (n_features - 8),   # very stuck
                [600, 3, 0.95, 4.0, 8, 0.9, 580, 2] + [0.95] * (n_features - 8), # extremely stuck
                [300, 5, 0.85, 3.2, 6, 0.8, 280, 8] + [0.8] * (n_features - 8),  # clearly stuck
            ], columns=feature_names)
            
            y_dummy = pd.Series([0, 0, 0, 1, 1, 1])  # not stuck x3, stuck x3
            
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

    ML_AVAILABLE = True
    print("✅ ML wrapper system loaded successfully")
    
except Exception as e:
    ML_AVAILABLE = False
    StuckDetector = None
    print(f"❌ ML wrapper failed to load: {e}")