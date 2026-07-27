"""Deterministic project-capability signals for intake and roadmap scope.

The five-question intake mixes project facts with a student self-assessment.
Only purpose, scope, and stack describe the product.  This module keeps that
boundary explicit and gives both classification and roadmap generation the
same bounded exclusion rules.  It makes no provider calls.
"""

from dataclasses import dataclass
import re


_EXCLUSION_TERMS: dict[str, tuple[str, ...]] = {
    "ai": (
        "ai features", "ai feature", "ai behavior", "ai app", "ai application",
        "artificial intelligence", "model api", "llm", "language model", "ai",
    ),
    "accounts": ("accounts", "account", "authentication", "auth", "login", "sign-in", "sign in"),
    "database": ("database", "databases", "postgres", "postgresql", "supabase", "mysql", "sqlite", "mongodb"),
    "backend": ("backend", "back-end", "server", "server-side", "api"),
    "notifications": ("notifications", "notification", "push alerts", "email alerts"),
    "calendar": ("calendar integration", "calendar sync", "calendar"),
}

_FRONTEND_TERMS = (
    "frontend", "front-end", "front end", "react", "next.js", "nextjs", "vue",
    "svelte", "angular", "html", "css", "website", "web app", "webapp", "ui",
    "dashboard", "browser", "browser-only", "browser-based", "javascript", "typescript",
)
_DATABASE_TERMS = (
    "database", "db", "postgres", "postgresql", "mysql", "sqlite", "mongodb",
    "supabase", "full-stack", "full stack", "fullstack",
)

# A provider/tool name on its own is intentionally absent.  Positive AI
# evidence must describe intended product behavior, not how the student codes.
_AI_FEATURE_PATTERNS = (
    r"\b(?:ai[- ]powered|ai[- ]based)\s+(?:feature|assistant|app|application|tool|tutor)\b",
    r"\b(?:calls?|uses?|integrates?\s+with)\s+(?:an?\s+)?(?:llm|language model|openai(?: api)?|anthropic(?: api)?|gemini(?: api)?)\b",
    r"\b(?:sends?|submits?)\b[^.\n]{0,60}\b(?:prompts?|content|requests?|messages?)\b[^.\n]{0,30}\bto\s+(?:gemini|openai|anthropic|an?\s+llm|a\s+language model)\b",
    r"\b(?:an?\s+)?(?:llm|language model|gemini|openai api|anthropic api)\s+(?:summari[sz]es?|generates?|analy[sz]es?|answers?|classifies?|translates?)\b",
    r"\b(?:chatbot|ai assistant|ai tutor|prompt[- ]based content generator)\b",
    r"\b(?:summari[sz]es?|generates?|analy[sz]es?)\b[^.\n]{0,80}\b(?:with|using|through)\s+(?:an?\s+)?(?:ai|llm|language model|model)\b",
    r"\bgenerates?\s+summaries?\s+from\s+(?:user|student|uploaded|notes?|text|content)\b",
    r"\b(?:users?|students?)\s+(?:send|submit)\b[^.\n]{0,60}\bto\s+"
    r"(?:openai|gemini|anthropic|an?\s+llm|a\s+language model)\b"
    r"[^.\n]{0,40}\bfor\s+(?:analysis|summari[sz]ation|classification|translation)\b",
    r"\b(?:openai|gemini|anthropic)\s+api\b",
    r"\b(?:llm|language model)\b",
    r"\bgemini\b",
)

_AI_TOOL_META_PATTERNS = (
    r"\b(?:i|we|the student)\s+(?:use|uses|used|ask|asks|asked)\b[^.\n]{0,50}\b(?:ai|llm|language model|chatgpt|claude|codex|cursor|copilot|gemini)\b[^.\n]{0,80}\b(?:code|coding|write|build|debug|stuck|help)\b",
    r"\b(?:ai|chatgpt|claude|codex|cursor|copilot|gemini)\b[^.\n]{0,40}\b(?:generated|changed|wrote|edited|patched)\b[^.\n]{0,70}\b(?:code|files?|functions?|project|app)\b",
    r"\b(?:ai|chatgpt|claude|codex|cursor|copilot|gemini)\b[^.\n]{0,35}"
    r"\b(?:helped?|helps?|assisted?)\b[^.\n]{0,60}"
    r"\b(?:code|coding|write|build|debug|implement)\b",
    r"\b(?:app|project|code|files?)\b[^.\n]{0,35}\b(?:generated|changed|written|edited|patched)\b[^.\n]{0,35}\b(?:by|using|with)\s+(?:ai|chatgpt|claude|codex|cursor|copilot|gemini)\b",
)

_SCRIPTED_CHATBOT_QUALIFIERS = re.compile(
    r"\b(?:scripted|pre[- ]written|rule[- ]based|hard[- ]coded|static)\b[^.\n]{0,45}\bchatbot\b|"
    r"\bchatbot(?:[- ]style)?\b[^.\n]{0,60}\b(?:scripted|pre[- ]written|rule[- ]based|hard[- ]coded|static)\b",
    re.IGNORECASE,
)

_LOCAL_BROWSER_PATTERNS = (
    r"\blocal\s*storage\b",
    r"\blocalstorage\b",
    r"\bsession\s*storage\b",
    r"\bsessionstorage\b",
    r"\bindexeddb\b",
    r"\bbrowser\s+(?:storage|persistence)\b",
    r"\bclient[- ]side\s+(?:storage|persistence)\b",
    r"\bdata\b[^.\n]{0,50}\b(?:remain|remains|persist|persists|survive|survives)\b"
    r"[^.\n]{0,45}\b(?:refresh|browser)\b",
    r"\b(?:persist|save|store|keep)\b[^.\n]{0,55}\b(?:locally|in\s+the\s+browser|client[- ]side)\b",
    r"\b(?:keep|save|store)\b[^.\n]{0,55}\b(?:on\s+)?(?:the\s+)?"
    r"(?:current|same|this)\s+device\b",
    r"\b(?:each|every|this)\s+browser\b[^.\n]{0,55}\b(?:its\s+own|local)\s+data\b",
    r"\bworks?\s+offline\b[^.\n]{0,55}\b(?:keeps?|stores?|saves?)\s+local\s+state\b",
    r"\bbrowser[- ]based\b",
    r"\bbrowser[- ]only\b",
    r"\blocal\s+browser\s+(?:app|application)\b",
    r"\bruns?\s+(?:entirely\s+)?in\s+the\s+browser\b",
)

_DEFERRED_CLAUSE = re.compile(
    r"\b(?:future(?:\s+(?:version|release|phase))?|"
    r"(?:later|eventual)\s+(?:version|release|phase)|someday|not\s+now|"
    r"deferred|"
    r"not\s+in\s+(?:version|v)\s*1|"
    r"after\s+(?:the\s+)?(?:first|initial)\s+(?:version|release)|"
    r"(?:may|might|could|can)\s+be\s+(?:added|included|built|supported)\s+later|"
    r"(?:may|might|could|can|will)\b[^.\n]{0,35}\b"
    r"(?:add|include|build|support|need|use|plan)\b[^.\n]{0,35}"
    r"\b(?:later|eventually|someday)|"
    r"(?:may|might|could|can|will)\b[^.\n]{0,35}"
    r"\b(?:later|eventually|someday)\b)\b",
    re.IGNORECASE,
)

_BACKEND_FEATURE_PATTERNS = (
    r"\b(?:browser|frontend|client|app|application)\b[^.\n]{0,55}\b(?:calls?|connects?|sends?)\b"
    r"[^.\n]{0,45}\b(?:my|our|the|custom)\s+(?:backend|server)(?:\s+api)?\b",
    r"\b(?:browser|frontend|client|app|application)\b[^.\n]{0,55}\b(?:calls?|connects?|sends?)\b"
    r"[^.\n]{0,35}\b(?:my\s+own|my|our|custom)\s+api\b",
    r"\b(?:has|uses|needs|requires|includes|builds?|adds?)\b[^.\n]{0,35}"
    r"\b(?:backend|back[- ]end|server(?:-side)?|server\s+api|api\s+routes?)\b",
    r"\b(?:backend|back[- ]end|server(?:-side)?|server\s+api|api\s+routes?)\b"
    r"[^.\n]{0,45}\b(?:is|are|will\s+be)?\s*(?:already\s+|currently\s+)?"
    r"(?:required|needed|included|authoritative|stores?|handles?|provides?|runs?|syncs?)\b",
    r"\b(?:data|records?|assignments?|profiles?|changes?)\b[^.\n]{0,55}"
    r"\bsyncs?\s+(?:between|across)\s+(?:devices?|browsers?|clients?)\b",
    r"\bsyncs?\s+(?:to|with)\s+(?:the\s+)?(?:backend|server)\b",
    r"\bclient\s*/\s*server\s+architecture\b",
)

_DATABASE_FEATURE_PATTERNS = (
    r"\b(?:has|uses|needs|requires|includes|writes?\s+to|reads?\s+from|syncs?\s+(?:to|through|with))\b"
    r"[^.\n]{0,45}\b(?:database|postgres(?:ql)?|mysql|sqlite|mongodb|supabase)\b",
    r"\b(?:database|postgres(?:ql)?|mysql|sqlite|mongodb|supabase)\b"
    r"[^.\n]{0,45}\b(?:is|are|will\s+be)?\s*(?:required|needed|included|stores?|persists?|syncs?|backs?)\b",
    r"\b(?:data|records?|assignments?|profiles?|homework|preferences?)\b[^.\n]{0,55}"
    r"\b(?:are\s+|is\s+)?(?:stored|persisted|saved|synced)\s+(?:in|to|through|with)\s+"
    r"(?:an?\s+|the\s+)?(?:database|postgres(?:ql)?|mysql|sqlite|mongodb|supabase)\b",
    r"\b(?:data|records?|assignments?|profiles?|homework|preferences?)\b[^.\n]{0,55}"
    r"\bsyncs?\b[^.\n]{0,45}\b(?:to|through|with)\s+(?:an?\s+|the\s+)?"
    r"(?:database|postgres(?:ql)?|mysql|sqlite|mongodb|supabase)\b",
    r"\b(?:server|service)\b[^.\n]{0,35}\b(?:stores?|persists?|syncs?)\b[^.\n]{0,35}\b(?:data|records?|assignments?|profiles?)\b",
)

_ACCOUNT_FEATURE_PATTERNS = (
    r"\b(?:users?|students?|members?)\b[^.\n]{0,35}\b(?:create|have|register|sign\s+up\s+for)\b"
    r"[^.\n]{0,20}\baccounts?\b",
    r"\b(?:users?|students?|members?)\b[^.\n]{0,35}\b(?:sign\s+in|log\s+in|authenticate)\b",
    r"\b(?:has|uses|needs|requires|includes)\b[^.\n]{0,35}\b(?:accounts?|authentication|auth|login|sign[- ]in)\b",
    r"\b(?:authenticated|signed[- ]in)\s+(?:users?|profiles?|accounts?)\b",
    r"\bsupabase\s+(?:auth|authentication)\b",
)


@dataclass(frozen=True)
class ProjectCapabilities:
    ai_feature: bool
    frontend: bool
    database: bool
    backend: bool
    accounts: bool
    exclusions: frozenset[str]
    local_persistence: bool

    @property
    def frontend_or_database(self) -> bool:
        return self.frontend or self.database

    @property
    def server_capability(self) -> bool:
        return self.backend or self.database or self.accounts

    @property
    def local_browser_app(self) -> bool:
        return (
            self.frontend
            and self.local_persistence
            and not self.server_capability
            and not self.ai_feature
        )

    @property
    def classification_label(self) -> str | None:
        return "Browser App" if self.local_browser_app else None


def _mentions(text: str, term: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", text) is not None


def _strip_quoted_examples(text: str) -> str:
    """Ignore explicitly-labelled quoted examples, not ordinary quoted names."""
    return re.sub(
        r"\b(?:example|phrase|copy|tutorial|docs?|documentation)\b[^\"']{0,35}([\"'])[^\"']*\1",
        " ",
        text,
        flags=re.IGNORECASE,
    )


def _exclusion_clauses(text: str) -> list[str]:
    clean = _strip_quoted_examples(text.lower())
    clauses: list[str] = []
    for sentence in re.split(r"[.!?;\n]+", clean):
        for clause in re.split(r"\b(?:but|however|except|though|although)\b", sentence):
            # "I do not want no backend" is deliberately ambiguous. Remove
            # that double-negative clause instead of pretending it is a clear
            # exclusion (or a clear positive requirement).
            clause = re.sub(
                r"\b(?:do\s+not|don't|does\s+not|doesn't|did\s+not|didn't|never)\s+"
                r"(?:want|need|mean|request|say)\s+no\b.*$",
                " ",
                clause,
            )
            if clause.strip():
                clauses.append(clause.strip())
    return clauses


def _explicitly_excludes(clause: str, term: str) -> bool:
    escaped = re.escape(term)
    search_clause = clause
    if term == "api":
        # "model API" / "OpenAI API" is an AI-capability phrase, not a claim
        # that the project has no backend HTTP API.
        search_clause = re.sub(
            r"\b(?:model|llm|language model|openai|gemini|anthropic)\s+api\b",
            "model service",
            search_clause,
        )
    # Negative introducers may govern a short coordinated list: "no backend
    # or database", "exclude accounts, auth, and notifications".
    prefix = (
        r"(?:\bno\b|\bwithout\b|\bexclude(?:d|s|ing)?\b|"
        r"\b(?:do\s+not|don't|does\s+not|doesn't|will\s+not|won't|should\s+not|"
        r"shouldn't|is\s+not|isn't|are\s+not|aren't|not\s+going\s+to)\b)"
    )
    if re.search(
        rf"{prefix}[^.\n;]{{0,100}}(?<![\w-]){escaped}(?![\w-])",
        search_clause,
    ):
        return True
    if re.search(
        rf"\bneither\b[^.\n;]{{0,100}}(?<![\w-]){escaped}(?![\w-])",
        search_clause,
    ):
        return True
    if re.search(
        rf"\bnot\s+(?:yet\s+)?(?:an?\s+)?(?<![\w-]){escaped}(?![\w-])",
        search_clause,
    ):
        return True
    # Capability-first forms: "accounts are out of scope", "AI is later",
    # "notifications are not in this version".
    suffix = (
        r"(?:\b(?:out\s+of|outside(?:\s+the)?)\s+scope\b|\bdeferred\b|\bexclude(?:d)?\b|\b(?:isn't|aren't|won't)\s+(?:yet\s+)?(?:included|planned|"
        r"supported|in\s+(?:this|the)\s+(?:version|release|mvp))\b|\bnot\s+(?:yet\s+)?(?:included|planned|"
        r"supported|in\s+(?:this|the)\s+(?:version|release|mvp)|for\s+(?:this|the)\s+"
        r"(?:version|release|mvp))\b|\bnot\s+yet\b|\b(?:later|future)\s+(?:only|version)?\b)"
    )
    return re.search(
        rf"(?<![\w-]){escaped}(?![\w-])[^.\n;]{{0,80}}{suffix}", search_clause
    ) is not None


def explicit_exclusions(*project_answers: str) -> frozenset[str]:
    clauses = _exclusion_clauses("\n".join(project_answers))
    found = {
        capability
        for capability, terms in _EXCLUSION_TERMS.items()
        if any(
            _explicitly_excludes(clause, term)
            for clause in clauses
            for term in terms
        )
    }
    return frozenset(found)


def _current_ai_feature_text(text: str) -> str:
    """Keep current product-AI behavior while respecting clause direction.

    A negative clause does not erase a separate affirmative behavior after a
    contrast ("No AI feature, but Gemini generates summaries"). Historical or
    explicitly discarded ideas remain non-current as a whole.
    """
    clean = _strip_quoted_examples(text)
    kept: list[str] = []
    for sentence in re.split(r"[.!?;\n]+", clean.lower()):
        if not sentence.strip():
            continue
        if re.search(
            r"\b(?:earlier|previous|old|discarded|rejected)\b[^.\n]{0,45}"
            r"\b(?:idea|version|proposal|plan|requirement)\b",
            sentence,
        ) and re.search(r"\b(?:excluded|removed|rejected|discarded)\b", sentence):
            continue
        sentence = _SCRIPTED_CHATBOT_QUALIFIERS.sub("scripted interface", sentence)
        for clause in re.split(r"\b(?:but|however|yet|though|although)\b", sentence):
            clause = clause.strip()
            if not clause or _DEFERRED_CLAUSE.search(clause):
                continue
            if any(_explicitly_excludes(clause, term) for term in _EXCLUSION_TERMS["ai"]):
                continue
            if any(re.search(pattern, clause) for pattern in _AI_TOOL_META_PATTERNS):
                continue
            kept.append(clause)
    return "\n".join(kept)


def _current_capability_text(text: str, capability: str) -> str:
    """Keep affirmative current-version clauses for one server capability.

    Exclusions and deferred ideas are not positive evidence. Splitting on
    contrast words preserves independent requirements in mixed input, such as
    "No database, but the browser calls a custom backend API."
    """
    terms = _EXCLUSION_TERMS[capability]
    kept: list[str] = []
    for clause in re.split(
        r"[.!?;\n]+|\b(?:but|however|except|yet|though|although)\b",
        _strip_quoted_examples(text.lower()),
    ):
        clause = clause.strip()
        if not clause or _DEFERRED_CLAUSE.search(clause):
            continue
        if any(_explicitly_excludes(clause, term) for term in terms):
            continue
        kept.append(clause)
    return "\n".join(kept)


def _has_capability(text: str, capability: str, patterns: tuple[str, ...]) -> bool:
    evidence = _current_capability_text(text, capability)
    return any(re.search(pattern, evidence) for pattern in patterns)


def _current_local_persistence_text(text: str) -> str:
    """Keep affirmative current-version browser-local persistence clauses."""
    local_terms = (
        r"local\s*storage|localstorage|session\s*storage|sessionstorage|"
        r"indexeddb|browser\s+(?:storage|persistence)|"
        r"client[- ]side\s+(?:storage|persistence)|local\s+persistence|"
        r"local\s+state|(?:current|same|this)\s+device"
    )
    negative_prefix = (
        r"(?:\bno\b|\bwithout\b|\bexclude(?:d|s|ing)?\b|"
        r"\b(?:do\s+not|don't|does\s+not|doesn't|will\s+not|won't|"
        r"is\s+not|isn't|are\s+not|aren't)\b)"
    )
    kept: list[str] = []
    for clause in re.split(
        r"[.!?;\n]+|\b(?:but|however|except|yet|though|although)\b",
        _strip_quoted_examples(text.lower()),
    ):
        clause = clause.strip()
        if not clause or _DEFERRED_CLAUSE.search(clause):
            continue
        if re.search(rf"{negative_prefix}[^.\n;]{{0,90}}\b(?:{local_terms})\b", clause):
            continue
        if re.search(
            rf"\b(?:{local_terms})\b[^.\n;]{{0,70}}"
            r"\b(?:excluded|deferred|out\s+of\s+scope|outside\s+(?:the\s+)?scope|"
            r"not\s+(?:yet\s+)?(?:included|planned|supported))\b",
            clause,
        ):
            continue
        kept.append(clause)
    return "\n".join(kept)


def product_purpose_text(purpose: str) -> str:
    """Return purpose wording without student AI-tool workflow statements.

    This is intentionally narrower than classification: it removes only the
    same explicit coding-tool meta clauses so deterministic roadmap fallback
    does not repeat provider names as if they were product requirements.
    """
    parts = re.split(
        r"(?<=[.!?;])\s+|\n+|,\s+(?=(?:and|but)\s+(?:i|we|the student)\b)",
        purpose,
        flags=re.IGNORECASE,
    )
    kept = [
        part.strip(" ,")
        for part in parts
        if part.strip(" ,")
        and not any(
            re.search(pattern, part, flags=re.IGNORECASE)
            for pattern in _AI_TOOL_META_PATTERNS
        )
    ]
    return " ".join(kept).strip()


def derive_project_capabilities(purpose: str, scope: str, stack: str) -> ProjectCapabilities:
    """Derive product facts from Q1-Q3 only; Q4 is deliberately not accepted."""
    purpose_scope = f"{purpose}\n{scope}".lower()
    all_project_text = f"{purpose_scope}\n{stack}".lower()
    exclusions = explicit_exclusions(purpose, scope, stack)
    feature_text = _current_ai_feature_text(all_project_text)

    ai_feature = any(
        re.search(pattern, feature_text) for pattern in _AI_FEATURE_PATTERNS
    )
    frontend = any(_mentions(all_project_text, term) for term in _FRONTEND_TERMS)
    database = _has_capability(
        all_project_text, "database", _DATABASE_FEATURE_PATTERNS
    )
    # Keep the legacy database vocabulary as affirmative evidence only when it
    # is not negated/deferred and appears in a capability-bearing phrase.
    if not database:
        database_text = _current_capability_text(all_project_text, "database")
        database = any(
            _mentions(database_text, term)
            for term in _DATABASE_TERMS
            if term in {"full-stack", "full stack", "fullstack"}
        )
    backend = _has_capability(
        all_project_text, "backend", _BACKEND_FEATURE_PATTERNS
    )
    accounts = _has_capability(
        all_project_text, "accounts", _ACCOUNT_FEATURE_PATTERNS
    )
    local_text = _current_local_persistence_text(all_project_text)
    local_signal = any(re.search(pattern, local_text) for pattern in _LOCAL_BROWSER_PATTERNS)
    return ProjectCapabilities(
        ai_feature=ai_feature,
        frontend=frontend,
        database=database,
        backend=backend,
        accounts=accounts,
        exclusions=exclusions,
        local_persistence=local_signal,
    )


def classification_name(archetype_id: int, capabilities: ProjectCapabilities, names: dict[int, str]) -> str:
    """Keep the stored three-archetype id while presenting an accurate label."""
    return capabilities.classification_label or names[archetype_id]
