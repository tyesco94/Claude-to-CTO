# Claude to CTO

A shared workspace for Claude and cto.new: both work on this repository through GitHub.

## What's inside
| Folder | What it is |
|---|---|
| `plugins/power-kit/` | A Claude Code plugin: project memory across sessions, a token guard for huge files, a skill observer, and `/recommend-setup` |
| `skills/` | 10 Claude skills (dashboards, content engine, research auditor, contrarian partner, meeting notes, email writer, presentations, competitor teardown, YouTube launch kit, project memory) |
| `tools/elevenlabs/` | ElevenLabs voiceover tool: script → MP3 in your chosen voice (see its README) |
| `skills/voiceover/` | Claude skill that writes speakable scripts and runs the voiceover tool |
| `clip.py` + `clipper/` | Clipping agent: Claude picks the best moments of a long video and renders vertical Shorts with a hook title bar and 3-word captions (see below) |
| `AGENTS.md` | Working rules every AI agent (Claude, cto.new, others) follows in this repo |

## Install the plugin in Claude Code
```
/plugin marketplace add tyesco94/claude-to-cto
/plugin install power-kit@claude-to-cto
```
Restart Claude Code afterwards. The hooks need `python3`.

## Use the skills on claude.ai
Zip any folder in `skills/` (the zip must contain the folder) and upload it in **Customize → Skills → Add → Upload a skill**.
Fill in the `___` blanks in content-engine, brand-email-writer, brand-presentation and youtube-launch-kit first.

## How Claude and cto.new share this repo
1. Each agent works on its own branch and opens a pull request — never commits straight to `main`.
2. The other agent (or you) reviews the pull request before merging.
3. `AGENTS.md` holds the rules both follow, so they stay consistent.

## Clipping agent
```
pip install -r clipper/requirements.txt
python3 clip.py VIDEO_OR_URL --count 3 --len 59            # best 3 clips, up to 59 s each
python3 clip.py VIDEO_OR_URL --from 10:00 --to 40:00 --pick-only   # just list the moments
python3 clip.py VIDEO_OR_URL --crop                        # fill the frame instead of a blurred background
python3 clip.py day NAME                                   # newest video of each source in campaigns/NAME.json
```
Needs ffmpeg and a signed-in Claude Code (`claude`), which picks the moments on your Claude plan; set `"ai": "api-key"` in `settings.json` to use an API key from `.env` instead, or `"ai": "free"` to pick moments with no AI at all (laughter markers, questions, punchy lines, pace). If Claude can't answer (usage limit, signed out), the clipper falls back to the free picker on its own. Results go to `output/<clip-title>/final.mp4`. Copy `campaigns/_example.json` to start a campaign.
