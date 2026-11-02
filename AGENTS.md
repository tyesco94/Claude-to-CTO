# Rules for AI agents working in this repo

These apply to every agent (Claude, cto.new, others) and to people.

## Workflow
- Work on a new branch named `<agent>/<short-task>` (for example `claude/add-email-skill`, `cto/fix-memory-hook`). Never push to `main`.
- Open a pull request per task, with a short description: what changed, why, and how it was tested.
- Keep pull requests small — one task each.
- Don't merge your own pull request; the owner (or the other agent, when asked) reviews it.

## Repo layout
- `plugins/power-kit/` — Claude Code plugin. `hooks/hooks.json` wires the Python scripts in `scripts/` (standard library only, Python 3.8+).
- `skills/<name>/SKILL.md` — one skill per folder. Frontmatter needs `name` and `description`; the description says *when* to use the skill.
- `.claude-plugin/marketplace.json` — lists the plugin; bump `version` in it and in `plugins/power-kit/.claude-plugin/plugin.json` together.

## Checks before opening a pull request
- `python3 -m py_compile plugins/power-kit/scripts/*.py`
- JSON files parse: `python3 -c "import json,glob;[json.load(open(f)) for f in glob.glob('**/*.json',recursive=True)]"`
- If you have the Claude Code CLI: `claude plugin validate .`

## Never
- Commit secrets, API keys, tokens or personal data.
- Add dependencies to the hook scripts (they must run on a plain Python install).
