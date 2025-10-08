"""
OpenTelemetry Configuration

Sets up distributed tracing, metrics, and logging for the S.O.S Cidadão API
following the observability patterns defined in the project guidelines.
"""

import os
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, AlwaysOn, AlwaysOff
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter


def setup_observability():
    """Initialize OpenTelemetry instrumentation based on environment configuration."""
    environment = os.getenv('ENVIRONMENT', 'development')
    otel_enabled = os.getenv('OTEL_ENABLED', 'true').lower() == 'true'
    service_name = 'sos-cidadao-api'
    service_version = os.getenv('SERVICE_VERSION', '1.0.0')
    
    if not otel_enabled:
        trace.set_tracer_provider(TracerProvider(sampler=AlwaysOff()))
        return
    
    # Environment-specific sampling
    if environment == 'production':
        sampler = TraceIdRatioBased(0.1)  # 10% sampling in production
    elif environment == 'staging':
        sampler = TraceIdRatioBased(0.5)  # 50% sampling in staging
    else:
        sampler = AlwaysOn()  # 100% sampling in development
    
    # Configure resource attributes
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "deployment.environment": environment
    })
    
    # Configure tracer provider
    tracer_provider = TracerProvider(
        sampler=sampler,
        resource=resource
    )
    
    # Environment-specific exporters
    if environment == 'production':
        # Production: Export to OTLP collector
        otlp_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                headers={"Authorization": f"Bearer {os.getenv('OTEL_API_KEY', '')}"}
            )
            tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter, max_export_batch_size=512)
            )
    
    elif environment == 'staging':
        # Staging: Export to Jaeger
        jaeger_exporter = JaegerExporter(
            agent_host_name=os.getenv('JAEGER_AGENT_HOST', 'localhost'),
            agent_port=int(os.getenv('JAEGER_AGENT_PORT', '6831'))
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    
    else:
        # Development: Console output and local collector
        console_exporter = ConsoleSpanExporter()
        tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        
        # Also try to connect to local collector
        try:
            otlp_exporter = OTLPSpanExporter(
                endpoint="http://localhost:4317",
                insecure=True
            )
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        except Exception:
            # Ignore if local collector is not available
            pass
    
    trace.set_tracer_provider(tracer_provider)
    
    # Configure structured logging
    setup_structured_logging(environment)


def setup_structured_logging(environment: str):
    """Configure structured JSON logging with trace correlation."""
    log_level = {
        'production': logging.WARNING,
        'staging': logging.INFO,
        'development': logging.DEBUG
    }.get(environment, logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(message)s',  # StructuredFormatter will handle formatting
        handlers=[logging.StreamHandler()]
    )
    
    # Environment-specific logger configuration
    if environment == 'production':
        # Production: Reduce noise, focus on errors and business events
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('pika').setLevel(logging.ERROR)
    
    elif environment == 'development':
        # Development: Verbose logging for debugging
        logging.getLogger('domain').setLevel(logging.DEBUG)
        logging.getLogger('services').setLevel(logging.DEBUG)