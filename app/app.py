from flask import Flask, jsonify
import os
import logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@app.errorhandler(404)
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
