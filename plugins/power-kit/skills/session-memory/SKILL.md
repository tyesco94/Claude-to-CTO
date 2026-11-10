---
name: session-memory
description: Keep a curated long-term memory file for the current project so facts, decisions and preferences survive between Claude Code sessions. Use when the user says "remember", "don't forget", "note that", makes or changes a decision, states a preference, or asks what was decided before. Also use when the session starts with "[power-kit] Memory for ..." in context.
---

# Session Memory

The power-kit plugin loads this project's memory at the start of every session
(look for the `[power-kit] Memory for ...` message, which names the exact
`MEMORY.md` path) and logs a short note about each session automatically.

The automatic log only records *what* happened. **You** keep `MEMORY.md`
— the curated part — accurate.

## MEMORY.md layout
```
# Project memory
## Goal
## Key facts
## Decisions (YYYY-MM-DD — decision — why)
## Preferences and style
## Open tasks
## Tried and did not work
```

## Rules
1. **Read first.** Trust the loaded memory, but if it conflicts with the code, the code wins — fix the memory.
2. **Write when it matters**: a decision is made or reversed, the user states a preference, a fact is learned that a future session would otherwise have to rediscover, a task is finished, or an approach fails.
3. **Edit, don't append forever.** Update the existing line, remove stale items, keep the file under ~150 lines.
4. **Never store secrets** (API keys, passwords, tokens, personal data).
5. When the user asks "what did we decide about X", answer from MEMORY.md and the session log, and say so.
6. If no `MEMORY.md` exists yet and something worth remembering comes up, create it at the path the start-up message gave.
