"""Scope-safe deterministic roadmap projections.

Codize still stores exactly one of the three archetype ids.  A small browser-
only project can be the closest fit to archetype 3 without being full stack.
When the student explicitly excludes both a backend and database and names a
browser/local-storage application, this module projects archetype 3 into a
strict seven-phase browser-app template.  The projected template—not model
output—remains the structural validator's source of truth.
"""

import copy
import re

from app.services import project_capability_service


def _phase(
    number: int,
    title: str,
    concept: str,
    ai_tasks: list[str],
    human_tasks: list[str],
    targets: list[str],
    depth: str = "medium",
) -> dict:
    return {
        "phase": number,
        "phase_title": title,
        "core_concept": concept,
        "ai_appropriate_tasks": ai_tasks,
        "human_required_tasks": human_tasks,
        "explanation_gate_targets": targets,
        "gate_depth": depth,
        "unlock_condition": "3-turn gate passed with no unresolved follow-ups",
        "functional_unlock": "A reusable browser-app checklist for the next phase",
    }


_LOCAL_BROWSER_PHASES = [
    _phase(
        1,
        "Browser App Scope & Data Shape",
        "Turn [PROJECT_PURPOSE] into a small browser-only user flow and a plain JavaScript data shape",
        ["Generate a minimal folder scaffold", "Draft sample assignment objects for review"],
        [
            "Write the first-version user flow and keep every excluded capability out of scope",
            "Define the assignment fields: title, subject, due date, and completion state",
            "Decide which browser state is temporary and which state must survive refreshes",
        ],
        [
            "Why these fields are enough for the first version of [PROJECT_PURPOSE]",
            "How one assignment moves through the browser app from creation to deletion",
            "Which requested exclusions shape the architecture",
        ],
        "light",
    ),
    _phase(
        2,
        "Semantic HTML Foundation",
        "Structure the browser interface with semantic HTML before adding behavior",
        ["Generate starter form and list markup", "Generate a small set of accessible empty-state copy"],
        [
            "Build the assignment form with explicit labels",
            "Build the list and empty state with semantic elements",
            "Confirm the page remains understandable with styles disabled",
        ],
        [
            "How labels and form controls are connected in your markup",
            "Why the assignment list uses the elements you chose",
            "What the user sees before any assignments exist",
        ],
        "light",
    ),
    _phase(
        3,
        "Local State & Persistence",
        "Keep one in-memory assignment list synchronized with browser local storage",
        ["Generate serialization helper stubs", "Generate cautious invalid-data fallback cases"],
        [
            "Write the load and save functions for local storage",
            "Choose one stable storage key and document the saved shape",
            "Handle missing or malformed saved data without breaking the page",
        ],
        [
            "When the in-memory list is written to local storage",
            "What happens when saved data is missing or malformed",
            "How you prevent the rendered list and saved list from disagreeing",
        ],
    ),
    _phase(
        4,
        "Assignment Interactions",
        "Add, complete, and delete assignments through small named JavaScript functions",
        ["Generate event-listener boilerplate", "Generate repetitive rendering branches after the first is understood"],
        [
            "Implement assignment creation with input validation",
            "Implement completion toggling without mutating unrelated fields",
            "Implement deletion and persist each successful change",
        ],
        [
            "Which function owns assignment creation and what it returns",
            "How completion changes flow from a click to saved browser state",
            "What deletion changes in memory, storage, and the rendered list",
        ],
    ),
    _phase(
        5,
        "Filtering & Rendering",
        "Derive filtered views from one source list and render user text safely",
        ["Generate filter-control styling", "Generate repetitive list-item markup after the first item is reviewed"],
        [
            "Implement subject and completion filters as derived views",
            "Render assignment text with textContent rather than HTML insertion",
            "Keep empty states accurate for both the full list and filtered views",
        ],
        [
            "Why filtering does not overwrite the saved assignment list",
            "Where user-entered text reaches the page and how it is rendered safely",
            "How your empty state distinguishes no assignments from no filter matches",
        ],
    ),
    _phase(
        6,
        "Browser Verification & Accessibility",
        "Verify the main user loop, failure cases, keyboard behavior, and responsive layout",
        ["Generate a manual test checklist draft", "Generate boundary-value examples for due dates and empty text"],
        [
            "Run add, complete, filter, refresh, and delete checks and record what happened",
            "Test keyboard focus order and visible focus at narrow and wide widths",
            "Test malformed local storage and confirm the recovery behavior",
        ],
        [
            "One check that failed first and what you changed",
            "How keyboard-only use reaches every assignment action",
            "What the app does when saved browser data cannot be parsed",
        ],
    ),
    _phase(
        7,
        "Pre-Deployment Security Checklist",
        "Confirm the browser-only build matches its stated scope and handles local user data honestly",
        ["Generate a static-file review checklist"],
        [
            "Confirm the deployed app makes no unexpected network requests.",
            "Confirm assignment text is rendered as text, never inserted as HTML.",
            "Confirm local storage contains only the assignment fields the student chose to save.",
            "Confirm clearing site data resets the app without leaving a broken state.",
            "Confirm every visible control has a keyboard path and visible focus.",
            "Confirm the layout works at phone, tablet, and desktop widths.",
        ],
        [
            "Walk through one checklist item, what you inspected, and what you found",
            "Which browser-only risk mattered most for [PROJECT_PURPOSE]",
            "What remains intentionally out of scope after this release",
        ],
        "heavy",
    ),
]


def capabilities_for_project(project: dict) -> project_capability_service.ProjectCapabilities:
    return project_capability_service.derive_project_capabilities(
        project.get("intake_purpose") or "",
        project.get("intake_scope") or "",
        project.get("intake_stack") or "",
    )


def template_for_project(template: dict, project: dict) -> tuple[dict, project_capability_service.ProjectCapabilities]:
    capabilities = capabilities_for_project(project)
    if not capabilities.local_browser_app:
        return copy.deepcopy(template), capabilities
    return {
        "archetype_id": template["archetype_id"],
        "archetype_name": "Browser App",
        "description": "A browser-based application that runs locally and preserves data in browser storage.",
        "default_stack": "Plain HTML + CSS + JavaScript",
        "phases": copy.deepcopy(_LOCAL_BROWSER_PHASES),
    }, capabilities


_LOCAL_FORBIDDEN = re.compile(
    r"\b(?:llm|language model|model provider|openai|anthropic|gemini|chatbot|python|fastapi|"
    r"backend|back-end|database|postgres|supabase|authentication|auth middleware|conversation history)\b",
    re.IGNORECASE,
)


def validate_scope_constraints(roadmap: dict, capabilities: project_capability_service.ProjectCapabilities) -> list[str]:
    """Reject personalization that reintroduces excluded local-app systems."""
    if not capabilities.local_browser_app:
        return []
    blob = str(roadmap)
    matches = sorted({match.group(0).lower() for match in _LOCAL_FORBIDDEN.finditer(blob)})
    return [f"excluded capability reintroduced: {term}" for term in matches]
