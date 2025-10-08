# Observability Patterns & Rules

## ⚠️ MANDATORY PATTERNS - STRICT ENFORCEMENT

These observability patterns are **REQUIRED** for all code. Deviations must be explicitly justified and approved.

## OpenTelemetry Core Principles

### 1. Distributed Tracing (MANDATORY)
**RULE**: ALL request flows MUST be traced with proper span hierarchy and correlation.

```python
# ✅ CORRECT - Proper distributed tracing
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.propagate import inject, extract
import logging

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)

class NotificationService:
    def approve_notification(self, notification_id: str, user_context: UserContext) -> Result[Notification, Error]:
        # Create parent span for the entire operation
        with tracer.start_as_current_span(
            "notification.approve",
            attributes={
                "notification.id": notification_id,
                "user.id": user_context.user_id,
                "organization.id": user_context.org_id,
                "operation": "approve"
            }
        ) as span:
            try:
                # Child span for database read
                with tracer.start_as_current_span("db.notification.read") as db_span:
                    notification = self.mongo_svc.find_one_by_org(
                        "notifications", user_context.org_id, notification_id
                    )
                    db_span.set_attributes({
                        "db.collection": "notifications",
                        "db.operation": "find_one",
                        "db.organization_id": user_context.org_id
                    })
                
                # Child span for domain logic
                with tracer.start_as_current_span("domain.notification.validate_approval") as domain_span:
                    validation_result = domain.notifications.validate_approval(notification, user_context)
                    domain_span.set_attributes({
                        "validation.result": "success" if validation_result.is_success() else "failed",
                        "notification.status": notification.status
                    })
                
                if validation_result.is_success():
                    # Child span for AMQP publishing
                    with tracer.start_as_current_span("amqp.notification.publish") as amqp_span:
                        # Inject trace context into message headers
                        headers = {}
                        inject(headers)
                        
                        publish_result = self.amqp_svc.publish_notification(
                            notification, headers=headers
                        )
                        amqp_span.set_attributes({
                            "amqp.exchange": "notifications",
                            "amqp.routing_key": f"org.{user_context.org_id}.approved",
                            "message.correlation_id": publish_result.correlation_id
                        })
                
                # Success - set span status
                span.set_status(Status(StatusCode.OK))
                span.set_attribute("result", "success")
                
                # Structured logging with trace correlation
                logger.info(
                    "Notification approved successfully",
                    extra={
                        "notification_id": notification_id,
                        "user_id": user_context.user_id,
                        "org_id": user_context.org_id,
                        "trace_id": span.get_span_context().trace_id,
                        "span_id": span.get_span_context().span_id
                    }
                )
                
                return Result(value=notification)
                
            except Exception as e:
                # Error handling with span status
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.set_attribute("error.type", type(e).__name__)
                
                # Error logging with trace correlation
                logger.error(
                    "Failed to approve notification",
                    extra={
                        "notification_id": notification_id,
                        "user_id": user_context.user_id,
                        "org_id": user_context.org_id,
                        "error": str(e),
                        "trace_id": span.get_span_context().trace_id,
                        "span_id": span.get_span_context().span_id
                    },
                    exc_info=True
                )
                
                return Result(error=ServiceError(str(e)))

# ❌ WRONG - No tracing or correlation
def approve_notification(notification_id: str, user_context: UserContext) -> Notification:
    # No spans, no trace correlation, no observability
    notification = mongo_service.find_one(notification_id)
    result = amqp_service.publish(notification)
    logger.info("Notification approved")  # No context
    return notification
```

### 2. Custom Span Attributes (MANDATORY)
**RULE**: ALL spans MUST include relevant business context and standardized attributes.

```python
# ✅ CORRECT - Rich span attributes
class SpanAttributes:
    """Standardized span attribute keys for consistency."""
    
    # Business Context
    USER_ID = "user.id"
    ORG_ID = "organization.id"
    NOTIFICATION_ID = "notification.id"
    NOTIFICATION_STATUS = "notification.status"
    NOTIFICATION_SEVERITY = "notification.severity"
    
    # Database Operations
    DB_COLLECTION = "db.collection"
    DB_OPERATION = "db.operation"
    DB_QUERY_FILTER = "db.query.filter"
    DB_RESULT_COUNT = "db.result.count"
    
    # HTTP Operations
    HTTP_METHOD = "http.method"
    HTTP_URL = "http.url"
    HTTP_STATUS_CODE = "http.status_code"
    HTTP_USER_AGENT = "http.user_agent"
    
    # AMQP Operations
    AMQP_EXCHANGE = "amqp.exchange"
    AMQP_ROUTING_KEY = "amqp.routing_key"
    AMQP_MESSAGE_ID = "amqp.message.id"
    
    # Business Operations
    OPERATION_TYPE = "operation.type"
    OPERATION_RESULT = "operation.result"
    VALIDATION_RESULT = "validation.result"
    PERMISSION_CHECK = "permission.check"

def create_notification_span(operation: str, notification: Notification, user_context: UserContext) -> Dict[str, Any]:
    """Create standardized span attributes for notification operations."""
    return {
        SpanAttributes.OPERATION_TYPE: operation,
        SpanAttributes.USER_ID: user_context.user_id,
        SpanAttributes.ORG_ID: user_context.org_id,
        SpanAttributes.NOTIFICATION_ID: notification.id,
        SpanAttributes.NOTIFICATION_STATUS: notification.status,
        SpanAttributes.NOTIFICATION_SEVERITY: notification.severity,
    }

# Usage in service methods
with tracer.start_as_current_span(
    "notification.create",
    attributes=create_notification_span("create", notification, user_context)
) as span:
    # Add operation-specific attributes
    span.set_attributes({
        SpanAttributes.DB_COLLECTION: "notifications",
        SpanAttributes.DB_OPERATION: "insert_one",
        SpanAttributes.VALIDATION_RESULT: "success"
    })

# ❌ WRONG - Missing or inconsistent attributes
with tracer.start_as_current_span("some_operation") as span:
    # No attributes, no business context
    pass

with tracer.start_as_current_span("notification_stuff") as span:
    # Inconsistent naming, no standardization
    span.set_attribute("notif_id", notification_id)
    span.set_attribute("usr", user_id)
```

### 3. Trace Context Propagation (MANDATORY)
**RULE**: Trace context MUST be propagated across all service boundaries.

```python
# ✅ CORRECT - Trace context propagation
from opentelemetry.propagate import inject, extract
from opentelemetry import context

class AMQPService:
    def publish_notification(self, notification: Notification, user_context: UserContext) -> PublishResult:
        with tracer.start_as_current_span("amqp.publish") as span:
            # Create message with trace context
            headers = {}
            inject(headers)  # Inject current trace context into headers
            
            message = {
                "notification_id": notification.id,
                "organization_id": user_context.org_id,
                "payload": notification.to_dict(),
                "trace_headers": headers  # Include trace context
            }
            
            return self.channel.basic_publish(
                exchange="notifications",
                routing_key=f"org.{user_context.org_id}.approved",
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    headers=headers,  # AMQP headers with trace context
                    correlation_id=str(uuid.uuid4()),
                    timestamp=int(time.time())
                )
            )

class NotificationConsumer:
    def handle_message(self, channel, method, properties, body):
        # Extract trace context from message headers
        headers = properties.headers or {}
        parent_context = extract(headers)
        
        # Continue the distributed trace
        with tracer.start_as_current_span(
            "notification.process",
            context=parent_context
        ) as span:
            message = json.loads(body)
            span.set_attributes({
                "notification.id": message["notification_id"],
                "organization.id": message["organization_id"],
                "amqp.correlation_id": properties.correlation_id
            })
            
            # Process message with continued trace context
            self.process_notification(message)

# HTTP Client with trace propagation
class APIClient:
    def post(self, url: str, data: Dict, user_context: UserContext) -> Response:
        with tracer.start_as_current_span("http.client.post") as span:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {user_context.token}"
            }
            
            # Inject trace context into HTTP headers
            inject(headers)
            
            span.set_attributes({
                "http.method": "POST",
                "http.url": url,
                "organization.id": user_context.org_id
            })
            
            response = requests.post(url, json=data, headers=headers)
            span.set_attribute("http.status_code", response.status_code)
            
            return response

# ❌ WRONG - No trace context propagation
def publish_notification(notification):
    # Trace context is lost across service boundaries
    message = {"id": notification.id}
    channel.basic_publish("exchange", "key", json.dumps(message))

def handle_message(body):
    # No trace context, can't correlate with original request
    message = json.loads(body)
    process_notification(message)
```

## Multi-Level Logging Patterns

### 4. Structured Logging (MANDATORY)
**RULE**: ALL logs MUST be structured JSON with standardized fields and trace correlation.

```python
# ✅ CORRECT - Structured logging configuration
import logging
import json
from datetime import datetime
from opentelemetry import trace

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record):
        # Get current span context for trace correlation
        span = trace.get_current_span()
        span_context = span.get_span_context()
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add trace correlation if available
        if span_context.is_valid:
            log_entry.update({
                "trace_id": format(span_context.trace_id, "032x"),
                "span_id": format(span_context.span_id, "016x"),
                "trace_flags": span_context.trace_flags
            })
        
        # Add extra fields from log record
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        return json.dumps(log_entry)

# Configure structured logging
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)
    
    return logger

# Usage with business context
class NotificationService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def approve_notification(self, notification_id: str, user_context: UserContext):
        # Structured logging with business context
        self.logger.info(
            "Starting notification approval process",
            extra={
                "extra_fields": {
                    "notification_id": notification_id,
                    "user_id": user_context.user_id,
                    "organization_id": user_context.org_id,
                    "operation": "approve",
                    "severity": notification.severity,
                    "targets_count": len(notification.targets)
                }
            }
        )
        
        try:
            result = self._process_approval(notification_id, user_context)
            
            self.logger.info(
                "Notification approval completed successfully",
                extra={
                    "extra_fields": {
                        "notification_id": notification_id,
                        "user_id": user_context.user_id,
                        "organization_id": user_context.org_id,
                        "operation": "approve",
                        "result": "success",
                        "processing_time_ms": result.processing_time
                    }
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Notification approval failed",
                extra={
                    "extra_fields": {
                        "notification_id": notification_id,
                        "user_id": user_context.user_id,
                        "organization_id": user_context.org_id,
                        "operation": "approve",
                        "result": "error",
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                },
                exc_info=True
            )
            raise

# ❌ WRONG - Unstructured logging
def approve_notification(notification_id, user_id):
    print(f"Approving notification {notification_id}")  # No structure, no correlation
    logger.info("Starting approval")  # No context
    try:
        result = process_approval(notification_id)
        logger.info("Done")  # No details
    except Exception as e:
        logger.error(f"Error: {e}")  # No trace correlation, minimal context
```

### 5. Log Levels and Context (MANDATORY)
**RULE**: Use appropriate log levels with rich contextual information.

```python
# ✅ CORRECT - Proper log levels and context
class NotificationService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_notification_workflow(self, notification: Notification, user_context: UserContext):
        # DEBUG: Detailed information for development/troubleshooting
        self.logger.debug(
            "Processing notification workflow with detailed context",
            extra={
                "extra_fields": {
                    "notification": {
                        "id": notification.id,
                        "title": notification.title[:50],  # Truncated for logs
                        "severity": notification.severity,
                        "status": notification.status,
                        "targets": notification.targets,
                        "categories": notification.categories
                    },
                    "user": {
                        "id": user_context.user_id,
                        "org_id": user_context.org_id,
                        "permissions": user_context.permissions
                    },
                    "workflow_step": "validation"
                }
            }
        )
        
        # INFO: Important business events
        self.logger.info(
            "Notification workflow initiated",
            extra={
                "extra_fields": {
                    "notification_id": notification.id,
                    "user_id": user_context.user_id,
                    "organization_id": user_context.org_id,
                    "workflow_type": "approval_process",
                    "severity": notification.severity
                }
            }
        )
        
        # WARN: Potential issues that don't stop processing
        if notification.severity >= 4 and len(notification.targets) > 1000:
            self.logger.warning(
                "High-severity notification with large target audience detected",
                extra={
                    "extra_fields": {
                        "notification_id": notification.id,
                        "severity": notification.severity,
                        "target_count": len(notification.targets),
                        "organization_id": user_context.org_id,
                        "risk_level": "high",
                        "recommendation": "manual_review_suggested"
                    }
                }
            )
        
        # ERROR: Failures that prevent operation completion
        try:
            validation_result = self.validate_notification(notification, user_context)
        except ValidationError as e:
            self.logger.error(
                "Notification validation failed",
                extra={
                    "extra_fields": {
                        "notification_id": notification.id,
                        "user_id": user_context.user_id,
                        "organization_id": user_context.org_id,
                        "validation_errors": e.errors,
                        "workflow_step": "validation",
                        "impact": "workflow_blocked"
                    }
                },
                exc_info=True
            )
            raise
        
        # CRITICAL: System-level failures requiring immediate attention
        try:
            self.publish_to_queue(notification)
        except AMQPConnectionError as e:
            self.logger.critical(
                "AMQP connection failure - notifications cannot be dispatched",
                extra={
                    "extra_fields": {
                        "notification_id": notification.id,
                        "organization_id": user_context.org_id,
                        "amqp_broker": self.amqp_config.broker_url,
                        "error_type": "infrastructure_failure",
                        "impact": "service_degradation",
                        "action_required": "immediate_investigation"
                    }
                },
                exc_info=True
            )
            # Trigger alerts for critical failures
            self.alert_service.send_critical_alert("AMQP_CONNECTION_FAILURE", str(e))
            raise

# ❌ WRONG - Inappropriate log levels and poor context
def process_notification(notification, user):
    logger.debug("Starting")  # Too vague
    logger.info("Processing notification 123")  # Hardcoded values
    logger.error("Something went wrong")  # No context, wrong level for warnings
    logger.critical("Validation failed")  # Wrong level, should be ERROR
```

### 6. Performance and Security Logging (MANDATORY)
**RULE**: Log performance metrics and security events with appropriate detail.

```python
# ✅ CORRECT - Performance and security logging
import time
from functools import wraps

def log_performance(operation_name: str):
    """Decorator to log performance metrics for operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger = logging.getLogger(func.__module__)
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                logger.info(
                    f"Operation completed: {operation_name}",
                    extra={
                        "extra_fields": {
                            "operation": operation_name,
                            "duration_ms": round(duration_ms, 2),
                            "result": "success",
                            "function": func.__name__,
                            "performance_category": "normal" if duration_ms < 1000 else "slow"
                        }
                    }
                )
                
                # Warn on slow operations
                if duration_ms > 5000:
                    logger.warning(
                        f"Slow operation detected: {operation_name}",
                        extra={
                            "extra_fields": {
                                "operation": operation_name,
                                "duration_ms": round(duration_ms, 2),
                                "threshold_ms": 5000,
                                "performance_impact": "degraded_user_experience"
                            }
                        }
                    )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Operation failed: {operation_name}",
                    extra={
                        "extra_fields": {
                            "operation": operation_name,
                            "duration_ms": round(duration_ms, 2),
                            "result": "error",
                            "error_type": type(e).__name__,
                            "function": func.__name__
                        }
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator

class SecurityLogger:
    """Dedicated logger for security events."""
    
    def __init__(self):
        self.logger = logging.getLogger("security")
    
    def log_authentication_attempt(self, email: str, success: bool, ip_address: str, user_agent: str):
        """Log authentication attempts with security context."""
        self.logger.info(
            "Authentication attempt",
            extra={
                "extra_fields": {
                    "event_type": "authentication",
                    "email": email,
                    "success": success,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "timestamp": datetime.utcnow().isoformat(),
                    "security_category": "auth_event"
                }
            }
        )
    
    def log_authorization_failure(self, user_id: str, org_id: str, required_permission: str, 
                                 resource: str, ip_address: str):
        """Log authorization failures for security monitoring."""
        self.logger.warning(
            "Authorization failure - insufficient permissions",
            extra={
                "extra_fields": {
                    "event_type": "authorization_failure",
                    "user_id": user_id,
                    "organization_id": org_id,
                    "required_permission": required_permission,
                    "resource": resource,
                    "ip_address": ip_address,
                    "security_category": "access_denied",
                    "risk_level": "medium"
                }
            }
        )
    
    def log_suspicious_activity(self, user_id: str, org_id: str, activity: str, 
                               details: Dict, risk_level: str):
        """Log suspicious activities for security analysis."""
        self.logger.error(
            "Suspicious activity detected",
            extra={
                "extra_fields": {
                    "event_type": "suspicious_activity",
                    "user_id": user_id,
                    "organization_id": org_id,
                    "activity": activity,
                    "details": details,
                    "risk_level": risk_level,
                    "security_category": "threat_detection",
                    "requires_investigation": True
                }
            }
        )

# Usage examples
class NotificationService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.security_logger = SecurityLogger()
    
    @log_performance("notification_approval")
    def approve_notification(self, notification_id: str, user_context: UserContext):
        # Performance logging handled by decorator
        return self._process_approval(notification_id, user_context)
    
    def validate_user_permissions(self, user_context: UserContext, required_permission: str):
        if required_permission not in user_context.permissions:
            # Log security event
            self.security_logger.log_authorization_failure(
                user_context.user_id,
                user_context.org_id,
                required_permission,
                "notification_approval",
                user_context.ip_address
            )
            raise InsufficientPermissionsError(f"Missing permission: {required_permission}")

# ❌ WRONG - Missing performance and security context
def approve_notification(notification_id, user_id):
    # No performance tracking
    result = process_approval(notification_id)
    logger.info("Approved")  # No security context
    return result

def check_permissions(user, permission):
    if permission not in user.permissions:
        logger.info("Access denied")  # No security details
        raise Exception("No permission")
```

### 7. Audit Trail Integration (MANDATORY)
**RULE**: Audit logs MUST be correlated with traces and include complete context.

```python
# ✅ CORRECT - Integrated audit trail with observability
class AuditService:
    def __init__(self, mongo_svc: MongoDBService):
        self.mongo_svc = mongo_svc
        self.logger = logging.getLogger(__name__)
    
    def log_action(self, user_id: str, org_id: str, entity: str, entity_id: str,
                   action: str, before: Dict, after: Dict, request_context: RequestContext) -> str:
        """Log audit trail with trace correlation and structured logging."""
        
        # Get current span for trace correlation
        span = trace.get_current_span()
        span_context = span.get_span_context()
        
        audit_entry = {
            "id": str(ObjectId()),
            "timestamp": datetime.utcnow(),
            "user_id": user_id,
            "organization_id": org_id,
            "entity": entity,
            "entity_id": entity_id,
            "action": action,
            "before": before,
            "after": after,
            "ip_address": request_context.ip_address,
            "user_agent": request_context.user_agent,
            "session_id": request_context.session_id,
            "schema_version": 1
        }
        
        # Add trace correlation to audit entry
        if span_context.is_valid:
            audit_entry.update({
                "trace_id": format(span_context.trace_id, "032x"),
                "span_id": format(span_context.span_id, "016x")
            })
        
        # Store audit entry
        with tracer.start_as_current_span("audit.log_action") as audit_span:
            audit_span.set_attributes({
                "audit.entity": entity,
                "audit.action": action,
                "audit.user_id": user_id,
                "audit.organization_id": org_id
            })
            
            self.mongo_svc.create("audit_logs", audit_entry)
        
        # Structured logging for audit event
        self.logger.info(
            "Audit trail entry created",
            extra={
                "extra_fields": {
                    "audit_id": audit_entry["id"],
                    "entity": entity,
                    "entity_id": entity_id,
                    "action": action,
                    "user_id": user_id,
                    "organization_id": org_id,
                    "trace_id": audit_entry.get("trace_id"),
                    "changes_count": len(self._calculate_changes(before, after)),
                    "audit_category": "business_action"
                }
            }
        )
        
        return audit_entry["id"]
    
    def _calculate_changes(self, before: Dict, after: Dict) -> List[Dict]:
        """Calculate field-level changes for detailed audit trail."""
        changes = []
        
        all_keys = set(before.keys()) | set(after.keys())
        for key in all_keys:
            old_value = before.get(key)
            new_value = after.get(key)
            
            if old_value != new_value:
                changes.append({
                    "field": key,
                    "old_value": old_value,
                    "new_value": new_value
                })
        
        return changes

# Usage in service layer
class NotificationService:
    def approve_notification(self, notification_id: str, user_context: UserContext) -> Result[Notification, Error]:
        with tracer.start_as_current_span("notification.approve") as span:
            # Get current state for audit trail
            notification_before = self.mongo_svc.find_one_by_org(
                "notifications", user_context.org_id, notification_id
            )
            
            # Process approval
            result = self._process_approval(notification_before, user_context)
            
            if result.is_success():
                notification_after = result.value
                
                # Create audit trail with trace correlation
                audit_id = self.audit_svc.log_action(
                    user_id=user_context.user_id,
                    org_id=user_context.org_id,
                    entity="notification",
                    entity_id=notification_id,
                    action="approve",
                    before=notification_before.to_dict(),
                    after=notification_after.to_dict(),
                    request_context=user_context.request_context
                )
                
                # Add audit reference to span
                span.set_attribute("audit.id", audit_id)
                
                self.logger.info(
                    "Notification approved with audit trail",
                    extra={
                        "extra_fields": {
                            "notification_id": notification_id,
                            "user_id": user_context.user_id,
                            "organization_id": user_context.org_id,
                            "audit_id": audit_id,
                            "operation": "approve"
                        }
                    }
                )
            
            return result

# ❌ WRONG - Disconnected audit trail
def approve_notification(notification_id, user_id):
    notification = get_notification(notification_id)
    notification.status = "approved"
    save_notification(notification)
    
    # Audit trail without trace correlation or context
    audit_log = {
        "action": "approve",
        "user": user_id,
        "timestamp": datetime.now()
    }
    save_audit(audit_log)  # No correlation with traces or detailed context
```

### 8. Environment-Specific Configuration (MANDATORY)
**RULE**: Observability configuration MUST be environment-aware with proper sampling and export.

```python
# ✅ CORRECT - Environment-specific observability configuration
import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, AlwaysOn, AlwaysOff
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

class ObservabilityConfig:
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.otel_enabled = os.getenv("OTEL_ENABLED", "true").lower() == "true"
        self.service_name = "sos-cidadao-api"
        self.service_version = os.getenv("SERVICE_VERSION", "1.0.0")
    
    def setup_tracing(self):
        """Configure OpenTelemetry tracing based on environment."""
        if not self.otel_enabled:
            trace.set_tracer_provider(TracerProvider(sampler=AlwaysOff()))
            return
        
        # Environment-specific sampling
        if self.environment == "production":
            sampler = TraceIdRatioBased(0.1)  # 10% sampling in production
        elif self.environment == "staging":
            sampler = TraceIdRatioBased(0.5)  # 50% sampling in staging
        else:
            sampler = AlwaysOn()  # 100% sampling in development
        
        # Configure tracer provider
        tracer_provider = TracerProvider(
            sampler=sampler,
            resource=Resource.create({
                "service.name": self.service_name,
                "service.version": self.service_version,
                "deployment.environment": self.environment
            })
        )
        
        # Environment-specific exporters
        if self.environment == "production":
            # Production: Export to OTLP collector
            otlp_exporter = OTLPSpanExporter(
                endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
                headers={"Authorization": f"Bearer {os.getenv('OTEL_API_KEY')}"}
            )
            tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter, max_export_batch_size=512)
            )
            
        elif self.environment == "staging":
            # Staging: Export to Jaeger
            jaeger_exporter = JaegerExporter(
                agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
                agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831"))
            )
            tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            
        else:
            # Development: Console output
            console_exporter = ConsoleSpanExporter()
            tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        
        trace.set_tracer_provider(tracer_provider)
    
    def setup_logging(self):
        """Configure structured logging based on environment."""
        log_level = {
            "production": logging.WARNING,
            "staging": logging.INFO,
            "development": logging.DEBUG
        }.get(self.environment, logging.INFO)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format='%(message)s',  # StructuredFormatter handles formatting
            handlers=[logging.StreamHandler()]
        )
        
        # Add structured formatter
        for handler in logging.root.handlers:
            handler.setFormatter(StructuredFormatter())
        
        # Environment-specific logger configuration
        if self.environment == "production":
            # Production: Reduce noise, focus on errors and business events
            logging.getLogger("urllib3").setLevel(logging.WARNING)
            logging.getLogger("requests").setLevel(logging.WARNING)
            logging.getLogger("pika").setLevel(logging.ERROR)
            
        elif self.environment == "development":
            # Development: Verbose logging for debugging
            logging.getLogger("domain").setLevel(logging.DEBUG)
            logging.getLogger("services").setLevel(logging.DEBUG)

# Application initialization
def initialize_observability():
    config = ObservabilityConfig()
    config.setup_tracing()
    config.setup_logging()
    
    logger = logging.getLogger(__name__)
    logger.info(
        "Observability initialized",
        extra={
            "extra_fields": {
                "environment": config.environment,
                "otel_enabled": config.otel_enabled,
                "service_name": config.service_name,
                "service_version": config.service_version
            }
        }
    )

# ❌ WRONG - No environment awareness
def setup_observability():
    # Same configuration for all environments
    trace.set_tracer_provider(TracerProvider())
    logging.basicConfig(level=logging.DEBUG)  # Always debug level
    # No sampling, no environment-specific exporters
```

These observability patterns ensure comprehensive monitoring, debugging capabilities, and audit compliance while maintaining performance and security standards across all environments.