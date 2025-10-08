# Contributing to S.O.S Cidadão

Thank you for your interest in contributing to S.O.S Cidadão! This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## 📜 Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Git

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/sos-cidadao.git
   cd sos-cidadao
   ```

2. **Set up local development environment**
   ```bash
   # Start infrastructure services
   docker-compose up -d
   
   # Install backend dependencies
   cd api
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   
   # Install frontend dependencies
   cd ../frontend
   npm install
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

4. **Run the application**
   ```bash
   # Terminal 1: Backend
   cd api && flask run --debug
   
   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```

## 🔄 Development Workflow

### Branching Strategy

We follow a trunk-based development model:

- `main` - Production-ready code (protected)
- Feature branches - Short-lived branches for development

### Branch Naming Convention

```
feat/feature-name          # New features
fix/bug-description        # Bug fixes
docs/documentation-update  # Documentation changes
refactor/code-improvement  # Code refactoring
test/test-improvements     # Test additions/improvements
chore/maintenance-task     # Maintenance tasks
```

### Commit Message Format

We use [Conventional Commits](https://conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(notifications): add notification approval endpoint
fix(auth): resolve JWT token validation issue
docs(api): update OpenAPI specification
test(notifications): add integration tests for workflow
```

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes**
   - Follow coding standards (see below)
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   # Backend tests
   cd api && pytest --cov=. --cov-report=html
   
   # Frontend tests
   cd frontend && npm run test
   
   # Integration tests
   docker-compose -f docker-compose.test.yml up --abort-on-container-exit
   ```

4. **Commit and push**
   ```bash
   git add .
   git commit -m "feat(scope): description of changes"
   git push origin feat/your-feature-name
   ```

5. **Create a Pull Request**
   - Use the provided PR template
   - Ensure all CI checks pass
   - Request review from maintainers

## 🎯 Coding Standards

### Backend (Python)

**Architecture Patterns:**
- **Functional Programming**: Pure functions for domain logic
- **Dependency Injection**: Services injected into domain functions
- **Multi-tenant by Design**: All operations scoped to organizations
- **Result Pattern**: Use Result types for error handling

**Code Style:**
```python
# Use Black for formatting
black api/

# Use flake8 for linting
flake8 api/

# Use mypy for type checking
mypy api/
```

**Example Domain Function:**
```python
def approve_notification(
    notification: Notification,
    user_context: UserContext,
    mongo_svc: MongoDBService,
    audit_svc: AuditService
) -> Result[Notification, Error]:
    """Pure function with injected dependencies."""
    # Validation logic
    if notification.status != NotificationStatus.RECEIVED:
        return Result(error=ValidationError("Cannot approve non-received notification"))
    
    # Business logic
    approved_notification = notification.copy(update={
        "status": NotificationStatus.APPROVED,
        "updated_at": datetime.utcnow(),
        "updated_by": user_context.user_id
    })
    
    return Result(value=approved_notification)
```

**HAL Response Format:**
```python
def build_notification_hal_response(notification: Notification, user_context: UserContext) -> Dict:
    response = {
        "id": notification.id,
        "title": notification.title,
        "status": notification.status,
        "_links": {
            "self": {"href": f"/api/notifications/{notification.id}"}
        }
    }
    
    # Conditional affordance links
    if notification.status == "received" and "notification:approve" in user_context.permissions:
        response["_links"]["approve"] = {
            "href": f"/api/notifications/{notification.id}/approve",
            "method": "POST"
        }
    
    return response
```

### Frontend (Vue 3 + TypeScript)

**Architecture Patterns:**
- **Composition API Only**: No Options API
- **TypeScript Strict Mode**: All components fully typed
- **HAL-Aware**: Process HAL responses for dynamic UI

**Code Style:**
```bash
# Use Prettier for formatting
npm run format

# Use ESLint for linting
npm run lint

# Use Vue TSC for type checking
npm run type-check
```

**Example Component:**
```vue
<template>
  <div>
    <NotificationCard
      v-for="notification in notifications"
      :key="notification.id"
      :notification="notification"
      :available-actions="getAvailableActions(notification)"
      @approve="handleApprove"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Notification } from '@/types'
import { useNotificationStore } from '@/stores/notifications'

interface Props {
  organizationId: string
}

const props = defineProps<Props>()
const notificationStore = useNotificationStore()

const notifications = computed(() => notificationStore.notifications)

const getAvailableActions = (notification: Notification): string[] => {
  return extractActionsFromHalLinks(notification._links)
}

const handleApprove = async (notification: Notification, targets: string[]) => {
  await notificationStore.approveNotification(notification.id, targets)
}
</script>
```

### Database Patterns

**Multi-tenant Scoping:**
```python
# Always include organization scoping
def find_notifications(org_id: str, filters: Dict = None) -> List[Dict]:
    query = {"organizationId": org_id, "deletedAt": None}
    if filters:
        query.update(filters)
    return db.notifications.find(query)
```

**Schema Versioning:**
```python
class BaseEntity(BaseModel):
    schema_version: int = Field(default=1)  # MANDATORY
    organization_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None
```

## 🧪 Testing Guidelines

### Test Structure

```
api/tests/
├── unit/           # Pure function tests
├── integration/    # Service integration tests
└── e2e/           # End-to-end workflow tests

frontend/tests/
├── unit/          # Component unit tests
├── integration/   # Store and service tests
└── e2e/          # Playwright end-to-end tests
```

### Backend Testing

**Pure Function Tests:**
```python
def test_notification_approval_logic():
    notification = Notification(id="123", status="received")
    user_context = UserContext(user_id="user1", org_id="org1", permissions=["notification:approve"])
    
    result = domain.notifications.approve_notification(notification, user_context)
    
    assert result.is_success()
    assert result.value.status == "approved"
```

**Integration Tests:**
```python
@pytest.mark.integration
def test_notification_approval_endpoint(client, auth_headers):
    response = client.post(
        "/api/notifications/123/approve",
        json={"targets": ["target1"]},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
```

### Frontend Testing

**Component Tests:**
```typescript
import { mount } from '@vue/test-utils'
import NotificationCard from '@/components/NotificationCard.vue'

describe('NotificationCard', () => {
  it('renders notification details correctly', () => {
    const notification = {
      id: '123',
      title: 'Test Notification',
      status: 'received'
    }
    
    const wrapper = mount(NotificationCard, {
      props: { notification }
    })
    
    expect(wrapper.text()).toContain('Test Notification')
  })
})
```

### Test Coverage Requirements

- **Minimum 80% code coverage** for all new code
- **100% coverage** for domain logic (pure functions)
- **Integration tests** for all API endpoints
- **E2E tests** for critical user workflows

## 📚 Documentation

### API Documentation

- **OpenAPI 3.0 specification** in `api/specs/`
- **HAL examples** for all responses
- **Error response formats** following RFC 7807

### Code Documentation

- **Docstrings** for all public functions
- **Type hints** for all function parameters and returns
- **Inline comments** for complex business logic

### Architecture Decision Records (ADRs)

Document significant architectural decisions in `docs/ADRs/`:

```markdown
# ADR-001: Use HAL for API Hypermedia

## Status
Accepted

## Context
We need a standard format for hypermedia APIs that supports discoverability.

## Decision
Use HAL (Hypertext Application Language) for all API responses.

## Consequences
- Improved API discoverability
- Dynamic UI based on available actions
- Consistent link format across all endpoints
```

## 🔄 Pull Request Process

### PR Requirements

1. **Branch is up-to-date** with main
2. **All CI checks pass**
3. **Code coverage** meets minimum requirements
4. **Documentation updated** if needed
5. **At least one approval** from maintainers

### PR Template

Use the provided template that includes:

- **Description** of changes
- **Type of change** (feature, fix, docs, etc.)
- **Testing** performed
- **Breaking changes** (if any)
- **Documentation** updates

### Review Process

1. **Automated checks** run first
2. **Manual review** by maintainers
3. **Address feedback** and update PR
4. **Final approval** and merge

### Merge Strategy

- **Squash and merge** for feature branches
- **Conventional commit format** for merge commit
- **Delete branch** after merge

## 🚀 Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Workflow

1. **Create release branch** from main
2. **Update version** in relevant files
3. **Generate changelog** from conventional commits
4. **Create release PR** and merge
5. **Tag release** on main branch
6. **Deploy to production**

### Changelog Generation

Automated changelog generation from conventional commits:

```bash
npx conventional-changelog -p angular -i CHANGELOG.md -s
```

## 🛡️ Security

### Security Guidelines

- **Never commit secrets** or credentials
- **Use environment variables** for configuration
- **Validate all inputs** with Pydantic models
- **Implement proper authentication** and authorization
- **Follow OWASP guidelines** for web security

### Reporting Security Issues

Please report security vulnerabilities privately to the maintainers. Do not create public issues for security problems.

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Documentation**: Check the `docs/` directory
- **Code Examples**: Look at existing implementations

## 🙏 Recognition

Contributors will be recognized in:

- **CONTRIBUTORS.md** file
- **Release notes** for significant contributions
- **GitHub contributors** page

Thank you for contributing to S.O.S Cidadão! 🎉