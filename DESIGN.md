---
name: TAL Proof Workbench
description: A restrained, proof-led career workspace where every recommendation stays traceable to an exact source.
colors:
  proof-yellow: "#ffd400"
  proof-yellow-hover: "#e9c200"
  workspace-ink: "#141413"
  ink-secondary: "#4f4f4a"
  ink-muted: "#6e6e68"
  canvas: "#f5f5f2"
  surface: "#ffffff"
  surface-subtle: "#ecece8"
  border: "#d8d8d2"
  border-strong: "#a9a9a2"
  success: "#247b46"
  success-soft: "#e2f1e7"
  warning: "#785900"
  warning-soft: "#fff3c2"
  danger: "#a92f2f"
  danger-soft: "#f7e2e2"
typography:
  display:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "3.75rem"
    fontWeight: 900
    lineHeight: 1.02
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "3rem"
    fontWeight: 900
    lineHeight: 1.05
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.75
    letterSpacing: "0"
  label:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "0"
  meta:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0.01em"
rounded:
  brand: "9px"
  control: "10px"
  field: "12px"
  container: "14px"
  panel: "16px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
  section: "48px"
  page: "64px"
components:
  button-primary:
    backgroundColor: "{colors.proof-yellow}"
    textColor: "{colors.workspace-ink}"
    rounded: "{rounded.control}"
    padding: "12px 20px"
    height: "44px"
  button-dark:
    backgroundColor: "{colors.workspace-ink}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "12px 20px"
    height: "44px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.workspace-ink}"
    rounded: "{rounded.control}"
    padding: "12px 20px"
    height: "44px"
  chip-status:
    backgroundColor: "{colors.surface-subtle}"
    textColor: "{colors.ink-secondary}"
    rounded: "{rounded.pill}"
    padding: "5px 10px"
    height: "28px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.workspace-ink}"
    rounded: "{rounded.field}"
    padding: "12px 14px"
    height: "44px"
---

## Overview

TAL's creative north star is **The Proof Workbench**: a calm, editorial workspace where a job seeker can attach a résumé, watch TAL verify it, and inspect the exact evidence behind every claim. The interface should feel decisive and useful, not magical. Proof is the product; AI remains a quiet implementation detail.

The visual system combines oversized, confident type with a dense but orderly desktop workbench. Warm gray canvas, white working surfaces, near-black focus areas, and one unmistakable yellow create a recognizable TAL rhythm without copying another AI product's branding or interface. The canonical visual flow is also preserved in the TAL Penpot file: https://design.penpot.app/#/workspace?team-id=63bdc57a-636a-81ba-8008-841b52b079bc&file-id=63bdc57a-636a-81ba-8008-841baf3ecfd1&page-id=1c3e303a-d254-8049-8008-841ecb7d6f9e

Key characteristics:

- Proof-first: exact source text, provenance, conflicts, and uncertainty are visible before conclusions.
- Editorial hierarchy: large black headlines, short supporting copy, and compact evidence metadata.
- Restrained color: yellow marks the next action or current state; semantic colors communicate verification status.
- Flat workbench: borders, dividers, and tonal surfaces create structure without decorative depth.
- Progressive disclosure: Analyzing summaries stay compact and expandable; they never expose private chain-of-thought.
- Responsive by structure: desktop uses a 256px sidebar and broad evidence tables; mobile collapses navigation and stacks evidence fields without shrinking touch targets.
- Honest motion: only progress, state changes, and direct manipulation animate. Standard transitions use 180ms with cubic-bezier(0.16, 1, 0.3, 1); the working ring uses 900ms linear rotation; reduced-motion preferences receive near-instant state changes.

## Colors

**Proof First Rule.** Proof Yellow (#ffd400) is TAL's signature and the only default accent. Use it for the single primary action, the active work state, and small proof markers. Its hover state is Proof Yellow Hover (#e9c200). Never use yellow as decorative wallpaper, long-form text, or on multiple competing actions.

**Workbench Rule.** Workspace Ink (#141413) is used for the sidebar, focused analysis surfaces, primary text, and dark actions. Canvas (#f5f5f2), Surface (#ffffff), and Surface Subtle (#ecece8) form the neutral working environment. Ink Secondary (#4f4f4a) and Ink Muted (#6e6e68) support secondary copy and metadata. Border (#d8d8d2) and Border Strong (#a9a9a2) separate content without shadow.

**Semantic Evidence Rule.** Success (#247b46) with Success Soft (#e2f1e7) means verified. Warning (#785900) with Warning Soft (#fff3c2) means adjacent, incomplete, or needs review. Danger (#a92f2f) with Danger Soft (#f7e2e2) means conflict or unsupported. Always pair color with a label or icon; color alone cannot carry evidence meaning.

Aim for WCAG AA contrast for all normal text. On yellow, use Workspace Ink. On Workspace Ink, use Surface for body text and yellow only for focused accents.

## Typography

**One Family Rule.** Geist is the UI family. System sans-serif is the fallback. Geist Mono is reserved for technical identifiers, structured payloads, or developer-facing diagnostics; it is not a second decorative voice.

**Evidence Hierarchy Rule.** Display type is 3.75rem, weight 900, line-height 1.02, and -0.035em tracking on large screens. Headline type is 3rem, weight 900, line-height 1.05, and -0.03em tracking. Use these for one short statement per view, such as “Your résumé is ready to prove things.” Mobile may step down to 2.25rem for display and 1.875rem for headline while preserving the same visual hierarchy.

Titles use 1.5rem/800; body text uses 1rem/400 with a generous 1.75 line-height; labels use 0.875rem/700; metadata uses 0.75rem/600 with slight positive tracking. Keep body measure between roughly 52 and 72 characters. Sentence case is the default. Avoid all-caps UI labels except tiny technical status markers where scanning materially improves.

## Elevation

TAL is flat by default. Create hierarchy in this order: canvas change, surface change, border, divider, then spacing. Do not use gradients, glass effects, glowing edges, or floating card shadows in the core product.

The sidebar and Analyzing panel use Workspace Ink as intentional focus surfaces. White containers sit on the warm canvas with 1px Border; important containers use Border Strong when selected or editable. Dividers are preferred inside evidence lists so repeated proof rows read as one coherent record rather than a pile of cards.

Focus is visible and consistent: use a 2px Workspace Ink outline with a 3px offset on light surfaces, and a 2px Proof Yellow outline with a 3px offset on dark surfaces. Modal overlays, if introduced, may use a restrained neutral backdrop; the modal itself remains flat with a strong border.

## Components

**Brand mark.** A compact near-black TAL tile with a 9px radius. It is a product anchor, not an illustration. Keep it small and pair it with the TAL wordmark in navigation.

**Primary action.** Proof Yellow background, Workspace Ink text, 10px radius, minimum 44px height, and bold 0.875rem label. One primary action per region. Hover uses Proof Yellow Hover; pressed may translate by 1px only when reduced motion is not requested; disabled uses Surface Subtle and Ink Muted.

**Dark action.** Workspace Ink background, Surface text, 10px radius, and minimum 44px height. Use for committing an inline correction or another action occurring inside a light evidence surface. Do not place it beside a yellow action with equal prominence unless the user is at a true fork.

**Secondary action.** Surface background, Workspace Ink text, 1px Border, 10px radius, and minimum 44px height. Hover shifts to Surface Subtle and Border Strong. Text-only controls are reserved for low-risk, reversible actions.

**Navigation item.** The desktop sidebar is 256px wide and uses Workspace Ink. Active rows use a subtle white overlay and Proof Yellow text; inactive rows use softened white text. Every row is at least 48px high. Below 1024px, replace the sidebar with a compact header or drawer rather than compressing it.

**Upload composer.** A 16px-radius Workspace Ink panel with plain-language guidance, a yellow attach control, and one clear submission action. Accepted file types and limits are visible before upload. Upload status, retry, and removal are explicit. The first screen does not show analysis or evidence until the user attaches a résumé.

**Analyzing panel.** A collapsible Workspace Ink panel with a compact vertical status line. The collapsed label says “Analyzing” while work is active and changes to a factual completion summary when finished. Expanded content may show actions such as reading résumé sections, mapping requirements, checking proof sources, and flagging uncertainty. It must show truthful progress summaries and useful artifacts, never private chain-of-thought or invented internal reasoning.

**Status chip.** Fully rounded, 28px high, and paired with text. Neutral chips use Surface Subtle; verified, needs-review, and conflict states use their semantic soft backgrounds and dark semantic text. Keep chips short and do not turn every metadata value into a pill.

**Evidence list.** A single bordered container with divider-separated rows. Each row contains a numbered proof, the claim it supports, and an exact source quote or location. On desktop, use a stable multi-column grid; on mobile, stack claim, status, and source in reading order. “Review proofs” opens correction controls without losing the source context.

**Correction editor.** Appears inline beneath its evidence row. It has a persistent label, a strong-border field with a 12px radius, a dark save action, and a secondary cancel action. Validation errors sit beside the field and explain how to recover.

**Job match row.** Future typed tool output, not fabricated demo content. It must include a real job title, company, clickable canonical job URL, and a short “Why it suits you” explanation tied to verified proof. Adjacent and missing evidence remain visible. Never show a match score without an understandable basis.

**Loading, empty, and error states.** Skeletons mirror the final structure and use a restrained 1.4s shimmer. Empty states explain the next action. Errors name what failed, preserve user input, and offer retry. Never use a perpetual spinner to hide a failed request.

Template status:

- Implemented north-star templates: résumé attach/start, Analyzing, evidence review, and inline correction.
- Approved future templates: job results with canonical URLs and “Why it suits you,” job-to-proof comparison, saved/application views, and generated résumé preview/download.
- Future templates remain design references until matching backend capabilities exist. The UI must not imply live search, generation, or download before those APIs are available.

## Do's and Don'ts

Do:

- Lead with what the user's résumé can prove, not an opaque intelligence score.
- Show exact source text, source location, verification state, conflicts, and unknowns.
- Keep Analyzing collapsed by default after completion and let users inspect it on demand.
- Use one yellow primary action per region and preserve at least 44px touch targets.
- Keep labels outside fields, keyboard focus visible, and interactions usable without color alone.
- Preserve user input across retries and make corrections reversible.
- Use responsive structural changes at 640px, 768px, and 1024px rather than proportionally shrinking the desktop UI.
- Keep recommendations calm, direct, specific, and honest about uncertainty.

Don't:

- Present TAL as a generic chatbot, an LLM wrapper, or a résumé “intelligence” dashboard.
- Copy ChatGPT, Claude, ChaTin, Elysium, or any other product's branding, proprietary assets, or distinctive interface.
- Reveal or simulate private chain-of-thought; show concise progress summaries and evidence artifacts instead.
- Fabricate job URLs, match scores, metrics, testimonials, résumé changes, or download capability.
- Hide unsupported claims behind confidence badges or decorative analytics.
- Use gradients, glassmorphism, glow, excessive shadows, oversized rounding, or a card around every sentence.
- Use yellow decoratively or allow multiple yellow calls to action to compete.
- Remove provenance when condensing content for mobile.
