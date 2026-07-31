from __future__ import annotations

import json
import re
import sys


DENY = [
    (
        re.compile(r"(^|[;&|]\s*)git\s+add\s+(?:-A|--all|\.)(?:\s|$)"),
        "Bulk staging is forbidden; stage explicit paths.",
    ),
    (
        re.compile(r"(^|[;&|]\s*)git\s+push\b[^\n]*(?:--force|-f)"),
        "Force-push is forbidden by Cruthunas policy.",
    ),
    (
        re.compile(r"(^|[;&|]\s*)git\s+reset\s+--hard\b"),
        "Destructive reset requires explicit human authorization outside the agent hook.",
    ),
    (
        re.compile(r"(^|[;&|]\s*)git\s+tag\b[^\n]*(?:-f|--force)"),
        "Moving or replacing a tag is forbidden.",
    ),
]
PROTECTED_SUFFIXES = {"claims/claims.yaml", "CORRECTIONS.md"}
PROTECTED_SEGMENTS = (
    "/audit/proposals/",
    "/audit/evidence/",
    "/audit/transitions/",
)


def command_denial(command: str) -> str | None:
    for pattern, reason in DENY:
        if pattern.search(command):
            return reason
    return None


def protected_record(path: str) -> bool:
    normalized = "/" + path.replace("\\", "/").lstrip("/")
    return any(normalized.endswith("/" + item) for item in PROTECTED_SUFFIXES) or any(
        segment in normalized for segment in PROTECTED_SEGMENTS
    )


def main() -> int:
    payload = json.load(sys.stdin)
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input", {})
    reason = None
    decision = "allow"
    if tool_name == "Bash":
        reason = command_denial(str(tool_input.get("command", "")))
        decision = "deny" if reason else "allow"
    elif tool_name in {"Write", "Edit"}:
        path = str(tool_input.get("file_path", ""))
        if protected_record(path):
            decision = "ask"
            reason = (
                "This is a canonical claim or audit record. Confirm explicit authorization "
                "and use cruthunas claim propose/register/transition or evidence add instead "
                "of editing the record freehand."
            )
    if decision == "allow":
        return 0
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
