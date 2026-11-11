# YT Engine (from 820's email)

Type a topic, get a finished vertical Short (YouTube Shorts / TikTok / Reels): script, fact-check,
voice, pictures, captions, assembly. The AI runs through Claude Code on your Claude plan (`claude -p`).
The engine itself is not stored in this repo; it lives in `~/Documents/YT-Engine` (Mac) after setup.

## Setup on the Mac
Paste `SETUP-PROMPT.txt` from the email into Claude Code, or double-click `Install.command`, then
`Start Studio.command` (browser opens http://localhost:8765). Keys are optional and go on the studio's Keys page.

## What it makes (`python run.py ...` in the YT-Engine folder)
| Command | Result |
|---|---|
| `video` | 25–40 s news-take Short from today's top headlines (2 versions; `--one` = 1) |
| `video --topic "story"` | news-take Short on a story in the news |
| `video --mine --topic "X" [--minutes 1-3]` | your own topic: Wikipedia + Library of Congress newspapers + Internet Archive + Google News |
| `video --doc` | ~5 min faceless documentary from the topic list |
| `script --oncam --topic "what you built"` | script for you to film yourself |
| `review DIR` / `approve DIR` | quality check, then your approval |
| `upload DIR [--public / --unlisted]` | upload an approved video to YouTube (private by default; `ytauth` once first) |
| `shorts DIR` | cut vertical Shorts out of a long video |
| `retention FILE.csv` | read a YouTube Studio retention export: where viewers leave |
| `learn` | pull stats of uploaded videos and improve the prompts |
| `facts --topic "X"` | 30 s interesting-facts mini documentary |
| `tips --topic "X"` | Claude / AI / automation tip with a mascot, screen demos and memes |
| `recap --topic "X"` | a character recaps a movie in first person |
| `theory --topic "X"` | movie-theory Short: question hook, clips, AI stills, one-word captions |

**Personalities** (`--persona`): `roast` (funny, default), `suspense` (spooky narrator, ends on a question),
`anyway` (gossip), `preview` (game-day preview, e.g. "Bills vs Chiefs"), `versus` (superhero fight, e.g. "Spider-Man vs Black Widow").

**Free extras:** `--story-rules` (stronger structure), `--polish-voice` (clearer, -14 LUFS), `--title-cards`,
`--background run|ride|drone|mine`, `--little-motion` (animated scenes), `--auto` (approve automatically if the review passes).

## Keys worth getting (studio → Keys, never in chat)
- **Pixabay** – free; stock footage for `--doc`, `--mine` and Facts videos. Get it at pixabay.com/api/docs.
- **YouTube Data API** – free; trending topic ideas and uploads. Google Cloud console → enable YouTube Data API v3.
- **ElevenLabs** – paid; better voices than the free edge-tts / Kokoro voices.
- **Replicate** – paid; AI pictures when nothing else fits.

**Look options** (news Shorts): `--captions green|red|yellow|rainbow`, `--color red|amber|cyan|magenta|lime|violet|orange`,
`--frame square|circle|triangle`, `--panel square|circle|triangle`, `--clips` (real YouTube clips instead of photos), `--draft` (fast 720p test).
Add `--script-only` to facts/tips/recap to write the script first and render later.

Not in this copy: Clip / Clip day (use this repo's `clip.py`), Playlists, NBA preview, and posting through Posterract.

## Good to know
- `recap`, `theory` and `--clips` pull real clips from movies and other people's videos. Keep them short and add commentary, since copyrighted clips can get a video claimed or taken down.
- The free Microsoft voice sometimes returns 403; the engine then switches to the Kokoro voice. Normal.
- News Shorts are written from today's headlines; a topic not in the news can fail the fact-check. Use `--mine` for evergreen topics.
- One video at a time; each uses some Claude plan usage. Finished videos: `output/<name>/final.mp4`.
