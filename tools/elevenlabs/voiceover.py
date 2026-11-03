#!/usr/bin/env python3
"""Turn text or a script file into an MP3 voiceover with ElevenLabs.

Standard library only. Needs an ElevenLabs API key in the ELEVENLABS_API_KEY
environment variable (create one at https://elevenlabs.io/app/settings/api-keys).

Examples:
  python3 voiceover.py voices                      # list the voices on your account
  python3 voiceover.py quota                       # characters used / left this month
  python3 voiceover.py speak "Hello there" -o hello.mp3
  python3 voiceover.py speak --file script.txt --voice Rachel -o script.mp3
  python3 voiceover.py speak --file script.txt --split -o out/   # one MP3 per paragraph
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = os.environ.get("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io").rstrip("/")
DEFAULT_VOICE = os.environ.get("ELEVENLABS_VOICE", "JBFqnCBsd6RMkjVDRZzb")  # "George", a stock voice
DEFAULT_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
MAX_CHUNK = 4000  # characters per request; long scripts are split on sentence boundaries


class ApiError(Exception):
    pass


def api_key():
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise ApiError(
            "ELEVENLABS_API_KEY is not set. Create a key at "
            "https://elevenlabs.io/app/settings/api-keys and run:  export ELEVENLABS_API_KEY=your_key"
        )
    return key


def request(method, path, body=None, accept="application/json", query=None):
    url = API_BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("xi-api-key", api_key())
    req.add_header("Accept", accept)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        hint = {401: " (check your API key)", 402: " (out of credits?)", 422: " (bad voice, model or text)",
                429: " (rate limited, try again shortly)"}.get(e.code, "")
        raise ApiError(f"ElevenLabs returned HTTP {e.code}{hint}: {detail}") from None
    except urllib.error.URLError as e:
        raise ApiError(f"Could not reach ElevenLabs at {API_BASE}: {e.reason}") from None


def list_voices():
    data = json.loads(request("GET", "/v1/voices"))
    return [
        {
            "voice_id": v.get("voice_id"),
            "name": v.get("name"),
            "category": v.get("category"),
            "labels": v.get("labels") or {},
        }
        for v in data.get("voices", [])
    ]


def resolve_voice(voice):
    """Accept a voice id or a voice name (case-insensitive)."""
    if not voice:
        return DEFAULT_VOICE
    if re.fullmatch(r"[A-Za-z0-9]{20}", voice):
        return voice
    for v in list_voices():
        if (v["name"] or "").lower() == voice.lower():
            return v["voice_id"]
    raise ApiError(f"No voice named '{voice}' on your account. Run:  python3 voiceover.py voices")


def chunk_text(text, limit=MAX_CHUNK):
    """Split text into pieces under `limit` characters, breaking between sentences."""
    text = re.sub(r"[ \t]+", " ", text).strip()
    if len(text) <= limit:
        return [text] if text else []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for s in sentences:
        while len(s) > limit:  # a single giant sentence: hard split on a space
            cut = s.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            if current:
                chunks.append(current)
                current = ""
            chunks.append(s[:cut].strip())
            s = s[cut:].strip()
        if len(current) + len(s) + 1 > limit:
            chunks.append(current)
            current = s
        else:
            current = f"{current} {s}".strip()
    if current:
        chunks.append(current)
    return chunks


def synthesize(text, voice_id, model, stability, similarity, style, speed, fmt):
    body = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity,
            "style": style,
            "use_speaker_boost": True,
            "speed": speed,
        },
    }
    return request("POST", f"/v1/text-to-speech/{voice_id}", body=body, accept="audio/mpeg",
                   query={"output_format": fmt})


def cmd_voices(args):
    voices = list_voices()
    if args.json:
        print(json.dumps(voices, indent=2))
        return
    for v in voices:
        labels = ", ".join(f"{k}: {val}" for k, val in v["labels"].items())
        print(f"{v['name']:<24} {v['voice_id']}  [{v['category']}] {labels}")
    print(f"\n{len(voices)} voices. Use a name or id with:  speak --voice <name-or-id>")


def cmd_quota(args):
    sub = json.loads(request("GET", "/v1/user/subscription"))
    used, limit = sub.get("character_count", 0), sub.get("character_limit", 0)
    print(f"Plan: {sub.get('tier', '?')}  |  characters used: {used:,} / {limit:,}  |  left: {max(limit - used, 0):,}")


def cmd_speak(args):
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        text = " ".join(args.text)
    else:
        text = sys.stdin.read()
    if not text.strip():
        raise ApiError("No text given. Pass text, --file script.txt, or pipe text in.")

    voice_id = resolve_voice(args.voice)
    settings = (args.model, args.stability, args.similarity, args.style, args.speed, args.format)

    if args.split:
        out_dir = Path(args.output or "voiceover")
        out_dir.mkdir(parents=True, exist_ok=True)
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        for i, para in enumerate(paragraphs, 1):
            audio = b"".join(synthesize(c, voice_id, *settings) for c in chunk_text(para))
            path = out_dir / f"{i:02d}.mp3"
            path.write_bytes(audio)
            print(f"wrote {path}  ({len(para)} chars)")
        print(f"{len(paragraphs)} files in {out_dir}/")
        return

    chunks = chunk_text(text)
    out = Path(args.output or "voiceover.mp3")
    out.parent.mkdir(parents=True, exist_ok=True)
    # MP3 frames can be joined end to end, so long scripts become one file.
    audio = b"".join(synthesize(c, voice_id, *settings) for c in chunks)
    out.write_bytes(audio)
    print(f"wrote {out}  ({len(text)} chars, {len(chunks)} request{'s' if len(chunks) != 1 else ''}, voice {voice_id})")


def main(argv=None):
    p = argparse.ArgumentParser(description="ElevenLabs voiceover tool")
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("voices", help="list voices on your account")
    v.add_argument("--json", action="store_true")
    v.set_defaults(func=cmd_voices)

    q = sub.add_parser("quota", help="show characters used and left")
    q.set_defaults(func=cmd_quota)

    s = sub.add_parser("speak", help="turn text into an MP3")
    s.add_argument("text", nargs="*", help="text to speak (or use --file, or pipe text in)")
    s.add_argument("--file", "-f", help="read the script from a text file")
    s.add_argument("--output", "-o", help="output .mp3 (or a folder with --split)")
    s.add_argument("--voice", "-v", help="voice name or id (default: George, or $ELEVENLABS_VOICE)")
    s.add_argument("--model", "-m", default=DEFAULT_MODEL,
                   help="eleven_multilingual_v2 (best quality, default) or eleven_flash_v2_5 (fast, cheap)")
    s.add_argument("--split", action="store_true", help="one MP3 per paragraph instead of one file")
    s.add_argument("--stability", type=float, default=0.5, help="0-1: lower = more expressive")
    s.add_argument("--similarity", type=float, default=0.75, help="0-1: how closely to match the voice")
    s.add_argument("--style", type=float, default=0.0, help="0-1: style exaggeration")
    s.add_argument("--speed", type=float, default=1.0, help="0.7-1.2: speaking speed")
    s.add_argument("--format", default="mp3_44100_128", help="ElevenLabs output_format")
    s.set_defaults(func=cmd_speak)

    args = p.parse_args(argv)
    try:
        args.func(args)
    except ApiError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
