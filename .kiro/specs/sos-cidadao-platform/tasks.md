# Implementation Plan

- [-] 1. Set up project structure and core infrastructure
- [x] 1.1 Initialize repository and trunk-based workflow
  - Initialize git repository with main branch
  - Create .gitignore for Python and Node.js
  - Set up branch protection rules and conventional commit validation
  - Create initial commit with project structure
  - _Requirements: 24.1, 24.5_

- [-] 1.2 Create project directory structure
  - Create feature branch: `git checkout -b feat/project-structure`
  - Create directory structure for API (domain, services, models, routes) and frontend
  - Set up Vercel configuration with Python runtime and routing
  - Create Docker Compose for local development (MongoDB, Redis, LavinMQ, OTel Collector)
  - Initialize package.json for frontend and requirements.txt for API
  - Commit changes: `git commit -m "feat: set up project structure and infrastructure"`
  - _Requirements: 18.1, 19.1, 19.2_

- [ ] 1.3 Merge infrastructure setup
  - Create pull request for project structure
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/project-structure`
  - _Requirements: 24.1_

- [ ] 2. Implement core data models and validation
- [ ] 2.1 Create feature branch for data models
  - Create feature branch: `git checkout -b feat/data-models`
  - Pull latest changes from main: `git pull origin main`
  - _Requirements: 24.1_

- [ ] 2.2 Create Pydantic models for all entities
  - Write Organization, User, Role, Permission, Notification, NotificationTarget, NotificationCategory, Endpoint models
  - Include validation rules, field constraints, and schema versioning
  - Add enum classes for NotificationStatus and other constants
  - Commit changes: `git commit -m "feat: add Pydantic models for core entities"`
  - _Requirements: 1.1, 11.1, 21.1_

- [ ] 2.3 Create MongoDB service layer with multi-tenant operations
  - Implement MongoDBService class with org-scoped CRUD operations
  - Add connection pooling, error handling, and soft delete support
  - Create database indexes for performance optimization
  - Commit changes: `git commit -m "feat: implement MongoDB service with multi-tenant support"`
  - _Requirements: 1.2, 11.2, 11.3, 11.4_

- [ ] 2.4 Write unit tests for data models and MongoDB service
  - Test Pydantic model validation and serialization
  - Test MongoDB service operations with test database
  - Test multi-tenant data isolation
  - Commit changes: `git commit -m "test: add unit tests for data models and MongoDB service"`
  - _Requirements: 1.2, 11.1_

- [ ] 2.5 Merge data models implementation
  - Create pull request for data models feature
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/data-models`
  - _Requirements: 24.1_- 
[ ] 3. Implement authentication and authorization system
- [ ] 3.1 Create feature branch for authentication
  - Create feature branch: `git checkout -b feat/authentication`
  - Pull latest changes from main: `git pull origin main`
  - _Requirements: 24.1_

- [ ] 3.2 Create JWT authentication service
  - Implement JWT token generation, validation, and refresh logic
  - Add RS256 signing with public/private key pair
  - Create password hashing utilities with bcrypt
  - Commit changes: `git commit -m "feat: implement JWT authentication service"`
  - _Requirements: 2.1, 2.2, 2.6_

- [ ] 3.3 Implement Redis service for token management
  - Create RedisService class with Upstash HTTP client
  - Add JWT blocklist functionality with TTL
  - Implement user permission caching
  - Commit changes: `git commit -m "feat: add Redis service for token management"`
  - _Requirements: 2.3, 12.1, 12.2, 12.3_

- [ ] 3.4 Create authorization domain logic
  - Implement role-based permission aggregation
  - Add permission checking functions
  - Create user context building from JWT claims
  - Commit changes: `git commit -m "feat: implement authorization domain logic"`
  - _Requirements: 2.4, 2.5, 16.3, 21.1_

- [ ]* 3.5 Write unit tests for authentication and authorization
  - Test JWT token lifecycle (generate, validate, refresh, revoke)
  - Test permission aggregation and checking logic
  - Test Redis token blocklist functionality
  - Commit changes: `git commit -m "test: add unit tests for authentication system"`
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 3.6 Merge authentication implementation
  - Create pull request for authentication feature
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/authentication`
  - _Requirements: 24.1_

- [ ] 4. Create Flask API foundation with OpenAPI
- [ ] 4.1 Create feature branch for API foundation
  - Create feature branch: `git checkout -b feat/api-foundation`
  - Pull latest changes from main: `git pull origin main`
  - _Requirements: 24.1_

- [ ] 4.2 Set up Flask app with flask-openapi3
  - Initialize Flask application with OpenAPI 3.0 configuration
  - Add Pydantic request/response validation
  - Configure CORS and security headers
  - Commit changes: `git commit -m "feat: set up Flask app with OpenAPI 3.0"`
  - _Requirements: 8.1, 8.4, 18.1_

- [ ] 4.3 Implement HAL response formatting middleware
  - Create HAL response builder with _links and _embedded support
  - Add pagination link generation
  - Implement conditional affordance links based on permissions
  - Commit changes: `git commit -m "feat: implement HAL response formatting middleware"`
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 4.4 Add JWT authentication middleware
  - Create Flask middleware for JWT validation
  - Integrate with Redis blocklist checking
  - Add organization context extraction from tokens
  - Commit changes: `git commit -m "feat: add JWT authentication middleware"`
  - _Requirements: 2.1, 2.3, 2.6_

- [ ] 4.5 Write integration tests for API foundation
  - Test OpenAPI spec generation and validation
  - Test HAL response formatting
  - Test JWT middleware with various token scenarios
  - Commit changes: `git commit -m "test: add integration tests for API foundation"`
  - _Requirements: 7.1, 8.1, 2.1_

- [ ] 4.6 Merge API foundation implementation
  - Create pull request for API foundation feature
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/api-foundation`
  - _Requirements: 24.1_- [ ] 5.
 Implement notification workflow endpoints
- [ ] 5.1 Create feature branch for notification workflow
  - Create feature branch: `git checkout -b feat/notification-workflow`
  - Pull latest changes from main: `git pull origin main`
  - _Requirements: 24.1_

- [ ] 5.2 Create notification intake webhook endpoint
  - Implement POST /api/notifications/incoming with JWT protection
  - Add request validation and organization scoping
  - Store notifications with status='received' and preserve originalPayload
  - Commit changes: `git commit -m "feat: implement notification intake webhook endpoint"`
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 5.3 Implement notification listing and detail endpoints
  - Create GET /api/notifications with filtering, pagination, and HAL collection format
  - Add GET /api/notifications/{id} with HAL affordance links
  - Include conditional approve/deny links based on status and permissions
  - Commit changes: `git commit -m "feat: add notification listing and detail endpoints"`
  - _Requirements: 4.1, 4.2, 4.3, 7.3_

- [ ] 5.4 Create notification approval endpoint
  - Implement POST /api/notifications/{id}/approve with target/category validation
  - Add business logic for status transitions and permission checks
  - Integrate with AMQP publishing for dispatch
  - Commit changes: `git commit -m "feat: implement notification approval endpoint"`
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 5.5 Create notification denial endpoint
  - Implement POST /api/notifications/{id}/deny with reason storage
  - Add status transition validation and audit logging
  - Commit changes: `git commit -m "feat: add notification denial endpoint"`
  - _Requirements: 6.1, 6.2, 6.3_

- [ ]* 5.6 Write integration tests for notification endpoints
  - Test complete notification workflow (receive → approve → dispatch)
  - Test notification denial with reason storage
  - Test HAL affordance links and pagination
  - Commit changes: `git commit -m "test: add integration tests for notification workflow"`
  - _Requirements: 3.1, 4.1, 5.1, 6.1_

- [ ] 5.7 Merge notification workflow implementation
  - Create pull request for notification workflow feature
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/notification-workflow`
  - _Requirements: 24.1_

- [ ] 6. Implement AMQP message publishing
- [ ] 6.1 Create feature branch for AMQP integration
  - Create feature branch: `git checkout -b feat/amqp-publishing`
  - Pull latest changes from main: `git pull origin main`
  - _Requirements: 24.1_

- [ ] 6.2 Create AMQP service for LavinMQ integration
  - Implement AMQPService class with pika library
  - Add connection management and error handling
  - Create exchange and queue setup functionality
  - Commit changes: `git commit -m "feat: implement AMQP service for LavinMQ"`
  - _Requirements: 13.1, 13.3_

- [ ] 6.3 Implement payload transformation logic
  - Create data mapping engine using JSONPath transformations
  - Add endpoint-specific payload formatting
  - Include correlation ID and trace context in messages
  - Commit changes: `git commit -m "feat: add payload transformation for AMQP messages"`
  - _Requirements: 13.2, 13.5_

- [ ] 6.4 Integrate AMQP publishing with approval workflow
  - Connect notification approval to message publishing
  - Add retry logic with exponential backoff
  - Handle publishing failures gracefully
  - Commit changes: `git commit -m "feat: integrate AMQP publishing with notification approval"`
  - _Requirements: 5.2, 5.5, 13.4_

- [ ] 6.5 Write integration tests for AMQP publishing
  - Test message publishing with various payload transformations
  - Test retry logic and error handling
  - Test correlation ID and trace context propagation
  - Commit changes: `git commit -m "test: add integration tests for AMQP publishing"`
  - _Requirements: 13.1, 13.2, 13.4_

- [ ] 6.6 Merge AMQP implementation
  - Create pull request for AMQP publishing feature
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/amqp-publishing`
  - _Requirements: 24.1_- 
[ ] 7. Implement audit logging system
- [ ] 7.1 Create feature branch for audit logging
  - Create feature branch: `git checkout -b feat/audit-logging`
  - Pull latest changes from main: `git pull origin main`
  - _Requirements: 24.1_

- [ ] 7.2 Create audit service for action logging
  - Implement AuditService class with MongoDB persistence
  - Add structured audit log entry creation
  - Include OpenTelemetry trace ID correlation
  - Commit changes: `git commit -m "feat: implement audit service for action logging"`
  - _Requirements: 9.1, 9.5_

- [ ] 7.3 Integrate audit logging with all state-changing operations
  - Add audit logging to notification approval/denial
  - Include before/after state capture
  - Add request context (IP, user agent) to audit entries
  - Commit changes: `git commit -m "feat: integrate audit logging with state changes"`
  - _Requirements: 5.4, 6.2, 9.1_

- [ ] 7.4 Create audit log query and export endpoints
  - Implement GET /api/audit-logs with filtering and pagination
  - Add audit log export functionality (CSV/JSON)
  - Include organization scoping and permission checks
  - Commit changes: `git commit -m "feat: add audit log query and export endpoints"`
  - _Requirements: 9.2, 9.3, 9.4_

- [ ]* 7.5 Write integration tests for audit logging
  - Test audit log creation for all tracked actions
  - Test audit log querying with various filters
  - Test audit log export functionality
  - Commit changes: `git commit -m "test: add integration tests for audit logging"`
  - _Requirements: 9.1, 9.2, 9.4_

- [ ] 7.6 Merge audit logging implementation
  - Create pull request for audit logging feature
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/audit-logging`
  - _Requirements: 24.1_

- [ ] 8. Add OpenTelemetry observability
- [ ] 8.1 Create feature branch for observability
  - Create feature branch: `git checkout -b feat/observability`
  - Pull latest changes from main: `git pull origin main`
  - _Requirements: 24.1_

- [ ] 8.2 Set up OpenTelemetry instrumentation
  - Configure OpenTelemetry SDK with auto-instrumentation for Flask
  - Add manual instrumentation for business logic spans
  - Set up trace and metric exporters for development and production
  - Commit changes: `git commit -m "feat: set up OpenTelemetry instrumentation"`
  - _Requirements: 10.1, 10.2, 10.6_

- [ ] 8.3 Add custom spans for business operations
  - Create spans for notification approval/denial with relevant attributes
  - Add spans for AMQP publishing and database operations
  - Include user context and organization ID in span attributes
  - Commit changes: `git commit -m "feat: add custom spans for business operations"`
  - _Requirements: 10.3, 10.4_

- [ ] 8.4 Configure structured logging with trace correlation
  - Set up JSON logging with trace_id and span_id correlation
  - Add log correlation for audit entries
  - Configure log levels and PII scrubbing
  - Commit changes: `git commit -m "feat: configure structured logging with trace correlation"`
  - _Requirements: 9.5, 10.4_

- [ ] 8.5 Write tests for observability instrumentation
  - Test trace generation and span creation
  - Test log correlation with trace IDs
  - Test metric collection and export
  - Commit changes: `git commit -m "test: add tests for observability instrumentation"`
  - _Requirements: 10.1, 10.2, 10.4_

- [ ] 8.6 Merge observability implementation
  - Create pull request for observability feature
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/observability`
  - _Requirements: 24.1_- [ 
] 9. Implement management endpoints for entities
- [ ] 9.1 Create feature branch for entity management
  - Create feature branch: `git checkout -b feat/entity-management`
  - Pull latest changes from main: `git pull origin main`
  - _Requirements: 24.1_

- [ ] 9.2 Create organization management endpoints
  - Implement CRUD operations for organizations
  - Add organization slug validation and uniqueness
  - Include soft delete functionality
  - Commit changes: `git commit -m "feat: implement organization management endpoints"`
  - _Requirements: 1.1, 1.3_

- [ ] 9.3 Create user and role management endpoints
  - Implement user CRUD with role assignment
  - Add role and permission management endpoints
  - Include password change and user activation functionality
  - Commit changes: `git commit -m "feat: add user and role management endpoints"`
  - _Requirements: 2.5, 16.1, 16.2_

- [ ] 9.4 Create notification target and category management
  - Implement hierarchical target management with parent/child relationships
  - Add category management with target associations
  - Include endpoint configuration with data mapping
  - Commit changes: `git commit -m "feat: implement target and category management"`
  - _Requirements: 14.1, 14.2, 15.1, 15.2_

- [ ]* 9.5 Write integration tests for management endpoints
  - Test CRUD operations for all entity types
  - Test hierarchical target relationships
  - Test role and permission assignment
  - Commit changes: `git commit -m "test: add integration tests for entity management"`
  - _Requirements: 1.1, 14.1, 16.1_

- [ ] 9.6 Merge entity management implementation
  - Create pull request for entity management feature
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/entity-management`
  - _Requirements: 24.1_

- [ ] 10. Create health check and system status endpoints
- [ ] 10.1 Create feature branch for health checks
  - Create feature branch: `git checkout -b feat/health-checks`
  - Pull latest changes from main: `git pull origin main`
  - _Requirements: 24.1_

- [ ] 10.2 Implement health check endpoint
  - Create GET /api/healthz with HAL response format
  - Add dependency health checks (MongoDB, Redis, LavinMQ)
  - Include system version and environment information
  - Commit changes: `git commit -m "feat: implement health check endpoint"`
  - _Requirements: 23.1, 23.2, 23.4_

- [ ] 10.3 Add system status and metrics endpoints
  - Implement basic system metrics collection
  - Add endpoint for system configuration status
  - Include feature flag status reporting
  - Commit changes: `git commit -m "feat: add system status and metrics endpoints"`
  - _Requirements: 23.4, 25.2, 25.3, 25.4_

- [ ] 10.4 Write integration tests for health and status endpoints
  - Test health check with various dependency states
  - Test system status reporting
  - Test feature flag configuration
  - Commit changes: `git commit -m "test: add tests for health and status endpoints"`
  - _Requirements: 23.1, 23.3_

- [ ] 10.5 Merge health check implementation
  - Create pull request for health check feature
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/health-checks`
  - _Requirements: 24.1_- [ ] 11.
 Build Vue 3 frontend with Vuetify 3
- [ ] 11.1 Create feature branch for frontend setup
  - Create feature branch: `git checkout -b feat/frontend-setup`
  - Pull latest changes from main: `git pull origin main`
  - _Requirements: 24.1_

- [ ] 11.2 Set up Vue 3 project with Vuetify 3
  - Initialize Vue 3 project with Vite build tool
  - Configure Vuetify 3 with Material Design 3 theming
  - Set up Vue Router for client-side routing
  - Configure Pinia for state management
  - Commit changes: `git commit -m "feat: set up Vue 3 project with Vuetify 3"`
  - _Requirements: 17.1, 17.2, 17.3_

- [ ] 11.3 Create authentication components and stores
  - Implement login/logout components with JWT handling
  - Create Pinia store for authentication state
  - Add token refresh logic and automatic logout on expiration
  - Commit changes: `git commit -m "feat: implement authentication components and stores"`
  - _Requirements: 2.1, 2.2, 17.3_

- [ ] 11.4 Merge frontend setup
  - Create pull request for frontend setup
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/frontend-setup`
  - _Requirements: 24.1_

- [ ] 11.5 Create feature branch for notification interface
  - Create feature branch: `git checkout -b feat/notification-interface`
  - Pull latest changes from main: `git pull origin main`
  - _Requirements: 24.1_

- [ ] 11.6 Build notification management interface
  - Create notification list component with data table, filtering, and pagination
  - Implement notification detail view with approve/deny actions
  - Add HAL-aware action buttons based on available affordances
  - Commit changes: `git commit -m "feat: build notification management interface"`
  - _Requirements: 4.1, 4.2, 7.4, 17.4, 17.5_

- [ ] 11.7 Create admin interface for entity management
  - Build organization, user, and role management screens
  - Implement target hierarchy management with tree view
  - Add category and endpoint configuration interfaces
  - Commit changes: `git commit -m "feat: create admin interface for entity management"`
  - _Requirements: 1.1, 16.1, 14.1, 15.1_

- [ ] 11.8 Implement audit log viewer
  - Create audit log list with advanced filtering
  - Add audit log export functionality
  - Include trace ID linking for observability correlation
  - Commit changes: `git commit -m "feat: implement audit log viewer"`
  - _Requirements: 9.2, 9.3, 9.4_

- [ ]* 11.9 Write frontend unit tests
  - Test Vue components with Vue Test Utils
  - Test Pinia store actions and mutations
  - Test HAL response handling and action rendering
  - Commit changes: `git commit -m "test: add frontend unit tests"`
  - _Requirements: 17.1, 17.5_

- [ ] 11.10 Merge notification interface implementation
  - Create pull request for notification interface feature
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/notification-interface`
  - _Requirements: 24.1_

- [ ] 12. Configure CI/CD pipeline
- [ ] 12.1 Create feature branch for CI/CD setup
  - Create feature branch: `git checkout -b feat/cicd-pipeline`
  - Pull latest changes from main: `git pull origin main`
  - _Requirements: 24.1_

- [ ] 12.2 Set up GitHub Actions workflows
  - Create workflow for OpenAPI validation using Redocly CLI
  - Add Codium PR-Agent for AI-powered code review
  - Configure Gitleaks for secrets scanning
  - Set up Dependabot for dependency updates
  - Commit changes: `git commit -m "feat: set up GitHub Actions workflows"`
  - _Requirements: 20.1, 20.2, 20.3, 20.4_

- [ ] 12.3 Add automated testing in CI
  - Configure pytest for backend tests with coverage reporting
  - Add Vitest for frontend unit tests
  - Include integration tests with test database
  - Commit changes: `git commit -m "feat: add automated testing in CI pipeline"`
  - _Requirements: 20.5_

- [ ] 12.4 Configure deployment to Vercel
  - Set up Vercel deployment from GitHub
  - Configure environment variables and secrets
  - Add preview deployments for pull requests
  - Commit changes: `git commit -m "feat: configure Vercel deployment"`
  - _Requirements: 18.1, 18.4, 20.5_

- [ ] 12.5 Write deployment and CI tests
  - Test Vercel deployment configuration
  - Test environment variable handling
  - Test CI pipeline execution
  - Commit changes: `git commit -m "test: add deployment and CI tests"`
  - _Requirements: 18.1, 20.1_

- [ ] 12.6 Merge CI/CD implementation
  - Create pull request for CI/CD pipeline feature
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/cicd-pipeline`
  - _Requirements: 24.1_- [ ] 
13. Add project documentation and licensing
- [ ] 13.1 Create feature branch for documentation
  - Create feature branch: `git checkout -b feat/documentation`
  - Pull latest changes from main: `git pull origin main`
  - _Requirements: 24.1_

- [ ] 13.2 Create project documentation
  - Write comprehensive README with setup instructions
  - Add API documentation with OpenAPI spec
  - Create CONTRIBUTING.md and CODE_OF_CONDUCT.md
  - Commit changes: `git commit -m "docs: add comprehensive project documentation"`
  - _Requirements: 22.3, 22.4_

- [ ] 13.3 Configure Apache 2.0 licensing
  - Add LICENSE file with Apache 2.0 text
  - Include SPDX license identifiers in source files
  - Verify third-party dependency license compatibility
  - Commit changes: `git commit -m "feat: configure Apache 2.0 licensing"`
  - _Requirements: 22.1, 22.2, 22.5_

- [ ] 13.4 Set up conventional commits and changelog
  - Configure conventional commit validation
  - Set up automated changelog generation
  - Add release tagging and OpenAPI artifact storage
  - Commit changes: `git commit -m "feat: set up conventional commits and changelog"`
  - _Requirements: 24.1, 24.2, 24.3, 24.4_

- [ ]* 13.5 Write documentation tests
  - Test README instructions with fresh environment
  - Validate OpenAPI spec completeness
  - Test contribution workflow
  - Commit changes: `git commit -m "test: add documentation validation tests"`
  - _Requirements: 22.3, 8.1_

- [ ] 13.6 Merge documentation implementation
  - Create pull request for documentation feature
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/documentation`
  - _Requirements: 24.1_

- [ ] 14. Final integration and deployment testing
- [ ] 14.1 Create feature branch for integration testing
  - Create feature branch: `git checkout -b feat/integration-testing`
  - Pull latest changes from main: `git pull origin main`
  - _Requirements: 24.1_

- [ ] 14.2 Perform end-to-end testing
  - Test complete notification workflow from webhook to dispatch
  - Verify multi-tenant data isolation
  - Test authentication and authorization flows
  - Commit changes: `git commit -m "test: add end-to-end integration tests"`
  - _Requirements: 3.1, 4.1, 5.1, 1.2_

- [ ] 14.3 Validate production deployment
  - Deploy to Vercel production environment
  - Test with real MongoDB Atlas and Upstash Redis
  - Verify CloudAMQP LavinMQ integration
  - Commit changes: `git commit -m "feat: validate production deployment configuration"`
  - _Requirements: 18.1, 11.2, 12.1, 13.1_

- [ ] 14.4 Perform security and performance testing
  - Run security scans and penetration testing
  - Test API rate limiting and error handling
  - Validate OpenTelemetry observability in production
  - Commit changes: `git commit -m "test: add security and performance validation"`
  - _Requirements: 10.1, 12.4_

- [ ] 14.5 Write acceptance tests
  - Create automated acceptance tests for all major workflows
  - Test HAL API discoverability
  - Validate audit trail completeness
  - Commit changes: `git commit -m "test: add comprehensive acceptance tests"`
  - _Requirements: 7.1, 9.1, 23.1_

- [ ] 14.6 Merge integration testing and finalize
  - Create pull request for integration testing
  - Review and merge to main branch
  - Delete feature branch: `git branch -d feat/integration-testing`
  - Tag release: `git tag -a v1.0.0 -m "Release v1.0.0: S.O.S Cidadão MVP"`
  - Push release: `git push origin v1.0.0`
  - _Requirements: 24.1, 24.3_