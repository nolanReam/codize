"""Deterministic project-capability signals for intake and roadmap scope.

The five-question intake mixes project facts with a student self-assessment.
Only purpose, scope, and stack describe the product.  This module keeps that
boundary explicit and gives both classification and roadmap generation the
same bounded exclusion rules.  It makes no provider calls.
"""

from dataclasses import dataclass
import re


_EXCLUSION_TERMS: dict[str, tuple[str, ...]] = {
    "ai": ("ai features", "ai feature", "ai-powered features", "llm", "language model", "chatbot"),
    "accounts": ("accounts", "account", "authentication", "auth", "login", "sign-in", "sign in"),
    "database": ("database", "databases", "postgres", "postgresql", "supabase", "mysql", "sqlite", "mongodb"),
    "backend": ("backend", "back-end", "server", "server-side", "api"),
    "notifications": ("notifications", "notification", "push alerts", "email alerts"),
    "calendar": ("calendar integration", "calendar sync", "calendar"),
}

_FRONTEND_TERMS = (
    "frontend", "front-end", "front end", "react", "next.js", "nextjs", "vue",
    "svelte", "angular", "html", "css", "website", "web app", "webapp", "ui",
    "dashboard", "browser", "javascript", "typescript",
)
_DATABASE_TERMS = (
    "database", "db", "postgres", "postgresql", "mysql", "sqlite", "mongodb",
    "supabase", "full-stack", "full stack", "fullstack",
)

# A provider/tool name on its own is intentionally absent.  Positive AI
# evidence must describe intended product behavior, not how the student codes.
_AI_FEATURE_PATTERNS = (
    r"\b(?:ai[- ]powered|ai[- ]based)\s+(?:feature|assistant|app|application|tool|tutor)\b",
    r"\b(?:calls?|uses?|integrates?\s+with)\s+(?:an?\s+)?(?:llm|language model|openai api|anthropic api|gemini api)\b",
    r"\b(?:chatbot|ai assistant|ai tutor|prompt[- ]based content generator)\b",
    r"\b(?:summari[sz]es?|generates?|analy[sz]es?)\b[^.\n]{0,80}\b(?:with|using|through)\s+(?:an?\s+)?(?:ai|llm|language model|model)\b",
)

_LOCAL_BROWSER_PATTERNS = (
    r"\blocal\s*storage\b",
    r"\blocalstorage\b",
    r"\bbrowser[- ]based\b",
    r"\bruns?\s+(?:entirely\s+)?in\s+the\s+browser\b",
)


@dataclass(frozen=True)
class ProjectCapabilities:
    ai_feature: bool
    frontend_or_database: bool
    exclusions: frozenset[str]
    local_browser_app: bool

    @property
    def classification_label(self) -> str | None:
        return "Browser App" if self.local_browser_app else None


def _mentions(text: str, term: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", text) is not None


def _explicitly_excludes(text: str, term: str) -> bool:
    escaped = re.escape(term)
    patterns = (
        rf"\bno\s+(?:planned\s+)?(?:{escaped})\b",
        rf"\bwithout\s+(?:any\s+)?(?:{escaped})\b",
        rf"\b(?:does\s+not|doesn't|won't|will\s+not)\s+(?:have|include|use|need|add)\s+(?:any\s+)?(?:{escaped})\b",
        rf"\bnot\s+using\s+(?:any\s+)?(?:{escaped})\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def explicit_exclusions(*project_answers: str) -> frozenset[str]:
    text = "\n".join(project_answers).lower()
    found = {
        capability
        for capability, terms in _EXCLUSION_TERMS.items()
        if any(_explicitly_excludes(text, term) for term in terms)
    }
    return frozenset(found)


def derive_project_capabilities(purpose: str, scope: str, stack: str) -> ProjectCapabilities:
    """Derive product facts from Q1-Q3 only; Q4 is deliberately not accepted."""
    purpose_scope = f"{purpose}\n{scope}".lower()
    all_project_text = f"{purpose_scope}\n{stack}".lower()
    exclusions = explicit_exclusions(purpose, scope, stack)

    ai_feature = "ai" not in exclusions and any(
        re.search(pattern, purpose_scope) for pattern in _AI_FEATURE_PATTERNS
    )
    frontend = any(_mentions(all_project_text, term) for term in _FRONTEND_TERMS)
    database = "database" not in exclusions and any(
        _mentions(all_project_text, term) for term in _DATABASE_TERMS
    )
    local_signal = any(re.search(pattern, all_project_text) for pattern in _LOCAL_BROWSER_PATTERNS)
    local_browser_app = (
        frontend
        and local_signal
        and "backend" in exclusions
        and "database" in exclusions
    )
    return ProjectCapabilities(
        ai_feature=ai_feature,
        frontend_or_database=frontend or database,
        exclusions=exclusions,
        local_browser_app=local_browser_app,
    )


def classification_name(archetype_id: int, capabilities: ProjectCapabilities, names: dict[int, str]) -> str:
    """Keep the stored three-archetype id while presenting an accurate label."""
    return capabilities.classification_label or names[archetype_id]
