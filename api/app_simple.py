"""
Simple S.O.S Cidadão API - Minimal Flask Application for Testing

This is a minimal version to test the Docker setup.
"""

import os
from flask import Flask, jsonify
from datetime import datetime

# Create Flask app
app = Flask(__name__)

# Basic configuration
app.config['DEBUG'] = os.getenv('DEBUG', 'true').lower() == 'true'
app.config['ENVIRONMENT'] = os.getenv('ENVIRONMENT', 'development')

@app.route('/api/healthz')
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "sos-cidadao-api",
        "version": "1.0.0",
        "environment": app.config['ENVIRONMENT'],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

@app.route('/api/status')
def system_status():
    """Simple system status endpoint"""
    return jsonify({
        "service": "sos-cidadao-api",
        "version": "1.0.0",
        "environment": app.config['ENVIRONMENT'],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": "S.O.S Cidadão API is running"
    })

@app.route('/')
def root():
    """Root endpoint"""
    return jsonify({
        "message": "S.O.S Cidadão API",
        "version": "1.0.0",
        "docs": "/api/healthz"
    })

if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=app.config['DEBUG']
    )