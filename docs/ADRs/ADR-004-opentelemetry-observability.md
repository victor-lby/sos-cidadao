# ADR-004: OpenTelemetry for Observability

## Status
Accepted

## Context
The S.O.S Cidadão platform needs comprehensive observability for monitoring, debugging, and performance analysis. We need vendor-neutral observability that works across different environments and can export to various backends.

## Decision
Implement observability using OpenTelemetry with the following components:

1. **Distributed Tracing**: Full request tracing across all services
2. **Structured Logging**: JSON logs with trace correlation
3. **Custom Metrics**: Business and performance metrics
4. **Vendor Neutral**: Export to any OTLP-compatible backend
5. **Environment Specific**: Different sampling and export strategies per environment

## Consequences

### Positive
- **Vendor Neutral**: Not locked into specific monitoring vendor
- **Comprehensive**: Traces, logs, and metrics in one solution
- **Correlation**: Automatic correlation between traces and logs
- **Performance**: Configurable sampling for production efficiency
- **Standards**: Industry standard observability format

### Negative
- **Complexity**: Additional configuration and setup required
- **Overhead**: Some performance impact from instrumentation
- **Learning Curve**: Team needs to understand OpenTelemetry concepts

## Implementation Details

### Tracing Configuration
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

def setup_tracing(environment: str):
    # Environment-specific sampling
    if environment == "production":
        sampler = TraceIdRatioBased(0.1)  # 10% sampling
    elif environment == "staging":
        sampler = TraceIdRatioBased(0.5)  # 50% sampling
    else:
        sampler = AlwaysOn()  # 100% sampling in development
    
    tracer_provider = TracerProvider(sampler=sampler)
    trace.set_tracer_provider(tracer_provider)
```

### Custom Span Attributes
```python
class SpanAttributes:
    # Business Context
    USER_ID = "user.id"
    ORG_ID = "organization.id"
    NOTIFICATION_ID = "notification.id"
    NOTIFICATION_STATUS = "notification.status"
    
    # Database Operations
    DB_COLLECTION = "db.collection"
    DB_OPERATION = "db.operation"
    
    # AMQP Operations
    AMQP_EXCHANGE = "amqp.exchange"
    AMQP_ROUTING_KEY = "amqp.routing_key"

def create_notification_span(operation: str, notification: Notification, user_context: UserContext):
    return {
        SpanAttributes.USER_ID: user_context.user_id,
        SpanAttributes.ORG_ID: user_context.org_id,
        SpanAttributes.NOTIFICATION_ID: notification.id,
        SpanAttributes.NOTIFICATION_STATUS: notification.status,
    }
```

### Distributed Tracing Example
```python
class NotificationService:
    def approve_notification(self, notification_id: str, user_context: UserContext) -> Result[Notification, Error]:
        with tracer.start_as_current_span(
            "notification.approve",
            attributes=create_notification_span("approve", notification, user_context)
        ) as span:
            try:
                # Child span for database read
                with tracer.start_as_current_span("db.notification.read") as db_span:
                    notification = self.mongo_svc.find_one_by_org("notifications", user_context.org_id, notification_id)
                    db_span.set_attributes({
                        SpanAttributes.DB_COLLECTION: "notifications",
                        SpanAttributes.DB_OPERATION: "find_one"
                    })
                
                # Child span for AMQP publishing
                with tracer.start_as_current_span("amqp.notification.publish") as amqp_span:
                    headers = {}
                    inject(headers)  # Inject trace context
                    
                    result = self.amqp_svc.publish_notification(notification, headers=headers)
                    amqp_span.set_attributes({
                        SpanAttributes.AMQP_EXCHANGE: "notifications",
                        SpanAttributes.AMQP_ROUTING_KEY: f"org.{user_context.org_id}.approved"
                    })
                
                span.set_status(Status(StatusCode.OK))
                return Result(value=notification)
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
```

### Structured Logging with Trace Correlation
```python
class StructuredFormatter(logging.Formatter):
    def format(self, record):
        span = trace.get_current_span()
        span_context = span.get_span_context()
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName
        }
        
        # Add trace correlation
        if span_context.is_valid:
            log_entry.update({
                "trace_id": format(span_context.trace_id, "032x"),
                "span_id": format(span_context.span_id, "016x")
            })
        
        # Add business context from extra fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry)
```

### Business Metrics
```python
from opentelemetry import metrics

meter = metrics.get_meter(__name__)

# Business metrics
notification_counter = meter.create_counter(
    "notifications_total",
    description="Total number of notifications processed"
)

approval_duration = meter.create_histogram(
    "notification_approval_duration_seconds",
    description="Time taken to approve notifications"
)

def track_notification_approval(notification: Notification, user_context: UserContext, duration: float):
    notification_counter.add(1, {
        "organization_id": user_context.org_id,
        "status": "approved",
        "severity": str(notification.severity)
    })
    
    approval_duration.record(duration, {
        "organization_id": user_context.org_id,
        "severity": str(notification.severity)
    })
```

## Environment Configuration

### Development Environment
```python
# Local development with console exporter
def setup_dev_observability():
    # Console exporter for traces
    console_exporter = ConsoleSpanExporter()
    tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
    
    # Debug logging
    logging.basicConfig(level=logging.DEBUG)
```

### Staging Environment
```python
# Staging with Jaeger
def setup_staging_observability():
    jaeger_exporter = JaegerExporter(
        agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
        agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831"))
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
```

### Production Environment
```python
# Production with OTLP
def setup_production_observability():
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        headers={"Authorization": f"Bearer {os.getenv('OTEL_API_KEY')}"}
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter, max_export_batch_size=512))
```

## Audit Trail Integration

### Trace Correlation in Audit Logs
```python
class AuditService:
    def log_action(self, user_id: str, org_id: str, entity: str, action: str, before: Dict, after: Dict) -> str:
        span = trace.get_current_span()
        span_context = span.get_span_context()
        
        audit_entry = {
            "timestamp": datetime.utcnow(),
            "user_id": user_id,
            "organization_id": org_id,
            "entity": entity,
            "action": action,
            "before": before,
            "after": after
        }
        
        # Add trace correlation
        if span_context.is_valid:
            audit_entry.update({
                "trace_id": format(span_context.trace_id, "032x"),
                "span_id": format(span_context.span_id, "016x")
            })
        
        return self.mongo_svc.create("audit_logs", audit_entry)
```

## Performance Considerations

### Sampling Strategy
- **Production**: 10% sampling to reduce overhead
- **Staging**: 50% sampling for testing
- **Development**: 100% sampling for debugging

### Batch Processing
- Use `BatchSpanProcessor` for efficient export
- Configure appropriate batch sizes and timeouts
- Handle export failures gracefully

### Resource Attributes
```python
resource = Resource.create({
    "service.name": "sos-cidadao-api",
    "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
    "deployment.environment": os.getenv("ENVIRONMENT", "development")
})
```

## Monitoring and Alerting

### Key Metrics to Monitor
- Request rate and latency percentiles
- Error rates by endpoint and organization
- Database connection pool metrics
- Queue message processing metrics
- Cache hit/miss ratios

### Alerting Rules
- High error rates (>5% over 5 minutes)
- Slow response times (>2s p95)
- Database connection failures
- Queue message processing delays

## Security Considerations

### PII Scrubbing
```python
def scrub_sensitive_data(span_attributes: Dict) -> Dict:
    """Remove PII from span attributes."""
    scrubbed = span_attributes.copy()
    
    # Remove sensitive fields
    for key in ["email", "password", "token"]:
        if key in scrubbed:
            scrubbed[key] = "[REDACTED]"
    
    return scrubbed
```

### Trace Context Propagation
- Inject trace context into AMQP message headers
- Propagate context across HTTP requests
- Maintain context in async operations

## References
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [OpenTelemetry Python SDK](https://opentelemetry-python.readthedocs.io/)
- [Distributed Tracing Best Practices](https://opentelemetry.io/docs/concepts/observability-primer/)