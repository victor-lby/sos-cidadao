# S.O.S Cidadão API Documentation

This directory contains comprehensive API documentation for the S.O.S Cidadão platform.

## 📋 Contents

- [`openapi.yaml`](openapi.yaml) - Complete OpenAPI 3.0 specification
- [Authentication Guide](#authentication)
- [HAL Format Guide](#hal-format)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

## 🔐 Authentication

The API uses JWT (JSON Web Tokens) for authentication with the following flow:

### 1. Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "admin@municipality.gov",
  "password": "securePassword123"
}
```

**Response:**
```json
{
  "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...",
  "refreshToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...",
  "user": {
    "id": "user123",
    "email": "admin@municipality.gov",
    "name": "Admin User",
    "organizationId": "org456",
    "permissions": ["notification:approve", "notification:deny"]
  },
  "_links": {
    "self": { "href": "/api/auth/login" },
    "refresh": { "href": "/api/auth/refresh", "method": "POST" },
    "logout": { "href": "/api/auth/logout", "method": "POST" }
  }
}
```

### 2. Using Access Token
Include the access token in the Authorization header for all protected endpoints:

```http
GET /api/notifications
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
Accept: application/hal+json
```

### 3. Token Refresh
Access tokens expire after 15 minutes. Use the refresh token to get a new access token:

```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refreshToken": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."
}
```

### 4. Logout
Revoke tokens and logout:

```http
POST /api/auth/logout
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...
```

## 🔗 HAL Format

All API responses use HAL (Hypertext Application Language) format for hypermedia support.

### Key Concepts

- **`_links`**: Contains hypermedia links for navigation and actions
- **`_embedded`**: Contains embedded resources (used in collections)
- **Affordances**: Links that represent available actions based on current state and permissions

### Example HAL Response

```json
{
  "id": "notif123",
  "title": "Emergency Alert",
  "status": "received",
  "severity": 4,
  "_links": {
    "self": { 
      "href": "/api/notifications/notif123" 
    },
    "approve": { 
      "href": "/api/notifications/notif123/approve",
      "method": "POST"
    },
    "deny": { 
      "href": "/api/notifications/notif123/deny",
      "method": "POST"
    }
  }
}
```

### Collection Format

```json
{
  "total": 150,
  "page": 1,
  "pageSize": 20,
  "_embedded": {
    "items": [
      {
        "id": "notif123",
        "title": "Emergency Alert",
        "_links": {
          "self": { "href": "/api/notifications/notif123" }
        }
      }
    ]
  },
  "_links": {
    "self": { "href": "/api/notifications?page=1" },
    "first": { "href": "/api/notifications?page=1" },
    "next": { "href": "/api/notifications?page=2" },
    "last": { "href": "/api/notifications?page=8" }
  }
}
```

### Dynamic Actions

The presence of action links depends on:
- **Resource State**: `approve` and `deny` links only appear for notifications with status "received"
- **User Permissions**: Links only appear if the user has the required permission
- **Business Rules**: Additional constraints may apply

## ❌ Error Handling

Errors follow RFC 7807 Problem Details format with HAL extensions.

### Error Response Format

```json
{
  "type": "https://api.sos-cidadao.org/problems/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "The request body contains invalid data",
  "instance": "/api/notifications/123",
  "errors": [
    {
      "field": "severity",
      "message": "Must be between 0 and 5"
    },
    {
      "field": "title",
      "message": "Title is required"
    }
  ],
  "_links": {
    "self": { "href": "/api/notifications/123" },
    "help": { "href": "https://docs.sos-cidadao.org/api/errors#validation" }
  }
}
```

### HTTP Status Codes

| Code | Description | When Used |
|------|-------------|-----------|
| 200 | OK | Successful GET, PUT, POST operations |
| 201 | Created | Successful resource creation |
| 400 | Bad Request | Invalid request data or business rule violation |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | Valid token but insufficient permissions |
| 404 | Not Found | Resource doesn't exist or is soft-deleted |
| 409 | Conflict | Resource conflict (e.g., duplicate creation) |
| 422 | Unprocessable Entity | Valid JSON but semantic errors |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Service temporarily unavailable |

## 🚦 Rate Limiting

The API implements rate limiting to prevent abuse:

- **Per Organization**: 1000 requests per hour per organization
- **Per User**: 100 requests per minute per user
- **Per IP**: 500 requests per hour per IP address

### Rate Limit Headers

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

### Rate Limit Exceeded Response

```json
{
  "type": "https://api.sos-cidadao.org/problems/rate-limit-exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "Too many requests. Please try again later.",
  "instance": "/api/notifications",
  "_links": {
    "self": { "href": "/api/notifications" }
  }
}
```

## 📝 Examples

### Complete Notification Workflow

#### 1. Create Notification (Webhook)
```http
POST /api/notifications
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Road Closure Alert",
  "body": "Main Street closed for emergency repairs until 6 PM",
  "severity": 3,
  "origin": "traffic-management-system",
  "originalPayload": {
    "street": "Main Street",
    "reason": "Emergency repairs",
    "duration": "4 hours"
  },
  "targets": ["downtown", "business-district"],
  "categories": ["traffic", "emergency"]
}
```

#### 2. List Pending Notifications
```http
GET /api/notifications?status=received&page=1&pageSize=10
Authorization: Bearer <token>
Accept: application/hal+json
```

#### 3. Get Notification Details
```http
GET /api/notifications/notif123
Authorization: Bearer <token>
Accept: application/hal+json
```

#### 4. Approve Notification
```http
POST /api/notifications/notif123/approve
Authorization: Bearer <token>
Content-Type: application/json

{
  "targets": ["downtown", "business-district"],
  "categories": ["traffic", "emergency"]
}
```

#### 5. Check Audit Trail
```http
GET /api/audit-logs?entity=notification&entityId=notif123
Authorization: Bearer <token>
Accept: application/hal+json
```

### Search and Filtering

#### Search Notifications
```http
GET /api/notifications?search=emergency&severity=4&page=1
Authorization: Bearer <token>
```

#### Filter by Date Range
```http
GET /api/audit-logs?startDate=2024-01-01T00:00:00Z&endDate=2024-01-31T23:59:59Z
Authorization: Bearer <token>
```

### Error Scenarios

#### Invalid Notification Data
```http
POST /api/notifications
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "",
  "severity": 10
}
```

**Response (400 Bad Request):**
```json
{
  "type": "https://api.sos-cidadao.org/problems/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "The request body contains invalid data",
  "errors": [
    {
      "field": "title",
      "message": "Title cannot be empty"
    },
    {
      "field": "severity",
      "message": "Must be between 0 and 5"
    }
  ]
}
```

#### Insufficient Permissions
```http
POST /api/notifications/notif123/approve
Authorization: Bearer <token-without-approve-permission>
```

**Response (403 Forbidden):**
```json
{
  "type": "https://api.sos-cidadao.org/problems/insufficient-permissions",
  "title": "Insufficient Permissions",
  "status": 403,
  "detail": "You don't have permission to approve notifications",
  "instance": "/api/notifications/notif123/approve"
}
```

## 🔧 Development Tools

### Interactive Documentation

When running in development mode with `DOCS_ENABLED=true`:

- **Swagger UI**: http://localhost:5000/docs
- **Redoc**: http://localhost:5000/redoc

### OpenAPI Validation

Validate the OpenAPI specification:

```bash
npx @redocly/cli lint docs/API/openapi.yaml
```

### Code Generation

Generate client SDKs from the OpenAPI spec:

```bash
# Generate TypeScript client
npx @openapitools/openapi-generator-cli generate \
  -i docs/API/openapi.yaml \
  -g typescript-axios \
  -o clients/typescript

# Generate Python client
npx @openapitools/openapi-generator-cli generate \
  -i docs/API/openapi.yaml \
  -g python \
  -o clients/python
```

## 📚 Additional Resources

- [HAL Specification](https://tools.ietf.org/html/draft-kelly-json-hal-08)
- [RFC 7807 Problem Details](https://tools.ietf.org/html/rfc7807)
- [OpenAPI 3.0 Specification](https://swagger.io/specification/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)

## 🤝 Contributing

When making API changes:

1. Update the OpenAPI specification in `openapi.yaml`
2. Validate the spec with Redocly CLI
3. Update this documentation
4. Add examples for new endpoints
5. Test with the interactive documentation

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/sos-cidadao/issues)
- **API Questions**: Tag with `api` label
- **Documentation**: This README and the OpenAPI spec