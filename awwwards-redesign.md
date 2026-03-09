# Live System Dashboard: Redesign Plan

## Overview
A complete pivot to a highly technical, immersive "Live System Dashboard" experience for `kabhishek18.com` . Acting as a reflection of a Digital Architect's environment, the portfolio abandons standard web interfaces in favor of terminal logic, system logs, distributed module schemas, and real-time aesthetic behavior.

## Project Type
WEB

## Success Criteria
- [ ] Implement a fully functional "Theme Engine" driven by terminal-style commands (e.g., `system --theme light/dark`).
- [ ] Load projects dynamically using a "Module" distributed system schema rather than standard grid cards.
- [ ] Implement a Vercel/AWS-style "Deployment Timeline" for the career history.
- [ ] 100% exclusive use of Monospace-Variable typography (e.g., *JetBrains Mono*, *Fira Code*).
- [ ] 90+ Lighthouse Performance score across all metrics.
- [ ] Passing all automated script verifications (P0-P4).

## Deep Design Thinking & Commitment

### Context & Inspiration
- **Target Audience:** Highly technical peers, engineering leaders, and founders.
- **Soul/Vibe:** "The Operating System of a Digital Architect" - pristine, strictly grid-based, high-contrast, zero fluff.

### Design Hypothesis: The Technical Terminal Interface
- **Topology:** Strict 12-column terminal grid. Sections are not "pages" but rather "views" or "panels" divided by raw, 1px visible borders (using `zinc-800` or `zinc-200`). Continually visible "Agent Status" sidebar tracking scroll% and dummy bitrate metrics.
- **Geometry:** 0px border radius everywhere. Sharp, aggressive cuts to maintain the system UI feel.
- **Palette (Theme Engine):** 
  - *Carbon (Dark)*: Absolute Black (`#0a0a0a`) background, Bright Paper (`#f5f5f5`) text, Terminal Accent (e.g., Signal Orange or Terminal Green).
  - *Ivory (Light)*: Bright Paper (`#f5f5f5`) background, Absolute Black (`#0a0a0a`) text, High-Contrast Accent.
  - *Constraint*: Absolute ban on AI-cliché purples/indigos.
- **Typography:** Exclusive use of Monospace-Variable fonts to enforce the technical nature. No standard sans-serifs or serifs anywhere.
- **Interaction/Motion:** "Typewriter" caret/cursor entry effects for textual content. Scanline overlays applied to media/images. Commands (CLI inputs) replace standard interactive buttons.

## Tech Stack
- **Framework:** Next.js (App Router) / React
- **Styling:** Tailwind CSS (Custom rules, overriding default rounding/colors)
- **State/Theme Management:** Custom context or minimal Zustand store to handle the `system --theme` terminal command toggling (Carbon ↔ Ivory).
- **Animation:** Framer Motion (for typewriter sequencing, scanline looping, and structural panel shifts)
- **Data Layer:** Local dynamic schema mapping projects as data "modules" (JSON/TS structures).
- **UI Libraries:** 🚫 None (Custom CLI components exclusively).

## File Structure
```
/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   └── globals.css
├── components/
│   ├── ui/ (Custom primitives: CommandLine, TerminalPanel, SystemBorder)
│   ├── system/
│   │   ├── AgentStatus.tsx
│   │   ├── ThemeEngine.tsx
│   │   └── Shell.tsx
│   ├── modules/ (Project gallery)
│   └── timeline/ (Career history)
├── lib/
│   └── schemas/
│       └── projects.ts (Dynamic schema)
└── public/
    └── fonts/ (Monospace-Variable assets)
```

## Task Breakdown

### 1. The Terminal Protocol (Base Architecture & Theme Engine)
**Agent:** `frontend-specialist` | **Skills:** `tailwind-patterns`, `react-best-practices`
- **Input:** Next.js scaffolding.
- **Action:** Scaffold application with a global strict 12-column CSS grid. Implement the `ThemeEngine` context enabling the `system --theme [light/dark]` command toggle. Enforce `0px` border radiuses and a strictly Monospace-Variable font stack globally.
- **Output:** Base architecture ready, `Carbon` and `Ivory` themes functioning.
- **Verify:** `npm run dev` starts successfully; toggling between dark/light mode alters CSS variables flawlessly without hydration mismatch.

### 2. The OS Shell & Agent Status
**Agent:** `frontend-specialist` | **Skills:** `frontend-design`
- **Input:** Global Layout.
- **Action:** Implement the persistent 1px `zinc-800` border grid. Create the `AgentStatus` sidebar fixed to the right/left tracking simulated user inputs (scroll position %, bitrate). Provide an interactive CLI input at the top or bottom replacing a standard nav bar.
- **Output:** `Shell.tsx` and `AgentStatus.tsx`.
- **Verify:** Sidebar metric updates smoothly on scroll. Window looks like an OS panel.

### 3. Distributed Project Modules 
**Agent:** `frontend-specialist` | **Skills:** `frontend-design`, `react-best-practices`
- **Input:** Portfolio project data.
- **Action:** Build a `lib/schemas/projects.ts` dynamic data schema. Render these on the frontend not as cards, but as system "modules" or a directory tree. Use scanline image overlays for project thumbnails.
- **Output:** `ModulesGallery.tsx`.
- **Verify:** Data loads seamlessly; images feature the visual scanline effect natively.

### 4. Vercel/AWS Deployment Timeline (Career History)
**Agent:** `frontend-specialist` | **Skills:** `frontend-design`
- **Input:** Career experience history.
- **Action:** Build an experience timeline visually mirroring a CI/CD build log or Vercel deployment timeline (nodes, connecting structural lines, timestamps, success/warning states). Include typewriter reveal animations for the log texts.
- **Output:** `Timeline.tsx`.
- **Verify:** Timeline nodes connect cleanly without breaking at different viewport sizes.

## Phase X: Verification Checklist
- [ ] Run `npm run lint && npx tsc --noEmit`
- [ ] Run `python .agent/scripts/verify_all.py . --url http://localhost:3000`
- [ ] Rule Check: ZERO purple/violet hues anywhere in CSS.
- [ ] Rule Check: Font stack is EXCLUSIVELY Monospace.
- [ ] Rule Check: Command-line theme switching (`system --theme`) works perfectly.

## ✅ PHASE X COMPLETE
_To be marked as complete once all implementation and scripts succeed._
