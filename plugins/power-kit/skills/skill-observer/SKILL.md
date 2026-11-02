---
name: skill-observer
description: Watch the work in a session for things worth turning into a new skill or a fix to an existing skill — repeated workflows, user corrections, "I always do it this way" methods — and log them, then turn them into skill updates when the user asks for a review. Use during multi-step work sessions, when the user corrects how Claude did something, and when the user asks to "review my skills", "improve my skills" or "what skills should I make".
---

# Skill Observer

Skills improve fastest from friction noticed during real work. Keep a small log
of it, and turn the log into skill changes on request.

## Where the log lives
`~/.claude/power-kit/skill-observations.md` (create it if missing). One entry per observation:

```
## NNN · YYYY-MM-DD · open
- Type: new-skill | improve-skill | simplify-skill
- Skill: <existing skill name, or proposed name>
- What happened: <specific, understandable weeks later>
- Suggested change: <concrete edit or new skill outline>
- Principle: <the general lesson>
```

## What to log
- **New skill**: the same multi-step task done for the second time; a method the user explains; "I always…".
- **Improve a skill**: a user correction; a skill gave wrong or outdated advice; a better way turned up.
- **Simplify a skill**: a rule that keeps being ignored or never matters.
- Do **not** log one-off typos, personal secrets, or anything that only makes sense with private client data.

## How to behave
1. Log quietly in the same turn — don't interrupt the user's task to announce it.
2. Before adding, check for an existing open entry saying the same thing; add to it instead of duplicating.
3. At the end of a substantial session, give a one-line note: "Logged N skill observations — say 'review my skills' when you want them applied."
4. **Review (only when the user asks):** read open entries, group them by skill, propose the concrete edits or new SKILL.md drafts, apply only what the user approves, then mark those entries `done`.
5. If the same rule gets broken twice, propose a hook or check that prevents it, not louder wording.
