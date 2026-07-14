# The master spec is a Markdown file, not a PDF

`docs/context/codize_master_spec_v2.1.md` contains the still-applicable architecture and safety invariants. The active product direction is `docs/context/codize_product_operating_brief_v2.md`. Older references may point to `codize_master_spec_v2.1.pdf`, which does not exist.

Why it matters: a session that trusts the `.pdf` path will conclude the spec is missing. The local `conversations.json` export is not active authority and must not be loaded by default.
