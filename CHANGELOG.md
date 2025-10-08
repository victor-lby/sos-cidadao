# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup with Flask backend and Vue 3 frontend
- Multi-tenant architecture with organization scoping
- JWT authentication with role-based permissions
- HATEOAS Level-3 APIs using HAL format
- OpenTelemetry observability integration
- Comprehensive audit logging system
- Notification workflow (receive → approve/deny → dispatch)
- AMQP message publishing with LavinMQ
- MongoDB Atlas integration with schema versioning
- Redis caching and JWT token management
- Vercel serverless deployment configuration
- Docker Compose local development environment
- GitHub Actions CI/CD pipeline
- Comprehensive documentation and API specification
- Apache 2.0 licensing compliance

### Changed
- N/A (initial release)

### Deprecated
- N/A (initial release)

### Removed
- N/A (initial release)

### Fixed
- N/A (initial release)

### Security
- JWT token validation and revocation system
- Organization-scoped data isolation
- Comprehensive audit trail for all actions
- Secrets scanning with Gitleaks
- Dependency vulnerability scanning

## [1.0.0] - TBD

### Added
- Complete S.O.S Cidadão MVP implementation
- Multi-tenant civic notification platform
- Full observability and monitoring
- Production-ready deployment configuration

---

## Release Process

### Version Numbering

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Types

- **Major Release**: Breaking changes, new architecture, API changes
- **Minor Release**: New features, enhancements, non-breaking changes
- **Patch Release**: Bug fixes, security updates, documentation updates

### Changelog Categories

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security improvements

### Conventional Commits

This changelog is generated from [Conventional Commits](https://conventionalcommits.org/):

- `feat:` → **Added**
- `fix:` → **Fixed**
- `docs:` → **Changed** (documentation)
- `style:` → **Changed** (formatting)
- `refactor:` → **Changed** (code refactoring)
- `perf:` → **Changed** (performance improvements)
- `test:` → **Changed** (tests)
- `chore:` → **Changed** (maintenance)
- `security:` → **Security**

### Breaking Changes

Breaking changes are marked with `!` in the commit type:
- `feat!:` → **Added** + **Breaking Change**
- `fix!:` → **Fixed** + **Breaking Change**