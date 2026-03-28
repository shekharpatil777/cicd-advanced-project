from flask import Flask, jsonify, request
import os
import logging
from datetime import datetime
import sys
import json
from pathlib import Path

# Add mlops to path for imports
sys.path.append('/app')
sys.path.append('/app/mlops')

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model state (will be loaded on startup)
model_state = {
    'model': None,
    'scaler': None,
    'features': None,
    'metadata': None,
    'model_path': None
}

def load_model():
    """Load trained model and artifacts"""
    logger.info("Loading latest model...")
    try:
        # Try to import ML dependencies
        try:
            import joblib
            from pathlib import Path
        except ImportError as e:
            logger.warning(f"ML dependencies not available: {e}")
            return False

        model_base_path = Path("/app/models")
        if not model_base_path.exists():
            # Try relative path for local development
            model_base_path = Path("models")

        # Read latest model reference
        latest_file = model_base_path / "latest.json"
        if not latest_file.exists():
            logger.warning(f"Latest model reference not found: {latest_file}")
            return False

        with open(latest_file, 'r') as f:
            latest_info = json.load(f)

        latest_version = latest_info['latest_version']
        model_path = Path(latest_version)
        logger.info(f"Loading model version: {latest_version}")

        # Load model
        model_file = model_path / "model.joblib"
        model = joblib.load(model_file)
        logger.info(f"✅ Model loaded: {model.__class__.__name__}")

        # Load scaler
        scaler_file = model_path / "scaler.joblib"
        scaler = joblib.load(scaler_file)
        logger.info("✅ Scaler loaded")

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

# Load model on startup
load_model()

@app.route('/')
def hello():
    """Main endpoint - reads secret from environment"""
    secret = os.getenv("MY_SECRET", "No Secret Found")
    environment = os.getenv("ENVIRONMENT", "development")
    logger.info(f"Hello request from environment: {environment}")
    return {
        "message": "Hello DevOps 🚀",
        "environment": environment,
        "secret_configured": secret != "No Secret Found"
    }

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200

@app.route('/ready')
def ready():
    """Readiness check endpoint"""
    return jsonify({"status": "ready", "timestamp": datetime.now().isoformat()}), 200

@app.route('/version')
def version():
    """Version endpoint"""
    return jsonify({
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.now().isoformat()
    }), 200

# ML Prediction Endpoints
@app.route('/model-info', methods=['GET'])
def model_info():
    """Get model information and metadata"""
    if not model_state['model']:
        return jsonify({"error": "Model not loaded"}), 503

    return jsonify({
        "model_type": model_state['model'].__class__.__name__,
        "features": model_state['features'],
        "metadata": model_state['metadata'],
        "model_path": model_state['model_path']
    }), 200

@app.route('/predict', methods=['POST'])
def predict():
    """Make prediction for single sample"""
    if not model_state['model']:
        return jsonify({"error": "Model not loaded"}), 503

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Validate required features
        missing_features = []
        for feature in model_state['features']:
            if feature not in data:
                missing_features.append(feature)

        if missing_features:
            return jsonify({
                "error": f"Missing required features: {missing_features}",
                "required_features": model_state['features']
            }), 400

        # Prepare input data
        import pandas as pd
        import numpy as np

        input_data = pd.DataFrame([data])
        input_scaled = model_state['scaler'].transform(input_data)

        # Make prediction
        prediction = model_state['model'].predict(input_scaled)[0]
        prediction_proba = model_state['model'].predict_proba(input_scaled)[0]

        return jsonify({
            "prediction": int(prediction),
            "prediction_probability": {
                "class_0": float(prediction_proba[0]),
                "class_1": float(prediction_proba[1])
            },
            "model_version": model_state['metadata'].get('version'),
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Prediction error: {str(e)}", exc_info=True)
        return jsonify({"error": "Prediction failed", "details": str(e)}), 500

@app.route('/batch-predict', methods=['POST'])
def batch_predict():
    """Make predictions for multiple samples"""
    if not model_state['model']:
        return jsonify({"error": "Model not loaded"}), 503

    try:
        data = request.get_json()
        if not data or 'samples' not in data:
            return jsonify({"error": "No samples provided in JSON data"}), 400

        samples = data['samples']
        if not isinstance(samples, list) or len(samples) == 0:
            return jsonify({"error": "Samples must be a non-empty list"}), 400

        # Validate all samples have required features
        predictions = []
        for i, sample in enumerate(samples):
            if not isinstance(sample, dict):
                return jsonify({"error": f"Sample {i} must be a dictionary"}), 400

            missing_features = []
            for feature in model_state['features']:
                if feature not in sample:
                    missing_features.append(feature)

            if missing_features:
                return jsonify({
                    "error": f"Sample {i} missing features: {missing_features}",
                    "required_features": model_state['features']
                }), 400

            # Prepare input data
            import pandas as pd
            import numpy as np

            input_data = pd.DataFrame([sample])
            input_scaled = model_state['scaler'].transform(input_data)

            # Make prediction
            prediction = model_state['model'].predict(input_scaled)[0]
            prediction_proba = model_state['model'].predict_proba(input_scaled)[0]

            predictions.append({
                "sample_index": i,
                "prediction": int(prediction),
                "prediction_probability": {
                    "class_0": float(prediction_proba[0]),
                    "class_1": float(prediction_proba[1])
                }
            })

        return jsonify({
            "predictions": predictions,
            "total_samples": len(predictions),
            "model_version": model_state['metadata'].get('version'),
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Batch prediction error: {str(e)}", exc_info=True)
        return jsonify({"error": "Batch prediction failed", "details": str(e)}), 500

@app.route('/ml-metrics', methods=['GET'])
def ml_metrics():
    """Get ML-specific metrics"""
    try:
        # Try to import prometheus client
        try:
            from prometheus_client import Counter, Histogram, generate_latest
        except ImportError:
            return jsonify({"error": "Prometheus client not available"}), 503

        # Return metrics (this would be enhanced with actual ML metrics)
        return jsonify({
            "model_loaded": model_state['model'] is not None,
            "model_type": model_state['model'].__class__.__name__ if model_state['model'] else None,
            "features_count": len(model_state['features']) if model_state['features'] else 0,
            "model_version": model_state['metadata'].get('version') if model_state['metadata'] else None,
            "last_updated": model_state['metadata'].get('timestamp') if model_state['metadata'] else None
        }), 200

    except Exception as e:
        logger.error(f"Metrics error: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to get metrics", "details": str(e)}), 500
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Not Found", "message": str(error)}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({"error": "Internal Server Error", "message": str(error)}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "False") == "True"
    app.run(host='0.0.0.0', port=port, debug=debug)
