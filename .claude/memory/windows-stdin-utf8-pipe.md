---

> [!NOTE]
> **Implementation/technical reference.** Preserve applicable security, provenance, validation, ownership, and engineering lessons, but do not treat this file as V2 product or architecture authority.
name: windows-stdin-utf8-pipe
description: On Windows, piping curl/UTF-8 into `python json.load(sys.stdin)` shows false mojibake — a diagnostic artifact, not a real bug
metadata:
  type: feedback
---

When smoke-testing the Codize API on Windows, piping a UTF-8 HTTP body into
Python text stdin corrupts non-ASCII in the DISPLAY only: `curl ... | python -c
"json.load(sys.stdin)"` (and `python -m json.tool`) decode stdin using the
locale/console code page (cp1252 here), so a correct UTF-8 arrow "→" (bytes
`e2 86 92`) prints as mojibake "â†'" (`c3a2 e280a0 e28099`) and an em-dash "—"
prints as "â€"". This nearly caused a false bug report in the M13D.1 pre-pilot
smoke — the template, Supabase DB, `httpx resp.json()`, and the live API body
were all verified correct UTF-8 (`e2 86 92` present, mojibake absent).

**Why:** Windows Python defaults stdin text decoding to the ANSI code page, not
UTF-8; `resp.json()` / `json.loads(bytes)` and the browser's charset-driven
`fetch()` are unaffected, so real users never see the corruption.

**How to apply:** To check byte-level encoding of an HTTP response, read RAW
bytes — `curl -s URL | python -c "import sys; raw=sys.stdin.buffer.read(); print(b'\xe2\x86\x92' in raw)"` — or `curl -o file` then open with
`encoding='utf-8'`. Never trust `json.load(sys.stdin)` / `json.tool` output for
non-ASCII on Windows. Before reporting an encoding bug, confirm it in the DB
(`encode(convert_to(...,'UTF8'),'hex')`) and in the raw HTTP bytes, not through a
text pipe. See [[roadmap-llm-conventions]].
