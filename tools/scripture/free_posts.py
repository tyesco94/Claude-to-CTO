#!/usr/bin/env python3
"""God page content at $0: public-domain Bible paintings and free landscape photos from Wikimedia
Commons, brought to life as vertical "living picture" videos with the KJV verse fading in.

  python3 tools/scripture/ai_posts.py plan --draft tools/scripture/god_page_45.json --start 2026-12-01 --brand "My Page"
  python3 tools/scripture/free_posts.py              # every day in the plan
  python3 tools/scripture/free_posts.py --only 1     # just day 1

Per day, in output/god-page/: NN-*-photo.jpg (the source image), NN-*-post.jpg (1080x1350 feed post)
and NN-*-reel.mp4 (1080x1920, 15 s). captions.csv gets a credit line for every image.
Only public domain, CC0 and CC BY images are used (CC BY is credited in the caption).
No API keys. Needs Pillow and ffmpeg. Finished days are skipped.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ai_posts as A  # noqa: E402  (plan, captions, post card)
from make_posts import SANS, SERIF, SERIF_B, font, wrap  # noqa: E402

OUT = A.OUT
UA = {"User-Agent": "GodPageBot/1.0 (https://github.com/tyesco94/Claude-to-CTO) python-urllib"}
OK_LICENSES = ("public domain", "cc0", "pd", "cc by 1.0", "cc by 2.0", "cc by 2.5", "cc by 3.0", "cc by 4.0")
SECS = 15
W, H = 1080, 1920


def ok_license(name):
    n = (name or "").lower().strip()
    if "sa" in n.split() or "-sa" in n or "nc" in n or "nd" in n:
        return False
    return any(n.startswith(x) or n == x for x in OK_LICENSES)


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def get(url, timeout=120):
    """GET from Wikimedia, politely: one request at a time, waiting and retrying when asked to slow down."""
    for wait in (0, 30, 90, 240, 600, 900):
        time.sleep(wait or float(os.environ.get("WIKI_PAUSE", "3")))  # seconds between requests
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                raw = r.read()
                return json.loads(raw) if "json" in r.headers.get("Content-Type", "") else raw
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise SystemExit(f"Wikimedia {e.code}: {e.read()[:200]!r}")
            print("  Wikimedia asked to slow down; waiting...", flush=True)
    raise SystemExit("Wikimedia is still rate-limiting; try again in a few minutes.")


NOT_PAINTING = ("rp-p", "print", "engraving", "etching", "mezzotint", "lithograph", "woodcut", "drawing", "naar ",
                "sketch", "map", "stamp", "coin", "ontwerp", "titelblad", "titelpagina", "prent", "tekening", "gravure",
                "kupferstich", "zeichnung", "holzschnitt", "illustration", "book", "page", "manuscript", "bible card")
NOT_PHOTO = ("frame", "museum", "exhibition", "postcard", "poster", "logo", "detail", "sculpture", "statue", "relief")


def find_image(queries, photo=False):
    """First Commons file across the queries with a usable license and enough pixels.
    photo=True (verse days) skips prints, scans and museum shots, to get real landscape photos."""
    for q in queries:
        url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search"
               f"&gsrnamespace=6&gsrlimit=15&gsrsearch={urllib.parse.quote(q + ' filetype:bitmap')}"
               "&prop=imageinfo&iiprop=url|extmetadata|size|mime&iiurlwidth=2000")
        pages = get(url).get("query", {}).get("pages", {})
        for p in sorted(pages.values(), key=lambda p: p.get("index", 99)):
            ii = p["imageinfo"][0]
            m = ii.get("extmetadata", {})
            lic = clean(m.get("LicenseShortName", {}).get("value"))
            if ii.get("mime") not in ("image/jpeg", "image/png") or min(ii["width"], ii["height"]) < 900:
                continue
            if not ok_license(lic):
                continue
            title = p["title"].lower()
            if any(w in title for w in NOT_PAINTING + (NOT_PHOTO if photo else ())):
                continue
            artist = clean(m.get("Artist", {}).get("value")) or "Unknown"
            return {"url": ii.get("thumburl") or ii["url"], "page": ii["descriptionurl"], "license": lic,
                    "artist": artist[:80], "title": p["title"][5:], "query": q}
    return None


def shrink(path, longest=2400):
    from PIL import Image
    im = Image.open(path)
    if max(im.size) > longest:
        im.thumbnail((longest, longest))
        im.save(path, quality=90)


def credit_line(img):
    lic = img["license"]
    if lic.lower().startswith("cc by"):
        return f"Image: {img['artist']}, {lic}, via Wikimedia Commons"
    return f"Image: {img['artist']} (public domain), via Wikimedia Commons"


def text_layer(d, brand, path):
    """Transparent 1080x1920 PNG: dark fade at the bottom, KJV quote, reference and page name."""
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fade = Image.linear_gradient("L").resize((W, H)).point(lambda v: max(0, v - 90) * 235 // 165)
    im.paste(Image.new("RGBA", (W, H), (10, 8, 6, 255)), (0, 0), fade)
    dr = ImageDraw.Draw(im)
    size = 62
    while True:
        f = font(SERIF, size)
        lines = wrap(dr, "“" + d["quote"] + "”", f, W - 150)
        lh = size * 1.36
        if lh * len(lines) < H * 0.32 or size <= 38:
            break
        size -= 2
    y = H - 330 - lh * len(lines)
    for ln in lines:
        dr.text((W / 2 + 2, y + 2), ln, font=f, fill=(0, 0, 0, 160), anchor="ma")
        dr.text((W / 2, y), ln, font=f, fill=(255, 255, 255, 255), anchor="ma")
        y += lh
    dr.line([W / 2 - 50, y + 24, W / 2 + 50, y + 24], fill=(255, 255, 255, 220), width=3)
    dr.text((W / 2, y + 48), d["quote_reference"].upper() + " · KJV", font=font(SERIF_B, 36),
            fill=(255, 255, 255, 255), anchor="ma")
    if brand:
        dr.text((W / 2, H - 150), brand, font=font(SANS, 30), fill=(235, 235, 235, 230), anchor="ma")
    im.save(path)


def hook_layer(d, path):
    """Transparent PNG with the hook near the top, shown for the first seconds."""
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    top = Image.linear_gradient("L").rotate(180).resize((W, H)).point(lambda v: max(0, v - 150) * 200 // 105)
    im.paste(Image.new("RGBA", (W, H), (10, 8, 6, 255)), (0, 0), top)
    dr = ImageDraw.Draw(im)
    f = font(SERIF_B, 58)
    y = 230
    for ln in wrap(dr, d["hook"], f, W - 160):
        dr.text((W / 2 + 2, y + 2), ln, font=f, fill=(0, 0, 0, 170), anchor="ma")
        dr.text((W / 2, y), ln, font=f, fill=(255, 255, 255, 255), anchor="ma")
        y += 78
    im.save(path)


def reel(photo, hook_png, text_png, mp4):
    """Living picture: slow pan/zoom across the image, gentle light breathing, film grain, vignette;
    hook for the first 4 s, then the verse fades in."""
    ff = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    S = SECS
    bg = (f"[0:v]scale={int(W * 1.18)}:{int(H * 1.18)}:force_original_aspect_ratio=increase,"
          f"crop={int(W * 1.12)}:{int(H * 1.12)}:x='(iw-ow)*t/{S}':y='(ih-oh)*(0.5+0.5*sin(t/{S}*3.14))/2',"
          f"scale={W}:{H},setsar=1,"
          f"eq=brightness='0.025*sin(2*PI*t/5)':saturation=1.05:eval=frame,"
          f"noise=alls=4:allf=t,vignette=PI/5,format=yuv420p[bg]")
    graph = (f"{bg};"
             f"[1:v]format=rgba,fade=t=in:st=0.3:d=0.8:alpha=1,fade=t=out:st=3.6:d=0.7:alpha=1[hook];"
             f"[2:v]format=rgba,fade=t=in:st=4.0:d=1.4:alpha=1[txt];"
             f"[bg][hook]overlay=0:0:shortest=1[a];[a][txt]overlay=0:0:shortest=1,"
             f"fade=t=in:st=0:d=0.6,fade=t=out:st={S - 0.8}:d=0.8,format=yuv420p[v]")
    subprocess.run([ff, "-v", "error", "-y",
                    "-loop", "1", "-framerate", "30", "-t", str(S), "-i", str(photo),
                    "-loop", "1", "-framerate", "30", "-t", str(S), "-i", str(hook_png),
                    "-loop", "1", "-framerate", "30", "-t", str(S), "-i", str(text_png),
                    "-f", "lavfi", "-t", str(S), "-i", "anullsrc=r=44100:cl=stereo",
                    "-filter_complex", graph, "-map", "[v]", "-map", "3:a",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-maxrate", "6M", "-bufsize", "12M", "-r", "30",
                    "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(mp4)], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", type=int, help="just this day number")
    a = ap.parse_args()
    plan = A.load_plan()
    brand = plan.get("brand", "")
    for d in A.pick(plan, a.only):
        base = OUT / d["name"]
        photo, reel_mp4 = Path(f"{base}-photo.jpg"), Path(f"{base}-reel.mp4")
        if not photo.exists() or not d.get("credit"):
            img = find_image(d.get("art_query") or [d["title"] + " painting"], photo=d["kind"] == "verse")
            if not img:
                print(f"SKIP {d['name']}: no free image found; add art_query terms in plan.json", flush=True)
                continue
            A.save_jpeg(get(img["url"]), photo)
            shrink(photo)
            d["image"], d["credit"] = img, credit_line(img)
        A.post_card(photo, d, brand, Path(f"{base}-post.jpg"))
        if not reel_mp4.exists():
            hook_png, text_png = Path(f"{base}-hook.png"), Path(f"{base}-text.png")
            hook_layer(d, hook_png)
            text_layer(d, brand, text_png)
            reel(photo, hook_png, text_png, reel_mp4)
            hook_png.unlink()
            text_png.unlink()
        print(f"ok {d['name']}  ({d['image']['title'][:50]}, {d['image']['license']})", flush=True)
        (OUT / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    A.write_captions(plan)
    print(f"DONE: {OUT} (captions.csv has the post text, dates and image credits)")


if __name__ == "__main__":
    main()
