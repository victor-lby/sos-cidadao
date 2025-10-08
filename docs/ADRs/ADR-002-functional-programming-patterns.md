# ADR-002: Functional Programming Patterns for Domain Logic

## Status
Accepted

## Context
We need a maintainable, testable architecture that separates business logic from side effects. The system should be easy to reason about, test, and modify as requirements evolve.

## Decision
Implement domain logic using functional programming patterns with the following principles:

1. **Pure Functions for Domain Logic**: All business logic implemented as pure functions with no side effects
2. **Side Effects Isolation**: Database, Redis, AMQP, and HTTP operations isolated to service layer
3. **Dependency Injection**: Services injected into domain functions as parameters
4. **Result Pattern**: Use Result/Either types for error handling instead of exceptions in domain logic

## Consequences

### Positive
- **Testability**: Pure functions can be tested without mocks or external dependencies
- **Maintainability**: Clear separation between business logic and infrastructure concerns
- **Reliability**: Deterministic functions with predictable outputs
- **Composability**: Pure functions can be easily composed and reused

### Negative
- **Learning Curve**: Developers need to understand functional programming concepts
- **Verbosity**: Dependency injection requires more parameters in function signatures
- **Performance**: Some overhead from Result type wrapping

## Implementation Details

### Domain Function Example
```python
def approve_notification(
    notification: Notification,
    user_context: UserContext,
    mongo_svc: MongoDBService,
    audit_svc: AuditService
) -> Result[Notification, Error]:
    """Pure function with injected dependencies."""
    
    # Validation (pure logic)
    if notification.status != NotificationStatus.RECEIVED:
        return Result(error=ValidationError("Cannot approve non-received notification"))
    
    if "notification:approve" not in user_context.permissions:
        return Result(error=AuthorizationError("Insufficient permissions"))
    
    # Business logic (pure)
    approved_notification = notification.copy(update={
        "status": NotificationStatus.APPROVED,
        "updated_at": datetime.utcnow(),
        "updated_by": user_context.user_id
    })
    
    return Result(value=approved_notification)
```

### Service Layer Example
```python
class NotificationService:
    def approve_notification(self, notification_id: str, user_context: UserContext) -> Result[Notification, Error]:
        # Side effect: Database read
        notification = self.mongo_svc.find_one_by_org("notifications", user_context.org_id, notification_id)
        
        # Pure domain logic
        result = domain.notifications.approve_notification(notification, user_context, self.mongo_svc, self.audit_svc)
        
        if result.is_success():
            # Side effect: Database write
            self.mongo_svc.update_by_org("notifications", user_context.org_id, notification_id, result.value.dict())
            # Side effect: Audit log
            self.audit_svc.log_action(user_context.user_id, "notification", "approve", notification.dict(), result.value.dict())
        
        return result
```

### Result Pattern
```python
class Result(Generic[T, E]):
    def __init__(self, value: T = None, error: E = None):
        self._value = value
        self._error = error
    
    def is_success(self) -> bool:
        return self._error is None
    
    @property
    def value(self) -> T:
        if self._error:
            raise ValueError("Result contains error")
        return self._value
    
    @property
    def error(self) -> E:
        return self._error
```

## Architecture Layers

### Domain Layer (Pure Functions)
- `domain/notifications.py` - Notification workflow logic
- `domain/authorization.py` - Permission and role logic
- `domain/audit.py` - Audit trail generation

### Service Layer (Side Effects)
- `services/mongodb.py` - Database operations
- `services/redis.py` - Caching and JWT management
- `services/amqp.py` - Message queue operations

### Routes Layer (HTTP Handlers)
- `routes/notifications.py` - HTTP endpoint handlers
- Orchestrate domain and service calls
- Handle HTTP-specific concerns (headers, status codes)

## Testing Strategy

### Pure Function Tests
```python
def test_notification_approval_logic():
    notification = Notification(id="123", status="received")
    user_context = UserContext(user_id="user1", permissions=["notification:approve"])
    
    # No mocks needed - pure function test
    result = domain.notifications.approve_notification(notification, user_context)
    
    assert result.is_success()
    assert result.value.status == "approved"
```

### Integration Tests
```python
def test_notification_service_approval(mongo_service, audit_service):
    service = NotificationService(mongo_service, audit_service)
    
    # Test with real service dependencies
    result = service.approve_notification("123", user_context)
    
    assert result.is_success()
```

## References
- [Functional Core, Imperative Shell](https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell)
- [Railway Oriented Programming](https://fsharpforfunandprofit.com/rop/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)