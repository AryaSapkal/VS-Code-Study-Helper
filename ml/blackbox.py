"""
Blackbox Stuck Detection ML Model

Simple interface:
1. Pass in user signals → Get boolean stuck/not stuck
2. Log feedback → Accumulates training data
3. Auto-retrain → Improves over time
"""

import json
import joblib
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Literal
import pandas as pd
from models import StuckPredictor
from features import get_feature_names
from sklearn.model_selection import train_test_split


class StuckDetector:
    """
    Blackbox ML model for stuck detection
    
    Usage:
        detector = StuckDetector()
        
        # Check if stuck
        is_stuck = detector.is_stuck(user_signals)
        
        # Log feedback
        detector.log_feedback(user_signals, was_stuck=True)
        
        # Auto-retrain periodically
        detector.retrain_if_needed()
    """
    
    def __init__(
        self,
        model_path: str = 'models/stuck_predictor_v1.pkl',
        feedback_path: str = 'data/feedback.jsonl',
        auto_retrain_threshold: int = 100  # Retrain after N feedback samples
    ):
        """
        Initialize the detector
        
        Args:
            model_path: Path to trained model
            feedback_path: Path to store feedback data
            auto_retrain_threshold: Retrain after this many feedback samples
        """
        self.model_path = Path(model_path)
        self.feedback_path = Path(feedback_path)
        self.auto_retrain_threshold = auto_retrain_threshold
        
        # Create directories
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        self.feedback_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or create model
        if self.model_path.exists():
            self.model = StuckPredictor.load(str(self.model_path))
            print(f"✓ Loaded model from {self.model_path}")
        else:
            print("⚠ No existing model found. Training initial model...")
            self._train_initial_model()
        
        # Track feedback count
        self.feedback_count = self._count_feedback()
    
    def is_stuck(self, signals: Dict[str, float]) -> bool:
        """
        Main inference method: Check if user is stuck
        
        Args:
            signals: Dictionary of signal_name -> value
                    Expected keys (18 features):
                    - idle_time_total
                    - idle_time_max
                    - edit_events
                    - edit_velocity
                    - backspace_ratio
                    - cursor_moves
                    - cursor_distance
                    - cursor_entropy
                    - error_events
                    - unique_errors
                    - error_repeat_count
                    - error_persistence
                    - time_since_last_run
                    - run_attempt_count
                    - context_switches
                    - focus_time_avg
                    - comment_keywords
                    - comment_length_avg
        
        Returns:
            Boolean: True if stuck, False if productive
        """
        # Fill in missing signals with defaults
        signals = self._fill_defaults(signals)
        
        # Make prediction
        prediction = self.model.predict_single(signals)
        
        return prediction['is_stuck']
    
    def get_stuck_probability(self, signals: Dict[str, float]) -> float:
        """
        Get probability of being stuck (0-1)
        
        Args:
            signals: Dictionary of signal_name -> value
            
        Returns:
            Float between 0 and 1 (probability of being stuck)
        """
        signals = self._fill_defaults(signals)
        prediction = self.model.predict_single(signals)
        return prediction['probability_stuck']
    
    def log_feedback(
        self,
        signals: Dict[str, float],
        was_stuck: bool,
        source: Literal['manual', 'confirmed', 'rejected'] = 'manual'
    ):
        """
        Log user feedback for retraining
        
        Args:
            signals: The signals that were used for prediction
            was_stuck: Ground truth - was the user actually stuck?
            source: How we got this label
                   'manual' - user pressed "I'm stuck" button
                   'confirmed' - user clicked ✓ on prediction
                   'rejected' - user clicked ✗ on prediction
        """
        signals = self._fill_defaults(signals)
        
        feedback = {
            'timestamp': datetime.now().isoformat(),
            'signals': signals,
            'was_stuck': was_stuck,
            'source': source
        }
        
        # Append to feedback file (JSONL format)
        with open(self.feedback_path, 'a') as f:
            f.write(json.dumps(feedback) + '\n')
        
        self.feedback_count += 1
        print(f"✓ Logged feedback (total: {self.feedback_count})")
        
        # Auto-retrain if threshold reached
        if self.feedback_count >= self.auto_retrain_threshold:
            print(f"Auto-retraining triggered ({self.feedback_count} samples)")
            self.retrain_if_needed()
    
    def retrain_if_needed(self, force: bool = False):
        """
        Retrain model if enough feedback has accumulated
        
        Args:
            force: Force retrain even if threshold not met
        """
        if not force and self.feedback_count < self.auto_retrain_threshold:
            print(f"Not enough feedback yet ({self.feedback_count}/{self.auto_retrain_threshold})")
            return
        
        print("=" * 60)
        print("RETRAINING MODEL")
        print("=" * 60)
        
        # Load feedback data
        feedback_data = self._load_feedback()
        
        if len(feedback_data) < 50:
            print("⚠ Not enough real data (need at least 50 samples)")
            return
        
        # Load synthetic data
        synthetic_path = Path('data/synthetic/training_data.csv')
        if not synthetic_path.exists():
            print("⚠ No synthetic data found. Training on real data only...")
            training_data = feedback_data
        else:
            synthetic_data = pd.read_csv(synthetic_path)
            
            # Combine: weight real data 3x
            real_repeated = pd.concat([feedback_data] * 3, ignore_index=True)
            training_data = pd.concat([synthetic_data, real_repeated], ignore_index=True)
            
            print(f"✓ Combined {len(synthetic_data)} synthetic + {len(feedback_data)} real samples")
        
        # Train new model
        feature_names = get_feature_names()
        X = training_data[feature_names]
        y = training_data['is_stuck']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )
        
        new_model = StuckPredictor(model_type='xgboost', threshold=0.70)
        new_model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = new_model.predict(X_test)
        accuracy = (y_pred == y_test).mean()
        
        print(f"✓ New model accuracy: {accuracy:.3f}")
        
        # Save new model
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_model_path = self.model_path.parent / f"stuck_predictor_{timestamp}.pkl"
        new_model.save(str(new_model_path))
        
        # Update current model
        self.model = new_model
        self.model.save(str(self.model_path))
        
        # Reset feedback count
        self.feedback_count = 0
        
        # Archive old feedback
        archive_path = self.feedback_path.parent / f"feedback_archive_{timestamp}.jsonl"
        self.feedback_path.rename(archive_path)
        
        print(f"✓ Model retrained and saved to {self.model_path}")
        print(f"✓ Old feedback archived to {archive_path}")
        print("=" * 60)
    
    def _train_initial_model(self):
        """Train initial model from synthetic data"""
        from synthetic_data_generation import SyntheticDataGenerator
        
        print("Generating synthetic training data...")
        generator = SyntheticDataGenerator(seed=42)
        df = generator.generate_dataset(n_samples=10000)
        
        # Save synthetic data
        synthetic_path = Path('data/synthetic/training_data.csv')
        synthetic_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(synthetic_path, index=False)
        
        # Train model
        feature_names = get_feature_names()
        X = df[feature_names]
        y = df['is_stuck']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )
        
        self.model = StuckPredictor(model_type='xgboost', threshold=0.70)
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = (y_pred == y_test).mean()
        
        print(f"✓ Initial model trained with accuracy: {accuracy:.3f}")
        
        # Save
        self.model.save(str(self.model_path))
    
    def _fill_defaults(self, signals: Dict[str, float]) -> Dict[str, float]:
        """Fill in missing signals with default values"""
        defaults = {
            'idle_time_total': 0,
            'idle_time_max': 0,
            'edit_events': 0,
            'edit_velocity': 0,
            'backspace_ratio': 0,
            'cursor_moves': 0,
            'cursor_distance': 0,
            'cursor_entropy': 0,
            'error_events': 0,
            'unique_errors': 0,
            'error_repeat_count': 0,
            'error_persistence': 0,
            'time_since_last_run': 120,
            'run_attempt_count': 0,
            'context_switches': 0,
            'focus_time_avg': 60,
            'comment_keywords': 0,
            'comment_length_avg': 0
        }
        
        # Merge with provided signals
        full_signals = {**defaults, **signals}
        return full_signals
    
    def _load_feedback(self) -> pd.DataFrame:
        """Load all feedback data from JSONL file"""
        if not self.feedback_path.exists():
            return pd.DataFrame()
        
        feedback_list = []
        with open(self.feedback_path, 'r') as f:
            for line in f:
                if line.strip():
                    feedback_list.append(json.loads(line))
        
        if not feedback_list:
            return pd.DataFrame()
        
        # Convert to DataFrame
        rows = []
        for feedback in feedback_list:
            row = feedback['signals'].copy()
            row['is_stuck'] = 1 if feedback['was_stuck'] else 0
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def _count_feedback(self) -> int:
        """Count feedback samples"""
        if not self.feedback_path.exists():
            return 0
        
        with open(self.feedback_path, 'r') as f:
            return sum(1 for line in f if line.strip())
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            'model_loaded': self.model.is_fitted,
            'model_type': self.model.model_type,
            'threshold': self.model.threshold,
            'feedback_count': self.feedback_count,
            'auto_retrain_threshold': self.auto_retrain_threshold,
            'feedback_until_retrain': max(0, self.auto_retrain_threshold - self.feedback_count)
        }


# ============================================================================
# SIMPLE USAGE EXAMPLE
# ============================================================================

if __name__ == '__main__':
    # Initialize detector
    detector = StuckDetector()
    
    print("\n" + "=" * 60)
    print("EXAMPLE: Stuck Detection")
    print("=" * 60)
    
    # Example 1: Student with repeated errors (likely stuck)
    stuck_signals = {
        'idle_time_total': 45,
        'error_events': 12,
        'error_repeat_count': 8,
        'error_persistence': 0.85,
        'edit_velocity': 2.0,
        'backspace_ratio': 0.7
    }
    
    is_stuck = detector.is_stuck(stuck_signals)
    probability = detector.get_stuck_probability(stuck_signals)
    
    print(f"\n📊 Stuck Signals:")
    print(f"   Idle time: {stuck_signals['idle_time_total']}s")
    print(f"   Errors: {stuck_signals['error_events']}")
    print(f"   Error repeats: {stuck_signals['error_repeat_count']}")
    print(f"\n🔮 Prediction: {'STUCK' if is_stuck else 'PRODUCTIVE'}")
    print(f"   Probability: {probability:.3f}")
    
    # Example 2: Student making steady progress (not stuck)
    productive_signals = {
        'idle_time_total': 10,
        'error_events': 2,
        'error_repeat_count': 0,
        'edit_velocity': 8.0,
        'backspace_ratio': 0.2,
        'run_attempt_count': 5
    }
    
    is_stuck = detector.is_stuck(productive_signals)
    probability = detector.get_stuck_probability(productive_signals)
    
    print(f"\nProductive Signals:")
    print(f"   Idle time: {productive_signals['idle_time_total']}s")
    print(f"   Edit velocity: {productive_signals['edit_velocity']}")
    print(f"   Run attempts: {productive_signals['run_attempt_count']}")
    print(f"\n🔮 Prediction: {'STUCK' if is_stuck else 'PRODUCTIVE'}")
    print(f"   Probability: {probability:.3f}")
    
    # Example 3: Log feedback
    print("\n" + "=" * 60)
    print("EXAMPLE: Logging Feedback")
    print("=" * 60)
    
    # User pressed "I'm stuck" button
    detector.log_feedback(stuck_signals, was_stuck=True, source='manual')
    
    # User clicked ✓ on a correct prediction
    detector.log_feedback(productive_signals, was_stuck=False, source='confirmed')
    
    # Show stats
    stats = detector.get_stats()
    print(f"\n📈 Detector Stats:")
    print(f"   Model type: {stats['model_type']}")
    print(f"   Threshold: {stats['threshold']}")
    print(f"   Feedback collected: {stats['feedback_count']}")
    print(f"   Samples until retrain: {stats['feedback_until_retrain']}")
    
    print("\n✅ Done! The model will auto-retrain after 100 feedback samples.")



    # test out printing features
    # test out blackbox with test suite
    # test out backend with test suite?
    # make frontend
    # test everything