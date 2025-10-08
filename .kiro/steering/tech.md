# Technology Stack & Build System

## ⚠️ CRITICAL PROJECT RULE

**NO BACKWARD COMPATIBILITY NEEDED - THIS IS A NEW BOOTSTRAP PROJECT**

This is a greenfield project starting from scratch. There are no existing systems, APIs, or data formats to maintain compatibility with. This means:

- **Break things freely** during development - no legacy constraints
- **Use latest versions** of all dependencies and frameworks
- **Design optimal APIs** without worrying about existing integrations
- **Implement best practices** without legacy code limitations
- **Refactor aggressively** when better patterns emerge
- **Change database schemas** as needed during development
- **Evolve API contracts** based on requirements without versioning concerns

Focus on building the best possible system architecture without the burden of maintaining compatibility with non-existent legacy systems.

## Core Technologies

### Backend
- **Python 3.11+** with Flask framework
- **flask-openapi3** for OpenAPI 3.0 + Pydantic validation
- **PyJWT / Flask-JWT-Extended** for authentication
- **pymongo** for MongoDB Atlas integration
- **upstash-redis** (HTTP client) for serverless-friendly caching
- **pika** for AMQP (LavinMQ) message publishing
- **opentelemetry-api** with auto-instrumentation

### Frontend
- **Vue 3** with Composition API
- **Vuetify 3** (Material Design 3) for UI components
- **Vue Router** for client-side routing
- **Pinia** for state management
- **Axios** for HTTP with HAL response handling

### Infrastructure & Deployment
- **Vercel** for serverless deployment (default)
- **MongoDB Atlas** for persistent storage
- **Upstash Redis** for caching and JWT token management
- **CloudAMQP LavinMQ** for AMQP message queuing
- **Docker Compose** for local development environment

## Architecture Patterns

### Functional Programming (Backend)
- **Pure functions** for all domain logic
- **Side effects isolated** to service layer boundaries
- **Dependency injection** for testability
- **Result/Either patterns** for error handling

### API Design
- **HATEOAS Level-3** using HAL (Hypertext Application Language)
- **OpenAPI 3.0** specification with Pydantic validation
- **Multi-tenant by design** with organization scoping
- **Content-Type: application/hal+json** for all responses

### Security & Observability
- **JWT with RS256** signing and Redis-based revocation
- **Role-based permissions** scoped to organizations
- **OpenTelemetry** instrumentation throughout
- **Structured audit logging** with trace correlation

## Common Commands

### Local Development Setup
```bash
# Start local infrastructure
docker-compose up -d

# Install backend dependencies
cd api && pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install

# Run backend (development)
cd api && flask run --debug

# Run frontend (development)
cd frontend && npm run dev
```

### Testing
```bash
# Run backend tests
cd api && pytest --cov=. --cov-report=html

# Run frontend tests
cd frontend && npm run test

# Run integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Deployment
```bash
# Deploy to Vercel (automatic on main branch push)
vercel --prod

# Validate OpenAPI spec
npx @redocly/cli lint api/specs/openapi.yaml

# Build frontend for production
cd frontend && npm run build
```

### Database Operations
```bash
# Connect to local MongoDB
mongosh mongodb://localhost:27017/sos_cidadao_dev

# Create database indexes
cd api && python scripts/create_indexes.py

# Run database migrations
cd api && python scripts/migrate_schema.py
```

## Environment Configuration

### Required Environment Variables
- `ENVIRONMENT`: dev|staging|production
- `MONGODB_URI`: MongoDB Atlas connection string
- `REDIS_URL`: Upstash Redis HTTP URL
- `REDIS_TOKEN`: Upstash Redis authentication token
- `JWT_SECRET`: RS256 private key for token signing
- `JWT_PUBLIC_KEY`: RS256 public key for token verification
- `AMQP_URL`: CloudAMQP LavinMQ connection string
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OpenTelemetry collector endpoint

### Feature Flags
- `DOCS_ENABLED`: Enable/disable interactive API documentation
- `OTEL_ENABLED`: Enable/disable OpenTelemetry instrumentation
- `HAL_STRICT`: Enable strict HAL specification validation

## Code Quality & CI/CD

### Automated Checks
- **OpenAPI validation** with Redocly CLI
- **AI code review** with Codium PR-Agent
- **Secrets scanning** with Gitleaks
- **Dependency updates** with Dependabot
- **Conventional commits** validation

### Code Standards
- **Python**: Black formatting, flake8 linting, type hints
- **JavaScript**: Prettier formatting, ESLint rules
- **Commits**: Conventional Commits format (feat:, fix:, docs:)
- **Testing**: Minimum 80% code coverage requirement