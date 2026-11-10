---
name: voiceover
description: Make spoken audio (MP3 voiceovers) from text with ElevenLabs — narration for TikTok, Reels, YouTube, ads, explainers or podcasts. Use when the user asks for a voiceover, narration, text-to-speech, "read this out", or to list or pick ElevenLabs voices.
---

# Voiceover (ElevenLabs)

Uses `tools/elevenlabs/voiceover.py` from the claude-to-cto repo. It needs the
`ELEVENLABS_API_KEY` environment variable. If it is missing, tell the user to
create a key at https://elevenlabs.io/app/settings/api-keys and set it — never
ask them to paste the key into chat.

## Steps
1. **Script first.** Write or tidy the script for speaking, not reading:
   - Short sentences. One idea per sentence.
   - Write numbers and symbols the way they're said ("twenty-five percent", not "25%").
   - Spell out acronyms that should be read letter by letter ("A-I").
   - Hook in the first sentence for short-form video (first 3 seconds).
   - Aim for ~150 words per minute of audio; tell the user the estimated length.
2. **Check the budget** for long scripts: `python3 tools/elevenlabs/voiceover.py quota`.
3. **Pick a voice.** If the user named one, use it; otherwise `voices` lists what's on their account. Default is George.
4. **Generate:**
   ```bash
   python3 tools/elevenlabs/voiceover.py speak --file script.txt --voice "<name>" -o voiceover.mp3
   ```
   - One file per paragraph (for video scenes): add `--split -o scenes/`.
   - Faster and cheaper drafts: `--model eleven_flash_v2_5`.
   - More energetic delivery: `--stability 0.35 --style 0.3`. Calmer: `--stability 0.7`.
   - Slightly faster pace for TikTok: `--speed 1.1`.
5. **Hand over** the file path, voice, settings, and character count used. Offer one tweak (pace, energy, voice) rather than a list.

## Rules
- Only voices on the user's own account. Never imitate a real person's voice without their documented consent.
- Never print, log or commit the API key.
