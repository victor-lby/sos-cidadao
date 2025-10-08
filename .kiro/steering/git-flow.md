# Git Flow & Development Workflow

## Branching Strategy

### Trunk-Based Development
The project follows a simplified trunk-based development model:

- **`main`** - Production-ready code, protected branch
- **Feature branches** - Short-lived branches for individual features/fixes
- **No long-lived development branches** - Features merge directly to main

### Branch Naming Convention
```
feat/feature-name          # New features
fix/bug-description        # Bug fixes
docs/documentation-update  # Documentation changes
refactor/code-improvement  # Code refactoring
test/test-improvements     # Test additions/improvements
chore/maintenance-task     # Maintenance tasks
```

### Branch Protection Rules
- **Main branch** requires:
  - Pull request reviews (minimum 1 approval)
  - Status checks must pass (CI/CD pipeline)
  - Up-to-date branches before merge
  - No direct pushes allowed

## Conventional Commits

### Commit Message Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit Types
- **feat**: New feature for the user
- **fix**: Bug fix for the user
- **docs**: Documentation changes
- **style**: Code style changes (formatting, missing semicolons, etc.)
- **refactor**: Code refactoring without changing functionality
- **test**: Adding or updating tests
- **chore**: Maintenance tasks, dependency updates
- **perf**: Performance improvements
- **ci**: CI/CD pipeline changes
- **build**: Build system or external dependency changes

### Scope Examples
- **auth**: Authentication and authorization
- **notifications**: Notification workflow
- **api**: Backend API changes
- **frontend**: Frontend application changes
- **db**: Database schema or operations
- **docs**: Documentation updates
- **infra**: Infrastructure and deployment

### Commit Message Examples
```bash
# Feature commits
feat(notifications): add notification approval endpoint
feat(auth): implement JWT token refresh mechanism
feat(frontend): add notification list component with pagination

# Bug fix commits
fix(api): resolve organization scoping in notification queries
fix(auth): handle expired JWT tokens gracefully
fix(frontend): correct HAL link rendering in data tables

# Documentation commits
docs(api): update OpenAPI specification for notification endpoints
docs: add deployment instructions for Vercel

# Refactoring commits
refactor(domain): extract notification validation to pure functions
refactor(services): improve MongoDB connection pooling

# Test commits
test(notifications): add integration tests for approval workflow
test(auth): add unit tests for permission aggregation

# Chore commits
chore(deps): update dependencies to latest versions
chore(ci): configure Dependabot for security updates
```

### Breaking Changes
For breaking changes, add `!` after the type/scope:
```bash
feat(api)!: change notification status enum values
fix(auth)!: modify JWT token structure for enhanced security
```

## Pull Request Workflow

### PR Creation Process
1. **Create feature branch** from latest main
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feat/notification-approval
   ```

2. **Make commits** following conventional commit format
   ```bash
   git add .
   git commit -m "feat(notifications): implement approval endpoint with HAL links"
   ```

3. **Push branch** and create PR
   ```bash
   git push origin feat/notification-approval
   ```

4. **Create PR** using the provided template

### PR Requirements
- **Title** must follow conventional commit format
- **Description** must use the PR template
- **All CI checks** must pass
- **At least 1 approval** from code owner
- **Branch must be up-to-date** with main

### PR Merge Strategy
- **Squash and merge** for feature branches
- **Commit message** follows conventional commit format
- **Delete branch** after merge

## PR Template

Create `.github/pull_request_template.md`:

```markdown
## Description
Brief description of the changes and their purpose.

## Type of Change
- [ ] 🚀 New feature (feat)
- [ ] 🐛 Bug fix (fix)
- [ ] 📚 Documentation update (docs)
- [ ] 🎨 Code style/formatting (style)
- [ ] ♻️ Code refactoring (refactor)
- [ ] ✅ Tests (test)
- [ ] 🔧 Chore/maintenance (chore)
- [ ] ⚡ Performance improvement (perf)
- [ ] 🔄 CI/CD changes (ci)

## Related Issues
Closes #[issue_number]
Related to #[issue_number]

## Changes Made
- [ ] Change 1
- [ ] Change 2
- [ ] Change 3

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] All existing tests pass

## API Changes
- [ ] No API changes
- [ ] Backward compatible API changes
- [ ] Breaking API changes (requires version bump)

## Database Changes
- [ ] No database changes
- [ ] Schema migrations included
- [ ] Data migrations required

## Security Considerations
- [ ] No security implications
- [ ] Security review completed
- [ ] Secrets/credentials properly handled

## Documentation
- [ ] Code comments updated
- [ ] API documentation updated
- [ ] README updated
- [ ] Architecture docs updated

## Deployment Notes
- [ ] No special deployment requirements
- [ ] Environment variables added/changed
- [ ] Infrastructure changes required
- [ ] Feature flags involved

## Screenshots/Demo
<!-- Add screenshots or demo links if applicable -->

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Code is properly commented
- [ ] Tests cover the changes
- [ ] Documentation updated
- [ ] No console errors/warnings
- [ ] Conventional commit format used
```

## Release Management

### Version Numbering
Follow Semantic Versioning (SemVer):
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Process
1. **Create release branch** from main
   ```bash
   git checkout -b release/v1.2.0
   ```

2. **Update version** in package.json and other files

3. **Generate changelog** from conventional commits
   ```bash
   npx conventional-changelog -p angular -i CHANGELOG.md -s
   ```

4. **Create release PR** and merge to main

5. **Tag release** on main branch
   ```bash
   git tag -a v1.2.0 -m "Release v1.2.0: Add notification approval workflow"
   git push origin v1.2.0
   ```

### Changelog Format
Generated automatically from conventional commits:

```markdown
# Changelog

## [1.2.0] - 2024-01-15

### Added
- Notification approval workflow with HAL affordances
- JWT token refresh mechanism
- OpenTelemetry instrumentation for observability

### Changed
- Improved MongoDB connection pooling
- Enhanced error handling in API responses

### Fixed
- Organization scoping in notification queries
- JWT token expiration handling

### Security
- Enhanced JWT token validation
- Added rate limiting for API endpoints
```

## Code Review Guidelines

### Reviewer Checklist
- [ ] **Functionality**: Code works as intended
- [ ] **Architecture**: Follows project patterns (functional programming, HAL APIs)
- [ ] **Security**: No security vulnerabilities introduced
- [ ] **Performance**: No performance regressions
- [ ] **Testing**: Adequate test coverage
- [ ] **Documentation**: Code is well-documented
- [ ] **Style**: Follows project coding standards
- [ ] **Multi-tenancy**: Organization scoping properly implemented

### Review Process
1. **Automated checks** must pass first
2. **Manual review** by at least one team member
3. **Address feedback** before approval
4. **Re-review** if significant changes made
5. **Approve and merge** when ready

## Hotfix Process

For critical production issues:

1. **Create hotfix branch** from main
   ```bash
   git checkout -b hotfix/critical-security-fix
   ```

2. **Make minimal fix** with appropriate commit message
   ```bash
   git commit -m "fix(auth): patch JWT validation vulnerability"
   ```

3. **Create emergency PR** with expedited review

4. **Deploy immediately** after merge

5. **Follow up** with comprehensive fix if needed