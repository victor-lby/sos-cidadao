# Project Structure & Organization

## Repository Layout

```
/
├── LICENSE                    # Apache-2.0 license
├── README.md                  # Project overview and setup instructions
├── vercel.json               # Vercel deployment configuration
├── docker-compose.yml        # Local development environment
├── docker-compose.test.yml   # Testing environment
├── .github/
│   └── workflows/            # GitHub Actions CI/CD pipelines
│       ├── openapi-validate.yml
│       ├── pr-agent.yml
│       ├── dependabot.yml
│       └── gitleaks.yml
├── frontend/                 # Vue 3 + Vuetify 3 SPA
│   ├── src/
│   │   ├── components/       # Reusable Vue components
│   │   ├── views/           # Page-level components
│   │   ├── stores/          # Pinia state management
│   │   ├── router/          # Vue Router configuration
│   │   ├── services/        # API client and HAL utilities
│   │   └── utils/           # Helper functions
│   ├── package.json
│   └── vite.config.js
├── api/                     # Vercel Serverless Python API
│   ├── __init__.py
│   ├── app.py              # Flask app entry point
│   ├── routes/             # HTTP endpoint handlers
│   ├── domain/             # Pure business logic functions
│   ├── services/           # External service integrations
│   ├── models/             # Pydantic data models
│   ├── observability/      # OpenTelemetry configuration
│   ├── specs/              # OpenAPI specification
│   └── requirements.txt
├── infra/
│   ├── docker/             # Dockerfile and compose configs
│   └── collector/          # OpenTelemetry Collector config
└── docs/
    ├── ADRs/               # Architecture Decision Records
    ├── API/                # API documentation
    ├── CONTRIBUTING.md
    └── CODE_OF_CONDUCT.md
```

## Backend Architecture (api/)

### Domain Layer (`domain/`)
Contains pure business logic functions with no side effects:
- `notifications.py` - Notification workflow logic
- `authorization.py` - Permission and role logic
- `audit.py` - Audit trail generation
- `transformations.py` - Data mapping and validation

### Service Layer (`services/`)
Handles external integrations and side effects:
- `mongodb.py` - Database operations with connection pooling
- `redis.py` - Caching and JWT token management
- `amqp.py` - Message queue publishing
- `auth.py` - JWT token operations
- `audit.py` - Audit log persistence

### Routes Layer (`routes/`)
HTTP endpoint handlers that orchestrate domain and service calls:
- `notifications.py` - Notification CRUD and workflow endpoints
- `auth.py` - Authentication and user management
- `admin.py` - Organization and entity management
- `audit.py` - Audit log querying and export
- `health.py` - Health checks and system status

### Models Layer (`models/`)
Pydantic schemas for request/response validation:
- `entities.py` - Core entity models (Organization, User, Notification, etc.)
- `requests.py` - API request schemas
- `responses.py` - HAL response schemas
- `enums.py` - Enumeration types

## Frontend Architecture (frontend/src/)

### Components (`components/`)
Reusable Vue 3 components:
- `common/` - Generic UI components
- `notifications/` - Notification-specific components
- `admin/` - Administrative interface components
- `auth/` - Authentication-related components

### Views (`views/`)
Page-level components for routing:
- `LoginView.vue` - Authentication page
- `NotificationsView.vue` - Notification management
- `AdminView.vue` - Administrative dashboard
- `AuditView.vue` - Audit log viewer

### Stores (`stores/`)
Pinia state management:
- `auth.js` - Authentication state and JWT handling
- `notifications.js` - Notification data and operations
- `admin.js` - Administrative entity management
- `ui.js` - UI state (loading, errors, themes)

### Services (`services/`)
API integration and utilities:
- `api.js` - Axios HTTP client with HAL support
- `hal.js` - HAL response parsing and link handling
- `auth.js` - JWT token management
- `websocket.js` - Real-time updates (if needed)

## Multi-Tenant Data Organization

### Organization Scoping
All data operations are automatically scoped to the authenticated user's organization:
- Database queries include `organizationId` filter
- API endpoints validate organization access
- HAL links are generated with organization context
- Audit logs include organization isolation

### Entity Relationships
```
Organization (1) ──→ (N) User
Organization (1) ──→ (N) Notification
Organization (1) ──→ (N) NotificationTarget
Organization (1) ──→ (N) NotificationCategory
Organization (1) ──→ (N) Endpoint
Organization (1) ──→ (N) Role
User (N) ──→ (N) Role (many-to-many)
Role (N) ──→ (N) Permission (many-to-many)
```

## Configuration Management

### Environment-Specific Config
- `config/dev.py` - Development settings
- `config/staging.py` - Staging environment
- `config/production.py` - Production settings
- `config/base.py` - Shared configuration

### Feature Flags
Controlled via environment variables:
- Documentation endpoints (DOCS_ENABLED)
- OpenTelemetry instrumentation (OTEL_ENABLED)
- Strict HAL validation (HAL_STRICT)

## Testing Organization

### Backend Tests (`api/tests/`)
- `unit/` - Pure function tests
- `integration/` - Service integration tests
- `e2e/` - End-to-end workflow tests
- `fixtures/` - Test data and utilities

### Frontend Tests (`frontend/tests/`)
- `unit/` - Component unit tests
- `integration/` - Store and service tests
- `e2e/` - Playwright end-to-end tests

## Naming Conventions

### Files and Directories
- **Snake case** for Python files: `notification_service.py`
- **Kebab case** for Vue files: `notification-list.vue`
- **Camel case** for JavaScript: `notificationStore.js`

### API Endpoints
- **RESTful** with organization scoping: `/api/organizations/{orgId}/notifications`
- **HAL affordances** for actions: `_links.approve`, `_links.deny`
- **Consistent** HTTP methods: GET (read), POST (create), PUT (update), DELETE (remove)

### Database Collections
- **Plural nouns**: `organizations`, `users`, `notifications`
- **Consistent** field naming: `createdAt`, `updatedAt`, `deletedAt`
- **Organization scoping**: `organizationId` field in all tenant data