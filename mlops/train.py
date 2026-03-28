#!/usr/bin/env python3
"""
Production ML Training & Serving Pipeline

This implements a real ML workflow:
1. Load data from S3 (or local)
2. Preprocess and feature engineering
3. Train classification model
4. Evaluate metrics
5. Save artifacts to model registry
6. Prepare for serving API

Production considerations:
- Model versioning
- Metrics logging (MLflow)
- Performance tracking
- Model drift detection
"""

import os
import json
import logging
import pickle
import joblib
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MLPipeline:
    """Production ML training pipeline"""
    
    def __init__(self, model_dir: str = "models", data_dir: str = "data"):
        self.model_dir = Path(model_dir)
        self.data_dir = Path(data_dir)
        self.model_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        
        self.model = None
        self.scaler = None
        self.label_encoders = {}
        self.feature_names = None
        self.metrics = {}
        
    def load_data(self) -> pd.DataFrame:
        """Load training data from CSV or S3"""
        logger.info("Loading training data...")
        
        # For demo: create synthetic dataset
        # In production: load from S3 or database
        np.random.seed(42)
        n_samples = 1000
        
        data = pd.DataFrame({
            'age': np.random.randint(18, 80, n_samples),
            'income': np.random.randint(20000, 150000, n_samples),
            'credit_score': np.random.randint(300, 850, n_samples),
            'loan_amount': np.random.randint(1000, 500000, n_samples),
            'employment_years': np.random.randint(0, 40, n_samples),
            'default': np.random.randint(0, 2, n_samples)
        })
        
        logger.info(f"Loaded {len(data)} samples with {len(data.columns)} features")
        logger.info(f"\nDataset Summary:\n{data.describe()}")
        
        return data
    
    def preprocess_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess and feature engineering"""
        logger.info("Preprocessing data...")
        
        # Copy data
        df = data.copy()
        
        # Handle missing values (if any)
        df = df.fillna(df.mean())
        
        # Feature engineering
        df['income_to_loan_ratio'] = df['income'] / (df['loan_amount'] + 1)
        df['credit_income_ratio'] = df['credit_score'] / (df['income'] + 1)
        df['age_group'] = pd.cut(df['age'], bins=5, labels=False)
        
        logger.info(f"Created engineered features. Total: {df.shape[1]}")
        
        # Separate features and target
        X = df.drop('default', axis=1)
        y = df['default'].values
        
        self.feature_names = X.columns.tolist()
        
        # Store feature names for serving
        logger.info(f"Features: {self.feature_names}")
        
        return X.values, y
    
    def train_model(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Train multiple models and select best"""
        logger.info("Training models...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        logger.info(f"Training set: {X_train_scaled.shape}, Test set: {X_test_scaled.shape}")
        
        # Train models
        models = {
            'random_forest': RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                random_state=42
            )
        }
        
        best_model = None
        best_score = 0
        model_scores = {}
        
        for name, model in models.items():
            logger.info(f"Training {name}...")
            
            # Train
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            score = f1_score(y_test, y_pred)
            model_scores[name] = score
            
            logger.info(f"{name} F1-Score: {score:.4f}")
            
            if score > best_score:
                best_score = score
                best_model = model
                self.model = model
        
        logger.info(f"\n✅ Best Model: {best_model.__class__.__name__} (F1: {best_score:.4f})")
        
        return {
            'X_train': X_train_scaled,
            'X_test': X_test_scaled,
            'y_train': y_train,
            'y_test': y_test,
            'model_scores': model_scores
        }
    
    def evaluate_model(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Comprehensive model evaluation"""
        logger.info("Evaluating model...")
        
        X_test = data['X_test']
        y_test = data['y_test']
        
        # Predictions
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        
        # Metrics
        metrics = {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'precision': float(precision_score(y_test, y_pred)),
            'recall': float(recall_score(y_test, y_pred)),
            'f1_score': float(f1_score(y_test, y_pred)),
            'roc_auc': float(roc_auc_score(y_test, y_pred_proba)),
        }
        
        # Classification report
        report = classification_report(y_test, y_pred, output_dict=True)
        
        logger.info("\nModel Performance Metrics:")
        logger.info(f"  Accuracy:  {metrics['accuracy']:.4f}")
        logger.info(f"  Precision: {metrics['precision']:.4f}")
        logger.info(f"  Recall:    {metrics['recall']:.4f}")
        logger.info(f"  F1-Score:  {metrics['f1_score']:.4f}")
        logger.info(f"  ROC-AUC:   {metrics['roc_auc']:.4f}")
        
        # Confusion Matrix
        cm = confusion_matrix(y_test, y_pred)
        logger.info(f"\nConfusion Matrix:\n{cm}")
        
        self.metrics = metrics
        return metrics
    
    def save_model(self, version: str = "latest") -> str:
        """Save model artifacts with versioning"""
        logger.info("Saving model artifacts...")
        
        # Create version directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_dir = self.model_dir / f"{version}_{timestamp}"
        version_dir.mkdir(exist_ok=True)
        
        # Save model
        model_path = version_dir / "model.joblib"
        joblib.dump(self.model, model_path)
        logger.info(f"Model saved: {model_path}")
        
        # Save scaler
        scaler_path = version_dir / "scaler.joblib"
        joblib.dump(self.scaler, scaler_path)
        logger.info(f"Scaler saved: {scaler_path}")
        
        # Save feature names
        features_path = version_dir / "features.json"
        with open(features_path, 'w') as f:
            json.dump(self.feature_names, f)
        logger.info(f"Features saved: {features_path}")
        
        # Save metadata
        metadata = {
            'version': version,
            'timestamp': timestamp,
            'model_type': self.model.__class__.__name__,
            'metrics': self.metrics,
            'feature_count': len(self.feature_names),
            'features': self.feature_names
        }
        
        metadata_path = version_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Metadata saved: {metadata_path}")
        
        # Create symlink to latest
        latest_link = self.model_dir / "latest"
        if latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(version_dir)
        
        logger.info(f"✅ Model artifacts saved to: {version_dir}")
        
        return str(version_dir)
    
    def run(self) -> Dict[str, Any]:
        """Execute full pipeline"""
        logger.info("=" * 60)
        logger.info("Starting ML Training Pipeline")
        logger.info("=" * 60)
        
        try:
            # Load data
            data = self.load_data()
            
            # Preprocess
            X, y = self.preprocess_data(data)
            
            # Train
            train_data = self.train_model(X, y)
            
            # Evaluate
            metrics = self.evaluate_model(train_data)
            
            # Save
            model_path = self.save_model(version="v1.0")
            
            # Summary
            result = {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'metrics': metrics,
                'model_path': model_path,
                'feature_count': len(self.feature_names),
                'features': self.feature_names
            }
            
            logger.info("\n" + "=" * 60)
            logger.info("Pipeline Completed Successfully!")
            logger.info("=" * 60)
            logger.info(json.dumps(result, indent=2))
            
            return result
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }


def main():
    """Main entry point"""
    pipeline = MLPipeline()
    result = pipeline.run()
    
    # Print results
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    
    # Exit code
    exit(0 if result['status'] == 'success' else 1)


if __name__ == "__main__":
    main()