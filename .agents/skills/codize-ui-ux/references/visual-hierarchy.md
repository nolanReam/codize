# Visual Hierarchy

## Start hierarchy from the task

- **Principle:** Make the current goal, state, and next action form the first scan path.
- **Why:** New users otherwise inspect every element to decide where to begin.
- **Use:** Dashboards, workflow pages, prerequisites, and state transitions.
- **Do not use:** Do not visually suppress warnings, uncertainty, or required status merely to simplify the page.
- **Anti-pattern:** Every card, badge, heading, and button has equal contrast.
- **Codize:** Use at most one `.card.primary` and one obvious `.btn.primary` for the current state. Keep the accent left rail; do not restore full violet outlines or resting glow.
- **Source:** `[P1, P2; S1 00:24–03:19; S4 01:26–02:17; A2, A6]`

## Group by relationship, not by box count

- **Principle:** Use proximity, alignment, whitespace, and quiet separators before adding containers.
- **Why:** Strong groups reduce the area a user must search.
- **Use:** Related fields, workflow steps, target lists, metadata, and action groups.
- **Do not use:** Keep a boundary when it carries state, focus, ownership, or safety meaning.
- **Anti-pattern:** Nested cards, a border around every row, or unrelated controls sharing one visual group.
- **Codize:** Keep Change Map and linked Review items as rows within one primary surface; use quiet rules between categories. Keep `details.help` and Build Loop steps border-light.
- **Source:** `[S1 02:06–03:19; S4 04:25–05:09; S7 29:41–30:49, 36:02–36:33; A2–A6]`

## Reserve emphasis

- **Principle:** Spend scale, contrast, accent color, and weight on a small number of meaningful elements.
- **Why:** When everything calls for attention, nothing does.
- **Use:** Primary action, active workflow step, important status, generated-prompt payoff.
- **Do not use:** Do not turn decorative or secondary actions into competing focal points.
- **Anti-pattern:** Multiple primary buttons, rainbow semantic buttons, oversized headings, excessive pills, or ambient glow.
- **Codize:** Violet marks action/current state; green means recorded success; amber means attention, stale, cooldown, or uncertainty; red is for genuine error or honestly recorded failure.
- **Source:** `[S4 00:35–04:22; S6 01:15–03:08, 11:58–13:44; S7 31:00–32:27; A2, A6]`

## Keep typography and spacing deliberate

- **Principle:** Use the existing type and spacing scales; preserve readable measures and scan lines.
- **Why:** Random sizes, weights, and gaps create noise and break perceived relationships.
- **Use:** All protected-app and landing work.
- **Do not use:** Do not force a numeric grid when content, focus targets, or readability needs a deliberate exception.
- **Anti-pattern:** A new font for one page, many nearly identical text sizes, long full-width prose, or arbitrary gaps.
- **Codize:** Reuse DM Sans, Space Grotesk, IBM Plex Mono, `page-title`, `page-sub` (max 62ch), and existing CSS variables. Use mono only for code-like or technical text.
- **Source:** `[S6 03:08–04:28, 13:00–13:44; S7 14:58–20:52, 28:13–28:47; A2, A6]`

## Use objective critique language

- **Principle:** Explain hierarchy with primary/secondary/tertiary, dominant/subdued, weight/distribution, proximity, and contrast.
- **Why:** Objective vocabulary separates usability evidence from taste.
- **Use:** Design reviews and audits.
- **Do not use:** Do not present subjective preference as a confirmed defect.
- **Anti-pattern:** “This feels bad” without naming the relationship or user impact.
- **Codize:** Tie every visual finding to the user's scan, decision, state comprehension, or task completion.
- **Source:** `[S4 00:00–05:36]`

## Make motion earn its place

- **Principle:** Use motion to explain state change, continuity, or revealed content.
- **Why:** Purposeful motion can confirm cause and effect; decorative motion can obstruct task focus.
- **Use:** Short disclosure reveals, button press feedback, generated-output entrance, and public narrative scenes.
- **Do not use:** Avoid ambient or looping protected-app animation, scroll-jacking, and motion needed to understand content.
- **Anti-pattern:** Animation added because the surface looks static.
- **Codize:** Respect the global reduced-motion switch. Protected-app motion stays brief and transform/opacity-based. Landing motion must have a complete static/no-JS state.
- **Source:** `[S5 03:32–04:28; S6 13:50–15:31; A2, A6]`
