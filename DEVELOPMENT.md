# S.O.S Cidadão - Development Guide

## 🚀 Quick Start

### Complete Docker Environment (Recommended)

Start everything with one command:

```bash
./scripts/dev-start.sh
```

This will:
- Build and start all services (MongoDB, Redis, RabbitMQ, Jaeger, API, Frontend)
- Set up hot reloading for both backend and frontend
- Configure all services to work together

**Access Points:**
- 🌐 **Frontend**: http://localhost:3000
- 🔧 **Backend API**: http://localhost:5000
- 📚 **API Docs**: http://localhost:5000/openapi/swagger
- 🐰 **RabbitMQ**: http://localhost:15672 (admin/admin123)
- 🔍 **Jaeger**: http://localhost:16686

### Stop Everything

```bash
./scripts/dev-stop.sh
```

## 🔧 Development Workflow

### Hot Reloading

Both backend and frontend support hot reloading:

- **Backend**: Changes to Python files automatically restart the Flask server
- **Frontend**: Changes to Vue files trigger Vite's HMR (Hot Module Replacement)

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f frontend
docker compose logs -f mongodb
```

### Debugging

#### Backend Debugging
```bash
# Access the API container
docker compose exec api bash

# Run tests inside container
docker compose exec api pytest

# Check API health
curl http://localhost:5000/api/healthz
```

#### Frontend Debugging
```bash
# Access the frontend container
docker compose exec frontend sh

# Run tests inside container
docker compose exec frontend npm test

# Check frontend
curl http://localhost:3000
```

### Database Access

```bash
# MongoDB shell
docker compose exec mongodb mongosh sos_cidadao_dev

# Redis CLI
docker compose exec redis redis-cli
```

## 🛠️ Alternative Development Modes

### Hybrid Mode (Infrastructure in Docker, Apps Local)

1. Start only infrastructure:
```bash
docker compose up -d mongodb redis rabbitmq jaeger
```

2. Run backend locally:
```bash
cd api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

3. Run frontend locally:
```bash
cd frontend
npm install
npm run dev
```

### Individual Service Development

Start specific services:
```bash
# Just infrastructure
docker compose up -d mongodb redis rabbitmq jaeger

# Add backend
docker compose up -d api

# Add frontend
docker compose up -d frontend
```

## 📁 File Structure for Development

```
/
├── api/
│   ├── Dockerfile              # Backend container config
│   ├── .dockerignore          # Files to exclude from build
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── Dockerfile             # Frontend container config
│   ├── .dockerignore         # Files to exclude from build
│   └── package.json          # Node.js dependencies
├── scripts/
│   ├── dev-start.sh          # Start development environment
│   ├── dev-stop.sh           # Stop development environment
│   └── test-setup.sh         # Validate setup
├── docker-compose.yml        # Main service definitions
├── docker-compose.override.yml # Development overrides
├── .env                      # Local development config
└── .env.development         # Docker development config
```

## 🔄 Environment Variables

### Local Development (.env)
Used when running services directly on your machine.

### Docker Development (.env.development)
Used when running everything in Docker containers.

Key differences:
- **Local**: `MONGODB_URI=mongodb://localhost:27017/sos_cidadao_dev`
- **Docker**: `MONGODB_URI=mongodb://mongodb:27017/sos_cidadao_dev`

## 🧪 Testing

### Run All Tests
```bash
# Backend tests
docker compose exec api pytest

# Frontend tests
docker compose exec frontend npm test

# Integration tests (requires all services)
docker compose exec api pytest tests/integration/
```

### Test Individual Components
```bash
# Test API health
curl http://localhost:5000/api/healthz

# Test frontend
curl http://localhost:3000

# Test database connection
docker compose exec api python -c "from services.mongodb import MongoDBService; print('MongoDB OK')"
```

## 🚨 Troubleshooting

### Services Won't Start
```bash
# Check service status
docker compose ps

# View logs for failed service
docker compose logs [service-name]

# Restart specific service
docker compose restart [service-name]
```

### Port Conflicts
If ports are already in use, you can modify them in `docker-compose.yml`:
```yaml
ports:
  - "3001:3000"  # Change frontend to port 3001
  - "5001:5000"  # Change backend to port 5001
```

### Database Issues
```bash
# Reset database
docker compose down -v
docker compose up -d

# Check MongoDB logs
docker compose logs mongodb
```

### Performance Issues
```bash
# Check resource usage
docker stats

# Limit container resources in docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
```

## 📊 Monitoring

### Health Checks
All services include health checks. View status:
```bash
docker compose ps
```

### Observability
- **Traces**: http://localhost:16686 (Jaeger)
- **API Metrics**: http://localhost:5000/api/status
- **Logs**: `docker compose logs -f`

### Performance Monitoring
```bash
# Container resource usage
docker stats

# Service response times
curl -w "@curl-format.txt" http://localhost:5000/api/healthz
```

## 🔐 Security Notes

- Default credentials are for development only
- All services run with non-root users in containers
- Sensitive data should use environment variables
- Production deployment uses different configurations

## 🤝 Contributing

1. Make changes to code
2. Test locally with `./scripts/dev-start.sh`
3. Run tests: `docker compose exec api pytest`
4. Submit pull request

The development environment automatically reloads on code changes, making the development cycle fast and efficient!