#!/usr/bin/env python3
"""
ML Model Serving API

Exposes trained model for predictions:
- /health - Health check
- /predict - Single prediction
- /batch-predict - Batch predictions
- /model-info - Model metadata

Production considerations:
- Model versioning
- Request validation
- Error handling
- Performance monitoring
- Prometheus metrics
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
import joblib
from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, generate_latest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Prometheus metrics
prediction_counter = Counter('predictions_total', 'Total predictions', ['status'])
prediction_latency = Histogram('prediction_latency_seconds', 'Prediction latency')
model_load_time = Histogram('model_load_time_seconds', 'Model load time')

# Global model state
model_state = {
    'model': None,
    'scaler': None,
    'features': None,
    'metadata': None,
    'model_path': None
}


def load_model(model_dir: str = "models/latest"):
    """Load trained model and artifacts"""
    logger.info(f"Loading model from {model_dir}...")
    
    try:
        model_path = Path(model_dir)
        
        # Load model
        model_file = model_path / "model.joblib"
        model = joblib.load(model_file)
        logger.info(f"✅ Model loaded: {model.__class__.__name__}")
        
        # Load scaler
        scaler_file = model_path / "scaler.joblib"
        scaler = joblib.load(scaler_file)
        logger.info(f"✅ Scaler loaded")
        
        # Load features
        features_file = model_path / "features.json"
        with open(features_file, 'r') as f:
            features = json.load(f)
        logger.info(f"✅ Features loaded: {len(features)} features")
        
        # Load metadata
        metadata_file = model_path / "metadata.json"
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        logger.info(f"✅ Metadata loaded: {metadata.get('version')} - {metadata.get('timestamp')}")
        
        # Update global state
        model_state['model'] = model
        model_state['scaler'] = scaler
        model_state['features'] = features
        model_state['metadata'] = metadata
        model_state['model_path'] = str(model_path)
        
        logger.info(f"Model Performance: {metadata.get('metrics', {})}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}", exc_info=True)
        return False


def validate_request(data: Dict[str, Any]) -> tuple[bool, str]:
    """Validate prediction request"""
    
    if not isinstance(data, dict):
        return False, "Request must be JSON object"
    
    required_features = model_state['features']
    
    if 'features' not in data:
        return False, f"Request must contain 'features' field"
    
    features_data = data['features']
    
    if not isinstance(features_data, list):
        return False, "Features must be a list"
    
    if len(features_data) != len(required_features):
        return False, f"Expected {len(required_features)} features, got {len(features_data)}"
    
    return True, "Valid"


def preprocess_features(raw_features: List[float]) -> np.ndarray:
    """Preprocess raw features"""
    X = np.array([raw_features], dtype=np.float32)
    X_scaled = model_state['scaler'].transform(X)
    return X_scaled


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    if model_state['model'] is None:
        return jsonify({'status': 'unhealthy', 'reason': 'Model not loaded'}), 503
    
    return jsonify({
        'status': 'healthy',
        'model_version': model_state['metadata'].get('version'),
        'model_type': model_state['metadata'].get('model_type'),
        'features': len(model_state['features'])
    }), 200


@app.route('/model-info', methods=['GET'])
def model_info():
    """Get model metadata"""
    if model_state['model'] is None:
        return jsonify({'error': 'Model not loaded'}), 503
    
    return jsonify({
        'version': model_state['metadata'].get('version'),
        'model_type': model_state['metadata'].get('model_type'),
        'timestamp': model_state['metadata'].get('timestamp'),
        'features': model_state['features'],
        'feature_count': len(model_state['features']),
        'metrics': model_state['metadata'].get('metrics'),
        'model_path': model_state['model_path']
    }), 200


@app.route('/predict', methods=['POST'])
@prediction_latency.time()
def predict():
    """Single prediction endpoint
    
    Request:
    {
        "features": [age, income, credit_score, loan_amount, employment_years, ...]
    }
    
    Response:
    {
        "prediction": 0 or 1,
        "probability": [prob_class_0, prob_class_1],
        "model_version": "v1.0"
    }
    """
    
    if model_state['model'] is None:
        prediction_counter.labels(status='error').inc()
        return jsonify({'error': 'Model not loaded'}), 503
    
    try:
        # Parse request
        data = request.get_json()
        
        # Validate
        valid, message = validate_request(data)
        if not valid:
            prediction_counter.labels(status='invalid').inc()
            return jsonify({'error': message}), 400
        
        # Preprocess features
        features = data['features']
        X_scaled = preprocess_features(features)
        
        # Make prediction
        prediction = model_state['model'].predict(X_scaled)[0]
        probability = model_state['model'].predict_proba(X_scaled)[0]
        
        # Log prediction
        logger.info(f"Prediction: {prediction}, Confidence: {max(probability):.4f}")
        
        prediction_counter.labels(status='success').inc()
        
        return jsonify({
            'prediction': int(prediction),
            'probability': [float(p) for p in probability],
            'confidence': float(max(probability)),
            'model_version': model_state['metadata'].get('version'),
            'features_used': len(features)
        }), 200
        
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}", exc_info=True)
        prediction_counter.labels(status='error').inc()
        return jsonify({'error': 'Prediction failed', 'details': str(e)}), 500


@app.route('/batch-predict', methods=['POST'])
def batch_predict():
    """Batch predictions endpoint
    
    Request:
    {
        "instances": [
            [age, income, credit_score, ...],
            [age, income, credit_score, ...],
            ...
        ]
    }
    
    Response:
    {
        "predictions": [0, 1, 0, ...],
        "probabilities": [[p0, p1], [p0, p1], ...],
        "batch_size": 3
    }
    """
    
    if model_state['model'] is None:
        return jsonify({'error': 'Model not loaded'}), 503
    
    try:
        data = request.get_json()
        
        if 'instances' not in data:
            return jsonify({'error': "Request must contain 'instances' field"}), 400
        
        instances = data['instances']
        
        if not isinstance(instances, list) or len(instances) == 0:
            return jsonify({'error': 'Instances must be non-empty list'}), 400
        
        # Preprocess all instances
        X = np.array(instances, dtype=np.float32)
        X_scaled = model_state['scaler'].transform(X)
        
        # Batch prediction
        predictions = model_state['model'].predict(X_scaled)
        probabilities = model_state['model'].predict_proba(X_scaled)
        
        logger.info(f"Batch prediction: {len(instances)} instances")
        prediction_counter.labels(status='success').inc()
        
        return jsonify({
            'predictions': [int(p) for p in predictions],
            'probabilities': probabilities.tolist(),
            'batch_size': len(instances),
            'model_version': model_state['metadata'].get('version')
        }), 200
        
    except Exception as e:
        logger.error(f"Batch prediction failed: {str(e)}", exc_info=True)
        prediction_counter.labels(status='error').inc()
        return jsonify({'error': 'Batch prediction failed', 'details': str(e)}), 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200


@app.errorhandler(404)
def not_found(error):
    """404 handler"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """500 handler"""
    return jsonify({'error': 'Internal server error'}), 500


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("ML Model Serving API")
    logger.info("=" * 60)
    
    # Load model
    model_loaded = load_model()
    
    if not model_loaded:
        logger.error("Failed to load model. Exiting.")
        return 1
    
    # Get configuration from environment
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Flask server on {host}:{port}")
    logger.info("Available endpoints:")
    logger.info("  GET  /health          - Health check")
    logger.info("  GET  /model-info      - Model metadata")
    logger.info("  POST /predict         - Single prediction")
    logger.info("  POST /batch-predict   - Batch predictions")
    logger.info("  GET  /metrics         - Prometheus metrics")
    
    # Start server
    app.run(host=host, port=port, debug=debug)
    
    return 0


if __name__ == "__main__":
    exit(main())
