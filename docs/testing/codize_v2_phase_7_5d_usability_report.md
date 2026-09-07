# Phase 7.5D implementation report

## Recovered state

- Used only `C:/Users/purpl/Downloads/Codize/codize-v2-staging-fix` for repository edits.
- Branch: `ox/v2-beta-staging`.
- Starting local HEAD and read-only remote staging HEAD: `15ee953922dbbfba32ca9b230f8363678d0a870d`.
- The recovery check found a clean working tree and no surviving implementation edits. Continued from the established inspection findings.
- The dirty main worktree was inspected read-only and preserved.

## Direct-user feedback addressed

| Issue | Implementation | Verification |
| --- | --- | --- |
| Rushed wheel progression | Longer active act spans, wider eased fades, gradual fragment appearance | Native 120 px wheel increments, smaller increments, keyboard scrolling, intermediate screenshots |
| Twitchy interactions | Calmer V2 interaction timing and bounded landing CTA feedback | Intermediate/final computed transforms, live reduced-motion check |
| Abrupt text | Selective one-time later-act entrances; broader Scope text ranges | Browser visibility checks, no-JS rendering, reduced motion, semantic tests |
| Ambiguous hero decoration | Replaced overlapping ASCII cube/bracket with idea → framed player feature | Desktop/mobile rendered composition |
| Confusing first-change wording | Beginner-facing build/improve question plus consistent nearby copy | Rendered setup, invalid-field focus/error, both setup modes and unchanged payload in tests |
| Dense Learning | Moved both secondary paragraphs inside native disclosure | Collapsed/expanded screenshots, keyboard and browser accessibility tree |
| Project list crowding | Added 24 px above the list | Desktop/mobile measured gap, one/multiple project fixtures |
| Excess pixel word spacing | Display-role word spacing adjustment | Landing, Projects, Learning, Project Home and History inspection |

## Landing pacing

The short pinned distance magnified each wheel increment. At 1440×900, Scope previously mapped its full transition to 1,620 px; the focus-copy exit occupied only about 146 px and the lens fade about 162 px.

Exact adjustments:

| Span | Before | After |
| --- | --- | --- |
| Desktop capability act | 180svh | 220svh |
| Desktop Scope act | 280svh | 350svh |
| Desktop Scope active distance | 1,620 px | 2,250 px |
| Mobile capability act | 180svh | 190svh |
| Mobile Scope act | 210svh | 240svh |
| Mobile Scope active distance at 390×844 | 928.4 px | 1,181.6 px |

Scope's copy entrance now spans progress 0.02–0.24; focus-copy exit 0.44–0.64; lens fade 0.48–0.70; method organization 0.46–0.94; and detail entrance 0.72–0.98. The opacity transitions use smoothstep easing. At desktop size, the focus exit now occupies 450 px and the lens fade 495 px.

The same 120 px wheel increment advances desktop Scope about 5.3% instead of 7.4%. Intermediate browser captures show the recognizable feature holding before the method resolves; transitions are less abrupt and closer to the small-increment progression. The desktop page gains 110svh of active choreography, with no added acts or blank pinned sections. Mobile gains only 40svh across those acts.

Native scrolling, passive scroll handling, event-coalesced RAF, the bounded Canvas workload, the Scope Lens, the single peak, and Act 4 silence remain intact. Reduced motion and short viewports retain complete static posters without pinning. There is no wheel handler, scrolling framework, animation dependency, or idle animation loop.

## Landing entrances/interactions

Capability's heading/support line, Gap's heading, and Proof's heading/support line receive a finite 620 ms entrance from 25% opacity and 10 px below their resting position. Supporting lines use a modest 100 ms stagger. The H1 is immediate; Act 4 remains static. Entrances happen once on intersection and leave no persistent hidden state. Without JavaScript or motion enhancement, the HTML is visible; reduced motion suppresses the entrances.

Existing V2 hover interactions move from 150 ms to 220 ms with a gentler interaction easing, separate from stage entrances. Landing link accents transition over 240 ms; CTA arrows move only 2 px over 260 ms. Reduced motion removes that movement. No bounce, pulse, or additional startup sequence was introduced.

## Hero lower-right visual

Previously, a perspective ASCII box labeled `idea_`, scattered code fragments, and an oversized empty scope bracket overlapped. It suggested an idea entering a code/scope structure, but the relationship was visually unclear.

The replacement uses a short idea label, “A TEAM STAT TRACKER,” leading to one bracketed feature, “Add a player,” with small Name/Jersey field marks. It previews the same concrete feature used later in Scope. It remains a static decorative illustration, hidden from assistive technology and without interactive fields. No explanatory paragraph was added; the Typographic Poster layout remains.

## Project creation wording

| Location | Exact old wording | Exact new wording |
| --- | --- | --- |
| Initial idea option | “Shape the first useful change.” | “Pick a first feature to build.” |
| New-idea setup heading | “Shape your first useful change” | “Pick a first feature to build” |
| Setup question, both entry modes | “What’s the first change?” | “What do you want to build or improve first?” |
| Input placeholder | None | “For example, add a form for entering players” |
| Validation | “Fill in each field so your first change has a clear finish line.” | “Fill in each field so it’s clear what you want to build or improve and how you’ll check it.” |
| Draft Project Home follow-up | “Finish setup to shape your first change.” | “Finish setup to choose what to build or improve first.” |

“How will you know it’s done?” remains appropriate and unchanged. Internal change names, input names, IDs, payloads, draft saving, resumability, and state-machine behavior remain unchanged. Tests cover both new and existing project setup and the unchanged accepted submission arguments.

## Project spacing

The existing list now has a 24 px top margin. Browser checks measured the gap below “Start a project” at desktop and mobile widths and exercised one/multiple projects. The project-name grid track can shrink, and long names can wrap; this small related adjustment prevents long titles from defeating the responsive list layout. Other Project layout spacing is unchanged.

## Learning hierarchy

- **Collapsed:** habit name, existing status signal, description, and “Why this status.” Representative fixtures measure 165.5 px per desktop card and about 206.3 px per mobile card.
- **Expanded:** status explanation, how much help Codize currently provides, and all recent evidence with behavior, support explanation, project/change context, and date.
- **Hidden by default:** the formerly exposed status-explanation and support-direction paragraphs, alongside the existing evidence detail.
- **Accessibility:** native `details`/`summary`, browser accessibility-tree expanded state, Enter/Space toggling, a minimum 44 px control, and visible focus. Expansion preserves content order and focus; collapsing restores the original card heights. Cards align at the top so an adjacent card does not stretch with the expanded one.

The page introduction is shorter. The support-signal framing remains explicit; no scores, grades, categories, achievements, or badges were added. Evidence and backend-owned descriptors are preserved.

## Pixel-font typography

There was no explicit positive word-spacing rule. Press Start 2P's full character-width spaces produced the large gaps; letter spacing was already negative. Added `word-spacing: -0.22em` only to the landing hero/Scope display headings and signed-in page/Build headers. Existing letter spacing and letterforms remain unchanged. User-authored sans-serif headings explicitly retain normal word spacing. Small pixel labels and other font uses are unchanged.

Inspected the Landing hero, Projects heading, Learning heading, Project Home title, and History heading on desktop/mobile. No horizontal overflow was found; Learning and History headings read more naturally.

## Files changed

- `frontend/app/page.tsx`
- `frontend/components/landing/landing.module.css`
- `frontend/components/landing/storm-controller.ts`
- `frontend/components/landing/StormActs.tsx`
- `frontend/components/landing/ProductProof.tsx`
- `frontend/components/landing/Landing.test.tsx`
- `frontend/components/landing/storm-controller.test.ts`
- `frontend/app/app/projects/page.tsx`
- `frontend/app/app/project/[id]/page.tsx`
- `frontend/app/app/project/[id]/learning/page.tsx`
- `frontend/components/v2/V2ProjectSetupForm.tsx`
- `frontend/app/globals.css`
- `frontend/components/v2/Usability.test.tsx`
- `frontend/vitest.config.ts`
- This report.

The Vitest configuration enables the app's existing `@/` imports and automatic JSX runtime so behavioral tests can render the actual components. No package/dependency changes were needed.

## Tests

Commands run from the staging worktree's `frontend` directory unless noted:

```powershell
npm test -- components/v2/Usability.test.tsx components/landing/Landing.test.tsx components/landing/storm-controller.test.ts 'app/app/project/[id]/page.contract.test.ts' 'app/app/project/[id]/reflection.contract.test.ts'
npm test
npm run typecheck
npm run lint
npm run build
```

- Focused: **29 tests passed**, 5 files.
- Full frontend: **417 tests passed**, 52 files.
- Typecheck: **PASS**, exit 0.
- Lint: **PASS**, no ESLint warnings/errors. Next.js prints its existing `next lint` deprecation notice.
- Optimized production build: **PASS**, all 22 static pages generated, exit 0. This was a local build only.
- `git diff --check` from the worktree root: **PASS**, exit 0. Git's Windows line-ending notices are informational.

The initial new component-test run exposed missing Vitest alias support; the configuration above resolved it. No exact animation-duration assertions were added to the unit suite.

## Browser QA

**All listed outcomes PASS.** Final QA used the optimized local build at `http://127.0.0.1:3075`, served by `npm start -- --hostname 127.0.0.1 --port 3075`.

The local build used fixture-only public configuration:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8075'
$env:NEXT_PUBLIC_SUPABASE_URL='http://127.0.0.1:54321'
$env:NEXT_PUBLIC_SUPABASE_ANON_KEY='local-browser-fixture'
```

| Check | Result |
| --- | --- |
| Landing desktop, 1440×900 | PASS |
| Landing mobile, 390×844 | PASS |
| Normal 120 px native wheel progression | PASS |
| Small-increment scrolling and keyboard scrolling | PASS |
| Reduced motion, including live preference switching | PASS |
| Project desktop/mobile, setup, one/multiple and long titles | PASS |
| Learning desktop/mobile, collapsed/expanded details | PASS |
| Keyboard, focus, native accessibility-tree disclosure states | PASS |
| Console/hydration | PASS; zero console/page errors |
| Horizontal overflow | PASS |
| No-JavaScript semantic landing and auth CTA destinations | PASS |
| Additional 768 px / 1920 px landing and Learning checks | PASS |

The browser harness provided synthetic signed-in state and intercepted local API reads. All unexpected external requests were blocked; the final suite recorded none. It performed no server writes. Pointer lock/capture was disabled in the Playwright contexts.

Local evidence (outside the repository): `C:/Users/purpl/.codex/visualizations/phase75d/`. It contains `qa.cjs`, `results.json`, `slow.cjs`, and desktop/mobile screenshots of the hero, intermediate Scope wheel states, resolved method, static reduced-motion content, Project list/setup, Learning disclosures, and History. Commands:

```powershell
node C:/Users/purpl/.codex/visualizations/phase75d/qa.cjs
node C:/Users/purpl/.codex/visualizations/phase75d/slow.cjs
```

The dedicated agent-browser session also verified the final landing's semantic regions, headings, skip link, and four auth links, then closed. Playwright keyboard checks used PageDown, ArrowDown, Enter, and Space.

Scope of evidence: local Chromium with emulated viewport/motion settings and synthetic project data. This is not a physical-phone, real-trackpad, screen-reader listening, live authentication, or live backend integration test.

## Scope integrity and self-critique

The eight demonstrated friction points are addressed. The setup question asks for a recognizable feature/improvement; Learning can be scanned before opening evidence; native disclosure preserves agency; the wheel timeline gives the same choreography more room; entrances stay selective; hover responses remain bounded; the hero illustrates a concrete first piece; Project spacing is intentional; display words retain the pixel identity with less empty space.

The final visual pass added a small gap below Learning's expanded summary because its focus outline crowded the first paragraph. No other demonstrated issue required expansion of scope. Native expansion necessarily moves later content, but keeps focus in place and restores the original layout when closed.

No backend, schema, auth architecture, teaching policy, persistence, navigation, character progression, GitHub behavior, or Phase 11 work changed. No deployment or external-service tools were used.

## Commit

This report accompanies the single atomic commit `fix: refine pre-pilot usability and motion`. The completion response supplies its SHA.

## Remaining demonstrated issues

None within this pass's tested scope. Physical-device and live-service verification remain outside the local evidence described above.

## Production isolation

- Dirty main worktree untouched.
- No push.
- No deployment.
- No production changes.
- Production mutations: **ZERO**.

## Ready for focused Phase 7.5D review

**YES**, after the accompanying commit. Focused human review can use the saved captures and compare the wheel feel on an actual input device.
