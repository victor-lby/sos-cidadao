# ADR-003: Multi-Tenant Architecture with Organization Scoping

## Status
Accepted

## Context
The S.O.S Cidadão platform needs to support multiple municipalities (organizations) within a single deployment while ensuring complete data isolation and security between tenants.

## Decision
Implement multi-tenancy using organization scoping with the following approach:

1. **Shared Database, Isolated Data**: Single MongoDB instance with organization-scoped collections
2. **Organization ID in All Documents**: Every document includes `organizationId` field
3. **Automatic Scoping**: All database queries automatically include organization filter
4. **JWT-Based Tenant Context**: Organization ID embedded in JWT tokens
5. **Service Layer Enforcement**: All service methods require organization ID parameter

## Consequences

### Positive
- **Cost Effective**: Single database deployment for all tenants
- **Data Isolation**: Complete separation between organizations
- **Scalability**: Easy to add new organizations without infrastructure changes
- **Security**: Automatic scoping prevents cross-organization data access
- **Maintenance**: Single codebase and deployment for all tenants

### Negative
- **Query Complexity**: All queries must include organization scoping
- **Performance**: Additional filter on every query
- **Risk**: Programming errors could potentially leak data between tenants

## Implementation Details

### Database Schema
```javascript
// All collections include organizationId
{
  "_id": "ObjectId",
  "organizationId": "ObjectId",  // MANDATORY
  "title": "string",
  "status": "string",
  "createdAt": "ISODate",
  "updatedAt": "ISODate",
  "deletedAt": "ISODate | null",
  "schemaVersion": "number"
}
```

### Service Layer Scoping
```python
class MongoDBService:
    def find_by_org(self, collection: str, org_id: str, filters: Dict = None) -> List[Dict]:
        """All queries automatically scoped to organization."""
        query = {"organizationId": org_id, "deletedAt": None}
        if filters:
            query.update(filters)
        return list(self.db[collection].find(query))
    
    def update_by_org(self, collection: str, org_id: str, doc_id: str, updates: Dict) -> bool:
        """Updates automatically scoped to organization."""
        result = self.db[collection].update_one(
            {"_id": doc_id, "organizationId": org_id, "deletedAt": None},
            {"$set": {**updates, "updatedAt": datetime.utcnow()}}
        )
        return result.modified_count > 0
```

### JWT Token Structure
```json
{
  "sub": "user_id",
  "org_id": "organization_id",
  "permissions": ["notification:approve", "notification:deny"],
  "exp": 1234567890,
  "iat": 1234567890
}
```

### User Context Propagation
```python
@dataclass
class UserContext:
    user_id: str
    org_id: str  # Extracted from JWT
    permissions: List[str]
    trace_id: str

def handle_request(request_data: Dict, user_context: UserContext) -> Response:
    # All operations automatically scoped to user_context.org_id
    result = notification_service.create_notification(request_data, user_context)
    return build_hal_response(result, user_context)
```

### Database Indexes
```javascript
// Performance indexes with organization scoping
db.notifications.createIndex({ "organizationId": 1, "status": 1, "createdAt": -1 })
db.users.createIndex({ "organizationId": 1, "email": 1 }, { unique: true })
db.audit_logs.createIndex({ "organizationId": 1, "timestamp": -1 })
```

## Security Measures

### Automatic Scoping Enforcement
- **Service Layer**: All methods require `org_id` parameter
- **Database Queries**: Automatic organization filter in all queries
- **JWT Validation**: Organization ID extracted from validated token
- **API Responses**: HAL links scoped to user's organization

### Data Isolation Verification
```python
def test_organization_data_isolation():
    """Ensure users cannot access other organization's data."""
    org1_user = create_user(org_id="org1")
    org2_notification = create_notification(org_id="org2")
    
    # Should return empty result, not org2's notification
    result = notification_service.get_notification(org2_notification.id, org1_user.context)
    assert result is None
```

### Audit Trail
```python
# All audit logs include organization context
audit_entry = {
    "timestamp": datetime.utcnow(),
    "userId": user_context.user_id,
    "organizationId": user_context.org_id,  # Always included
    "entity": "notification",
    "action": "approve",
    "before": before_state,
    "after": after_state
}
```

## Alternative Approaches Considered

### Database Per Tenant
- **Pros**: Complete isolation, easier backup/restore per tenant
- **Cons**: Higher infrastructure costs, complex deployment, harder to maintain

### Schema Per Tenant
- **Pros**: Good isolation, single database
- **Cons**: Complex schema management, harder to add new tenants

### Application-Level Routing
- **Pros**: Complete separation
- **Cons**: Multiple deployments, higher operational overhead

## Migration Strategy

### Adding New Organizations
```python
def create_organization(name: str, slug: str, admin_user: Dict) -> Organization:
    """Create new organization with admin user."""
    org = Organization(
        name=name,
        slug=slug,
        created_at=datetime.utcnow(),
        schema_version=1
    )
    
    # Create admin user for organization
    admin = User(
        organization_id=org.id,
        email=admin_user["email"],
        name=admin_user["name"],
        roles=["admin"],
        schema_version=1
    )
    
    return org
```

### Data Migration
```python
def migrate_to_multi_tenant():
    """Migrate existing single-tenant data to multi-tenant structure."""
    default_org_id = create_default_organization()
    
    # Add organizationId to all existing documents
    for collection_name in ["notifications", "users", "audit_logs"]:
        db[collection_name].update_many(
            {"organizationId": {"$exists": False}},
            {"$set": {"organizationId": default_org_id}}
        )
```

## Monitoring and Observability

### Metrics by Organization
- Request count per organization
- Error rates per organization
- Response times per organization
- Storage usage per organization

### Audit and Compliance
- All actions logged with organization context
- Data access patterns monitored
- Cross-organization access attempts logged as security events

## References
- [Multi-Tenant Data Architecture](https://docs.microsoft.com/en-us/azure/sql-database/saas-tenancy-app-design-patterns)
- [SaaS Tenant Isolation Strategies](https://aws.amazon.com/blogs/apn/saas-tenant-isolation-strategies/)
- [MongoDB Multi-Tenancy](https://www.mongodb.com/blog/post/building-multitenant-applications-with-mongodb)