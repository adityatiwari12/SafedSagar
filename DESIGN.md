---
name: IP-SAKTI Sahayak
description: Citation-grounded Ayurveda IP/regulatory intelligence workspace for the Ministry of AYUSH
colors:
  saffron: "#FF671F"
  saffron-soft: "#FF9933"
  saffron-deep: "#D35400"
  forest: "#0A3D2E"
  forest-mid: "#0F5C45"
  forest-leaf: "#1A7A58"
  navy: "#0B1F3A"
  ivory: "#F7F3EA"
  ivory-deep: "#EDE6D6"
  gold: "#B08D57"
  gold-soft: "#E2D0A8"
  ink: "#1C2421"
  ink-muted: "#4A5550"
  ink-faint: "#6E7873"
  surface-border: "#DDD5C4"
  india-green: "#138808"
typography:
  display:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "clamp(3rem, 7vw, 5.5rem)"
    fontWeight: 800
    lineHeight: 0.95
    letterSpacing: "normal"
  headline:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "clamp(2rem, 4vw, 3.75rem)"
    fontWeight: 700
    lineHeight: 1.05
  body:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 700
rounded:
  none: "0px"
  hairline: "2px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.saffron}"
    textColor: "#FFFFFF"
    rounded: "{rounded.hairline}"
    padding: "0.85rem 1.35rem"
  button-primary-hover:
    backgroundColor: "{colors.saffron-deep}"
  button-secondary:
    backgroundColor: "#FFFFFF"
    textColor: "{colors.ink}"
    rounded: "{rounded.hairline}"
    padding: "0.85rem 1.35rem"
  button-secondary-hover:
    backgroundColor: "{colors.ivory}"
  input-default:
    backgroundColor: "#FFFFFF"
    textColor: "{colors.ink}"
    rounded: "{rounded.hairline}"
    padding: "0.75rem 1rem"
---

# Design System: IP-SAKTI Sahayak

## 1. Overview

**Creative North Star: "The Gazette Ledger"**

IP-SAKTI reads like an official gazette crossed with a working case ledger: every claim is dated, sourced and attributable, and every page carries the quiet authority of a document that will be cited later, not scrolled past. The system is flat, bordered and typographically confident rather than soft, shadowed and card-heavy - depth comes from hairline borders, generous whitespace and a saffron-on-ivory-and-navy palette lifted directly from the Government of India's own visual grammar, never from blur or elevation tricks. It rejects the two failure modes equally: it must never read as a generic SaaS chat product (rounded bubbles, gradient hero, glassmorphism), and it must never read as a dense, cluttered legacy portal either - GIGW conventions without GIGW's visual noise.

The authenticated workspace and the public site are the same ledger, opened to different pages: same top bar, same emblem, same disclaimer strip, same button and input vocabulary throughout. Nothing in the app should look like it belongs to a different product than the marketing site.

**Key Characteristics:**
- Flat and bordered, never shadowed: 2px radius everywhere, 1px hairline borders as the primary depth cue
- Saffron is a signal, not a wash: reserved for primary actions and active/pending status, never a background fill
- Forest green and navy carry institutional weight (headers, footers, primary text-on-dark); saffron carries momentum (CTAs, in-progress states)
- Bold, high-contrast typography does the hierarchy work columns and cards would otherwise do
- Every AI claim sits next to its evidence - the layout has no path for an unsourced assertion to stand alone

## 2. Colors

A tricolor-anchored, low-saturation palette: two institutional darks (forest, navy), one warm neutral field (ivory), and a single saffron accent held in reserve for action and momentum.

### Primary
- **Saffron** (#FF671F): the one accent. Primary buttons, active nav state, focus rings, in-progress/pending status. Used on a small minority of any given screen - its rarity is what makes it read as "act here."
- **Saffron Deep** (#D35400): hover/pressed state for saffron elements. Never a second accent color in its own right.

### Secondary
- **Forest** (#0A3D2E): the institutional anchor. Primary footer background, dark-surface text-on-color, the color the emblem inverts against.
- **Forest Mid / Leaf** (#0F5C45 / #1A7A58): secondary dark-surface tints, hover states on forest backgrounds, success/resolved status.

### Tertiary
- **Navy** (#0B1F3A): the Government-of-India utility bar and deep headline color on light surfaces. Distinct from Forest - Navy is "this is government," Forest is "this is IP-SAKTI."
- **Gold / Gold Soft** (#B08D57 / #E2D0A8): sparing ceremonial accent - citation/evidence markers, official-document flourishes. Not a general-purpose second accent.

### Neutral
- **Ivory** (#F7F3EA): the default page/body background - a warm paper tone, not stark white, evoking a printed gazette.
- **Ivory Deep** (#EDE6D6): secondary surface tint for subtle section separation.
- **Ink** (#1C2421): primary text color. **Ink Muted** (#4A5550) for secondary text, **Ink Faint** (#6E7873) for metadata/timestamps - never lighter than that; body text at low contrast is not "elegant," it's a defect.
- **Surface Border** (#DDD5C4): the one border color used everywhere. All hairline borders, all dividers, all input outlines share this single value.
- **India Green** (#138808): reserved for the tricolor bar itself and explicit "this is the Government of India tricolor" moments. Not a general success color (Forest Leaf owns that).

### Named Rules
**The One Accent Rule.** Saffron is the only color that means "act here" or "this is active." If a screen has more than one saffron element competing for attention, one of them is wrong.

**The No-Wash Rule.** Never use saffron, forest, or navy as a full-bleed section background on an app screen. They anchor bars, borders, buttons and badges - never wallpaper.

## 3. Typography

**Display Font:** Noto Sans (with system-ui, sans-serif fallback)
**Body Font:** Noto Sans (same family, weight contrast carries hierarchy)
**Regional scripts:** Noto Sans Devanagari / Bengali / Tamil / Telugu / Gujarati / Kannada / Malayalam / Gurmukhi / Oriya / Arabic - loaded per active language, never a fallback-only rendering for non-Latin scripts.

**Character:** One typeface family used with real weight and size contrast (400/700/800) rather than a decorative display face - this is a document product, not a brand-marketing one, so the type stays legible and institutional at every size instead of reaching for editorial flourish through a second serif family.

### Hierarchy
- **Display** (800, `clamp(3rem, 7vw, 5.5rem)`, line-height 0.95): landing-page hero headline only.
- **Headline** (700, `clamp(2rem, 4vw, 3.75rem)`, line-height 1.05): section headers on the public site, page titles like Product Dossier's product name.
- **Title** (700, 1.125-1.25rem): panel/card headers, PageHeader `h1` in the app shell.
- **Body** (400, 1rem, line-height 1.6, max 65-75ch): all reading text - answers, descriptions, evidence snippets.
- **Label** (700, 0.875rem): form labels, badge text, the 11px uppercase-tracked micro-labels already used for section eyebrows in AnswerPanel (`chat.sectionAnswer` etc.) - the one sanctioned uppercase-label use, kept small and functional, never a decorative section kicker.

### Named Rules
**The Weight-Not-Family Rule.** Hierarchy comes from font-weight and size steps within Noto Sans, not from introducing a second typeface. A serif display face would read as borrowed brand marketing, not institutional authority.

## 4. Elevation

Flat by default. This system uses borders and background-tint layering, not shadows, to separate surfaces - a direct rejection of the SaaS card-with-drop-shadow pattern. The two shadow tokens that exist in the codebase (`panel`, `lift`, `float` in `tailwind.config.js`) are real but rare: reserved for genuinely floating elements (an open mobile nav drawer, a dropdown) where a border alone can't communicate "this is above the page," never for resting cards or panels.

### Shadow Vocabulary
- **panel** (`0 1px 0 rgba(28,36,33,0.06)`): a near-invisible hairline lift, for a sticky header separating from scrolled content beneath it.
- **float** (`0 12px 32px rgba(10,61,46,0.14)`): open dropdowns, popovers, the mobile nav drawer.
- **lift** (`0 24px 60px rgba(10,61,46,0.22)`): reserved for a true modal/dialog surface, used sparingly.

### Named Rules
**The Flat-At-Rest Rule.** A card, panel or table row never has a shadow at rest. Shadows appear only on elements that are genuinely floating above the page's own stacking layer (dropdown, drawer, modal) - never as decoration on static content.

## 5. Components

### Buttons
- **Shape:** 2px radius (`.gov-btn-*` classes) - functionally square, never pill-shaped.
- **Primary:** saffron background (#FF671F), white text, bold (700) 0.9375rem label, `0.85rem 1.35rem` padding, no border.
- **Hover:** background darkens to Saffron Deep (#D35400); no scale/lift transform - state changes through color only, consistent with the Flat-At-Rest rule.
- **Secondary:** white background, ink text, 1px `surface-border` outline; hover fills to Ivory.
- **Outline-light:** transparent background, white text/border at 80% opacity - for use on dark (forest/navy) surfaces only.
- **Danger:** white background, `#991b1b` text, `#b91c1c` border - reserved for destructive confirmations (delete product, discard case).
- **Disabled:** 50% opacity, `cursor: not-allowed`, no color change.

### Chips / Status Badges
- **Style:** small, bold, uppercase, 2px-radius bordered pill (`StatusBadge` in `ui/primitives.tsx`) - background/text/border all shift together per status (open=red, in_progress=amber, resolved=green, draft=neutral). Never color-only: the label text always states the status in words alongside the color.
- **Confidence badges** are a status-badge variant with a mandatory one-line "why" underneath - confidence is never shown as a bare color chip.

### Cards / Panels
- **Corner style:** 2px radius, matching buttons/inputs exactly - one radius value across the entire system.
- **Background:** white on an ivory page, or ivory-tinted on a white page - always a one-step contrast from its parent, never a shadow-implied "floating" card.
- **Border:** 1px `surface-border` (#DDD5C4) on all four sides - the system's only border color, used everywhere so nothing needs its own bespoke border treatment.
- **Internal padding:** 1rem (16px) standard, 1.25-1.5rem for a page-level panel.
- **Evidence cards** (`EvidenceCard` in `ui/primitives.tsx`) are the one place a left accent exists, and it is a full 2px saffron border-left on a tinted ivory background - a citation marker, not a decorative stripe; it appears only here, never generalized to ordinary content cards.

### Inputs / Fields
- **Style:** 2px radius, 1px `surface-border` outline, white background, `0.75rem 1rem` padding.
- **Focus:** border shifts to saffron; `:focus-visible` additionally gets a 3px saffron outline ring at 2px offset - the outline ring, not a glow/shadow, is the accessibility-driving focus treatment.
- **Labels:** bold 0.875rem, positioned above the field, always present (never placeholder-as-label).

### Navigation
- **Top bar:** navy Government-of-India utility strip (language links, ministry name) sits above everything, always present, never collapsible.
- **Tricolor bar:** 3px saffron/white/india-green strip directly under the top bar - a fixed brand anchor, not decorative chrome that can be dropped on any page.
- **Sidebar (authenticated shell):** white background, 1px right border, role-grouped nav items in labeled sections; active item gets a solid Forest-green fill with white text (not a saffron highlight - saffron stays reserved for direct actions, not "where am I").
- **Breadcrumb:** plain text in a tinted (`#f0f4f8`) strip beneath the header, no chevron icons, no decorative separators beyond a plain string join.

### State Emblem + Disclaimer (signature pairing)
The State Emblem of India renders in every header/footer as a real, non-decorative mark of context - and by the same rule (CLAUDE.md caveat #4), the "SIH 2026 Prototype - not an official Government of India website" strip must render in the same footer every time the emblem appears. Treat this pairing as one atomic unit when building any new shell or page: never place one without the other.

## 6. Do's and Don'ts

### Do:
- **Do** use 2px radius everywhere a radius is needed - buttons, inputs, cards, badges. One value, no exceptions.
- **Do** use hairline (1px) `surface-border` (#DDD5C4) as the only border color in the system.
- **Do** keep saffron to primary actions and active/pending status only - if you're reaching for saffron a third time on one screen, use forest or a neutral instead.
- **Do** pair every AI claim with a citation via `EvidenceCard`/`EvidenceList` - no floating assertions.
- **Do** state confidence in words plus color, always with a one-line reason.
- **Do** keep the State Emblem and the "not an official GoI website" disclaimer strip together, every time either appears.
- **Do** use `text-wrap: balance` on headlines and cap body measure at 65-75ch.

### Don't:
- **Don't** use generic SaaS templates, generic ChatGPT-style chat UI, or a full-bleed chat window that crowds out evidence/workflow/expert context.
- **Don't** use excessive rounded corners, excessive shadows, glassmorphism, gradients (including gradient text), or neon colors - this system is flat, bordered and matte.
- **Don't** use decorative icons that don't carry information; don't ice every list item with an icon by default.
- **Don't** use a colored `border-left`/`border-right` as a decorative accent stripe anywhere except the one sanctioned `EvidenceCard` citation marker.
- **Don't** repeat identical same-sized card grids as a default layout - vary composition, use tables/lists where the content is actually tabular.
- **Don't** add a tiny uppercase tracked eyebrow above every section, or numbered 01/02/03 markers unless the content is a genuine, ordered sequence (the Ask workspace's journey stepper is the one legitimate numbered sequence in the system - don't add a second one elsewhere).
- **Don't** let the authenticated app diverge visually from the public site - same top bar language, same button/input vocabulary, same color roles, everywhere.
- **Don't** phrase AI output with more certainty than the backend has: "potentially applicable," never "you should file"; TKDL stays pointer-only language, GRATK stays "signed, not in force."
- **Don't** rely on color alone for status - every status badge carries its label in words.
- **Don't** let the legacy-portal failure creep in either: dense, cramped, dividers-around-everything. Use whitespace and typography for hierarchy before reaching for a border.
