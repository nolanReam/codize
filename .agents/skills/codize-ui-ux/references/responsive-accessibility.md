# Responsive Accessibility

> Accessibility principles are durable. V1 component/class examples below do not define V2 architecture or visual composition.

## Use semantic controls first

- **Principle:** Start with native elements matching the interaction: button, link, fieldset/legend, radio, checkbox, label, details/summary, progressbar, status, and alert.
- **Why:** Native semantics provide keyboard and assistive-technology behavior that styled containers do not.
- **Use:** Every interactive surface.
- **Do not use:** Do not replace semantics merely to achieve a visual treatment.
- **Anti-pattern:** Clickable `div`, custom radio cards without inputs, hover-only information, or a label detached from its field.
- **Codize:** Follow current semantic chip, decision picker, disclosure, progress, notice, and navigation patterns. Keep one page `h1` and ordered heading levels.
- **Source:** `[authority 1; A2–A6]`

## Keep focus, feedback, and names visible

- **Principle:** Every interactive element needs an accessible name, visible focus, and understandable state.
- **Why:** Keyboard users must locate and predict the active control.
- **Use:** Buttons, links, radios, checkboxes, disclosures, fields, and custom-styled controls.
- **Do not use:** Do not remove outlines without an equivalent or rely on color alone.
- **Anti-pattern:** Focus ring clipped by a card, unlabeled icon action, or disabled button with no explanation.
- **Codize:** Reuse the two-pixel outline and input ring. Wire errors with `aria-invalid`/`aria-describedby`; announce loading, save, generation, confirmation, and completion changes with restrained live regions.
- **Source:** `[S3 01:06–01:36; S7 09:09–10:18; A2, A5, A6]`

## Design responsive states, not just smaller boxes

- **Principle:** Re-evaluate order, width, density, and action placement at each breakpoint.
- **Why:** A desktop hierarchy can collapse into an incoherent mobile sequence.
- **Use:** Every new or substantially changed page.
- **Do not use:** Do not hide required state or primary actions to make the layout fit.
- **Anti-pattern:** Horizontal overflow, two-column forms squeezed onto mobile, tiny decision targets, or a wide empty desktop canvas.
- **Codize:** Verify approximately 390px, tablet, 1080p, and 1920px. Expect the workspace rail to collapse near 1150px and shell near 840px; stack decision controls/actions by roughly 640px when needed. Use wide space for meaningful rail/context while keeping text readable.
- **Source:** `[P1; S5 01:27–02:09; A2, A3, A5, A6]`

## Test hostile content

- **Principle:** Test with long and malformed-but-valid user content, not only ideal fixtures.
- **Why:** Real paths, code, errors, and explanations expose overflow and hierarchy failures.
- **Use:** Lists, cards, tables, source snapshots, excerpts, pills, buttons, and status copy.
- **Do not use:** Do not silently truncate editable or evidentiary content unless the contract explicitly requires it.
- **Anti-pattern:** File paths overflow the viewport, button labels clip, or source text is rendered as HTML.
- **Codize:** Wrap paths and prose anywhere when necessary; bound code/excerpts with scroll; render untrusted material as plain React text; keep counters and over-limit errors explicit.
- **Source:** `[S5 02:43–03:30; A3–A6]`

## Respect motion and sensory differences

- **Principle:** Content and control must remain complete without animation, hover, fine pointer, or color perception.
- **Why:** Motion, hover dependence, and color-only meaning can exclude users or obscure state.
- **Use:** Landing scenes, transitions, status, and interactive polish.
- **Do not use:** Never make scroll position or animation the only way to reveal required content.
- **Anti-pattern:** Color-only stale state, hover-only guidance, or reduced-motion users seeing an empty sticky scene.
- **Codize:** Honor `prefers-reduced-motion`; provide finished static landing frames; use explicit status words/icons with color; preserve tap and keyboard paths.
- **Source:** `[S5 03:32–04:28; A2, A3, A5, A6]`

## Browser verification checklist

At each target width:

1. Traverse the primary journey using keyboard only.
2. Check focus order, visibility, modal/disclosure behavior, and return focus where applicable.
3. Inspect headings, landmarks, labels, progress names, alerts, and live updates.
4. Test zoom, long content, empty/error/stale states, and reduced motion.
5. Confirm no horizontal overflow and no essential content hidden by sticky regions.
6. Confirm disabled and destructive actions explain how to proceed.
