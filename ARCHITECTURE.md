# TAL System Architecture

## Purpose and status

This document defines TAL's technical boundaries and target architecture. It complements
`PROJECT_BLUEPRINT.md`, which defines product behavior and delivery stages.

Labels used below:

- **Current** — implemented in the repository.
- **Target** — approved direction, not necessarily implemented yet.
- **Decision required** — must be resolved before the affected stage can ship.

## Architectural style

TAL is a modular monolith with independently testable feature modules. FastAPI owns the
HTTP, authentication, authorization, and mutation boundaries. PostgreSQL is the product
system of record. Redis and Celery execute asynchronous work. Private source documents
live in S3-compatible object storage.

Microservices are not an MVP goal. A module may be extracted only when independent
scaling, isolation, ownership, or deployment is demonstrated by production evidence.

```text
Browser
  |
  v
Next.js web application
  |
  v
FastAPI API
  |-- PostgreSQL: users, evidence, jobs, matches, audits
  |-- Private R2 bucket: original and generated documents
  |-- Redis: Celery broker/results, short-lived coordination
  |-- Celery workers: parsing, ingestion, evaluation, export
  `-- External adapters: OAuth, ATS providers, AI providers
```

## Module boundaries

| Module | Responsibility | Status |
| --- | --- | --- |
| `auth` | Users, password login, Google identity, sessions | Current, incomplete production controls |
| `applications` | Owner-scoped application tracking | Current |
| `resumes` | Upload metadata, private storage, lifecycle, versions | Upload/delete current; intelligence target |
| `profiles` | Confirmed candidate evidence and provenance | Target |
| `preferences` | Versioned intent and eligibility facts | Target |
| `jobs` | Provider adapters, observations, normalized opportunities | Target |
| `matching` | Requirements, hard gates, evidence links, scores | Target |
| `conversations` | Messages and controlled domain-tool orchestration | Target |
| `tailoring` | Grounded revisions, approval, diff, export | Target |
| `notifications` | User-controlled reminders and delivery | Target |
| `audit` | Security-sensitive actions and confirmed mutations | Target |

Modules communicate through typed service functions. Routers do not contain business
logic, workers call the same domain services as HTTP routes, and no conversational tool
receives a raw database session or unrestricted storage access.

## Request and ownership boundary

1. The API authenticates the request and resolves a server-side `user_id`.
2. Routers pass authenticated context to a typed domain service.
3. Private database queries include the ownership predicate in the query itself.
4. Missing and foreign-owned objects return the same not-found response.
5. Services validate state transitions before committing.
6. Security-sensitive mutations create an audit event.

Client-supplied ownership identifiers are never trusted. Shared job records are public
product data; preferences, evidence, matches, applications, documents, conversations,
and exports are private user data.

## Authentication design

### Current

- Argon2 password hashes
- Short-lived JWT access tokens
- Bearer token or HTTP-only cookie lookup
- Google OAuth identity storage

### Target browser flow

- The browser uses `Secure`, `HttpOnly`, `SameSite=Lax` cookies in production.
- Cookie security is environment-aware so local HTTP development works.
- State-changing cookie-authenticated requests require CSRF protection.
- OAuth callbacks create the TAL session and redirect to an allowlisted frontend URL;
  access tokens are not placed in query strings.
- CORS uses an explicit environment-specific origin allowlist and credentials are enabled
  only for those origins.
- Access tokens include `sub`, `exp`, `iat`, `iss`, `aud`, and a unique identifier.
- Long-lived browser access uses rotating, server-revocable sessions or refresh tokens.
- Password reset, email verification, account linking, logout-all, and session listing are
  required before public release.

API clients may use bearer tokens. Browser and API-client authentication behavior must be
tested separately.

## Core data model

All mutable domain tables use UUID identifiers and timezone-aware timestamps. Important
AI and scoring outputs retain their input and policy versions.

| Aggregate | Minimum records |
| --- | --- |
| Identity | `users`, `external_accounts`, `sessions` |
| Résumés | `resumes`, `resume_versions`, `resume_sources`, `evidence_claims`, `evidence_locations` |
| Intent | `preference_sets`, `preference_items`, eligibility confirmations |
| Jobs | `providers`, `companies`, `source_observations`, `jobs`, `job_requirements` |
| Matching | `match_runs`, `eligibility_results`, `evidence_links`, `score_components` |
| Conversation | `conversations`, `messages`, `tool_calls`, confirmations |
| Tailoring | `tailoring_runs`, proposed changes, approvals, generated exports |
| Operations | `background_jobs`, `audit_events`, provider health records |

Résumé versions, source observations, match inputs, scoring-policy versions, and approved
exports are immutable. Corrections create new versions rather than silently overwriting
historical evidence.

## Résumé lifecycle and storage consistency

```text
uploading -> uploaded -> processing -> ready
     |                       |
     `-> failed <------------'
```

The API validates the filename, declared MIME, signature, supported format, and size
before accepting a file. The object key is generated by the server and never includes a
user-controlled path.

Database and object storage cannot share a transaction. The target workflow therefore:

1. Creates an `uploading` database record with an idempotency key.
2. Uploads to a private temporary object key.
3. Verifies object metadata and checksum.
4. Promotes the record to `uploaded` and schedules parsing after commit.
5. Deletes temporary/orphaned objects through bounded compensation and reconciliation.

Deletion first records a deletion request, removes derivatives and the private object,
then marks the record deleted. A recurring reconciliation job detects missing and orphaned
objects. User-visible deletion has a documented retention window.

Downloads use short-lived signed URLs or authenticated API streaming. Bucket listing and
public object access remain disabled.

## Background-job contract

Celery tasks carry identifiers, never raw document bytes or secrets. Each task defines:

- idempotency key and expected state
- maximum attempts and exponential backoff with jitter
- execution timeout and provider timeout
- retryable and terminal error classes
- progress/status fields safe for users
- structured logs and trace correlation
- terminal failure handling and operator replay procedure

Planned queues are `documents`, `ingestion`, `matching`, `exports`, and `notifications`.
Separate queues prevent slow external providers or document parsing from blocking
user-facing work. Periodic tasks use a single scheduler instance or distributed lock.

## Job ingestion architecture

Provider adapters implement one contract: collect immutable source observations, normalize
them, and report source health. The initial sequence is Greenhouse, Lever, then Ashby.

```text
provider response
  -> immutable observation
  -> validation and cheap filters
  -> normalized job
  -> deduplication
  -> freshness/liveness status
  -> candidate-specific evaluation
```

Deduplication uses provider identity first, canonical URL second, and normalized
company-role-location identity as a guarded fallback. Provider HTML and descriptions are
untrusted data and cannot supply system instructions or invoke tools.

## Applied-AI boundary

AI calls are made through a provider-independent application interface. Every task defines
a strict input schema, output schema, timeout, permitted model class, and fallback behavior.

Persist for reproducibility:

- model provider and model identifier
- prompt/template and schema versions
- taxonomy and policy versions
- input document/version identifiers
- validated structured output or failure class
- latency, token usage, and estimated cost

AI may extract, classify semantic relationships, explain, and rewrite supported content.
It may not directly authorize data access, decide hard eligibility, invent evidence, or
choose an unsupported rating. Deterministic code applies gates and calculates versioned
score components.

External text is delimited as data, excluded from instruction channels, schema-validated,
and tested with prompt-injection fixtures. Invalid or low-confidence output is retried only
within a bounded policy and otherwise moves to review or failure.

**Decision required before Stage 4:** select primary and fallback model providers, approved
model classes per task, regional/privacy constraints, and per-task cost ceilings.

## API conventions

- Versioned REST routes under `/api/v1`
- Pydantic request and response contracts
- Stable domain-error codes with safe user messages
- Cursor pagination for growing collections
- Idempotency keys for retryable creation and external-effect requests
- Optimistic concurrency or expected-version checks for reviewed data
- Explicit confirmation tokens for conversational mutations
- OpenAPI is generated from the same route contracts

Health endpoints are separated into liveness and readiness. Readiness checks only critical
dependencies and uses strict timeouts; it does not call AI or job providers.

## Frontend boundary

The Next.js application consumes the documented API through one typed client configured by
environment. It must not hard-code backend URLs. Authentication state is derived from the
server session, and protected routes handle loading, unauthenticated, forbidden, empty,
failure, retry, and expired-session states.

The chat UI renders server-provided structured job and match data. It never calculates or
fabricates scores in the browser. Mutation confirmations state the exact action and target.

## Architecture decisions still requiring product input

- Hosting vendor and primary region
- AI provider/model allowlist and data-processing terms
- Supported launch countries and corresponding privacy obligations
- Email/notification provider
- Exact account-deletion grace period and legal retention exceptions
- Availability and latency objectives if the proposed defaults in `PRODUCTION.md` are not
  acceptable

These decisions do not block local feature development, but they block the production
release gate.
