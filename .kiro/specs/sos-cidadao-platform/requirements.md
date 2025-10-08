# Requirements Document

## Introduction

S.O.S Cidadão is a public, open-source civic notification system designed for multi-tenant municipal operations. The platform enables municipal teams to receive, moderate, and broadcast critical public alerts through an auditable workflow. The system features a serverless Python backend with Flask, a Vue 3 + Vuetify 3 frontend, JWT authentication, HATEOAS Level-3 APIs using HAL, full observability via OpenTelemetry, Redis caching, MongoDB Atlas storage, and AMQP message queuing via LavinMQ. The platform is designed to deploy on Vercel by default with Docker support for local development.

## Requirements

### Requirement 1: Multi-tenant Organization Management

**User Story:** As a system administrator, I want to manage multiple municipal organizations within a single platform, so that each municipality can operate independently with isolated data and users.

#### Acceptance Criteria

1. WHEN a new organization is created THEN the system SHALL store organization data with unique id, name, slug, timestamps, and schemaVersion
2. WHEN any data query is executed THEN the system SHALL automatically scope results to the authenticated user's organization
3. WHEN an organization is soft-deleted THEN the system SHALL set deletedAt timestamp and exclude it from default queries
4. IF a user attempts to access data from another organization THEN the system SHALL deny access and return 403 Forbidden

### Requirement 2: User Authentication and Authorization

**User Story:** As a municipal operator, I want to securely log in with role-based permissions, so that I can perform only the actions authorized for my role within my organization.

#### Acceptance Criteria

1. WHEN a user logs in with valid credentials THEN the system SHALL issue JWT access and refresh tokens
2. WHEN an access token expires THEN the system SHALL allow token refresh using a valid refresh token
3. WHEN a token is revoked THEN the system SHALL add it to Redis blocklist and reject subsequent requests using that token
4. IF a user lacks required permission for an action THEN the system SHALL return 403 Forbidden with clear error message
5. WHEN a user is assigned roles THEN the system SHALL aggregate all permissions from those roles for authorization checks
6. WHEN JWT tokens are issued THEN the system SHALL include organizationId claim for multi-tenant scoping

### Requirement 3: Notification Intake via Webhook

**User Story:** As an external system integrator, I want to submit notifications via a secure webhook endpoint, so that alerts can be ingested into the moderation workflow.

#### Acceptance Criteria

1. WHEN a POST request is made to /notifications/incoming with valid JWT THEN the system SHALL create a notification with status='received'
2. WHEN a notification is created THEN the system SHALL preserve the originalPayload and origin metadata
3. WHEN a notification is stored THEN the system SHALL include organizationId, createdBy, createdAt, updatedAt, and schemaVersion fields
4. IF the webhook request lacks valid JWT THEN the system SHALL return 401 Unauthorized
5. WHEN notification data is invalid THEN the system SHALL return 400 Bad Request with Pydantic validation errors

### Requirement 4: Notification Review and Moderation

**User Story:** As a municipal operator, I want to review incoming notifications and decide whether to approve or deny them, so that only verified alerts are dispatched to the public.

#### Acceptance Criteria

1. WHEN I request GET /notifications?status=received THEN the system SHALL return a HAL collection with pagination links (self, next, prev, item)
2. WHEN I request GET /notifications/{id} THEN the system SHALL return notification details with HAL affordance links for approve and deny actions
3. WHEN I view a notification detail THEN the system SHALL display title, body, severity, origin, targets, categories, and current status
4. IF I lack 'notification:review' permission THEN the system SHALL deny access to review endpoints
5. WHEN notifications are listed THEN the system SHALL support filtering by status, severity, date range, and target

### Requirement 5: Notification Approval and Dispatch

**User Story:** As a municipal operator, I want to approve notifications and have them automatically dispatched to configured endpoints, so that critical alerts reach the public through appropriate channels.

#### Acceptance Criteria

1. WHEN I POST to /notifications/{id}/approve with valid permissions THEN the system SHALL validate target and category selections
2. WHEN a notification is approved THEN the system SHALL publish a message to LavinMQ queue with transformed payload based on endpoint dataMapping
3. WHEN a message is published THEN the system SHALL update notification status to 'dispatched'
4. WHEN approval completes THEN the system SHALL create an audit log entry with userId, action, before/after state, and traceId
5. IF message publishing fails THEN the system SHALL log the error, maintain status as 'approved', and return 500 with retry guidance
6. WHEN multiple endpoints are configured for selected categories THEN the system SHALL publish separate messages for each endpoint

### Requirement 6: Notification Denial

**User Story:** As a municipal operator, I want to deny inappropriate or invalid notifications with a reason, so that the decision is documented and auditable.

#### Acceptance Criteria

1. WHEN I POST to /notifications/{id}/deny with a reason THEN the system SHALL update status to 'denied' and store the reason
2. WHEN a notification is denied THEN the system SHALL create an audit log entry with denial reason and metadata
3. WHEN a denied notification is viewed THEN the system SHALL display the denial reason and timestamp
4. IF I lack 'notification:moderate' permission THEN the system SHALL return 403 Forbidden

### Requirement 7: HATEOAS Level-3 API with HAL

**User Story:** As an API consumer, I want hypermedia-driven responses with embedded links and resources, so that I can discover available actions dynamically without hardcoding URLs.

#### Acceptance Criteria

1. WHEN any API response is returned THEN the system SHALL use Content-Type: application/hal+json
2. WHEN a resource is returned THEN the system SHALL include _links object with at minimum a self link
3. WHEN a collection is returned THEN the system SHALL include _links for pagination (next, prev, first, last) and _embedded with items
4. WHEN a notification detail is returned THEN the system SHALL include conditional affordance links (approve, deny) based on current status and user permissions
5. WHEN HAL_STRICT feature flag is enabled THEN the system SHALL validate all responses against HAL specification

### Requirement 8: OpenAPI 3.0 Documentation

**User Story:** As a developer integrating with the API, I want comprehensive OpenAPI documentation with request/response schemas, so that I can understand and test endpoints efficiently.

#### Acceptance Criteria

1. WHEN the API is deployed THEN the system SHALL generate OpenAPI 3.0 specification at /openapi.json
2. WHEN DOCS_ENABLED=true in development THEN the system SHALL expose Swagger UI at /docs and Redoc at /redoc
3. WHEN in production THEN the system SHALL disable interactive docs by default unless explicitly enabled via feature flag
4. WHEN OpenAPI spec is generated THEN the system SHALL include all routes, Pydantic schemas, authentication requirements, and HAL examples
5. WHEN CI pipeline runs THEN the system SHALL validate OpenAPI spec using Redocly CLI and fail build if invalid

### Requirement 9: Comprehensive Audit Logging

**User Story:** As a compliance officer, I want to view a complete audit trail of all user actions, so that I can investigate incidents and ensure accountability.

#### Acceptance Criteria

1. WHEN any state-changing action occurs THEN the system SHALL create an audit log entry with timestamp, userId, orgId, entity, entityId, action, before, after, ip, userAgent, and traceId
2. WHEN I access the audit UI THEN the system SHALL allow filtering by user, organization, time range, entity type, and action
3. WHEN I view audit logs THEN the system SHALL display entries in reverse chronological order with pagination
4. WHEN I export audit logs THEN the system SHALL generate CSV or JSON format with all filtered records
5. WHEN an audit entry is created THEN the system SHALL include OpenTelemetry traceId for correlation with observability traces

### Requirement 10: OpenTelemetry Observability

**User Story:** As a DevOps engineer, I want distributed tracing, structured logging, and metrics exported via OpenTelemetry, so that I can monitor system health and troubleshoot issues vendor-agnostically.

#### Acceptance Criteria

1. WHEN OTEL_ENABLED=true THEN the system SHALL auto-instrument Flask and HTTP client libraries
2. WHEN a request is processed THEN the system SHALL create a trace with spans for HTTP handling, database queries, Redis operations, and AMQP publishing
3. WHEN approval or denial actions occur THEN the system SHALL create custom spans with relevant attributes (notificationId, status, userId)
4. WHEN logs are emitted THEN the system SHALL include trace_id and span_id for correlation
5. WHEN running locally THEN the system SHALL export telemetry to OpenTelemetry Collector configured in docker-compose
6. WHEN in production THEN the system SHALL export telemetry to configured OTLP endpoint via environment variables

### Requirement 11: Data Storage with MongoDB Atlas

**User Story:** As a backend developer, I want persistent storage in MongoDB Atlas with schema versioning, so that data is durable and migrations are manageable.

#### Acceptance Criteria

1. WHEN any entity is created THEN the system SHALL include schemaVersion field set to current version integer
2. WHEN connecting to MongoDB THEN the system SHALL use connection pooling and configure appropriate timeouts
3. WHEN queries are executed THEN the system SHALL automatically filter out soft-deleted records (deletedAt != null) unless explicitly requested
4. WHEN documents are updated THEN the system SHALL update the updatedAt timestamp and updatedBy field
5. WHEN a soft-delete occurs THEN the system SHALL set deletedAt timestamp without removing the document

### Requirement 12: Redis Caching and Token Management

**User Story:** As a backend developer, I want Redis for caching and JWT token management, so that frequently accessed data is fast and token revocation is immediate.

#### Acceptance Criteria

1. WHEN using Redis in serverless environment THEN the system SHALL use Upstash HTTP-based client for connectionless access
2. WHEN a JWT is revoked THEN the system SHALL add token ID to Redis blocklist with TTL matching token expiration
3. WHEN validating JWT THEN the system SHALL check Redis blocklist and reject if present
4. WHEN caching data THEN the system SHALL set appropriate TTL values and use org-scoped cache keys
5. WHEN Redis is unavailable THEN the system SHALL log errors and degrade gracefully without blocking requests

### Requirement 13: Message Queue Integration with LavinMQ

**User Story:** As a system integrator, I want approved notifications published to AMQP queue, so that downstream systems can consume and process alerts asynchronously.

#### Acceptance Criteria

1. WHEN a notification is approved THEN the system SHALL publish message to CloudAMQP LavinMQ using AMQP protocol
2. WHEN publishing a message THEN the system SHALL transform notification data using endpoint-specific dataMapping configuration
3. WHEN multiple categories are selected THEN the system SHALL route messages to appropriate exchanges/queues based on endpoint configuration
4. IF queue publishing fails THEN the system SHALL retry with exponential backoff and log failure details
5. WHEN message is published THEN the system SHALL include correlation ID and trace context for distributed tracing

### Requirement 14: Notification Target Hierarchy

**User Story:** As a municipal operator, I want to organize notification targets in a hierarchical structure, so that I can efficiently manage geographic or organizational groupings.

#### Acceptance Criteria

1. WHEN creating a NotificationTarget THEN the system SHALL allow optional parent reference for hierarchy
2. WHEN a target has a parent THEN the system SHALL maintain bidirectional relationship with children array
3. WHEN querying targets THEN the system SHALL support retrieving full hierarchy tree or flat list
4. WHEN a notification is approved for a parent target THEN the system SHALL optionally cascade to all child targets based on configuration
5. WHEN soft-deleting a parent target THEN the system SHALL handle child targets according to configured cascade policy

### Requirement 15: Notification Categories and Endpoint Mapping

**User Story:** As a system administrator, I want to configure notification categories mapped to endpoints, so that different alert types route to appropriate external systems.

#### Acceptance Criteria

1. WHEN creating a NotificationCategory THEN the system SHALL allow association with multiple NotificationTargets
2. WHEN creating an Endpoint THEN the system SHALL require name, URL, dataMapping configuration, and associated categories
3. WHEN a notification is approved THEN the system SHALL determine target endpoints based on selected categories
4. WHEN dataMapping is applied THEN the system SHALL transform notification fields to match external API schema
5. WHEN endpoint configuration is invalid THEN the system SHALL validate on save and return clear error messages

### Requirement 16: Role-Based Access Control

**User Story:** As an organization administrator, I want to assign roles with specific permissions to users, so that access is controlled according to job responsibilities.

#### Acceptance Criteria

1. WHEN creating a Role THEN the system SHALL allow assignment of multiple Permissions
2. WHEN assigning a Role to a User THEN the system SHALL scope the assignment to the user's organization
3. WHEN checking permissions THEN the system SHALL aggregate all permissions from all user roles
4. WHEN a permission is revoked from a role THEN the system SHALL immediately affect all users with that role
5. WHEN listing available actions THEN the system SHALL filter HAL affordance links based on user permissions

### Requirement 17: Frontend with Vue 3 and Vuetify 3

**User Story:** As a municipal operator, I want a modern, responsive Material Design interface, so that I can efficiently manage notifications on desktop and mobile devices.

#### Acceptance Criteria

1. WHEN the frontend loads THEN the system SHALL use Vuetify 3 with Material Design 3 theming
2. WHEN navigating the app THEN the system SHALL use Vue Router for client-side routing
3. WHEN managing state THEN the system SHALL use Pinia stores for authentication, notifications, and UI state
4. WHEN displaying notifications list THEN the system SHALL render data tables with sorting, filtering, and pagination
5. WHEN HAL links are present THEN the system SHALL render action buttons dynamically based on available affordances
6. WHEN on mobile devices THEN the system SHALL adapt layout responsively using Vuetify breakpoints

### Requirement 18: Vercel Serverless Deployment

**User Story:** As a DevOps engineer, I want the application to deploy seamlessly on Vercel, so that infrastructure management is minimal and scaling is automatic.

#### Acceptance Criteria

1. WHEN deploying to Vercel THEN the system SHALL use Python serverless functions for API routes under /api/*
2. WHEN configuring Vercel THEN the system SHALL use vercel.json for routing, environment variables, and build settings
3. WHEN a serverless function is invoked THEN the system SHALL reuse database and Redis connections across invocations to minimize cold start impact
4. WHEN environment variables are needed THEN the system SHALL document all required vars (MongoDB URI, Redis URL/TOKEN, JWT secrets, AMQP URL)
5. WHEN frontend is deployed THEN the system SHALL serve Vue 3 SPA with proper routing and API proxy configuration

### Requirement 19: Docker Development Environment

**User Story:** As a developer, I want to run the complete stack locally using Docker Compose, so that I can develop and test without external dependencies.

#### Acceptance Criteria

1. WHEN running docker-compose up THEN the system SHALL start MongoDB, Redis, LavinMQ, and OpenTelemetry Collector services
2. WHEN the API starts locally THEN the system SHALL connect to containerized MongoDB and Redis instances
3. WHEN DOCS_ENABLED=true locally THEN the system SHALL expose Swagger UI and Redoc for API exploration
4. WHEN publishing messages locally THEN the system SHALL use containerized LavinMQ instance
5. WHEN telemetry is enabled THEN the system SHALL export to local Collector with console exporter for debugging

### Requirement 20: CI/CD Pipeline with GitHub Actions

**User Story:** As a development team, I want automated validation and security checks in CI/CD, so that code quality and security standards are enforced before deployment.

#### Acceptance Criteria

1. WHEN a PR is opened THEN the system SHALL run OpenAPI validation using Redocly CLI and fail if spec is invalid
2. WHEN a PR is opened THEN the system SHALL run Codium PR-Agent for AI-powered code review
3. WHEN code is pushed THEN the system SHALL run Gitleaks to scan for exposed secrets and fail if found
4. WHEN dependencies have updates THEN Dependabot SHALL create PRs for security and version updates
5. WHEN all checks pass THEN the system SHALL allow merge and trigger deployment to Vercel preview environment

### Requirement 21: Functional Programming Patterns

**User Story:** As a backend developer, I want domain logic implemented as pure functions, so that code is testable, maintainable, and side-effects are isolated.

#### Acceptance Criteria

1. WHEN implementing domain logic THEN the system SHALL use pure functions that accept inputs and return outputs without side effects
2. WHEN side effects are needed (DB, Redis, AMQP) THEN the system SHALL isolate them in service layer functions
3. WHEN composing operations THEN the system SHALL use dependency injection to pass service functions to domain logic
4. WHEN testing domain logic THEN the system SHALL be able to test pure functions without mocking external dependencies
5. WHEN handling errors THEN the system SHALL use Result/Either patterns or exceptions at service boundaries, not within pure functions

### Requirement 22: Apache 2.0 Open Source License

**User Story:** As an open source contributor, I want the project licensed under Apache 2.0, so that usage, modification, and distribution rights are clear and permissive.

#### Acceptance Criteria

1. WHEN the repository is created THEN the system SHALL include LICENSE file with Apache 2.0 text
2. WHEN source files are created THEN the system SHALL include SPDX license identifier comments where appropriate
3. WHEN documentation is published THEN the system SHALL clearly state Apache 2.0 licensing
4. WHEN accepting contributions THEN the system SHALL include CONTRIBUTING.md with CLA or DCO requirements
5. WHEN third-party dependencies are added THEN the system SHALL verify license compatibility with Apache 2.0

### Requirement 23: Health Check and System Status

**User Story:** As a monitoring system, I want a health check endpoint that returns system status with HAL links, so that I can verify service availability and dependencies.

#### Acceptance Criteria

1. WHEN GET /healthz is requested THEN the system SHALL return 200 OK with HAL response including _links.self
2. WHEN health check runs THEN the system SHALL verify connectivity to MongoDB, Redis, and LavinMQ
3. WHEN a dependency is unavailable THEN the system SHALL return 503 Service Unavailable with details of failed checks
4. WHEN health check succeeds THEN the system SHALL include version, environment, and timestamp in response
5. WHEN health endpoint is called THEN the system SHALL not require authentication

### Requirement 24: Conventional Commits and Changelog

**User Story:** As a project maintainer, I want standardized commit messages and automated changelog generation, so that release notes are consistent and comprehensive.

#### Acceptance Criteria

1. WHEN commits are made THEN the system SHALL follow Conventional Commits format (feat:, fix:, docs:, etc.)
2. WHEN a release is tagged THEN the system SHALL generate CHANGELOG.md in Keep a Changelog format
3. WHEN changelog is generated THEN the system SHALL group changes by type (Added, Changed, Fixed, etc.)
4. WHEN OpenAPI spec changes THEN the system SHALL store versioned spec artifacts with each release
5. WHEN CI runs THEN the system SHALL validate commit message format and fail if non-compliant

### Requirement 25: Feature Flags and Environment Configuration

**User Story:** As a DevOps engineer, I want environment-specific configuration and feature flags, so that behavior can be controlled without code changes.

#### Acceptance Criteria

1. WHEN the application starts THEN the system SHALL load configuration based on environment (DEV, STAGE, PROD)
2. WHEN DOCS_ENABLED flag is set THEN the system SHALL enable or disable interactive API documentation
3. WHEN OTEL_ENABLED flag is set THEN the system SHALL enable or disable OpenTelemetry instrumentation
4. WHEN HAL_STRICT flag is set THEN the system SHALL enforce strict HAL specification validation
5. WHEN configuration is invalid THEN the system SHALL fail fast at startup with clear error messages
