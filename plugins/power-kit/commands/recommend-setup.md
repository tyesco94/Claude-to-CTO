---
description: Scan this project and recommend Claude Code hooks, skills, sub-agents and MCP servers
---
Scan the current project without changing any files:

1. Identify the languages, frameworks, package managers, test/lint/format commands, CI config, and any existing `.claude/` settings, `CLAUDE.md`, hooks, skills or agents.
2. Recommend, in priority order (most useful first, max ~8 items):
   - **Hooks** — e.g. run the formatter after edits, block edits to generated or secret files, run tests before stopping.
   - **Skills** — repeated workflows in this repo worth writing down.
   - **Sub-agents** — focused helpers (reviewer, test-writer) if the project is big enough to benefit.
   - **MCP servers / connectors** — only for services the project actually uses.
   - **CLAUDE.md** — the 5–10 facts every session needs (build/test commands, conventions).
3. For each: what it does, why this project needs it, and the exact snippet or file to add.
4. Ask which ones to set up; do not create anything until the user picks.
