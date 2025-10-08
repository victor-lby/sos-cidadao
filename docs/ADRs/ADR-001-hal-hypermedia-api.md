# ADR-001: Use HAL for API Hypermedia

## Status
Accepted

## Context
We need a standard format for hypermedia APIs that supports discoverability and follows HATEOAS Level-3 principles. The API should allow clients to discover available actions dynamically without hardcoding URLs or business logic.

## Decision
Use HAL (Hypertext Application Language) for all API responses with the following specifications:

- Content-Type: `application/hal+json`
- Include `_links` object with at minimum a `self` link
- Use conditional affordance links based on resource state and user permissions
- Include `_embedded` resources for collections
- Follow HAL specification strictly when `HAL_STRICT` feature flag is enabled

## Consequences

### Positive
- **API Discoverability**: Clients can discover available actions dynamically
- **Reduced Coupling**: Frontend doesn't need to hardcode business rules about when actions are available
- **Consistent Format**: Standardized hypermedia format across all endpoints
- **Future-Proof**: Easy to add new actions without breaking existing clients

### Negative
- **Response Size**: HAL responses are larger due to link metadata
- **Complexity**: Requires careful link generation logic based on permissions and state
- **Learning Curve**: Developers need to understand HAL concepts

## Implementation Details

### Example HAL Response
```json
{
  "id": "123",
  "title": "Emergency Alert",
  "status": "received",
  "_links": {
    "self": { "href": "/api/notifications/123" },
    "approve": { 
      "href": "/api/notifications/123/approve",
      "method": "POST"
    },
    "deny": { 
      "href": "/api/notifications/123/deny",
      "method": "POST"
    }
  }
}
```

### Link Generation Rules
- `approve` link only present if status is "received" and user has "notification:approve" permission
- `deny` link only present if status is "received" and user has "notification:deny" permission
- `edit` link only present if user has "notification:edit" permission

## References
- [HAL Specification](https://tools.ietf.org/html/draft-kelly-json-hal-08)
- [HATEOAS Maturity Model](https://martinfowler.com/articles/richardsonMaturityModel.html)