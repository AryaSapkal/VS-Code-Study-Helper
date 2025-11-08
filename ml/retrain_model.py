import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import joblib
from sqlalchemy import create_engine
from models import StuckPredictor
from features import get_feature_names
from sklearn.metrics import classification_report, confusion_matrix

class ModelRetrainer:
    """Retrain model with real user feedback"""
    
    def __init__(self, db_connection_string: str):
        self.engine = create_engine(db_connection_string)
        self.feature_names = get_feature_names()
    
    def fetch_real_data(self) -> pd.DataFrame:
        """Fetch labeled data from production"""
        
        query = """
        SELECT 
            features,
            CASE 
                WHEN source = 'manual_button' THEN 1
                WHEN source = 'predicted_confirmed' THEN 1
                WHEN source = 'predicted_rejected' THEN 0
            END as is_stuck
        FROM stuck_events
        WHERE features IS NOT NULL
        
        UNION ALL
        
        SELECT 
            features,
            CASE 
                WHEN user_feedback = 'correct' AND predicted_stuck THEN 1
                WHEN user_feedback = 'correct' AND NOT predicted_stuck THEN 0
                WHEN user_feedback = 'incorrect' AND predicted_stuck THEN 0
                WHEN user_feedback = 'incorrect' AND NOT predicted_stuck THEN 1
            END as is_stuck
        FROM predictions
        WHERE user_feedback != 'no_feedback'
        AND features IS NOT NULL
        """
        
        df = pd.read_sql(query, self.engine)
        
        # Expand JSON features into columns
        features_df = pd.json_normalize(df['features'])
        features_df['is_stuck'] = df['is_stuck']
        
        return features_df
    
    def load_synthetic_data(self) -> pd.DataFrame:
        """Load original synthetic training data"""
        return pd.read_csv('data/synthetic/training_data.csv')
    
    def retrain_model(self, strategy: str = 'combine'):
        """
        Retrain model with real data
        
        Strategies:
        - 'combine': Mix synthetic + real data
        - 'real_only': Train only on real data (if enough samples)
        - 'fine_tune': Start from synthetic model, fine-tune on real data
        """
        
        print("=" * 60)
        print("MODEL RETRAINING PIPELINE")
        print("=" * 60)
        
        # Fetch real data
        real_data = self.fetch_real_data()
        print(f"\n✓ Fetched {len(real_data)} real samples from production")
        print(f"  Stuck: {real_data['is_stuck'].sum()}")
        print(f"  Productive: {(~real_data['is_stuck'].astype(bool)).sum()}")
        
        if len(real_data) < 50:
            print("\n⚠ Not enough real data yet. Need at least 50 samples.")
            print("  Keeping current model.")
            return
        
        # Load synthetic data
        synthetic_data = self.load_synthetic_data()
        print(f"\n✓ Loaded {len(synthetic_data)} synthetic samples")
        
        # Prepare training data based on strategy
        if strategy == 'combine':
            # Weight real data more heavily
            real_weight = min(3.0, len(synthetic_data) / len(real_data))
            print(f"\nStrategy: COMBINE (real data weight: {real_weight:.1f}x)")
            
            # Duplicate real data to give it more weight
            real_repeated = pd.concat([real_data] * int(real_weight), ignore_index=True)
            training_data = pd.concat([synthetic_data, real_repeated], ignore_index=True)
            
        elif strategy == 'real_only':
            if len(real_data) < 500:
                print("\n⚠ Not enough real data for real_only strategy (need 500+)")
                print("  Falling back to 'combine' strategy")
                return self.retrain_model(strategy='combine')
            
            print("\nStrategy: REAL ONLY")
            training_data = real_data
        
        elif strategy == 'fine_tune':
            print("\nStrategy: FINE TUNE")
            # Train on synthetic first, then continue training on real
            # (This is model-dependent, shown below)
        
        print(f"\n✓ Training data prepared: {len(training_data)} samples")
        
        # Split features and labels
        X = training_data[self.feature_names]
        y = training_data['is_stuck']
        
        # Train-test split (use real data for test if available)
        from sklearn.model_selection import train_test_split
        
        if len(real_data) > 100:
            # Use real data for testing!
            X_train = X
            y_train = y
            X_test = real_data[self.feature_names]
            y_test = real_data['is_stuck']
            print("\n✓ Using ALL real data for testing (most reliable)")
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, stratify=y, random_state=42
            )
        
        # Train model
        print("\n" + "=" * 60)
        print("TRAINING MODEL")
        print("=" * 60)
        
        model = StuckPredictor(model_type='xgboost')
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        accuracy = (y_pred == y_test).mean()
        
        print(f"\n✓ Model trained!")
        print(f"  Accuracy: {accuracy:.3f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, 
                                   target_names=['Productive', 'Stuck']))
        
        print("\nConfusion Matrix:")
        print(confusion_matrix(y_test, y_pred))
        
        # Save model with version
        version = f"v{len(list(Path('models').glob('stuck_predictor_v*.pkl'))) + 1}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = f"models/stuck_predictor_{version}_{timestamp}.pkl"
        
        model.save(model_path)
        print(f"\n✓ Model saved: {model_path}")
        
        # Save metadata
        metadata = {
            'version': version,
            'timestamp': timestamp,
            'training_samples': len(X_train),
            'real_samples': len(real_data),
            'synthetic_samples': len(synthetic_data),
            'strategy': strategy,
            'accuracy': accuracy,
            'test_samples': len(X_test)
        }
        
        import json
        with open(f'models/metadata_{version}.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print("\n" + "=" * 60)
        print("✓ RETRAINING COMPLETE")
        print("=" * 60)
        
        return model_path
    
    def compare_models(self, old_model_path: str, new_model_path: str):
        """Compare old vs new model on real test data"""
        
        real_data = self.fetch_real_data()
        if len(real_data) < 20:
            print("Not enough real data for comparison")
            return
        
        X_test = real_data[self.feature_names]
        y_test = real_data['is_stuck']
        
        old_model = joblib.load(old_model_path)
        new_model = joblib.load(new_model_path)
        
        old_pred = old_model.predict(X_test)
        new_pred = new_model.predict(X_test)
        
        old_acc = (old_pred == y_test).mean()
        new_acc = (new_pred == y_test).mean()
        
        print(f"\nModel Comparison on Real Data ({len(real_data)} samples):")
        print(f"  Old model: {old_acc:.3f}")
        print(f"  New model: {new_acc:.3f}")
        print(f"  Improvement: {(new_acc - old_acc):.3f}")
        
        if new_acc > old_acc:
            print("\n✓ New model is better! Deploy it.")
        else:
            print("\n⚠ New model is worse. Keep old model.")