# Backend Coding Patterns & Rules

## ⚠️ MANDATORY PATTERNS - STRICT ENFORCEMENT

These patterns are **REQUIRED** for all backend code. Deviations must be explicitly justified and approved.

## Functional Programming Core Principles

### 1. Pure Functions for Domain Logic
**RULE**: All business logic MUST be implemented as pure functions.

```python
# ✅ CORRECT - Pure function
def calculate_notification_priority(severity: int, target_count: int) -> int:
    """Pure function - no side effects, deterministic output."""
    if severity >= 4 and target_count > 1000:
        return 1  # High priority
    elif severity >= 2:
        return 2  # Medium priority
    return 3  # Low priority

# ❌ WRONG - Impure function with side effects
def calculate_notification_priority(notification_id: str) -> int:
    # Don't access database or external services in domain logic
    notification = db.notifications.find_one({"_id": notification_id})
    # Don't log or perform I/O in pure functions
    logger.info(f"Calculating priority for {notification_id}")
    return calculate_priority_logic(notification)
```

### 2. Side Effects Isolation
**RULE**: All side effects (DB, Redis, AMQP, HTTP) MUST be isolated to service layer.

```python
# ✅ CORRECT - Service layer handles side effects
class NotificationService:
    def __init__(self, mongo_svc: MongoDBService, audit_svc: AuditService):
        self.mongo_svc = mongo_svc
        self.audit_svc = audit_svc
    
    def approve_notification(self, notification_id: str, user_context: UserContext) -> Result[Notification, Error]:
        # Side effect: Database read
        notification = self.mongo_svc.find_one_by_org("notifications", user_context.org_id, notification_id)
        
        # Pure domain logic
        result = domain.notifications.approve_notification(notification, user_context)
        
        if result.is_success():
            # Side effect: Database write
            self.mongo_svc.update_by_org("notifications", user_context.org_id, notification_id, result.value)
            # Side effect: Audit log
            self.audit_svc.log_action(user_context.user_id, "notification", "approve", notification, result.value)
        
        return result

# ❌ WRONG - Domain logic mixed with side effects
def approve_notification(notification_id: str, user_context: UserContext) -> Notification:
    # Don't access database directly in domain functions
    notification = mongo_client.db.notifications.find_one({"_id": notification_id})
    notification["status"] = "approved"
    # Don't save directly in domain functions
    mongo_client.db.notifications.update_one({"_id": notification_id}, {"$set": notification})
    return notification
```

### 3. Dependency Injection Pattern
**RULE**: Use dependency injection for all service dependencies.

```python
# ✅ CORRECT - Dependency injection
def process_notification_approval(
    notification: Notification,
    user_context: UserContext,
    mongo_svc: MongoDBService,
    amqp_svc: AMQPService,
    audit_svc: AuditService
) -> Result[Notification, Error]:
    # Pure logic with injected dependencies
    pass

# ❌ WRONG - Global dependencies or direct imports
def process_notification_approval(notification: Notification, user_context: UserContext) -> Notification:
    # Don't use global variables or direct service imports
    from services.mongodb import mongo_service
    global amqp_client
```

## Multi-Tenant Architecture Patterns

### 4. Organization Scoping (MANDATORY)
**RULE**: ALL data operations MUST include organization scoping.

```python
# ✅ CORRECT - Organization scoped
class MongoDBService:
    def find_notifications(self, org_id: str, filters: Dict = None) -> List[Dict]:
        query = {"organizationId": org_id, "deletedAt": None}
        if filters:
            query.update(filters)
        return self.db.notifications.find(query)
    
    def update_notification(self, org_id: str, notification_id: str, updates: Dict) -> bool:
        result = self.db.notifications.update_one(
            {"_id": notification_id, "organizationId": org_id, "deletedAt": None},
            {"$set": {**updates, "updatedAt": datetime.utcnow()}}
        )
        return result.modified_count > 0

# ❌ WRONG - Missing organization scoping
def find_notifications(filters: Dict = None) -> List[Dict]:
    # SECURITY RISK: No organization isolation
    return db.notifications.find(filters or {})
```

### 5. User Context Propagation
**RULE**: User context MUST be passed through all request processing layers.

```python
# ✅ CORRECT - User context propagation
@dataclass
class UserContext:
    user_id: str
    org_id: str
    permissions: List[str]
    trace_id: str

def handle_notification_request(request_data: Dict, user_context: UserContext) -> Response:
    # Pass context through all layers
    result = notification_service.create_notification(request_data, user_context)
    return build_hal_response(result, user_context)

# ❌ WRONG - Missing user context
def handle_notification_request(request_data: Dict) -> Response:
    # How do we know which organization this belongs to?
    result = notification_service.create_notification(request_data)
    return build_response(result)
```

## Error Handling Patterns

### 6. Result/Either Pattern
**RULE**: Use Result types for error handling, avoid exceptions in domain logic.

```python
# ✅ CORRECT - Result pattern
from typing import Union, Generic, TypeVar

T = TypeVar('T')
E = TypeVar('E')

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

def validate_notification(notification: Dict) -> Result[Notification, ValidationError]:
    if not notification.get("title"):
        return Result(error=ValidationError("Title is required"))
    
    if notification.get("severity", 0) not in range(6):
        return Result(error=ValidationError("Severity must be 0-5"))
    
    return Result(value=Notification(**notification))

# ❌ WRONG - Exceptions in domain logic
def validate_notification(notification: Dict) -> Notification:
    if not notification.get("title"):
        raise ValueError("Title is required")  # Don't raise exceptions in pure functions
    return Notification(**notification)
```

## API Response Patterns

### 7. HAL Response Format (MANDATORY)
**RULE**: ALL API responses MUST use HAL format with proper links.

```python
# ✅ CORRECT - HAL response builder
def build_notification_hal_response(notification: Notification, user_context: UserContext, base_url: str) -> Dict:
    response = {
        "id": notification.id,
        "title": notification.title,
        "status": notification.status,
        "_links": {
            "self": {"href": f"{base_url}/api/notifications/{notification.id}"}
        }
    }
    
    # Conditional affordance links based on permissions and state
    if notification.status == "received" and "notification:approve" in user_context.permissions:
        response["_links"]["approve"] = {
            "href": f"{base_url}/api/notifications/{notification.id}/approve",
            "method": "POST"
        }
    
    if notification.status == "received" and "notification:deny" in user_context.permissions:
        response["_links"]["deny"] = {
            "href": f"{base_url}/api/notifications/{notification.id}/deny",
            "method": "POST"
        }
    
    return response

# ❌ WRONG - Plain JSON without HAL
def build_notification_response(notification: Notification) -> Dict:
    return {
        "id": notification.id,
        "title": notification.title,
        "status": notification.status
        # Missing _links, no discoverability
    }
```

### 8. Pydantic Models (MANDATORY)
**RULE**: ALL request/response data MUST use Pydantic models for validation.

```python
# ✅ CORRECT - Pydantic models
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum

class NotificationStatus(str, Enum):
    RECEIVED = "received"
    APPROVED = "approved"
    DENIED = "denied"
    DISPATCHED = "dispatched"

class CreateNotificationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=2000)
    severity: int = Field(..., ge=0, le=5)
    targets: List[str] = Field(default_factory=list)
    
    @validator('title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    status: NotificationStatus
    created_at: datetime
    links: Dict[str, Any] = Field(alias="_links")

# ❌ WRONG - Raw dictionaries without validation
def create_notification(data: dict) -> dict:
    # No validation, type safety, or documentation
    return {"id": "123", "title": data["title"]}
```

## Database Patterns

### 9. Soft Delete Pattern (MANDATORY)
**RULE**: ALL entities MUST support soft deletion with audit trails.

```python
# ✅ CORRECT - Soft delete implementation
class MongoDBService:
    def soft_delete(self, collection: str, org_id: str, doc_id: str, user_id: str) -> bool:
        result = self.db[collection].update_one(
            {"_id": doc_id, "organizationId": org_id, "deletedAt": None},
            {
                "$set": {
                    "deletedAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow(),
                    "updatedBy": user_id
                }
            }
        )
        return result.modified_count > 0
    
    def find_active(self, collection: str, org_id: str, filters: Dict = None) -> List[Dict]:
        query = {"organizationId": org_id, "deletedAt": None}
        if filters:
            query.update(filters)
        return list(self.db[collection].find(query))

# ❌ WRONG - Hard delete
def delete_notification(notification_id: str) -> bool:
    # Don't permanently delete data
    result = db.notifications.delete_one({"_id": notification_id})
    return result.deleted_count > 0
```

### 10. Schema Versioning (MANDATORY)
**RULE**: ALL documents MUST include schemaVersion for future migrations.

```python
# ✅ CORRECT - Schema versioning
class BaseEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    organization_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None
    created_by: str
    updated_by: str
    schema_version: int = Field(default=1)  # MANDATORY

class Notification(BaseEntity):
    title: str
    body: str
    severity: int
    status: NotificationStatus
    schema_version: int = Field(default=2)  # Increment when schema changes

# ❌ WRONG - No schema versioning
class Notification(BaseModel):
    id: str
    title: str
    body: str
    # Missing schema_version field
```

## Security Patterns

### 11. JWT Validation (MANDATORY)
**RULE**: ALL protected endpoints MUST validate JWT and extract user context.

```python
# ✅ CORRECT - JWT middleware
from functools import wraps

def require_jwt(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({"error": "Missing authorization token"}), 401
        
        try:
            # Validate token and check blocklist
            user_context = auth_service.validate_token(token)
            if not user_context:
                return jsonify({"error": "Invalid token"}), 401
            
            # Pass user context to route handler
            return f(user_context, *args, **kwargs)
        
        except Exception as e:
            return jsonify({"error": "Token validation failed"}), 401
    
    return decorated_function

@app.route('/api/notifications', methods=['GET'])
@require_jwt
def list_notifications(user_context: UserContext):
    # user_context is guaranteed to be valid
    pass

# ❌ WRONG - No JWT validation
@app.route('/api/notifications', methods=['GET'])
def list_notifications():
    # No authentication, security vulnerability
    pass
```

## Testing Patterns

### 12. Pure Function Testing
**RULE**: Domain logic MUST be testable without mocks or external dependencies.

```python
# ✅ CORRECT - Pure function tests
def test_notification_priority_calculation():
    # Test pure function without any setup or mocks
    assert calculate_notification_priority(5, 2000) == 1  # High priority
    assert calculate_notification_priority(3, 500) == 2   # Medium priority
    assert calculate_notification_priority(1, 100) == 3   # Low priority

def test_notification_approval_logic():
    notification = Notification(id="123", status="received", severity=4)
    user_context = UserContext(user_id="user1", org_id="org1", permissions=["notification:approve"])
    
    # Pure function test - no database or external services
    result = domain.notifications.approve_notification(notification, user_context)
    
    assert result.is_success()
    assert result.value.status == "approved"

# ❌ WRONG - Tests requiring complex setup
def test_notification_approval():
    # Don't require database setup for domain logic tests
    setup_test_database()
    create_test_user()
    create_test_notification()
    
    result = notification_service.approve_notification("123", "user1")
    assert result.status == "approved"
```

## Code Organization Rules

### 13. File Structure Enforcement
**RULE**: Code MUST be organized according to the defined layer architecture.

```
api/
├── domain/           # Pure business logic only
│   ├── notifications.py
│   ├── authorization.py
│   └── audit.py
├── services/         # Side effects and external integrations
│   ├── mongodb.py
│   ├── redis.py
│   └── amqp.py
├── routes/           # HTTP handlers only
│   ├── notifications.py
│   └── auth.py
└── models/           # Pydantic schemas only
    ├── entities.py
    └── requests.py
```

### 14. Import Rules
**RULE**: Strict import hierarchy must be maintained.

```python
# ✅ CORRECT - Proper import hierarchy
# Routes can import from services, domain, and models
from services.mongodb import MongoDBService
from domain.notifications import approve_notification
from models.entities import Notification

# Services can import from domain and models
from domain.notifications import validate_notification_data
from models.entities import Notification

# Domain can only import from models and standard library
from models.entities import Notification
from typing import List, Dict

# ❌ WRONG - Circular or upward imports
# Domain importing from services (FORBIDDEN)
from services.mongodb import MongoDBService  # Domain should not know about services

# Services importing from routes (FORBIDDEN)  
from routes.notifications import notification_handler  # Services should not know about HTTP
```

These patterns are **NON-NEGOTIABLE** and must be followed in all backend code. Any deviations require explicit architectural review and approval.