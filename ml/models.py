import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import joblib
from typing import Optional, Dict, Any, Union
import json
from pathlib import Path

# Optional XGBoost import (graceful fallback if not available)
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except (ImportError, Exception) as e:
    XGBOOST_AVAILABLE = False
    print(f"⚠️ XGBoost not available ({e.__class__.__name__}), using scikit-learn models only")

class StuckPredictor:
    """Machine learning model for predicting if a student is stuck"""
    
    def __init__(self, model_type: str = 'xgboost', threshold: float = 0.7):
        """
        Initialize the stuck predictor
        
        Args:
            model_type: 'xgboost', 'random_forest', 'gradient_boosting', or 'logistic'
            threshold: Confidence threshold for predicting stuck (0-1)
        """
        self.model_type = model_type
        self.threshold = threshold
        self.scaler = StandardScaler()
        self.feature_names = None
        self.is_fitted = False
        
        # Type annotation for model attribute
        self.model: Union[RandomForestClassifier, GradientBoostingClassifier, LogisticRegression, Any]
        
        # Initialize the appropriate model
        if model_type == 'xgboost':
            if not XGBOOST_AVAILABLE:
                print("⚠️ XGBoost not available, falling back to RandomForest")
                model_type = 'random_forest'
                self.model_type = 'random_forest'
            else:
                self.model = xgb.XGBClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42,
                    eval_metric='logloss'
                )
        
        if model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        elif model_type == 'gradient_boosting':
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
        elif model_type == 'logistic':
            self.model = LogisticRegression(
                random_state=42,
                max_iter=1000
            )
        else:
            print(f"⚠️ Unknown model_type: {model_type}, falling back to RandomForest")
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            self.model_type = 'random_forest'
    
    def fit(self, X: pd.DataFrame, y: pd.Series):
        """
        Train the model
        
        Args:
            X: Feature DataFrame
            y: Target labels (1 = stuck, 0 = productive)
        """
        self.feature_names = list(X.columns)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict stuck/productive labels
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Array of predictions (1 = stuck, 0 = productive)
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")
        
        probas = self.predict_proba(X)
        return (probas[:, 1] >= self.threshold).astype(int)
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict probability of being stuck
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Array of shape (n_samples, 2) with [prob_productive, prob_stuck]
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")
        
        # Ensure features are in correct order
        X = X[self.feature_names]
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Predict
        return self.model.predict_proba(X_scaled)
    
    def predict_single(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Predict for a single sample with detailed output
        
        Args:
            features: Dictionary of feature_name -> value
            
        Returns:
            Dictionary with prediction, probability, and confidence
        """
        # Convert to DataFrame
        X = pd.DataFrame([features])
        
        # Get probabilities
        probas = self.predict_proba(X)[0]
        prob_stuck = probas[1]
        
        # Make prediction
        is_stuck = prob_stuck >= self.threshold
        
        # Calculate confidence (distance from threshold)
        confidence = abs(prob_stuck - self.threshold) / (1 - self.threshold) if is_stuck else abs(prob_stuck - self.threshold) / self.threshold
        confidence = min(confidence, 1.0)
        
        return {
            'is_stuck': bool(is_stuck),
            'probability_stuck': float(prob_stuck),
            'probability_productive': float(probas[0]),
            'confidence': float(confidence),
            'threshold': self.threshold
        }
    
    def get_feature_importance(self) -> pd.DataFrame:
        """Get feature importance scores"""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")
        
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            importances = np.abs(self.model.coef_[0])
        else:
            raise ValueError("Model doesn't support feature importance")
        
        return pd.DataFrame({
            'feature': self.feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
    
    def set_threshold(self, threshold: float):
        """Update the prediction threshold"""
        if not 0 <= threshold <= 1:
            raise ValueError("Threshold must be between 0 and 1")
        self.threshold = threshold
    
    def save(self, path: str):
        """Save model to disk"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'model_type': self.model_type,
            'threshold': self.threshold,
            'is_fitted': self.is_fitted
        }
        
        joblib.dump(model_data, path)
    
    @classmethod
    def load(cls, path: str) -> 'StuckPredictor':
        """Load model from disk"""
        model_data = joblib.load(path)
        
        predictor = cls(
            model_type=model_data['model_type'],
            threshold=model_data['threshold']
        )
        
        predictor.model = model_data['model']
        predictor.scaler = model_data['scaler']
        predictor.feature_names = model_data['feature_names']
        predictor.is_fitted = model_data['is_fitted']
        
        return predictor


class ThresholdOptimizer:
    """Optimize prediction threshold based on feedback"""
    
    def __init__(self, target_precision: float = 0.8, target_recall: float = 0.7):
        """
        Initialize threshold optimizer
        
        Args:
            target_precision: Desired precision (avoid false positives)
            target_recall: Desired recall (catch stuck cases)
        """
        self.target_precision = target_precision
        self.target_recall = target_recall
    
    def find_optimal_threshold(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        strategy: str = 'balanced'
    ) -> float:
        """
        Find optimal threshold
        
        Args:
            y_true: True labels
            y_proba: Predicted probabilities for stuck class
            strategy: 'balanced', 'high_precision', or 'high_recall'
            
        Returns:
            Optimal threshold value
        """
        from sklearn.metrics import precision_recall_curve, f1_score
        
        precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)
        
        if strategy == 'balanced':
            # Maximize F1 score
            f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
            best_idx = np.argmax(f1_scores)
            
        elif strategy == 'high_precision':
            # Find highest recall while maintaining target precision
            valid_idx = precisions >= self.target_precision
            if not any(valid_idx):
                best_idx = np.argmax(precisions)
            else:
                best_idx = np.where(valid_idx)[0][np.argmax(recalls[valid_idx])]
                
        elif strategy == 'high_recall':
            # Find highest precision while maintaining target recall
            valid_idx = recalls >= self.target_recall
            if not any(valid_idx):
                best_idx = np.argmax(recalls)
            else:
                best_idx = np.where(valid_idx)[0][np.argmax(precisions[valid_idx])]
        
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        # Handle edge case where best_idx might be out of bounds
        if best_idx >= len(thresholds):
            best_idx = len(thresholds) - 1
            
        return float(thresholds[best_idx])
    
    def evaluate_threshold(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        threshold: float
    ) -> Dict[str, float]:
        """Evaluate a specific threshold"""
        from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
        
        y_pred = (y_proba >= threshold).astype(int)
        
        return {
            'threshold': threshold,
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, zero_division=0),
            'recall': recall_score(y_true, y_pred, zero_division=0),
            'f1': f1_score(y_true, y_pred, zero_division=0)
        }