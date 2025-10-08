# PRP — S.O.S Cidadão

## 1) One-liner / Mission

Build a public, open-source, Apache-licensed, serverless Python backend + Vue 3 frontend app for multi-tenant civic notifications, with JWT auth, full auditability, HATEOAS Level-3 APIs (HAL), OpenAPI 3.0, observability via OpenTelemetry, Redis caching, MongoDB Atlas storage, and Vercel default deploy (Docker optional).

## 2) Why this matters

Municipal teams need a trustworthy way to receive, moderate, and broadcast critical public alerts. This system provides auditable flows (receive → approve/deny → dispatch), strong privacy/security practices, and developer-friendly governance (OpenAPI, CI/CD, Dependabot, secrets scanning).

## 3) Success criteria (Definition of Done)

- ✅ **Deploys on Vercel** as the default (serverless functions) with a working Vue app and Python API.
- ✅ **Docker** works for local dev (compose for MongoDB/Redis/LavinMQ).
- ✅ **Functional-style Python** modules (pure functions for domain logic, side-effects at edges).
- ✅ **JWT auth** with access/refresh, revocation (Redis), and role/permission checks per org.
- ✅ **Observability**: HTTP traces, logs, and basic metrics exported via OpenTelemetry; docs on how to run the Collector locally.
- ✅ **Auditing**: every user action recorded and visible in an Admin UI (filter by user, org, time, entity, action).
- ✅ **API Level-3 (HATEOAS)** using `application/hal+json` with `_links` and `_embedded`.
- ✅ **OpenAPI 3.0** spec(s) generated/maintained; interactive docs enabled in **development** only.
- ✅ **CI/CD (GitHub Actions)**: OpenAPI lint/validate, AI PR review, Dependabot, and secret scanning.
- ✅ **Data**: MongoDB Atlas as long-term storage with `schemaVersion` on each entity; Redis for low-latency, frequently-changing values (and JWT blocklist).
- ✅ **Dispatch**: on approval, publish to CloudAMQP **LavinMQ** (AMQP) to be consumed by a downstream API.

## 4) Non-goals / Out of scope

- No SMS/email gateway implementation (only the queue hand-off).
- No custom mobile app.
- No vendor-specific monitoring lock-in (use OTel).

## 5) Target users

- **Operators/Admins** (municipal staff) who approve or deny notifications and manage targets/categories/endpoints.
- **View-only users** who browse notifications.
- **System integrators** using the HAL+OpenAPI APIs.

## 6) Environments

- **dev**: local Docker compose & Vercel preview; Swagger/Redoc enabled.
- **stage/prod**: on Vercel; docs endpoints disabled by default (feature-flag toggle for internal access only).

## 7) Architecture (high-level)

- **Frontend**: Vue 3 + **Vuetify 3** (Material Design 3). Routing via Vue Router; state via Pinia.
- **Backend (serverless)**: Python on Vercel Serverless Functions (Flask + `flask-openapi3` for OpenAPI + Pydantic validation).
- **Storage**: MongoDB Atlas (`pymongo`); `schemaVersion` stored per document.
- **Cache / tokens**: Upstash/Redis (HTTP client, serverless-friendly).
- **Queue**: CloudAMQP LavinMQ (AMQP) for outbound messages to external API(s).
- **Observability**: OpenTelemetry auto/manual instrumentation (HTTP traces/logs/metrics) → Collector (dev) and vendor-agnostic exporters.
- **API style**: HATEOAS Level-3 using **HAL** (`_links`, `_embedded`).

## 8) Tech constraints & licensing

- **Apache-2.0** license.
- Public repo, open to contributions.
- Functional programming guidelines for domain logic (pure functions + dependency injection).
- API responses: `application/hal+json`.

## 9) Entities & CRUD (timestampable + soft-deletable)

> All CRUDs include: `id`, `organizationId`, `createdAt`, `updatedAt`, `deletedAt` (nullable), `createdBy`, `updatedBy`, `schemaVersion:int`.

- **Organization**: `{ name, slug }`
- **User**: `{ email, name, roles: [roleId], permissions: [permId] }` (role-based per org)
- **Role**: `{ name, permissions: [permId] }`
- **Permission**: `{ code, description }`
- **NotificationTarget**: `{ name, description, parent: targetId|null, children: [targetId], createdBy }`
- **NotificationCategory**: `{ name, notificationTargets: [targetId] }`
- **Endpoint**: `{ name, description, url, dataMapping, notificationCategories: [categoryId] }`
  - `dataMapping` defines transformation from local `Notification` document to remote payload schema.
- **Notification**: `{ title, body, severity:0..5, origin, originalPayload, baseTarget:targetId, targets:[targetId]|null, categories:[categoryId], status: 'received'|'approved'|'denied'|'dispatched' }`

### Relations

- Multi-tenant by **Organization**; all queries are org-scoped.
- **User** ↔ **Role** (many-to-many); **Role** ↔ **Permission**.
- **Notification** references **Targets**, **Category**, and **Endpoint** via categories.

## 10) Core flows

### 10.1 Receive (Webhook, JWT-protected)

- `POST /notifications/incoming` (JWT required) stores the incoming `Notification` with `status='received'` and preserves `originalPayload` and `origin` metadata.

### 10.2 Review & Decide (UI + HAL affordances)

- List: `GET /notifications?status=received` returns HAL collection with pagination `_links` (`self`, `next`, `prev`, `item`).
- Detail: `GET /notifications/{id}` includes affordance links:
  - `_links.approve: { href: ..., method:'POST' }`
  - `_links.deny: { href: ..., method:'POST' }`
- Admin UI lets the reviewer **select Targets**, add `title`/`description` as needed.

### 10.3 Approve

- `POST /notifications/{id}/approve`:
  - Validates selection & permissions.
  - Publishes a message to **LavinMQ** with transformed payload (via `dataMapping` and per-endpoint category routing) → downstream API.
  - Sets `status='dispatched'` and writes an **audit log** entry.

### 10.4 Deny

- `POST /notifications/{id}/deny`:
  - Stores decision + reason, `status='denied'`, and writes **audit** entry.

## 11) API design details (HATEOAS + OpenAPI)

- Media type: `application/hal+json` with `_links` (`self`, `collection`, `approve`, `deny`, `next`, `prev`) and optional `_embedded`.
- Pagination: `page`, `pageSize` + HAL nav links.
- Validation & docs: `flask-openapi3` + Pydantic; OpenAPI 3.0 spec under `/openapi.json`.
- **Dev-only** interactive docs (Swagger/Redoc) exposed via config flag.

## 12) AuthN/AuthZ

- **JWT** (PyJWT / Flask-JWT-Extended) with:
  - Access/refresh tokens, expiration, rotation.
  - Redis-backed blocklist/revocation.
  - Org-scoped roles/permissions middleware.
- All endpoints require org context (header or token claim).

## 13) Observability & Auditability

- **OpenTelemetry** auto-instrumentation (Flask, requests), plus custom spans around approval/denial and message publish; log correlation (trace/span IDs).
- **Audit logs** collection: `{ at, userId, orgId, entity, entityId, action, before, after, ip, userAgent, traceId }`.
- Admin UI for filtering/exporting audit trails.

## 14) Data & caching

- **MongoDB Atlas** via `pymongo`; connection string & timeouts documented. Each entity includes `schemaVersion` for future migrations.
- **Redis** (Upstash) for:
  - JWT blocklist & rate limits.
  - Short-TTL caches (e.g., counts, hot lists).
  - Connectionless HTTP client ideal for serverless.

## 15) Frontend (Vue 3 + Material 3)

- **Vuetify 3** Material-You theme; responsive admin panel with tables, filters, and inline HAL-aware actions (approve/deny).
- Screens: Login, Notifications List/Detail, Approvals, Audit Logs, Targets & Categories, Endpoints, Users/Roles/Permissions, Org settings.

## 16) CI/CD (GitHub Actions)

- **OpenAPI lint/validate** with Redocly CLI; fails build if invalid.
- **AI PR review** with Codium/Qodo **PR-Agent** (OSS).
- **Dependabot** security & version updates.
- **Secrets scanning** with **Gitleaks** action.

## 17) Versioning & changelog

- **Conventional Commits** + **Keep a Changelog** style (CHANGELOG.md generated in releases).
- Tag releases and store OpenAPI artifacts per release.

## 18) Multi-env config

- Environment-based config files/vars: `DEV|STAGE|PROD`.
- Feature flags: `DOCS_ENABLED`, `OTEL_ENABLED`, `HAL_STRICT`.
- Vercel env vars documented (Atlas URI, Upstash URL/TOKEN, JWT keys, AMQP URL).

## 19) Repository layout (proposal)

```
/
  LICENSE (Apache-2.0)
  README.md
  vercel.json
  .github/workflows/
    openapi-validate.yml
    pr-agent.yml
    dependabot.yml
    gitleaks.yml
  frontend/
    (Vue 3 + Vuetify app)
  api/               # Vercel Serverless (Python)
    __init__.py
    app.py           # Flask app (exported for Vercel)
    routes/          # pure endpoint adapters -> domain
    domain/          # pure functions (FP)
    services/        # mongo, redis, lavinmq, auth
    models/          # pydantic schemas
    observability/   # OTel setup
    specs/           # openapi.yaml (generated/validated)
  infra/
    docker/          # Dockerfile, docker-compose.dev.yml
    collector/       # otel-collector.yaml (dev)
  docs/
    ADRs/, API/, CONTRIBUTING.md, CODE_OF_CONDUCT.md
```

## 20) Acceptance tests (high-impact)

1. Deploy preview on Vercel; `/healthz` returns HAL with `_links.self`.
2. Login → JWT issued; Redis blocklist revokes a token; blocked token denied.
3. POST webhook stores notification; OpenTelemetry traces visible locally via Collector.
4. Approve path publishes to LavinMQ; queue message received by test consumer.
5. Dev docs at `/docs` show OpenAPI; CI fails if spec invalid.
6. Admin audit page shows all actions with filters and export.

## 21) Risks & mitigations

- **Serverless cold starts** → keep handlers slim; cache connections (Mongo/Redis clients) between invocations.
- **HAL complexity** → start with minimal `_links` set; validate via contract tests.
- **Secrets exposure** → Gitleaks in CI; Vercel env vars only; no keys in code.

## 22) Build instructions (initial)

- **Deploy**: use Vercel Python runtime template; `vercel` will expose `/api/*`.
- **Frontend**: Vue 3 + Vuetify 3 (MD3 blueprint) scaffold; connect to API via HAL client.
- **API**: Flask + `flask-openapi3` for routes/spec; PyJWT / Flask-JWT-Extended; Upstash Redis; PyMongo; LavinMQ AMQP client.
- **Observability**: add OTel auto-instrument and sample Collector config.

---

### Appendix — Key references

- Vercel Python Serverless template
- Vuetify 3 (Material 3)
- OpenTelemetry Python getting started
- HAL draft (JSON Hypertext Application Language)
- MongoDB Atlas with PyMongo
- Upstash Redis (serverless Python SDK)
- Flask-OpenAPI3 (OpenAPI 3 + Swagger/Redoc)
- CloudAMQP LavinMQ (queue)
- CI: Redocly OpenAPI CLI action, PR-Agent, Dependabot, Gitleaks

