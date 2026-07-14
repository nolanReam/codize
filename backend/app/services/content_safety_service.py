"""Shared read-boundary safety helpers for untrusted workflow content.

Workflow write schemas reject the credential formats used by this stack, but
historical rows and intake answers predate some of those guards.  Downstream
Defense/Report readers therefore use this one value-shaped redactor before
content can enter a provider prompt or a student-safe report response.

This is intentionally a small seatbelt, not a claim of complete secret
detection.  Bare environment-variable names remain ordinary educational text.
"""

import re
import unicodedata

REDACTION_MARKER = "[REDACTED_SECRET]"

_SECRET_PATTERNS = (
    re.compile(r"sb_secret_[A-Za-z0-9_-]{8,}"),
    re.compile(r"sk-or-[A-Za-z0-9_-]{8,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{16,}"),
    re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
        r"(?:.*?-----END [A-Z ]*PRIVATE KEY-----|.*$)",
        re.DOTALL,
    ),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{16,}=*"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"),
)


def redact_secrets(text: str) -> tuple[str, bool]:
    """Replace supported credential-shaped values with a stable marker."""
    redacted = False
    for pattern in _SECRET_PATTERNS:
        text, count = pattern.subn(REDACTION_MARKER, text)
        redacted = redacted or count > 0
    return text, redacted


def has_unsafe_control_chars(text: str) -> bool:
    """Match the workflow Evidence boundary: tab/newline/CR are permitted."""
    return any(
        unicodedata.category(char) == "Cc" and char not in "\t\n\r"
        for char in text
    )
