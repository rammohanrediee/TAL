# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

TAL serves active job seekers across all experience levels, including people seeking internships. They need one trustworthy place to understand what their résumé actually supports, state what they want, find current opportunities, evaluate fit, and keep track of deliberate application decisions.

The primary user is authenticated and works with private résumé, preference, match, and application data. The product must remain useful to people with different levels of job-search experience without assuming that they understand résumé parsing, eligibility rules, semantic retrieval, or scoring systems.

## Product Purpose

TAL is an applied-AI job-search copilot. It turns a user-controlled résumé into a reviewed, provenance-backed evidence profile; combines that evidence with explicit candidate preferences and current jobs; and produces transparent, reproducible opportunity rankings and explanations.

The validation product succeeds when a user can complete the loop from account creation through résumé review, preferences, ranked fresh opportunities, explanation, and save/apply tracking without developer intervention. TAL may later produce truthful, ATS-friendly résumé versions that the user can review and download, while preserving the original résumé and every supporting source claim.

## Positioning

TAL is differentiated by an evidence-and-policy engine rather than an unrestricted chatbot. Every positive match claim must connect to verified résumé evidence, eligibility and scoring remain explicit and versioned, and identical versioned inputs produce identical ratings. The chatbot is an interface over typed, owner-aware product tools; it is not the source of truth.

TAL explains fit, gaps, conflicts, and unknowns without presenting a match rating as a hiring probability. It helps users apply truthfully and deliberately rather than maximizing application volume.

## Operating Context

Users work in a responsive web application with authenticated, owner-scoped data. The core workflow uses PDF or DOCX résumés, exact source passages, structured evidence claims, explicit job preferences, public job postings from configured sources, ranked results, and application states.

Résumé processing follows the backend-owned lifecycle `uploaded -> processing -> ready` or `failed`. Review requires users to compare extracted claims with immutable source quotations and correct interpretations without overwriting the original source. Job evaluation must expose source freshness, eligibility outcomes, requirement-to-evidence links, rating components, and meaningful unknowns.

## Capabilities and Constraints

Current product capabilities include authentication, owner-scoped application tracking, private PDF/DOCX upload and storage, source-text extraction with provenance, asynchronous résumé processing, structured evidence extraction, versioned skill normalization, and an owner-scoped evidence read/correction API. The frontend currently supports authentication awareness, résumé upload, and polling of processing states; its text-chat surface is presentational and is not connected to a conversation service.

The validation MVP must prioritize the secure loop of résumé evidence, candidate preferences, one reliable job source, requirement intelligence, deterministic evidence-backed matching, grounded explanations, and usable opportunity tracking. Mobile applications, broad job-source coverage, collaborative filtering, opaque engagement ranking, and unrestricted chatbot behavior are deferred.

Private access must always be scoped to the authenticated owner. Missing eligibility or preference information remains `unknown` and must not be guessed from résumé text. External job descriptions and webpages are untrusted data, never model instructions. Embeddings may retrieve candidate evidence but never determine the user-facing rating. Chatbot-triggered mutations require confirmation, and TAL does not automatically submit job applications.

Résumé generation and download are intended product behavior, but they are not supported by the current S1E7 API and must not be presented as operational until the required backend capability exists. Generated versions must remain evidence-grounded, user-approved, versioned, and exportable as ATS-readable PDF or DOCX without altering the original résumé.

Open product decisions include pricing, the initial beta cohort, retention periods, and the exact post-validation scope of tailoring and conversational tools.

## Brand Commitments

The product name is TAL. TAL presents itself as an evidence-led career workspace and applied-AI copilot, not a generic LLM wrapper. Its voice should be calm, direct, specific, and honest about uncertainty. Product language must distinguish verified evidence, adjacent evidence, unsupported claims, conflicts, and unknown information instead of collapsing them into opaque confidence or match language.

TAL must not copy another AI product's branding, proprietary assets, or interface. Existing visual decisions are implementation evidence rather than product truth and belong in a separate design record.

## Evidence on Hand

- `PROJECT_BLUEPRINT.md` — authoritative product behavior, safety boundaries, and ordered delivery sequence.
- `.omx/plans/mvp-action-plan.md` — four-month validation-MVP scope, acceptance criteria, and verification plan.
- `.omx/plans/project-season-tracker.md` — current milestone state; Season 1, Episode 7 is the active frontend evidence-review episode.
- `README.md` — repository overview, stack, local workflow, and public capability summary.
- `ARCHITECTURE.md` and `PRODUCTION.md` — system, deployment, privacy, security, reliability, and release constraints.
- `frontend/src/components/tal-workspace.tsx` and `frontend/src/app/globals.css` — current implemented web workflow and visual evidence.
- `TAL_SYSTEM_DESIGN.excalidraw` and `TAL_SYSTEM_DESIGN.png` — system-design artifacts.

No validated customer testimonials, production adoption metrics, hiring-outcome claims, pricing evidence, or public case studies are currently recorded. Future product and marketing work must not fabricate them.

## Product Principles

1. Evidence before assertion: every consequential positive claim must be traceable to verified source material.
2. Determinism before persuasion: eligibility, policies, and ratings remain explicit, versioned, reproducible application behavior.
3. User control before automation: preserve originals, require approval for mutations, and never submit applications automatically.
4. Product workflow before chatbot theater: conversation should reveal and operate trustworthy domain capabilities, not substitute for them.
5. Complete the secure validation loop before expanding breadth, autonomy, or platform coverage.

## Accessibility & Inclusion

The web experience must work responsively across desktop and mobile, preserve keyboard access and visible focus, provide accessible names and status announcements, respect reduced-motion preferences, and avoid communicating progress, confidence, or errors through color alone. Explanations should use plain language so users do not need technical knowledge of AI, retrieval, or scoring to make informed decisions.
