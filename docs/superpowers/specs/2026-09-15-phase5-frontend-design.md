# Phase 5 — Frontend (React + TS) — Design

Status: approved by user 2026-09-15. Scope: full Section 7 core user journey UI.

## Context

`apps/web` does not exist yet. Only `apps/api/app/auth/*` (register/login/me, OAuth2
password flow, bearer JWT) is real. Phase 3 (LangGraph retrieval/citation) and Phase 4
(classifier/router nodes) and Phase 6 (escalation queue) are not built, so there is no
`/chat` or `/escalations` API to call yet. This spec builds the frontend in parallel
against a mock adapter so it isn't blocked on those phases, per the same pattern discussed
for Phase 3 vs Phase 2.

Out of scope this pass (unchanged from CLAUDE.md build order): full Bhashini multilingual
coverage (Phase 8, Hindi-only later), facilitator/admin working views (Phase 6), GIGW
accessibility audit pass (Phase 7 — this pass follows GIGW conventions but isn't the
dedicated polish pass).

## Stack

- Vite + React 18 + TypeScript + react-router-dom
- Tailwind CSS for styling
- Vitest + React Testing Library for component/unit tests
- No global state library (Redux/Zustand) — React Context (auth session) + a local
  `useChatSession` reducer hook cover the state needs. Adding a store library would be
  premature for this scope.

## Backend dependency handling — mock adapter

Define a `ChatApi` interface in `apps/web/src/api/chatApi.ts`:

```ts
export interface ChatApi {
  sendTurn(input: ChatTurnInput): Promise<ChatTurnResponse>
  escalate(conversationId: string): Promise<{ escalation_id: string }>
}
```

Two implementations:
- `mockChatApi.ts` — canned but realistic responses matching the LangGraph node
  pipeline's eventual output shape (classify → route_jurisdiction → route_ip_type →
  retrieve → rerank → reason_and_cite → validate_citations → score_confidence →
  escalate_if_needed). Deterministic fixtures keyed on keywords in the input text
  (e.g. "ashwagandha" → patent + India + medium confidence) so the UI is exercisable
  and demoable before Phase 3/4 land.
- `realChatApi.ts` — thin fetch wrapper hitting `/chat` and `/escalations`, written now
  but not exercised until those endpoints exist.

Selected via `VITE_USE_MOCK_CHAT` env var, default `true`. Swapping to real backend
later is a one-line env change, no component changes, because both implementations
satisfy the same `ChatApi` interface.

### Data contract

```ts
type ChatTurnResponse = {
  clarifying_questions?: string[]
  classification: { product_type: string; ip_type: string }
  jurisdiction: 'india' | 'international'
  answer: string
  citations: {
    doc_id: string
    title: string
    section_or_article?: string
    source_url?: string
    last_verified_date?: string
  }[]
  confidence: number // 0-1
  confidence_band: 'high' | 'medium' | 'low'
  escalate_recommended: boolean
}
```

Field names mirror the Postgres metadata model in CLAUDE.md (`doc_id`, `section_or_article`,
`source_url`, `last_verified_date`) so wiring the real API later requires no field
renaming on the frontend.

## Routing

- `/login`, `/register` — public
- `/` — chat, protected, default landing for `user` role
- Facilitator/admin roles land on a "Coming in Phase 6" placeholder page after login,
  not a 404 or generic error — the RBAC roles already exist in the `users` table.
- Unauthenticated access to `/` redirects to `/login`.

## Layout (GIGW-style, per CLAUDE.md caveat #4)

- Persistent strip in **both** header and footer: "SIH 2026 Prototype — Not an official
  Government of India website." Non-negotiable per project caveats.
- Header: app name/logo placeholder (no State Emblem, no AYUSH branding), jurisdiction
  toggle (India / International), language switcher (English active; हिंदी shown but
  disabled with a "coming soon" tooltip — Phase 8 territory, not this pass), user menu
  with logout.
- Breadcrumb nav row below header.
- Skip-to-content link, semantic landmarks (`<header>`, `<nav>`, `<main>`, `<footer>`),
  visible focus states, WCAG 2.1 AA contrast — baseline accessibility now, dedicated
  audit is Phase 7.

## Chat journey UI (PRD Section 7 flow, single screen)

Sequence: input box → clarifying-question follow-up turns (rendered as chat bubbles,
user answers inline, resends merged context) → classification/IP-type/jurisdiction
badges once resolved (jurisdiction badge is also the override toggle — changing it
re-sends the turn) → answer bubble with inline `[1][2]` citation markers → citation list
below the answer (doc_id, title, section/article, source URL, last-verified date) →
confidence badge (high/medium/low, color-coded; low confidence renders visible
abstention language, not just a lower number, per FR-07 safe-abstention intent) →
"next steps" bullet list → persistent "Talk to a human IP facilitator" escalate CTA,
visually emphasized when `escalate_recommended` is true. The escalate CTA calls
`ChatApi.escalate()` (mocked this pass).

## Components (apps/web/src)

```
src/
  api/
    chatApi.ts            — ChatApi interface + types
    mockChatApi.ts
    realChatApi.ts
    authApi.ts             — wraps existing /auth/register, /auth/login, /auth/me
  auth/
    AuthContext.tsx         — session state, token storage, login/logout/register
    RequireAuth.tsx         — route guard component
  chat/
    useChatSession.ts        — reducer: turns, clarifying-question state, jurisdiction override
    ChatPage.tsx
    MessageBubble.tsx
    ClarifyingQuestionForm.tsx
    ClassificationBadges.tsx
    CitationList.tsx
    ConfidenceBadge.tsx
    EscalateButton.tsx
  layout/
    AppShell.tsx             — header/footer/breadcrumb/skip-link
    PrototypeStrip.tsx
    LanguageSwitcher.tsx
    JurisdictionToggle.tsx
  pages/
    LoginPage.tsx
    RegisterPage.tsx
    RolePlaceholderPage.tsx  — facilitator/admin "coming in Phase 6"
  App.tsx, main.tsx
```

## Auth wiring (real, not mocked)

`authApi.ts` calls the existing FastAPI endpoints directly:
- `POST /auth/register` (email + password, min 8 / max 72 chars matching backend's
  bcrypt-bound validation)
- `POST /auth/login` (OAuth2 password form — `username`/`password` fields, not JSON)
- `GET /auth/me` for session restore on app load

Token stored in memory + `localStorage` (prototype-appropriate; httpOnly cookie flow is
out of scope for MVP). `AuthContext` attaches `Authorization: Bearer <token>` to all
authenticated requests via a shared fetch wrapper.

## Testing

Vitest + React Testing Library:
- Auth forms: validation, error display, successful login/register against a mocked
  fetch of the real auth contract
- `useChatSession` reducer: clarifying-question flow, jurisdiction override re-triggers
  a turn, escalate flag surfaces the CTA
- `CitationList` / `ConfidenceBadge` rendering from fixture data
- `RequireAuth` route guard: redirects unauthenticated, respects role for the
  placeholder page

No e2e (Playwright) this pass — deferred to when a real backend exists end-to-end.

## Error handling

- Network/API failure on chat turn: show inline retry, don't lose the user's typed
  question.
- 401 from any authenticated call: clear session, redirect to `/login`.
- No client-side validation duplicating server rules beyond what's needed for good UX
  (e.g. password length hint) — server remains the source of truth.
