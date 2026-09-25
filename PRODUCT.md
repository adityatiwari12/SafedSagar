# Product

## Register

product

## Users

Five roles, one shared workspace shell:

- **AYUSH User** (entrepreneur/MSME persona) — practitioners, startups and cultivators tracking a product's IP, regulatory and ABS pathway from formulation through commercialization.
- **Researcher** (practitioner_researcher persona, same `user` role/permissions as above — differs in dashboard framing and intake questions, not access) — discovering prior art, spotting IP opportunities, and mapping TK/ABS considerations before a formal filing.
- **IP Facilitator** — triages the case queue, reviews AI assessments and citations, coordinates between users and experts.
- **Regulatory/IP Expert** — validates AI classification and regulatory compliance, closes or escalates cases with authoritative judgment.
- **Admin** (institutional_admin / ministry_admin / kb_manager tiers) — governs users, the source-document knowledge base, AI/RAG quality, and system-wide audit.

All work inside India's Ministry of AYUSH context; India and international jurisdictions are always kept visibly separate, never blended in one answer.

## Product Purpose

IP-SAKTI Sahayak is a multilingual, citation-grounded RAG assistant that helps Ayurveda practitioners, researchers, AYUSH startups/MSMEs and cultivators navigate intellectual property, biodiversity/ABS and regulatory questions. Every AI claim traces to a real, retrieved source document — statute, rule, treaty or judgment already in the ingested corpus — never an invented citation. Where AI confidence is low or the matter is complex, a human IP facilitator or regulatory expert takes over. Success looks like: a practitioner gets a sourced, defensible starting point in minutes instead of a blind guess, and knows exactly when to stop trusting the AI and ask a human.

## Brand Personality

Government-grade, editorial, authoritative — a professional intelligence workspace, not a chatbot wrapper. The public site reads like a serious institutional publication; the authenticated app is the same identity translated into a working tool. Confident but never overclaiming: AI output is framed as "potentially applicable" evidence for a human to weigh, never a legal determination.

Composition, not decoration: AI + Authoritative Evidence + Structured Workflow + Human Expertise + Actionable Guidance, visibly all present at once — never a full-bleed chat window that hides the other four.

## Anti-references

Explicitly avoid: generic SaaS templates, generic ChatGPT-style chat UI, excessive rounded cards, excessive shadows, glassmorphism, gradients (including gradient text), neon colors, excessive/decorative icons, side-stripe accent borders, identical repeated card grids, tiny uppercase tracked eyebrows above every section, numbered 01/02/03 section markers used as default scaffolding rather than a real sequence, and dense legacy-government-portal density (the opposite failure mode — cramped, cluttered, no whitespace).

No specific named reference sites were given; work from the design language below plus the GoI-portal conventions already committed in this codebase (GovTopBar, tricolor bar, State Emblem, `gov-btn-*`/`gov-input` classes).

## Design Principles

1. **AI is a component, not the whole interface.** Every AI answer shares visual weight with its evidence, confidence and next-step guidance — never a giant wall of chat text.
2. **One coherent shell.** Public site, AI workspace, Product Dossier, and every persona's workspace must read as the same product wearing different hats, never a different UI per section.
3. **Show reasoning, not just answers.** Confidence level and its stated reason, classification, jurisdiction and evidence are structural parts of every AI response, not optional collapsibles.
4. **Restraint over decoration.** Cards, borders, icons and shadows only where they carry real information; hierarchy comes from typography, spacing and color-as-signal, not ornament.
5. **Never overclaim.** "Potentially applicable," never "you should file." TKDL stays pointer-only, GRATK stays "signed, not in force," per CLAUDE.md's non-negotiable caveats — the UI must never visually imply more certainty than the backend actually has.

## Accessibility & Inclusion

WCAG 2.1 AA, GIGW/UX4G conventions (already a stated project requirement — see CLAUDE.md caveat #4). Full keyboard navigation, visible focus states on every interactive element, proper form labels, no color-only status signaling (confidence/status badges need a label or icon alongside color). Multilingual across 13 languages including RTL (Urdu) — layouts must not assume LTR-only text flow.
