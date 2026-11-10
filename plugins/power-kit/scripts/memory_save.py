"""Stop / PreCompact hook: append a short note about this session to the project's session log.

Reads the transcript (JSONL) and records the latest request and the files Claude changed.
Each session gets one entry, rewritten as the session goes on, so the log does not
grow on every turn.
"""
import json
import re
import sys
from datetime import datetime
from common import read_hook_input, project_dir

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
MAX_ENTRIES = 40


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
    return ""


def scan(transcript_path):
    first_prompt, last_prompt, files = "", "", []
    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                msg = ev.get("message") or {}
                if ev.get("type") == "user" and msg.get("role") == "user":
                    t = text_of(msg.get("content")).strip()
                    if t and not t.startswith("<"):
                        first_prompt = first_prompt or t
                        last_prompt = t
                elif ev.get("type") == "assistant":
                    for c in msg.get("content") or []:
                        if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") in EDIT_TOOLS:
                            p = (c.get("input") or {}).get("file_path") or (c.get("input") or {}).get("notebook_path")
                            if p and p not in files:
                                files.append(p)
    except OSError:
        pass
    return first_prompt, last_prompt, files


def short(s, n=200):
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def main():
    data = read_hook_input()
    session = (data.get("session_id") or "unknown")[:8]
    d, cwd = project_dir(data.get("cwd"))
    first, last, files = scan(data.get("transcript_path") or "")
    if not first and not files:
        return 0

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"### {stamp} · session {session}\n- Started with: {short(first)}\n"
    if last and last != first:
        entry += f"- Latest request: {short(last)}\n"
    if files:
        entry += "- Files changed: " + ", ".join(files[:15]) + (" …" if len(files) > 15 else "") + "\n"

    log = d / "session-log.md"
    old = log.read_text(encoding="utf-8") if log.exists() else ""
    entries = [e for e in old.split("\n### ") if e.strip()]
    entries = [e for e in entries if f"session {session}" not in e.split("\n", 1)[0]]
    entries = ["### " + e.lstrip("# ").strip() for e in entries] + [entry.strip()]
    log.write_text("\n\n".join(entries[-MAX_ENTRIES:]) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
