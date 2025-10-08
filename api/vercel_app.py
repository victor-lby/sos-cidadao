"""
Vercel-specific Flask application entry point.
Optimized for serverless deployment with connection pooling and caching.
"""

import os
from app import create_app

# Create the Flask application instance
app = create_app()

# Vercel expects the WSGI application to be named 'app'
# This is the entry point for Vercel serverless functions
if __name__ == "__main__":
    # This won't be called in Vercel, but useful for local testing
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))