"""
Observability Middleware

Flask middleware for adding OpenTelemetry instrumentation and structured logging
to all HTTP requests.
"""

import time
import logging
from flask import Flask, request, g
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor


def add_observability_middleware(app: Flask):
    """Add OpenTelemetry instrumentation and request logging to Flask app."""
    
    # Auto-instrument Flask
    FlaskInstrumentor().instrument_app(app)
    
    logger = logging.getLogger(__name__)
    
    @app.before_request
    def before_request():
        """Set up request context and start timing."""
        g.start_time = time.time()
        g.trace_id = None
        
        # Get current span for trace correlation
        span = trace.get_current_span()
        if span.is_recording():
            span_context = span.get_span_context()
            g.trace_id = format(span_context.trace_id, "032x")
            
            # Add request attributes to span
            span.set_attributes({
                "http.method": request.method,
                "http.url": request.url,
                "http.scheme": request.scheme,
                "http.host": request.host,
                "http.target": request.path,
                "http.user_agent": request.headers.get("User-Agent", ""),
                "http.remote_addr": request.remote_addr
            })
    
    @app.after_request
    def after_request(response):
        """Log request completion and add response attributes to span."""
        duration_ms = (time.time() - g.get('start_time', time.time())) * 1000
        
        # Add response attributes to current span
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attributes({
                "http.status_code": response.status_code,
                "http.response.size": len(response.get_data()),
                "http.duration_ms": round(duration_ms, 2)
            })
        
        # Structured request logging
        logger.info(
            "HTTP request completed",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "remote_addr": request.remote_addr,
                    "user_agent": request.headers.get("User-Agent", ""),
                    "trace_id": g.get('trace_id'),
                    "request_size": request.content_length or 0,
                    "response_size": len(response.get_data())
                }
            }
        )
        
        # Add trace ID to response headers for debugging
        if g.get('trace_id'):
            response.headers['X-Trace-Id'] = g.trace_id
        
        return response