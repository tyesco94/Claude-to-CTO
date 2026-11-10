"""Small helpers the clipper needs: settings, JSON files, ffmpeg, fonts, Claude, whisper word timings."""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from PIL import ImageFont

ROOT = Path(__file__).resolve().parent.parent
YELLOW = (255, 214, 10)


# ---------------------------------------------------------------- files + settings

def read_json(path, default):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def write_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def config():
    return read_json(ROOT / "settings.json", {"model": "claude-sonnet-5-5"})


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def extract_json(text):
    """Pull the first JSON array/object out of a model reply."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start = min((i for i in (text.find("["), text.find("{")) if i != -1), default=-1)
    if start == -1:
        raise ValueError("no JSON found in model reply")
    return json.loads(text[start:])


def load_env():
    """Read KEY=VALUE lines from .env (made by 'Save My Key.command'). Never prints values."""
    env = ROOT / ".env"
    if not env.exists():
        raise SystemExit("No key saved yet. Double-click 'Save My Key.command' first.")
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


# ---------------------------------------------------------------- ffmpeg

def ffbin(name="ffmpeg"):
    """ffmpeg from the Mac (Homebrew) if there is one, else the copy pip installed (imageio-ffmpeg)."""
    found = shutil.which(name)
    if found:
        return found
    for p in ("/opt/homebrew/bin/" + name, "/usr/local/bin/" + name):
        if Path(p).exists():
            return p
    if name == "ffmpeg":
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
    raise SystemExit(f"{name} not found. Double-click 'Setup.command' again.")


def _run(args):
    r = subprocess.run([ffbin("ffmpeg"), "-v", "error", "-y", *map(str, args)], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("ffmpeg failed: " + r.stderr.strip()[-600:])


def _length(path):
    """Seconds of a video file (read from ffmpeg's own report, so ffprobe is not needed)."""
    r = subprocess.run([ffbin("ffmpeg"), "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


# ---------------------------------------------------------------- fonts + text

_MAC_FONTS = {
    "bolditalic": ["/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
                   "/Library/Fonts/Arial Bold Italic.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf"],
    "bold": ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf",
             "/System/Library/Fonts/Helvetica.ttc",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
}


def _font(name, size):
    """name 'segoeuiz.ttf' = bold italic (title bar), anything else = bold (captions)."""
    kind = "bolditalic" if "z" in Path(name).stem[-1:] else "bold"
    for p in _MAC_FONTS[kind] + _MAC_FONTS["bold"] + [str(ROOT / "fonts" / name)]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def _wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


# ---------------------------------------------------------------- Claude

def ask(prompt, model=None, max_tokens=8000):
    """settings.json "ai": "claude-plan" (default) uses the Claude Code login (Pro/Max plan usage);
    "api-key" uses the API key saved by 'Save My Key.command'."""
    if config().get("ai", "claude-plan") != "api-key":
        return _ask_plan(prompt)
    load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("No Claude key found. Double-click 'Save My Key.command' first.")
    import anthropic
    msg = anthropic.Anthropic(timeout=max(120, max_tokens / 60), max_retries=2).messages.create(
        model=model or config()["model"], max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in msg.content if b.type == "text")


def _claude_bin():
    found = shutil.which("claude")
    if found:
        return found
    for p in (Path.home() / ".local/bin/claude", Path.home() / ".claude/local/claude",
              Path("/opt/homebrew/bin/claude"), Path("/usr/local/bin/claude")):
        if p.exists():
            return str(p)
    raise SystemExit("Claude Code is not installed. Double-click 'Setup.command' again.")


def _ask_plan(prompt):
    """Ask through Claude Code ('claude -p'), which runs on the Claude plan the user signed in with."""
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    try:
        r = subprocess.run([_claude_bin(), "-p", "--model", config().get("plan_model", "sonnet"),
                            "--output-format", "text"], input=prompt, capture_output=True, text=True,
                           encoding="utf-8", timeout=900, env=env)
    except subprocess.TimeoutExpired:
        raise SystemExit("Claude took too long to answer. Try again in a few minutes.")
    text = (r.stdout or "").strip()
    problem = (r.stderr or "").strip() or text
    low = problem.lower()
    if r.returncode or not text:
        if "login" in low or "log in" in low or "api key" in low or "auth" in low:
            raise SystemExit("Claude is not signed in. Double-click 'Sign In to Claude.command' first.")
        if "limit" in low:
            raise SystemExit("Your Claude plan's usage limit is reached. Try again after it resets.")
        raise SystemExit("Claude did not answer: " + problem[-300:])
    return text


# ---------------------------------------------------------------- whisper

_whisper = None


def _timings(wav):
    """Word timings [(word, start, end)] for a 16 kHz mono wav (faster-whisper 'base' on the CPU)."""
    import soundfile as sf
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel("base", device="cpu", compute_type="int8")
    audio, _ = sf.read(wav, dtype="float32")
    segments, _ = _whisper.transcribe(audio, language="en", word_timestamps=True)
    return [(w.word.strip(), w.start, w.end) for seg in segments for w in seg.words or [] if w.word.strip()]
