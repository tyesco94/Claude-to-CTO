"""PreToolUse hook for Read: stop Claude from loading a huge file in one go.

If a file is bigger than the limits and the Read call has no offset/limit,
the call is refused with advice to search first or read a slice. Everything
else passes through untouched. Limits can be changed with the environment
variables POWER_KIT_MAX_LINES and POWER_KIT_MAX_KB.
"""
import json
import os
import sys
from common import read_hook_input

MAX_LINES = int(os.environ.get("POWER_KIT_MAX_LINES", "1500"))
MAX_KB = int(os.environ.get("POWER_KIT_MAX_KB", "150"))
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".ipynb"}  # Read handles these specially


def count_lines(path, stop_after):
    n = 0
    with open(path, "rb") as f:
        for _ in f:
            n += 1
            if n > stop_after:
                break
    return n


def main():
    data = read_hook_input()
    if data.get("tool_name") != "Read":
        return 0
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ""
    if not path or ti.get("limit") or ti.get("offset") or ti.get("pages"):
        return 0
    if os.path.splitext(path)[1].lower() in SKIP_EXT or not os.path.isfile(path):
        return 0

    size_kb = os.path.getsize(path) / 1024
    lines = count_lines(path, MAX_LINES)
    if lines <= MAX_LINES and size_kb <= MAX_KB:
        return 0

    reason = (
        f"[power-kit token guard] {os.path.basename(path)} is large "
        f"({'over ' + str(MAX_LINES) if lines > MAX_LINES else lines} lines, {size_kb:.0f} KB). "
        "Reading it whole wastes tokens. Search it with Grep first, then Read only the part you need "
        "using offset and limit (for example offset=1, limit=300). If you truly need the whole file, "
        "read it in slices."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
