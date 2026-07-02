"""Validate the Milestone 1 pre-build artifacts against the master spec.

Checks the three archetype JSON templates and the six system prompts for the
structural and security invariants fixed by docs/context/codize_master_spec_v2.1.md.
Pure stdlib. Exit code 0 = all checks pass.

Run:  python scripts/validate_prebuild_artifacts.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "backend" / "app" / "templates"
PROMPTS_DIR = ROOT / "backend" / "app" / "prompts"

PHASE_KEYS = {
    "phase", "phase_title", "core_concept", "ai_appropriate_tasks",
    "human_required_tasks", "explanation_gate_targets", "gate_depth",
    "unlock_condition", "functional_unlock",
}
GATE_DEPTHS = {"light", "medium", "heavy"}

EXPECTED_TEMPLATES = {
    "archetype_1_ai_app.json": (1, "AI-Powered App"),
    "archetype_2_rest_api.json": (2, "REST API Backend"),
    "archetype_3_fullstack.json": (3, "Full-Stack Web App"),
}

RLS_FIRST_TASK = (
    "Enable RLS on this table and write an ownership policy before continuing. "
    "Do not proceed until this is done."
)
BACKEND_ONLY_NOTE = "If you are writing this in frontend code you are doing it wrong."
AUTH_NOTE = (
    "Hiding this in the UI does not protect it. This check must happen here, "
    "in the backend, on every request."
)
CHECKLIST_GATE_TARGET = (
    "Walk me through one item on this checklist. Tell me what you checked, "
    "what you found, and what you did or confirmed as a result."
)

# Required substrings per prompt file (structural spec requirements).
PROMPT_REQUIREMENTS = {
    "roadmap_generation.md": [
        "{{ARCHETYPE_TEMPLATE_JSON}}", "{{INTAKE_PURPOSE}}", "{{INTAKE_DESCRIPTION}}",
        "{{INTAKE_STACK}}", "{{INTAKE_SELF_ASSESSMENT}}", "{{INTAKE_DEADLINE}}",
        "may not add phases", "20% rule",
    ],
    "phase_explanation.md": [
        "{{PHASE_TEMPLATE_JSON}}", "{{PROJECT_DESCRIPTION}}", "{{PROJECT_PURPOSE}}",
        "{{STUDENT_STACK}}", "reference their actual project",
    ],
    "gate_turn_1.md": [
        "{{GATE_TARGETS}}", "{{PROJECT_SUMMARY}}",
        "Before we start — in one sentence, describe the specific structure you "
        "built for this phase. Name at least one variable, function, or database field.",
        "The gate does not start without an anchor",
        "Never invent, suggest, or complete an anchor",
    ],
    "gate_turn_2.md": [
        "{{ANCHOR_STATEMENT}}", "{{TURN_1_QUESTION}}", "{{TURN_1_RESPONSE}}",
        "Accuracy", "Specificity", "Completeness", "WEAKEST",
    ],
    "gate_turn_3.md": [
        "{{ANCHOR_STATEMENT}}", "{{TURN_1_QUESTION}}", "{{TURN_1_RESPONSE}}",
        "{{TURN_2_QUESTION}}", "{{TURN_2_RESPONSE}}",
        "must NOT be answerable from general knowledge",
    ],
    "gate_evaluation.md": [
        "{{ANCHOR_STATEMENT}}", "{{TURN_1_QUESTION}}", "{{TURN_1_RESPONSE}}",
        "{{TURN_2_QUESTION}}", "{{TURN_2_RESPONSE}}", "{{TURN_3_QUESTION}}",
        "{{TURN_3_RESPONSE}}",
        "Structural Identification", "System Ripple Effect", "Implementation Specificity",
        "return FAIL regardless of technical correctness",
        '{"verdict"',
    ],
}

errors: list[str] = []
checks = 0


def check(cond: bool, msg: str) -> None:
    global checks
    checks += 1
    if not cond:
        errors.append(msg)


def phase_text(phase: dict) -> str:
    return json.dumps(phase)


def validate_template(path: Path, expected_id: int, expected_name: str) -> None:
    name = path.name
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        errors.append(f"{name}: cannot load JSON ({e})")
        return

    check(data.get("archetype_id") == expected_id, f"{name}: archetype_id != {expected_id}")
    check(data.get("archetype_name") == expected_name, f"{name}: archetype_name != {expected_name!r}")
    check(bool(data.get("default_stack")), f"{name}: missing default_stack")

    phases = data.get("phases", [])
    check(len(phases) >= 4, f"{name}: too few phases ({len(phases)})")

    for i, ph in enumerate(phases, start=1):
        pid = f"{name} phase {i}"
        check(set(ph.keys()) == PHASE_KEYS, f"{pid}: keys mismatch: {sorted(set(ph.keys()) ^ PHASE_KEYS)}")
        check(ph.get("phase") == i, f"{pid}: phase number {ph.get('phase')} not sequential")
        check(ph.get("gate_depth") in GATE_DEPTHS, f"{pid}: bad gate_depth {ph.get('gate_depth')!r}")
        targets = ph.get("explanation_gate_targets", [])
        check(3 <= len(targets) <= 5, f"{pid}: {len(targets)} gate targets (need 3-5)")
        check(len(ph.get("human_required_tasks", [])) >= 1, f"{pid}: no human_required_tasks")
        check(bool(ph.get("functional_unlock")), f"{pid}: missing functional_unlock")
        check(
            ph.get("unlock_condition") == "3-turn gate passed with no unresolved follow-ups",
            f"{pid}: unlock_condition drifted",
        )

    all_text = json.dumps(data)

    # Security constraint 2: a database phase whose FIRST human task is the RLS mandate.
    db_phases = [p for p in phases if RLS_FIRST_TASK in p.get("human_required_tasks", [])]
    check(bool(db_phases), f"{name}: no phase carries the verbatim RLS-first task")
    for p in db_phases:
        check(
            p["human_required_tasks"][0] == RLS_FIRST_TASK,
            f"{name} phase {p['phase']}: RLS task is not the FIRST human-required task",
        )

    # Security constraint 3: auth middleware note verbatim somewhere.
    check(AUTH_NOTE in all_text, f"{name}: auth middleware NOTE missing/altered")

    # OWASP A01: gate target about removing the ownership/auth check.
    check(
        re.search(r"if the (auth middleware|ownership check) (is|were) removed", all_text) is not None,
        f"{name}: no A01 gate target (removed ownership/auth check)",
    )
    # OWASP A03: injection/validation gate target.
    check(
        "validation is removed" in all_text or "innerHTML" in all_text,
        f"{name}: no A03 gate target (validation removal / XSS)",
    )
    # A02: secrets — either the frontend .env target or service-role key target.
    check(
        ".env file in frontend code does not protect a secret" in all_text
        or "service-role key" in all_text,
        f"{name}: no A02 gate target (secret exposure)",
    )

    # Final phase: mandatory pre-deployment security checklist, gate-checked.
    final = phases[-1]
    check(
        final.get("phase_title") == "Pre-Deployment Security Checklist",
        f"{name}: final phase is not the Pre-Deployment Security Checklist",
    )
    check(
        len(final.get("human_required_tasks", [])) == 9,
        f"{name}: checklist must have exactly 9 items, has {len(final.get('human_required_tasks', []))}",
    )
    check(
        final.get("explanation_gate_targets", [""])[0] == CHECKLIST_GATE_TARGET,
        f"{name}: checklist gate question drifted from spec wording",
    )
    check(final.get("gate_depth") == "heavy", f"{name}: checklist phase must be gate_depth heavy")

    # Archetype 1 only: spec's Phase 3 example must be preserved.
    if expected_id == 1:
        p3 = phases[2]
        check(p3.get("phase_title") == "LLM Integration", f"{name}: phase 3 is not LLM Integration")
        check(
            "Generate boilerplate API client class" in p3.get("ai_appropriate_tasks", []),
            f"{name}: phase 3 lost spec's AI task (API client class)",
        )
        check(
            any("Write the system prompt for [PROJECT_PURPOSE]" in t for t in p3.get("human_required_tasks", [])),
            f"{name}: phase 3 lost spec's human task (system prompt)",
        )
        check(
            any(BACKEND_ONLY_NOTE in t for t in p3.get("human_required_tasks", [])),
            f"{name}: phase 3 external-API task lost the backend-only NOTE",
        )
        check(
            "How token cost is calculated and why it matters for [PROJECT_SCALE]"
            in p3.get("explanation_gate_targets", []),
            f"{name}: phase 3 lost spec's token-cost gate target",
        )


def validate_prompts() -> None:
    for fname, needles in PROMPT_REQUIREMENTS.items():
        path = PROMPTS_DIR / fname
        if not path.exists():
            errors.append(f"prompts/{fname}: missing")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            check(needle in text, f"prompts/{fname}: missing required content: {needle[:70]!r}")
        # Injection defense: every prompt receiving student text must neutralize it.
        check(
            re.search(r"(not|never)\s+(as\s+)?instructions|answer content", text, re.IGNORECASE) is not None,
            f"prompts/{fname}: no student-text-is-data clause found",
        )


def main() -> int:
    files = sorted(p.name for p in TEMPLATES_DIR.glob("*.json"))
    check(files == sorted(EXPECTED_TEMPLATES), f"templates dir must hold exactly {sorted(EXPECTED_TEMPLATES)}, found {files}")
    for fname, (aid, aname) in EXPECTED_TEMPLATES.items():
        validate_template(TEMPLATES_DIR / fname, aid, aname)
    validate_prompts()

    if errors:
        print(f"FAIL — {len(errors)} error(s) out of {checks} checks:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"PASS — all {checks} checks passed.")
    print("Templates: 3 archetypes validated (structure, security constraints, checklist phase).")
    print("Prompts: 6 system prompts validated (placeholders, rubric, injection defenses).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
