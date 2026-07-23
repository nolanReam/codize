# Bounded Assignment Practice Conventions

M18C.1 adds exactly one guided practice inside Prompt Builder. Its fixed
objective is `bounded_assignment_v1`, version `1`: define the finish condition,
excluded work, and observable inspection condition for the selected AI
assignment.

## Interaction and feedback

- Assignment selection comes first. Choosing an assignment does not prefill
  Prompt fields.
- The practice gives one short principle and one optional contrastive example.
  Guidance depth changes presentation only, never validation or required work.
- Feedback is transparent and deterministic: required presence, the documented
  800-character cap, safe characters, and secret-marker rejection. There is no
  semantic scoring, quality judgment, provider call, mastery state, or analytics.
- Applying is explicit. It replaces only Task and Don't touch with the student's
  own scope decisions, after confirmation if those fields contain different
  work. Context and every other Prompt input remain unchanged.
- Applied text remains editable. If the mapped fields diverge, the UI says the
  scope must be applied again before a new scoped save; it never silently
  overwrites edits.

## Persistence and compatibility

- `scope_practice` is stored inside the existing phase-scoped
  `prompt_builder` artifact. The client submits only the three student answers.
  The server derives objective id/version and the authoritative selected
  assignment id.
- A new assignment-bound Prompt requires complete scope. Existing
  assignment-bound Prompts that predate M18C.1 remain editable without
  retroactive blocking. Legacy unassigned Prompts remain unchanged.
- Once scope is stored it cannot be silently stripped. Assignment switching,
  Prompt history, sibling workflow artifacts, task completion, and Continue
  authority retain their existing seams.
- Scope drafts are local and separate from Prompt-field drafts, keyed by
  project, phase, assignment, objective id, and objective version. Both feed the
  existing one-dialog assignment-switch protection.

No migration, new route, provider call, lifecycle write, or task-completion
write belongs to this slice.
