#!/usr/bin/env python3
"""Daily scripture posts: a feed card (1080x1350), a Reel (1080x1920, slow zoom) and a caption per verse.

  python3 tools/scripture/make_posts.py                      # all verses in verses.json -> output/scripture/
  python3 tools/scripture/make_posts.py --days 7 --start 2026-11-12 --brand "My Page"
  python3 tools/scripture/make_posts.py --only 5             # just verse #5
  python3 tools/scripture/make_posts.py --no-reels           # cards only (fast)

Verses are King James Version (public domain). Needs Pillow and ffmpeg.
"""
import argparse
import csv
import datetime
import json
import random
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

PALETTES = [  # (top, bottom) gradient colours
    ((246, 214, 180), (196, 128, 112)),  # rose gold
    ((190, 214, 230), (92, 120, 160)),   # morning blue
    ((250, 226, 170), (214, 140, 90)),   # sunrise
    ((214, 226, 200), (110, 140, 112)),  # sage
    ((226, 208, 236), (130, 104, 160)),  # lavender
    ((244, 222, 206), (150, 112, 96)),   # warm sand
]

FONT_DIRS = ["/System/Library/Fonts/Supplemental", "/Library/Fonts", "/usr/share/fonts/truetype/dejavu",
             str(HERE / "fonts")]
SERIF = ["Georgia.ttf", "DejaVuSerif.ttf"]
SERIF_B = ["Georgia Bold.ttf", "DejaVuSerif-Bold.ttf"]
SANS = ["Arial.ttf", "DejaVuSans.ttf"]

REFLECTIONS = {
    "strength": "When you feel weak, His strength is already at work in you.",
    "grace": "You don't have to earn it. His grace is enough, today and every day.",
    "faithfulness": "Yesterday is gone. This morning, His mercy is brand new.",
    "provision": "Everything you need, He already knows.",
    "trust": "You don't have to figure it all out. Trust Him with the next step.",
    "hope": "Your story isn't over. God's plans for you are good.",
    "rest": "Lay it down. You were never meant to carry it alone.",
    "purpose": "Even this season is being worked together for your good.",
    "courage": "Wherever you go today, you are not going alone.",
    "healing": "If your heart is heavy, He is closer than you think.",
    "peace": "Breathe. Give Him the worry and keep the peace.",
    "joy": "Find one reason to rejoice today. He made this day for you.",
    "help": "Look up. Your help is on the way.",
    "fearless": "Fear doesn't get the final word. God does.",
    "presence": "You are held. He has never let go of you.",
    "delight": "Seek Him first and watch your heart change.",
    "victory": "With God for you, nothing can stand against you.",
    "love": "He doesn't just love you. He rejoices over you.",
}
PROMPTS = ["Type Amen if you needed this today 🙏", "Share this with someone who needs it ❤️",
           "Who are you praying for today? 🙏", "Type 'I receive it' if this is for you 🙌",
           "Tag someone who needs this reminder ❤️"]
TAGS = "#DailyScripture #BibleVerse #GodsGrace #Faith #Jesus #Christian #Encouragement"


def font(names, size):
    for n in names:
        for d in FONT_DIRS:
            p = Path(d) / n
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def background(w, h, top, bottom, seed):
    grad = Image.linear_gradient("L").resize((w, h))
    im = Image.composite(Image.new("RGB", (w, h), bottom), Image.new("RGB", (w, h), top), grad).convert("RGBA")
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    rnd = random.Random(seed)
    for _ in range(26):  # soft bokeh light
        r = rnd.randint(30, 140)
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        g.ellipse([x - r, y - r, x + r, y + r], fill=(255, 250, 235, rnd.randint(18, 55)))
    im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(28)))
    vig = Image.new("L", (w, h), 0)
    ImageDraw.Draw(vig).ellipse([-w * 0.25, -h * 0.2, w * 1.25, h * 1.2], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(160))
    return Image.composite(im, Image.alpha_composite(im, Image.new("RGBA", (w, h), (40, 25, 20, 120))), vig)


def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for wd in text.split():
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=f) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    return lines + [cur]


def card(w, h, verse, ref, palette, seed, brand):
    im = background(w, h, *palette, seed)
    d = ImageDraw.Draw(im)
    size = 74
    while True:
        f = font(SERIF, size)
        lines = wrap(d, "“" + verse + "”", f, w - 200)
        lh = size * 1.38
        if lh * len(lines) < h * 0.5 or size <= 44:
            break
        size -= 4
    y = h / 2 - lh * len(lines) / 2 - 40
    for ln in lines:
        d.text((w / 2 + 2, y + 3), ln, font=f, fill=(60, 35, 25, 90), anchor="ma")
        d.text((w / 2, y), ln, font=f, fill=(255, 255, 255), anchor="ma")
        y += lh
    d.line([w / 2 - 60, y + 30, w / 2 + 60, y + 30], fill=(255, 255, 255), width=3)
    d.text((w / 2, y + 60), ref.upper(), font=font(SERIF_B, 40), fill=(255, 255, 255), anchor="ma")
    footer = f"{brand}  ·  KJV" if brand else "KJV"
    d.text((w / 2, h - 90), footer, font=font(SANS, 28), fill=(255, 255, 255, 210), anchor="ma")
    return im.convert("RGB")


def reel(png, mp4, secs=12):
    ff = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    frames = secs * 30
    vf = (f"scale=1188:2112,zoompan=z='1+0.08*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={frames}:s=1080x1920:fps=30,fade=t=in:st=0:d=0.8,fade=t=out:st={secs - 0.8}:d=0.8,format=yuv420p")
    subprocess.run([ff, "-v", "error", "-y", "-loop", "1", "-framerate", "30", "-t", str(secs), "-i", str(png),
                    "-f", "lavfi", "-t", str(secs), "-i", "anullsrc=r=44100:cl=stereo", "-vf", vf,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-shortest",
                    "-movflags", "+faststart", str(mp4)], check=True)


def caption(verse, ref, theme, i):
    return (f"“{verse}” — {ref} (KJV)\n\n{REFLECTIONS.get(theme, '')}\n\n"
            f"{PROMPTS[i % len(PROMPTS)]}\n\n{TAGS}")


def slug(ref):
    return "".join(c.lower() if c.isalnum() else "-" for c in ref).strip("-").replace("--", "-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, help="how many posts (default: every verse)")
    ap.add_argument("--start", help="first post date YYYY-MM-DD (default: tomorrow)")
    ap.add_argument("--only", type=int, help="make just this verse number (1-based)")
    ap.add_argument("--brand", default="", help="page name shown on each card")
    ap.add_argument("--out", default=str(ROOT / "output" / "scripture"))
    ap.add_argument("--no-reels", action="store_true")
    a = ap.parse_args()

    verses = json.loads((HERE / "verses.json").read_text(encoding="utf-8"))
    picks = [verses[a.only - 1]] if a.only else verses[: a.days or len(verses)]
    start = datetime.date.fromisoformat(a.start) if a.start else datetime.date.today() + datetime.timedelta(days=1)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, (ref, verse, theme) in enumerate(picks):
        n = (a.only - 1) if a.only else i
        day = start + datetime.timedelta(days=i)
        name = f"{i + 1:02d}-{slug(ref)}"
        pal = PALETTES[n % len(PALETTES)]
        card(1080, 1350, verse, ref, pal, n, a.brand).save(out / f"{name}-feed.jpg", quality=92)
        if not a.no_reels:
            png = out / f"{name}-reel.png"
            card(1080, 1920, verse, ref, pal, n, a.brand).save(png)
            reel(png, out / f"{name}-reel.mp4")
            png.unlink()
        rows.append([day.isoformat(), name, ref, verse, caption(verse, ref, theme, n)])
        print(f"ok {name}", flush=True)
    with (out / "captions.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(["date", "file", "reference", "verse", "caption"])
        w.writerows(rows)
    print(f"DONE: {len(rows)} posts in {out} (captions.csv has the post text and dates)")


if __name__ == "__main__":
    main()
