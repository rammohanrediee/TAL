# TAL Production and Operations Baseline

## Purpose

This document defines the minimum operational standard for releasing TAL. It is
provider-neutral: a hosting vendor may be selected later, but the selected platform must
satisfy every requirement below.

## Environments

| Environment | Purpose | Data policy |
| --- | --- | --- |
| Local | Developer work | Synthetic/local fixtures only |
| CI | Automated verification | Ephemeral services and fake external credentials |
| Staging | Migration, integration, and release validation | Synthetic or explicitly sanitized data |
| Production | Real users | Private data under retention and deletion policy |

Each environment has separate databases, buckets, Redis instances, OAuth clients, secrets,
domains, encryption keys, and AI credentials. Production data is never copied into local or
CI environments.

## Initial deployment topology

- Next.js: independently deployable web application behind TLS/CDN
- FastAPI: stateless container with at least two production instances when traffic requires
  availability during restarts
- Celery: independently scalable worker containers split by queue workload
- Scheduler: exactly one Celery Beat/scheduler instance
- PostgreSQL: managed service with encrypted storage and automated point-in-time backups
- Redis: managed private service with authentication and encryption in transit
- R2/S3: private bucket with versioning/lifecycle rules where supported
- Secrets: hosting-platform secret manager, never image layers or repository files

Only the web and API ingress are public. PostgreSQL and Redis accept traffic only from
application networks. Administrative access requires least-privilege identities and audit
logging.

## Configuration contract

Application startup fails fast when a required production setting is missing or still has a
development value. Settings are documented in `.env.example` without secrets.

Required groups include:

- application environment, frontend URL, API URL, trusted hosts, CORS origins
- database and Redis connections
- JWT issuer/audience/keys and session/CSRF secrets
- Google OAuth client and allowlisted redirect URI
- R2 endpoint, bucket, access identity, and upload limit
- AI provider credentials, approved models, timeouts, and cost ceilings
- logging/telemetry endpoints and release identifier
- email/notification configuration when those features ship

Secrets are rotated on a documented schedule and immediately after suspected exposure.
Production credentials use minimum permissions and separate identities per service.

## Security baseline

- TLS for every external connection and supported internal connection
- `Secure`, `HttpOnly`, scoped cookies with documented `SameSite` behavior
- CSRF protection for state-changing cookie-authenticated requests
- Exact CORS origin allowlist; no wildcard with credentials
- Trusted-host validation and security headers including CSP, HSTS, frame restrictions,
  MIME sniffing protection, and a conservative referrer policy
- Rate limits for authentication, uploads, URL analysis, chat, and expensive AI actions
- Upload signature/type/size validation plus malware scanning before document processing
- Private object storage and short-lived signed access
- Database least privilege and parameterized queries
- Dependency, secret, static-analysis, and container-image scanning
- Audit records for authentication security events, data export/deletion, confirmations,
  administrative access, and external mutations
- Formal incident-response contacts and credential-revocation procedure

Logs must not contain passwords, access/refresh tokens, OAuth payloads, document contents,
full job descriptions, signed URLs, or unnecessary personal data.

## Reliability targets for MVP

Proposed initial service objectives, reviewed after real traffic:

| Measure | Initial objective |
| --- | --- |
| API availability | 99.9% monthly, excluding announced maintenance |
| Lightweight API latency | p95 below 500 ms |
| Readiness response | p95 below 250 ms |
| Accepted upload acknowledgement | p95 below 2 seconds, excluding object transfer time |
| Résumé processing | 95% complete within 2 minutes for supported documents |
| Job ingestion freshness | Configured providers checked at least every 6 hours |
| Unsupported-claim escape rate | 0 in labeled release evaluation cases |

External AI and provider latency is reported separately from core API latency. User-facing
asynchronous operations expose status and recoverable failure information.

## Observability

Every request and task carries a correlation identifier. Production emits structured logs,
metrics, and distributed traces with environment and release identifiers.

Minimum dashboards and alerts:

- API request volume, latency, status codes, saturation, and exceptions
- authentication failures and rate-limit activity
- database connections, slow queries, storage, replication, and backup health
- Redis availability and Celery queue depth, runtime, retries, and terminal failures
- object-storage failures and reconciliation mismatches
- provider ingestion freshness, timeouts, rate limits, and normalized job counts
- AI latency, validation failure, retry rate, tokens, estimated cost, and model/provider
- unsupported-claim and evaluation-regression metrics

Alerts must identify an owner, severity, runbook, and escalation path. Avoid alerts that
cannot result in an operator action.

## Backups and disaster recovery

- PostgreSQL: automated daily backup plus point-in-time recovery where supported
- Private documents: provider durability plus versioning/lifecycle protection where allowed
- Configuration: reproducible infrastructure and deployment configuration in version control
- Restore drills: staging restore at least quarterly and before major storage changes

Initial objectives:

- Recovery point objective: 15 minutes for PostgreSQL
- Recovery time objective: 4 hours for the MVP service

Backups are encrypted, access-controlled, monitored, and deleted according to retention
policy. A backup is not considered valid until a restore drill succeeds.

## Privacy and data lifecycle

Before launch, publish and implement:

- data inventory and purpose for each personal-data category
- user export in a portable format
- account and document deletion workflow
- retention periods for source documents, generated exports, logs, audits, and backups
- subprocessors and data regions
- consent/notice for AI processing
- support path for correction, access, and deletion requests

Deletion is asynchronous and auditable. It removes database records, private objects,
derived exports, queued work, and provider-side data where applicable. Backup expiration is
documented honestly rather than represented as immediate physical erasure.

**Decision required before launch:** supported jurisdictions, legal basis, retention periods,
and deletion grace period must be approved by the product owner with appropriate legal
guidance.

## Database migration policy

- Every schema change uses an Alembic migration with upgrade and downgrade review.
- Production migrations are tested against a recent schema snapshot in staging.
- Existing data is backfilled before adding a non-null constraint.
- Large changes use expand/backfill/contract rather than blocking table rewrites.
- Deployments remain compatible with both sides of an in-progress rolling migration.
- A database backup/checkpoint and rollback decision are recorded before release.

The existing application-ownership migration must be tested against a populated database;
adding a non-null `user_id` in one step is unsafe when rows already exist.

## CI/CD release gates

Pull requests must pass:

- backend tests and coverage threshold
- Ruff lint/format verification
- strict mypy type checking
- frontend ESLint, type check, and production build
- migration upgrade smoke test on PostgreSQL
- dependency, secret, and static security scans
- focused contract and authorization-isolation tests

Release candidates additionally pass:

- staging migrations and smoke tests
- end-to-end authentication and MVP workflow tests
- golden AI/evidence evaluation thresholds
- prompt-injection and unsupported-rewrite regression tests
- load/concurrency checks for changed critical paths
- backup, rollback, and feature-flag plan review

Deployments are immutable and identified by commit SHA. Production promotion requires an
approval, records the migration version, and supports application rollback. Database
rollback is used only when the migration explicitly makes it safe.

## Current gaps that block production

- `.env.example` does not list all required configuration.
- Cookie behavior and OAuth completion are not environment-correct end to end.
- CORS, CSRF, trusted-host, and security-header policies are absent.
- Frontend login and session handling are not connected to the API.
- Résumé storage lacks durable compensation/reconciliation for partial failures.
- Celery has configuration but no production tasks, queues, schedules, or failure policy.
- Liveness exists, but dependency-aware readiness does not.
- CI runs backend tests only.
- Ruff currently fails and mypy is not correctly checking the package.
- No deployable backend/worker container or infrastructure definition exists.
- No monitoring, alerting, backup verification, privacy workflow, or runbooks exist.
- Job ingestion, matching, conversational tools, and tailoring are not implemented.

## Production release checklist

### Product path

- A real user completes upload, evidence confirmation, preference capture, fresh-job ranking,
  explanation, approved tailoring, export, and application tracking.
- Every positive match and tailored claim links to verified evidence.
- Hard eligibility conflicts cannot be hidden by a high numeric score.

### Security and privacy

- Cross-user isolation tests cover every private access pattern.
- Threat model and security review are complete.
- Rate limits, CSRF, CORS, secure cookies, private storage, and secret rotation are verified.
- Export, account deletion, and retention workflows are tested end to end.

### Operations

- Dashboards, alerts, runbooks, and on-call ownership exist.
- Backup restore, rollback, worker retry, and provider-outage exercises succeed.
- SLO, cost, latency, and AI-quality dashboards are populated in staging.

### Delivery

- All CI/CD gates pass from a clean checkout.
- Staging uses production-equivalent topology and configuration classes.
- Database migrations are tested with populated representative data.
- The release owner records go/no-go approval and rollback criteria.

Production is ready only when all four sections pass. A successful local demo or green unit
test suite alone is not a production release signal.
