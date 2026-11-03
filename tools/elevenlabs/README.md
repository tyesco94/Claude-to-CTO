# ElevenLabs voiceover tool

Turn a script into an MP3 voiceover. Python 3.8+, no packages to install.

## Setup
1. Create an API key: https://elevenlabs.io/app/settings/api-keys
2. Set it in your terminal (don't commit it):
   ```bash
   export ELEVENLABS_API_KEY=your_key
   ```

## Use
```bash
python3 tools/elevenlabs/voiceover.py voices                    # your voices
python3 tools/elevenlabs/voiceover.py quota                     # characters left
python3 tools/elevenlabs/voiceover.py speak "Hello!" -o hello.mp3
python3 tools/elevenlabs/voiceover.py speak --file script.txt --voice Rachel -o script.mp3
python3 tools/elevenlabs/voiceover.py speak --file script.txt --split -o scenes/   # one MP3 per paragraph
```

| Option | Meaning |
|---|---|
| `--voice` | voice name or id (default George; or set `ELEVENLABS_VOICE`) |
| `--model` | `eleven_multilingual_v2` (best, default) or `eleven_flash_v2_5` (fast, cheaper) |
| `--stability` | 0–1, lower = more expressive (default 0.5) |
| `--style` | 0–1, more dramatic delivery (default 0) |
| `--speed` | 0.7–1.2 (default 1.0) |

Long scripts are split into ~4,000-character pieces on sentence boundaries and joined into one MP3.

In Claude, the `voiceover` skill (in `skills/voiceover/`) uses this tool: just ask "make a voiceover of this script".
