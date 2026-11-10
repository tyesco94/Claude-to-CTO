---
name: project-memory
description: Maintain a long-term memory file (PROJECT_MEMORY.md) for a project so key facts, decisions, preferences and progress survive long conversations. Use at the start of work in a project, when the user says "remember this", when an important decision is made, or when the user asks what was decided earlier.
---

# Long-Term Project Memory

## The memory file: PROJECT_MEMORY.md
```
# Project: <name>
_Last updated: <date>_

## Goal
## Key facts & context
## Decisions (dated, with reason)
## Preferences & style rules
## People & roles
## Open tasks / next steps
## Things that did NOT work (don't retry)
## Glossary
```

## Behavior
1. **Start of a session**: if PROJECT_MEMORY.md exists (project files or uploaded), read it first and briefly confirm what you know. If it doesn't exist, ask for the project name + a short summary and create it.
2. **During work**: when a decision is made, a preference is stated, a fact is learned, or a task is finished — update the file (or, if you can't write files, print the updated section and tell the user to save it).
3. **Keep it short**: bullets, under ~2 pages. Merge and prune outdated items; move finished tasks to a one-line "Done" log.
4. **When asked "what did we decide about X"** — answer from the file first.
5. At the end of a long session, output the full updated file.
