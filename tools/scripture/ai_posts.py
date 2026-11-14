#!/usr/bin/env python3
"""God page content with AI: a 30-45 day plan of Bible stories and verses, a photo per day
(OpenAI) and a short natural-looking video per day (Replicate), plus captions.

Run the steps in order. Each step skips days that are already done, so re-running never pays twice.

  python3 tools/scripture/ai_posts.py plan   --days 45 --start 2026-12-01 --brand "My Page"
  python3 tools/scripture/ai_posts.py images --yes            # OpenAI photos (costs credits)
  python3 tools/scripture/ai_posts.py videos --yes            # Replicate videos (costs credits)
  python3 tools/scripture/ai_posts.py images --only 1 --yes   # just day 1, to test the look

Keys: OPENAI_API_KEY and REPLICATE_API_TOKEN in the environment or in a .env file at the repo root.
Output: output/god-page/ (plan.json, captions.csv, NN-*-photo.jpg, NN-*-post.jpg, NN-*-video.mp4).
Scripture text is the King James Version (public domain), fetched from bible-api.com, never written by AI.
Standard library only, plus Pillow for the post images.
"""
import argparse
import base64
import csv
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = ROOT / "output" / "god-page"
STYLE_FILE = HERE / "style.md"  # optional: paste the owner's template / style notes here

TEXT_MODEL = os.environ.get("GOD_PAGE_TEXT_MODEL", "gpt-5.5")
IMAGE_MODEL = os.environ.get("GOD_PAGE_IMAGE_MODEL", "gpt-image-2")
VIDEO_MODEL = os.environ.get("GOD_PAGE_VIDEO_MODEL", "bytedance/seedance-1-pro")
VIDEO_SECONDS = int(os.environ.get("GOD_PAGE_VIDEO_SECONDS", "5"))

# Rough prices to warn before spending; check your own dashboards for exact numbers.
EST_IMAGE_USD = 0.25
EST_VIDEO_USD = 0.75

LOOK = ("Photorealistic, natural documentary feel, as if filmed on location in the ancient Near East: "
        "real people with natural skin texture, period-accurate clothing and settings, soft natural light, "
        "shallow depth of field, subtle film grain. No text, no captions, no logos, no halos, no fantasy glow, "
        "no modern objects. Respectful and reverent.")


# ---------- helpers ----------

def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def http(url, data=None, headers=None, method=None, timeout=300):
    body = json.dumps(data).encode() if isinstance(data, (dict, list)) else data
    h = {"Content-Type": "application/json"} if isinstance(data, (dict, list)) else {}
    h.update(headers or {})
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return json.loads(raw) if "json" in r.headers.get("Content-Type", "") else raw
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise SystemExit(f"{method or ('POST' if data else 'GET')} {url.split('?')[0]} failed: {e.code} {detail}")


def key(name):
    v = os.environ.get(name)
    if not v:
        raise SystemExit(f"Missing {name}. Put it in .env at the repo root (never commit that file).")
    return v


def openai(path, payload, timeout=300):
    return http("https://api.openai.com/v1/" + path, payload,
                {"Authorization": "Bearer " + key("OPENAI_API_KEY")}, timeout=timeout)


def kjv(reference):
    q = urllib.parse.quote(reference)
    d = http(f"https://bible-api.com/{q}?translation=kjv")
    text = " ".join(d["text"].split())
    return d["reference"], text


def slug(s):
    return "-".join("".join(c.lower() if c.isalnum() else " " for c in s).split())[:40]


def load_plan():
    p = OUT / "plan.json"
    if not p.exists():
        raise SystemExit("No plan yet. Run: python3 tools/scripture/ai_posts.py plan --days 45")
    return json.loads(p.read_text())


def pick(plan, only):
    return [d for d in plan["days"] if not only or d["day"] == only]


def confirm(n, each, what, yes):
    est = n * each
    print(f"{n} {what} to make, about ${est:.2f} (estimate).")
    if n and not yes:
        raise SystemExit("Nothing spent. Add --yes to go ahead.")


# ---------- step 1: plan ----------

PLAN_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["days"],
    "properties": {"days": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["kind", "title", "reference", "quote_reference", "hook", "story", "reflection",
                     "call_to_action", "hashtags", "image_prompt", "video_prompt"],
        "properties": {
            "kind": {"type": "string", "enum": ["story", "verse"]},
            "title": {"type": "string"},
            "reference": {"type": "string", "description": "Passage, e.g. 'Daniel 6:16-23' or 'Psalm 23:1'"},
            "quote_reference": {"type": "string", "description": "One to three verses to quote on the post, e.g. 'Daniel 6:22'"},
            "hook": {"type": "string", "description": "First line, under 90 characters"},
            "story": {"type": "string", "description": "Story days: 50-90 word plain-English retelling faithful to the passage. Verse days: empty string."},
            "reflection": {"type": "string", "description": "One or two short sentences applying it today"},
            "call_to_action": {"type": "string"},
            "hashtags": {"type": "array", "items": {"type": "string"}},
            "image_prompt": {"type": "string", "description": "One moment from the passage as a still photo: who, where, light, camera angle"},
            "video_prompt": {"type": "string", "description": "5 seconds of gentle, natural motion starting from that photo: what moves, camera move"},
        }}}}}


def cmd_plan(a):
    OUT.mkdir(parents=True, exist_ok=True)
    style = STYLE_FILE.read_text() if STYLE_FILE.exists() else "(no template yet)"
    prompt = (
        f"Plan {a.days} daily posts for a Christian social media page{' called ' + a.brand if a.brand else ''}. "
        "Alternate roughly 2 Bible story days for every 1 single-verse encouragement day. Cover both Old and New "
        "Testament: well-known stories (David and Goliath, Daniel in the lions' den, the prodigal son, Jesus calming "
        "the storm, Ruth and Naomi, ...) and less familiar ones. No repeats. Keep every retelling faithful to the "
        "text; do not invent details that contradict scripture. Warm, hopeful, non-denominational tone, short "
        "sentences for phones. Image and video prompts must describe real, natural scenes (no text in the image).\n\n"
        f"Owner's template / style notes:\n{style}")
    if a.draft:  # a plan written elsewhere (same fields as PLAN_SCHEMA); no OpenAI call
        days = json.loads(Path(a.draft).read_text())["days"][: a.days]
        print(f"Using {a.draft} ({len(days)} days)", flush=True)
    else:
        print(f"Planning {a.days} days with {TEXT_MODEL}...", flush=True)
        r = openai("responses", {
            "model": TEXT_MODEL, "input": prompt,
            "text": {"format": {"type": "json_schema", "name": "plan", "schema": PLAN_SCHEMA, "strict": True}},
        }, timeout=600)
        text = next(c["text"] for o in r["output"] if o["type"] == "message" for c in o["content"]
                    if c["type"] == "output_text")
        days = json.loads(text)["days"][: a.days]
    start = datetime.date.fromisoformat(a.start) if a.start else datetime.date.today() + datetime.timedelta(days=1)
    for i, d in enumerate(days):
        d["day"] = i + 1
        d["date"] = (start + datetime.timedelta(days=i)).isoformat()
        d["name"] = f"{i + 1:02d}-{slug(d['title'])}"
        d["quote_reference"], d["quote"] = kjv(d["quote_reference"])  # real KJV wording
        print(f"  {d['name']}  ({d['quote_reference']})", flush=True)
    plan = {"brand": a.brand, "created": datetime.datetime.now().isoformat(timespec="seconds"),
            "models": {"text": TEXT_MODEL, "image": IMAGE_MODEL, "video": VIDEO_MODEL}, "days": days}
    (OUT / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    write_captions(plan)
    print(f"DONE: {len(days)} days planned. Review {OUT / 'captions.csv'} before making images.")


def caption(d):
    parts = [d["hook"]]
    if d["story"]:
        parts.append(d["story"])
    parts += [f"“{d['quote']}” — {d['quote_reference']} (KJV)", d["reflection"], d["call_to_action"],
              " ".join("#" + h.lstrip("#") for h in d["hashtags"]), d.get("credit", "")]
    return "\n\n".join(p for p in parts if p)


def write_captions(plan):
    with (OUT / "captions.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(["date", "day", "file", "kind", "reference", "caption"])
        for d in plan["days"]:
            w.writerow([d["date"], d["day"], d["name"], d["kind"], d["reference"], caption(d)])


# ---------- step 2: images ----------

def cmd_images(a):
    plan = load_plan()
    todo = [d for d in pick(plan, a.only) if not (OUT / f"{d['name']}-photo.jpg").exists()]
    confirm(len(todo), EST_IMAGE_USD, "photos", a.yes)
    for d in todo:
        print(f"photo {d['name']}...", flush=True)
        prompt = f"{d['image_prompt']}\n\n{LOOK}"
        if "/" in IMAGE_MODEL:  # a Replicate model, e.g. google/imagen-4 or black-forest-labs/flux-1.1-pro
            raw = http(replicate_run(IMAGE_MODEL, {"prompt": prompt, "aspect_ratio": "9:16",
                                                   "output_format": "jpg"}), timeout=300)
        else:  # an OpenAI image model
            r = openai("images/generations", {"model": IMAGE_MODEL, "prompt": prompt, "size": "1024x1536", "n": 1})
            img = r["data"][0]
            raw = base64.b64decode(img["b64_json"]) if img.get("b64_json") else http(img["url"])
        photo = OUT / f"{d['name']}-photo.jpg"
        save_jpeg(raw, photo)
        post_card(photo, d, plan.get("brand", ""), OUT / f"{d['name']}-post.jpg")
    print(f"DONE: photos in {OUT}")


def save_jpeg(raw, path):
    from io import BytesIO
    from PIL import Image
    Image.open(BytesIO(raw)).convert("RGB").save(path, quality=93)


def post_card(photo, d, brand, out):
    """Feed post (1080x1350): the photo with the KJV quote over a soft dark fade."""
    from PIL import Image, ImageDraw
    sys.path.insert(0, str(HERE))
    from make_posts import SANS, SERIF, SERIF_B, font, wrap
    w, h = 1080, 1350
    im = Image.open(photo).convert("RGB")
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)))
    im = im.crop(((im.width - w) // 2, (im.height - h) // 2, (im.width - w) // 2 + w, (im.height - h) // 2 + h))
    fade = Image.linear_gradient("L").resize((w, h)).point(lambda v: max(0, v - 70) * 255 // 185)
    im = Image.composite(Image.new("RGB", (w, h), (12, 10, 8)), im, fade.point(lambda v: int(v * 0.85)))
    dr = ImageDraw.Draw(im)
    size = 54
    while True:
        f = font(SERIF, size)
        lines = wrap(dr, "“" + d["quote"] + "”", f, w - 160)
        lh = size * 1.35
        if lh * len(lines) < h * 0.3 or size <= 34:
            break
        size -= 2
    y = h - 170 - lh * len(lines)
    for ln in lines:
        dr.text((w / 2, y), ln, font=f, fill=(255, 255, 255), anchor="ma")
        y += lh
    dr.text((w / 2, y + 22), d["quote_reference"].upper() + " · KJV", font=font(SERIF_B, 30),
            fill=(255, 255, 255), anchor="ma")
    if brand:
        dr.text((w / 2, h - 60), brand, font=font(SANS, 26), fill=(230, 230, 230), anchor="ma")
    im.save(out, quality=92)


# ---------- step 3: videos ----------

def replicate_run(model, inputs):
    hdr = {"Authorization": "Bearer " + key("REPLICATE_API_TOKEN"), "Prefer": "wait=60"}
    p = http(f"https://api.replicate.com/v1/models/{model}/predictions", {"input": inputs}, hdr)
    while p["status"] not in ("succeeded", "failed", "canceled"):
        time.sleep(5)
        p = http(p["urls"]["get"], headers=hdr)
    if p["status"] != "succeeded":
        raise SystemExit(f"Replicate {p['status']}: {p.get('error')}")
    out = p["output"]
    return out[0] if isinstance(out, list) else out


def video_inputs(model, d, image_uri):
    prompt = f"{d['video_prompt']}. Natural, realistic motion, handheld documentary camera, no text."
    if model.startswith("kwaivgi/kling"):
        return {"prompt": prompt, "start_image": image_uri, "duration": 5 if VIDEO_SECONDS <= 5 else 10,
                "negative_prompt": "text, captions, watermark, cartoon, distorted faces"}
    if model.startswith("minimax/hailuo"):
        return {"prompt": prompt, "first_frame_image": image_uri, "duration": 6, "resolution": "1080p"}
    # bytedance/seedance-* and most others
    return {"prompt": prompt, "image": image_uri, "duration": VIDEO_SECONDS, "resolution": "1080p",
            "aspect_ratio": "9:16"}


def cmd_videos(a):
    plan = load_plan()
    days = pick(plan, a.only)
    missing = [d["name"] for d in days if not (OUT / f"{d['name']}-photo.jpg").exists()]
    if missing:
        raise SystemExit(f"Make the photos first (missing {len(missing)}, e.g. {missing[0]}).")
    todo = [d for d in days if not (OUT / f"{d['name']}-video.mp4").exists()]
    confirm(len(todo), EST_VIDEO_USD, f"videos ({VIDEO_MODEL}, {VIDEO_SECONDS}s)", a.yes)
    for d in todo:
        print(f"video {d['name']}... (1-3 minutes)", flush=True)
        uri = "data:image/jpeg;base64," + base64.b64encode((OUT / f"{d['name']}-photo.jpg").read_bytes()).decode()
        url = replicate_run(VIDEO_MODEL, video_inputs(VIDEO_MODEL, d, uri))
        (OUT / f"{d['name']}-video.mp4").write_bytes(http(url, timeout=600))
    print(f"DONE: videos in {OUT}")


def main():
    load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--days", type=int, default=45)
    p.add_argument("--start", help="first post date YYYY-MM-DD (default: tomorrow)")
    p.add_argument("--brand", default="", help="page name shown on posts")
    p.add_argument("--draft", help="use this plan JSON instead of asking OpenAI (KJV quotes are still fetched)")
    for n in ("images", "videos"):
        s = sub.add_parser(n)
        s.add_argument("--only", type=int, help="just this day number")
        s.add_argument("--yes", action="store_true", help="spend credits without asking")
    sub.add_parser("captions", help="rewrite captions.csv from plan.json after editing it")
    a = ap.parse_args()
    if a.cmd == "captions":
        write_captions(load_plan())
        return print(f"DONE: {OUT / 'captions.csv'}")
    {"plan": cmd_plan, "images": cmd_images, "videos": cmd_videos}[a.cmd](a)


if __name__ == "__main__":
    main()
