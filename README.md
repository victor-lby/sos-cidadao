# S.O.S Cidadão

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Vue](https://img.shields.io/badge/vue-3.3+-green.svg)](https://vuejs.org/)
[![Vercel](https://img.shields.io/badge/deploy-vercel-black.svg)](https://vercel.com)

S.O.S Cidadão is a public, open-source civic notification system designed for multi-tenant municipal operations. The platform enables municipal teams to receive, moderate, and broadcast critical public alerts through an auditable workflow.

## 🚀 Features

- **Multi-tenant Architecture**: Each municipality operates independently with isolated data and users
- **Notification Workflow**: Receive → Review → Approve/Deny → Dispatch pipeline
- **Audit Trail**: Complete audit logging of all user actions for compliance and accountability
- **Role-Based Access**: Granular permissions system scoped to organizations
- **API-First Design**: HATEOAS Level-3 APIs using HAL for maximum discoverability
- **Observability**: Full OpenTelemetry instrumentation for monitoring and troubleshooting

## 🏗️ Architecture

### Technology Stack

**Backend:**
- Python 3.11+ with Flask framework
- flask-openapi3 for OpenAPI 3.0 + Pydantic validation
- PyJWT for authentication
- pymongo for MongoDB Atlas integration
- Upstash Redis for caching and JWT token management
- CloudAMQP LavinMQ for AMQP message queuing
- OpenTelemetry for observability

**Frontend:**
- Vue 3 with Composition API
- Vuetify 3 (Material Design 3)
- Vue Router for client-side routing
- Pinia for state management
- TypeScript for type safety

**Infrastructure:**
- Vercel for serverless deployment
- Docker Compose for local development
- GitHub Actions for CI/CD

### Project Structure

```
/
├── api/                     # Python Flask API
│   ├── domain/             # Pure business logic functions
│   ├── services/           # External service integrations
│   ├── models/             # Pydantic data models
│   ├── routes/             # HTTP endpoint handlers
│   ├── observability/      # OpenTelemetry configuration
│   └── requirements.txt
├── frontend/               # Vue 3 + Vuetify 3 SPA
│   ├── src/
│   │   ├── components/     # Reusable Vue components
│   │   ├── views/         # Page-level components
│   │   ├── stores/        # Pinia state management
│   │   └── services/      # API client and utilities
│   └── package.json
├── infra/                 # Infrastructure configuration
│   ├── docker/           # Docker configurations
│   └── collector/        # OpenTelemetry Collector config
├── .github/workflows/    # CI/CD pipelines
├── docker-compose.yml    # Local development environment
└── vercel.json          # Vercel deployment configuration
```

## 🛠️ Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Git

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sos-cidadao
   ```

2. **Start local infrastructure**
   ```bash
   docker-compose up -d
   ```

3. **Set up backend**
   ```bash
   cd api
   pip install -r requirements.txt
   export FLASK_ENV=development
   export FLASK_DEBUG=1
   flask run
   ```

4. **Set up frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - API: http://localhost:5000
   - API Documentation: http://localhost:5000/docs (development only)
   - Jaeger UI: http://localhost:16686
   - LavinMQ Management: http://localhost:15672
   - OpenTelemetry Collector: http://localhost:4317

### Environment Variables

Create a `.env` file in the root directory:

```env
# Environment
ENVIRONMENT=development

# Database
MONGODB_URI=mongodb://localhost:27017/sos_cidadao_dev

# Redis
REDIS_URL=redis://localhost:6379
REDIS_TOKEN=

# JWT
JWT_SECRET=your-secret-key
JWT_PUBLIC_KEY=your-public-key

# Message Queue
AMQP_URL=amqp://admin:admin123@localhost:5672/

# OpenTelemetry
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Feature Flags
DOCS_ENABLED=true
HAL_STRICT=false
```

## 🧪 Testing

### Backend Tests
```bash
cd api
pytest --cov=. --cov-report=html
```

### Frontend Tests
```bash
cd frontend
npm run test
```

### Integration Tests
```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 🚀 Deployment

### Vercel (Recommended)

1. **Connect your repository to Vercel**
2. **Configure environment variables** in Vercel dashboard
3. **Deploy automatically** on push to main branch

### Manual Deployment

```bash
# Build frontend
cd frontend && npm run build

# Deploy to Vercel
vercel --prod
```

## 📚 API Documentation

The API follows HATEOAS Level-3 principles using HAL (Hypertext Application Language). Interactive documentation is available at `/docs` in development mode.

### Key Endpoints

- `GET /api/healthz` - Health check
- `POST /api/auth/login` - User authentication
- `GET /api/notifications` - List notifications
- `POST /api/notifications/{id}/approve` - Approve notification
- `POST /api/notifications/{id}/deny` - Deny notification

## 🔒 Security

- JWT-based authentication with RS256 signing
- Role-based access control (RBAC)
- Organization-scoped data isolation
- Comprehensive audit logging
- Secrets scanning with Gitleaks
- Dependency vulnerability scanning

## 📊 Observability

The platform includes comprehensive observability:

- **Distributed Tracing**: OpenTelemetry with Jaeger
- **Structured Logging**: JSON logs with trace correlation
- **Metrics**: Prometheus-compatible metrics
- **Health Checks**: Kubernetes-ready health endpoints

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/amazing-feature`
3. Make your changes following our coding standards
4. Add tests for your changes
5. Commit using conventional commits: `git commit -m "feat: add amazing feature"`
6. Push to your fork: `git push origin feat/amazing-feature`
7. Create a Pull Request

### Code Standards

- **Python**: Black formatting, flake8 linting, type hints
- **TypeScript**: Prettier formatting, ESLint rules
- **Commits**: Conventional Commits format
- **Testing**: Minimum 80% code coverage

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/sos-cidadao/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/sos-cidadao/discussions)

## 🙏 Acknowledgments

- Built with ❤️ for civic engagement and transparency
- Inspired by open government and digital democracy initiatives
- Thanks to all contributors and the open-source community

---

**S.O.S Cidadão** - Empowering municipalities with transparent, auditable civic notifications.