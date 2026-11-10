"""SessionStart hook: print this project's memory so Claude starts with it in context."""
import sys
from common import read_hook_input, project_dir

MAX_LOG_ENTRIES = 8
MAX_CHARS = 6000


def main():
    data = read_hook_input()
    d, cwd = project_dir(data.get("cwd"))
    memory = d / "MEMORY.md"
    log = d / "session-log.md"

    parts = []
    if memory.exists() and memory.read_text(encoding="utf-8").strip():
        parts.append("## Project memory (MEMORY.md)\n" + memory.read_text(encoding="utf-8").strip())
    if log.exists():
        entries = [e.strip() for e in log.read_text(encoding="utf-8").split("\n### ") if e.strip()]
        recent = entries[-MAX_LOG_ENTRIES:]
        if recent:
            parts.append("## Recent sessions (newest last)\n" + "\n".join("### " + e.lstrip("# ") for e in recent))

    if not parts:
        print(f"[power-kit] No saved memory yet for {cwd}. Memory file: {memory}")
        return 0

    text = "\n\n".join(parts)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n...(truncated — see " + str(d) + ")"
    print(f"[power-kit] Memory for {cwd} (file: {memory}). Use it; update MEMORY.md when decisions change.\n\n{text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
