# TAL Flagship Backend — Project Blueprint

## Product statement

TAL is a tool-assisted job-search backend that helps users manage résumés, discover
relevant roles, understand evidence-based job matches, track applications, schedule
follow-ups, and tailor résumés without inventing experience.

Honest job-discovery description:

> Aggregates and normalizes jobs from configured public sources and company career
> portals.

The project begins as a modular monolith. FastAPI owns the HTTP boundary, PostgreSQL
is the source of truth, and background work is introduced only when the relevant
stage needs it.

## Stage 1 — Backend foundation

Build first, without AI chat:

- User accounts, authentication, authorization, and user-owned resources
- Résumé upload and parsing
- Structured résumé evidence storage
- Companies, jobs, applications, interviews, and notes
- Append-only application-status history
- Search, filtering, sorting, and pagination
- Follow-up dates and reminders
- Automated tests and OpenAPI documentation

Completion outcome: a deployable, documented application-tracking REST API that is a
respectable backend portfolio project on its own.

## Stage 2 — Job ingestion and matching

- Ingest jobs from legitimate public APIs and company career pages
- Run scheduled background collection
- Deduplicate by canonical URL and normalized company/role identity
- Check posting freshness and liveness
- Extract skills and requirements
- Match résumé evidence to job-description requirements
- Explain match strengths, hard gaps, and optional gaps
- Return an explainable match score rather than an unsupported black-box number

## Stage 3 — Conversational interface

The chatbot receives controlled backend tools, never unrestricted database access.

Initial tool surface:

- `search_jobs`
- `explain_job_match`
- `list_applications`
- `update_application_status`
- `schedule_follow_up`
- `compare_resume_to_jd`
- `draft_resume_changes`

Mutations require explicit confirmation. Example:

> Move the Gravity AI application from Evaluated to Applied?

This stage must demonstrate scoped authorization, reliable tool use, validation,
auditing, and human-in-the-loop control.

## Stage 4 — Evidence-grounded résumé tailoring

The tailoring engine must:

1. Extract job-description requirements.
2. Retrieve exact supporting résumé evidence.
3. Separate supported skills from hard and optional gaps.
4. Reorder and rewrite only supported evidence.
5. Refuse to invent missing experience.
6. Show a diff before saving.
7. Version every tailored résumé.

## Stage 5 — Production engineering

- Redis and Celery workers
- Retries with exponential backoff and bounded retry policies
- Idempotent ingestion jobs
- Rate limiting
- Structured logging
- Health, readiness, and dependency checks
- Metrics
- Docker Compose
- PostgreSQL migrations
- GitHub Actions
- Role-based permissions
- Encryption for sensitive data
- Backup, export, account deletion, and retention workflows
- Load, concurrency, and failure testing

## Safety boundary

The first version will not submit job applications automatically. Application
portals vary, automation may violate platform rules, and silent submission can send
incorrect information.

Supported behavior:

- Direct application links
- Prefilled drafts where permitted
- Application checklists
- Human confirmation before external actions
- Manual “Mark as applied” or verified portal status

Product promise: “Apply easily,” not “automatically applies everywhere.”

## What the project demonstrates

- FastAPI and REST API design
- PostgreSQL data modeling and migrations
- Authentication and authorization
- Async workers and scheduling
- External API integration
- Ingestion, normalization, and deduplication
- Controlled LLM tool calling and retrieval
- Explainable, evidence-grounded matching
- Notifications and reminders
- Tests, CI/CD, containers, and observability
- Privacy, security, and deletion design

## Stage 1 delivery sequence

1. Application-status domain rule
2. First PostgreSQL-backed application vertical slice
3. Database migration workflow and test isolation
4. User registration and password authentication
5. Resource ownership and authorization
6. Companies, jobs, applications, interviews, and notes
7. Status-transition history and business rules
8. Query API: search, filters, sorting, and cursor/page pagination
9. Résumé upload, safe file handling, parsing, and evidence schema
10. Follow-up dates and reminder workflow
11. OpenAPI refinement, integration tests, and Stage 1 release checklist
