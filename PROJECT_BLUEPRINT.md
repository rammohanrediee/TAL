# TAL Applied AI Job-Search Copilot — Project Blueprint

Technical boundaries and the production operating baseline are defined separately in
[`ARCHITECTURE.md`](ARCHITECTURE.md) and [`PRODUCTION.md`](PRODUCTION.md). This blueprint
remains the product behavior and ordered-delivery source of truth.

## Product statement

TAL is an Applied AI job-search copilot. A user uploads a résumé, confirms a
structured career profile, selects job preferences, and receives current jobs and
internships ranked against verified résumé evidence. TAL explains each rating in
simple English and can produce truthful, ATS-friendly résumé versions for roles the
user chooses.

The chatbot is the interface, not the source of truth. FastAPI owns the HTTP and
authorization boundaries, PostgreSQL stores user-owned and shared product data, and
typed domain services perform ingestion, matching, scoring, and mutations.

Honest product promise:

> TAL aggregates and normalizes jobs from configured public sources and company
> career portals, ranks them using a versioned evidence-and-preference score, and
> explains the result. A match rating is not a hiring probability.

MVP loop:

```text
Résumé upload
→ verified evidence profile
→ candidate preferences
→ fresh jobs and internships
→ requirement-to-evidence matching
→ ranked results
→ simple chatbot explanation
→ approved tailored résumé
```

## Core architecture decisions

- Begin as a modular monolith rather than premature microservices.
- Keep every private query scoped to the authenticated user.
- Store each public job once and rank it separately for each user.
- Collect and filter jobs with ordinary code before using an AI model.
- Calculate ratings with versioned deterministic code.
- Use AI for schema-constrained extraction, semantic evidence matching, clear
  explanations, and grounded rewriting.
- Treat résumés and confirmed user corrections as candidate evidence.
- Treat preferences as intent, never as proof of experience.
- Treat job descriptions and external webpages as untrusted data, never model
  instructions.
- Require confirmation before chatbot-triggered mutations.
- Never submit job applications automatically in the MVP.

## Stage 0 — Secure backend foundation

Finish the reusable ownership boundary before calling the backend stable:

- User registration, password authentication, JWT/cookie authentication, and Google
  OAuth
- User-owned application creation, listing, retrieval, and status updates
- Owner predicates inside database queries rather than client-supplied ownership
- Identical not-found behavior for absent and foreign-owned resources
- User-A/user-B isolation tests for every private access pattern
- PostgreSQL migrations, domain errors, OpenAPI documentation, and automated tests

Exit gate: cross-user application access is impossible, owner-scoped GET and status
updates work, and the focused backend suite is green.

## Stage 1 — Résumé ingestion and intelligence

Outcome: an authenticated user uploads a résumé and receives a reviewed, structured
evidence profile.

### Source-document lifecycle

```text
uploaded → processing → ready
                      ↘ failed
```

### Required capabilities

- Secure PDF/DOCX upload with extension, MIME, file-signature, and size validation
- Private original-file storage with a deletion path
- File metadata including owner, storage key, content type, size, and SHA-256 hash
- PDF/DOCX text extraction with page, paragraph, or section locations
- Detection of empty, corrupted, unsupported, and image-only documents
- Strict structured extraction for experience, projects, skills, achievements,
  education, certifications, dates, and metrics
- Evidence provenance linking every extracted claim to exact source text
- Skill and title normalization while preserving the original wording
- Confidence flags and a user correction/confirmation flow
- Immutable résumé versions rather than silent overwrites
- Golden extraction fixtures and regression tests

Exit gate: important profile claims can be traced to exact résumé text, ambiguous
claims can be corrected, and unsupported claims are not silently accepted.

### Post-MVP provenance enhancement

If precise in-document highlighting or deeper audit tooling later requires character
positions, add `start_offset` and `end_offset` relative to an immutable source-block
version. The backend must compute and validate those offsets from the already verified
verbatim source quote; model-supplied offsets are never authoritative. Source-block
identity, exact source text, and page/paragraph locations remain sufficient for the
validation MVP.

### Post-MVP hybrid extraction optimization

If extraction evaluations later show a meaningful cost, latency, or recall benefit,
add deterministic extraction alongside model extraction:

```text
Résumé source blocks
        ↓
Deterministic extraction + model extraction/enrichment
        ↓
Merge and deduplicate candidates
        ↓
Apply the same provenance and schema validation
```

Deterministic extractors may identify high-confidence facts covered by versioned
taxonomies or explicit patterns, such as canonical skill mentions. The model remains
useful for contextual experience, project impact, achievements, and ambiguous meaning.
Both routes must produce the same typed candidate contract, preserve their extractor
and taxonomy versions, and pass the same backend provenance checks before persistence.
Deterministically discovered claims never bypass validation. Introduce this hybrid
path only after representative evaluations demonstrate an improvement over the
single model-extraction path; it is not required for the validation MVP.

## Stage 2 — Candidate intent and eligibility preferences

Outcome: TAL knows what the user wants without confusing preferences with skills.

Capture and version:

- Target roles, job families, and title aliases
- Job, internship, or both
- Preferred seniority and acceptable stretch range
- Preferred and excluded locations
- Remote, hybrid, and onsite preferences
- Work authorization and sponsorship needs
- Graduation/enrollment status and internship availability
- Employment type and schedule
- Compensation floor when applicable
- Preferred industries, company stages, and excluded companies
- Must-have, nice-to-have, and avoid preferences

Missing information remains unknown. TAL must not guess work authorization, student
status, availability, or other eligibility facts.

Exit gate: TAL can apply hard eligibility rules without inventing missing user
constraints.

## Stage 3 — Opportunity supply through provider adapters

Outcome: TAL maintains a small, trustworthy set of current jobs and internships.

Follow the useful Career-Ops discovery pattern:

```text
Configured companies
→ ATS provider adapter
→ public HTTP/JSON listings
→ cheap filters
→ normalization and deduplication
→ liveness verification
→ shared job database
```

### Initial provider sequence

1. Implement a Greenhouse provider.
2. Prove ingestion with 3–5 configured companies.
3. Add Lever using the same provider contract.
4. Add Ashby after the contract is stable.
5. Add other legitimate sources only when they provide measurable coverage value.

### Career-Ops patterns to adopt

Use [Career-Ops](https://github.com/santifer/career-ops) as a reference for discovery
workflow ideas, not as TAL's production architecture. Copy and adapt these patterns:

- A configured company registry rather than an unrestricted crawl of the web
- One provider contract with Greenhouse, Lever, Ashby, and future implementations
- Structured public ATS feeds or JSON APIs as the first and cheapest extraction path
- A shared pipeline for normalization, deduplication, freshness, and liveness
- Human review and a clear boundary against automatic application submission
- Browser automation as a narrow fallback, not the default job collector

Process a user-provided job URL through the following ordered strategy:

```text
validate public URL and redirects
→ use a known ATS provider adapter when possible
→ otherwise fetch with bounded ordinary HTTP
→ extract JSON-LD or readable job-description HTML
→ use Playwright only when required content is JavaScript-rendered
→ clean and normalize untrusted text
→ extract schema-constrained requirements
→ apply deterministic eligibility and matching
```

The Playwright fallback must run asynchronously in an isolated worker, not inside the
FastAPI request process. It requires strict navigation, redirect, DNS/IP, time, response-size,
browser-memory, and concurrency limits. It must block private-network destinations, close
each browser context after use, and emit observable failure reasons. Cache a successful
public observation so multiple users do not render the same page independently.

Do not copy these behaviors into TAL:

- Playwright-first browsing for every job URL
- Unrestricted agent-controlled navigation
- Bypassing authentication, CAPTCHAs, access controls, or portal restrictions
- Sending an unvalidated URL directly to an AI model and trusting its response
- Letting AI invent eligibility facts or directly choose the final numeric rating
- Automatic form filling or application submission in the MVP

Playwright may later be reused in a separate rendering workflow for ATS-readable PDF
exports and in the test suite for browser-level end-to-end tests. Those uses remain
separate from the job-requirement extraction and scoring responsibilities.

TAL does not need credentials for every job portal. Prefer public ATS feeds and
approved company career pages. Do not bypass logins, CAPTCHAs, access controls, or
anti-bot protections. Restricted portals require an approved integration or are
skipped.

### Ingestion requirements

- Scheduled collection through idempotent background jobs
- Raw immutable source observations before normalization
- Canonical company, title, location, employment type, compensation, description,
  job URL, and application URL fields
- Deduplication by provider ID, canonical URL, and normalized company/role identity
- Published, first-seen, last-seen, and last-verified timestamps
- Freshness and liveness checks before expensive evaluation
- Source health, timeout, rate-limit, retry, and failure reporting
- Cheap title, location, work-mode, age, and explicit exclusion filters

Job ingestion is shared work. TAL stores a public job once; it does not scrape the
same posting separately for every user or search every portal during every chat turn.

Exit gate: repeated ingestion does not create duplicates, expired roles are not
recommended, and source failures are visible.

## Stage 4 — Requirement extraction, matching, and ranking

Outcome: every shortlisted job receives a reproducible rating and a grounded
explanation.

The matching engine requires both inputs:

```text
Structured résumé evidence
             +
Normalized job requirements
             ↓
Early eligibility filters
             ↓
Exact/canonical matching + embedding retrieval
             ↓
Candidate requirement-to-evidence links
             ↓
Matching rules and late eligibility checks
             ↓
Deterministic rating → explanation
```

### Core matching domain objects

TAL's matching core is built around three separate, first-class objects:

```text
JobRequirement ↔ RequirementMatch ↔ ResumeEvidence
```

`ResumeEvidence` is a verified candidate claim. It stores the owning résumé, evidence
type, extracted and corrected wording, confirmation status, confidence, normalized
skill identity when applicable, and provenance through an immutable source block and
verbatim source quote.

`JobRequirement` is a source-grounded requirement extracted from a normalized job. It
stores whether the requirement is required, preferred, or contextual; its category,
original wording and source location, canonical identity when applicable, explicit
constraints or importance, and extractor, taxonomy, and source versions.

`RequirementMatch` records an evaluation-specific relationship between one
`JobRequirement` and candidate `ResumeEvidence`. It stores the requirement and
evidence identifiers, match type, optional retrieval similarity, satisfaction state,
stable reason code, and matching-policy version. A positive direct, adjacent, or
satisfied match must reference verified evidence. Missing or unresolved requirements
may have no evidence identifier, but must retain their explicit state and reason.

These objects remain distinct: source records preserve truth, retrieval proposes
candidate relationships, and versioned matching policy decides satisfaction and score
contribution. Embeddings may index `ResumeEvidence` and `JobRequirement`, but never
replace either object or become the authority for `RequirementMatch`.

### Requirement extraction

- Extract required, preferred, and contextual requirements separately.
- Preserve the exact job-description text and source location.
- Normalize skills and aliases without creating experience.
- Capture explicit years, seniority, education, credentials, location, schedule,
  work authorization, and compensation constraints.
- Store extractor, prompt, model, taxonomy, and policy versions.

### Matching rules

- Split eligibility into early filters and late checks. Both phases run before numeric
  scoring, but only the early phase runs before semantic retrieval.
- Apply early filters using cheap, indexed, structured facts such as job liveness,
  employment type, strict location/work-mode exclusions, compensation floors, and
  explicit work-authorization or sponsorship conflicts. A preference is an early
  filter only when the user marked it as a strict constraint; otherwise it contributes
  to preference fit during scoring.
- Run exact and canonical skill matching before embedding retrieval. Use embeddings to
  retrieve the top candidate evidence for each remaining job requirement, never as the
  final judgment or numeric match percentage.
- Apply late eligibility checks when the decision depends on requirement-to-evidence
  alignment, including required credentials, education, minimum experience, must-have
  technical evidence, and domain experience.
- Represent every eligibility decision as allowed, blocked, or unknown with a stable
  reason code and the phase that produced it. Missing candidate or job information
  remains unknown and must continue through the pipeline rather than being silently
  filtered out.
- Do not calculate a numeric rating for an explicitly blocked job. Unknown checks may
  proceed to scoring, but the uncertainty must remain visible in results and
  explanations.
- Classify evidence as direct, adjacent, unsupported, or unknown.
- Link every positive match claim to verified résumé evidence.
- Do not convert adjacent experience into direct experience.
- Treat missing information as unknown, not automatically negative.
- Ensure exact skill identity; for example, Java must not match JavaScript.
- Store the inputs and scoring-policy version for reproducibility.

### Retrieval and scoring boundary

Embedding similarity is a retrieval signal, not TAL's match percentage:

```text
Requirement embedding
        ↓
Retrieve relevant verified evidence
        ↓
Classify the candidate link with versioned matching rules
        ↓
Calculate the deterministic rating from accepted links and policy weights
```

Store similarity with the candidate link for evaluation and debugging, but never
convert cosine similarity directly into a user-facing rating. The matching policy
decides whether retrieved evidence is direct, adjacent, unsupported, or unknown and
whether the requirement is satisfied, partial, missing, or unresolved. Only accepted,
provenance-backed links may contribute positively to the deterministic rating.

### Rating boundary

Normal code calculates the 0–100 rating from versioned components such as required
coverage, experience/project evidence, role-level fit, user-preference fit, domain
fit, and source freshness. AI may propose semantic links and explain the result, but
it must not invent or directly choose an unsupported rating.

Normal user response:

> **82% — Strong match**
>
> Your Python and backend experience fit this role well. The main missing area is
> Kubernetes. Recommendation: Apply.

Detailed evidence, gaps, confidence, and score components remain available when the
user asks why or opens the match details.

### User-provided job URLs

When a user provides a public job URL, TAL fetches and normalizes the posting, checks
its liveness, extracts its requirements, and runs the same matching pipeline. It does
not create a separate ungrounded chatbot-only rating path.

Exit gate: repeated evaluations are stable within defined tolerances, every positive
claim has evidence, and no hard eligibility conflict is hidden inside a high score.

## Stage 5 — Conversational interface

The chatbot is a small orchestrator over typed, owner-aware domain tools. It never
receives unrestricted database access and never fabricates job or rating data.

Initial tool surface:

- `get_profile_summary`
- `search_jobs`
- `analyze_job_url`
- `explain_job_match`
- `compare_resume_to_job`
- `list_applications`
- `update_application_status`
- `draft_resume_changes`

Read-only tools can execute directly. Mutations require explicit confirmation and
produce an audit record. Tool services derive ownership from authenticated server
context.

Exit gate: the chatbot cannot bypass ownership, invent ratings, follow instructions
embedded in job pages, or mutate user data without confirmation.

## Stage 6 — Evidence-grounded résumé tailoring

The tailoring engine must:

1. Select a source résumé version and target job.
2. Extract and prioritize required and preferred job terms.
3. Map every proposed résumé claim to verified evidence.
4. Show unsupported and unknown requirements before drafting.
5. Reorder and rewrite only supported résumé content.
6. Reuse job-description vocabulary only when the meaning remains accurate.
7. Refuse to add missing skills, employers, titles, dates, metrics, credentials, or
   achievements.
8. Show a section-level diff and explanation.
9. Require user approval.
10. Save a new immutable version and export an ATS-readable PDF/DOCX.

Exit gate: no unsupported claim reaches an export, the original résumé is preserved,
and the user controls every revision.

## Stage 7 — Production hardening and MVP release

Production work is introduced when its feature requires it and completed before the
MVP release:

- Redis and Celery workers for durable parsing, ingestion, and evaluation jobs
- Idempotency, bounded retries, timeouts, and exponential backoff
- Rate limiting and external-source health monitoring
- Structured logs, metrics, traces, readiness, and dependency checks
- PostgreSQL migrations and upgrade/downgrade smoke tests
- Encryption, private object storage, signed access, and secret management
- Backup, export, account deletion, and retention workflows
- Cost, latency, token-usage, and model-failure visibility
- GitHub Actions, dependency/container scanning, and staged deployment
- Load, concurrency, recovery, and failure-path testing
- Frontend loading, empty, failure, retry, and confirmation states

Exit gate: a real user completes résumé upload → verified profile → ranked live jobs →
chat explanation → approved tailored résumé in a deployed environment with recorded
quality metrics.

## Evaluation strategy

Maintain small, version-controlled golden cases for:

- Résumé text and expected structured evidence
- Job descriptions and expected required/preferred requirements
- Expected direct, adjacent, unsupported, and unknown mappings
- Hard-gate outcomes
- Pairwise job-ranking expectations
- Safe and forbidden résumé rewrites
- Adversarial job descriptions containing prompt-injection text

Measure extraction accuracy, requirement-classification accuracy, evidence-link
precision, ranking quality and repeatability, unsupported-claim rate, latency, cost,
and failure behavior. Compare model output against labeled expectations rather than
subjective impressions.

## Safety and product boundaries

- TAL never automatically submits applications in the MVP.
- TAL never claims a rating is the probability of being hired.
- TAL never guarantees that a résumé will pass an ATS.
- TAL never invents candidate experience or qualifications.
- External content cannot change TAL's instructions or trigger tools.
- Application links lead to the employer's official flow.
- Every private record is owner-scoped.
- Every external mutation requires user approval.
- Users can export and delete their private data.

Product promise: **find and evaluate relevant opportunities, explain the result, and
help the user apply truthfully—not apply everywhere automatically.**

## What the project demonstrates

- Applied AI system design rather than a single-prompt chatbot
- Schema-constrained résumé and job-requirement extraction
- Evidence retrieval, semantic matching, and grounded generation
- Deterministic scoring combined with AI explanations
- LLM tool calling with narrow authorization boundaries
- AI evaluation, regression testing, and prompt-injection resistance
- FastAPI, PostgreSQL, SQLAlchemy, Alembic, and REST API design
- Multi-user authentication, authorization, and privacy
- External-source adapters, ingestion, normalization, and deduplication
- Async workers, scheduling, retries, and idempotency
- Tests, CI/CD, containers, observability, and deletion workflows

## Ordered delivery sequence

1. Finish owner-scoped application GET and status update behavior.
2. Add user-A/user-B isolation tests and restore the backend suite to green.
3. Finish the `Resume` entity, migration, and model tests.
4. Add authenticated upload, validation, and private file storage.
5. Extract PDF/DOCX text with source locations.
6. Build structured, reviewable résumé evidence.
7. Capture and version candidate preferences.
8. Implement the Greenhouse provider for 3–5 companies.
9. Normalize, deduplicate, store, and verify job postings.
10. Extract structured job requirements.
11. Implement hard gates, evidence matching, and deterministic rating.
12. Return a rating with a simple English explanation.
13. Add controlled chatbot tools.
14. Add grounded résumé tailoring, diff, approval, and export.
15. Complete production hardening and release the end-to-end MVP.
