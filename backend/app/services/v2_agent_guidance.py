"""Stable coding-agent identities and the deliberately small guidance seam.

Vendor model names and UI-control recommendations are intentionally absent.
They may be added only through reviewed, versioned metadata; until then the
safe fallback is the transferable Quick / Standard / Deep category itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from app.domain.v2 import CodingAgentKey


@dataclass(frozen=True, slots=True)
class CodingAgentMetadata:
    key: CodingAgentKey
    display_name: str
    reasoning_controls_known: bool
    mapping_key: str | None
    mapping_version: str | None
    reviewed_at: str | None
    stale_fallback: str


_UNKNOWN_MAPPING_FALLBACK = (
    "Use the selected Quick, Standard, or Deep category in the tool without "
    "inventing a vendor model or control name."
)

CODING_AGENTS = MappingProxyType(
    {
        key: CodingAgentMetadata(
            key=key,
            display_name=display_name,
            reasoning_controls_known=False,
            mapping_key=None,
            mapping_version=None,
            reviewed_at=None,
            stale_fallback=_UNKNOWN_MAPPING_FALLBACK,
        )
        for key, display_name in (
            (CodingAgentKey.CODEX, "Codex"),
            (CodingAgentKey.CLAUDE_CODE, "Claude Code"),
            (CodingAgentKey.CURSOR, "Cursor"),
            (CodingAgentKey.CHATGPT, "ChatGPT"),
            (CodingAgentKey.REPLIT, "Replit"),
            (CodingAgentKey.OTHER, "Other"),
        )
    }
)


def get_agent_metadata(key: CodingAgentKey) -> CodingAgentMetadata:
    return CODING_AGENTS[key]
