# Product Overview

## S.O.S Cidadão - Civic Notification Platform

S.O.S Cidadão is a public, open-source civic notification system designed for multi-tenant municipal operations. The platform enables municipal teams to receive, moderate, and broadcast critical public alerts through an auditable workflow.

### Core Mission
Build a trustworthy system for municipal teams to receive, moderate, and dispatch critical public alerts with full auditability, strong privacy/security practices, and developer-friendly governance.

### Key Features
- **Multi-tenant Architecture**: Each municipality operates independently with isolated data and users
- **Notification Workflow**: Receive → Review → Approve/Deny → Dispatch pipeline
- **Audit Trail**: Complete audit logging of all user actions for compliance and accountability
- **Role-Based Access**: Granular permissions system scoped to organizations
- **API-First Design**: HATEOAS Level-3 APIs using HAL for maximum discoverability
- **Observability**: Full OpenTelemetry instrumentation for monitoring and troubleshooting

### Target Users
- **Municipal Operators/Admins**: Staff who approve/deny notifications and manage system configuration
- **View-only Users**: Personnel who browse notifications without moderation rights
- **System Integrators**: Developers using the HAL+OpenAPI APIs for external integrations

### Success Criteria
- Deploys seamlessly on Vercel with working Vue app and Python API
- Functional-style Python with pure domain logic and side effects at boundaries
- JWT authentication with access/refresh tokens and Redis-based revocation
- Complete audit trail with admin UI for filtering and export
- HATEOAS Level-3 APIs using HAL format with dynamic affordance links
- OpenAPI 3.0 specification with interactive docs (development only)

### Non-Goals
- No SMS/email gateway implementation (only queue hand-off to external systems)
- No custom mobile applications
- No vendor-specific monitoring lock-in (OpenTelemetry only)