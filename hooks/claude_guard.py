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
PROTECTED_FILES = {"claims/claims.yaml", "CORRECTIONS.md"}


def command_denial(command: str) -> str | None:
    for pattern, reason in DENY:
        if pattern.search(command):
            return reason
    return None


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
        path = str(tool_input.get("file_path", "")).replace("\\", "/")
        if any(path.endswith(item) for item in PROTECTED_FILES):
            decision = "ask"
            reason = (
                "This is a canonical status/correction record. Confirm explicit "
                "authorization and use the transition workflow where applicable."
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
