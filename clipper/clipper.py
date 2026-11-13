"""Clipping agent: cut the best moments of a long video (podcast, stream, show) into vertical Shorts.

  python3 clip.py URL [--count 3] [--len 59] [--crop] [--from 1:00:00 --to 2:00:00] [--pick-only]
  python3 clip.py URL --campaign NAME        # one video under a campaign's rules
  python3 clip.py day NAME [--count 5]       # newest unclipped video of each source in campaigns/NAME.json

Steps: captions (or whisper) -> Claude picks moments -> only those minutes are downloaded -> 1080x1920 render
with a hook title bar and 3-word captions. Results go in output/, the tracker in data/campaigns/NAME/log.csv."""
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw

from .free_pick import free_candidates
from .helpers import (ROOT, YELLOW, _font, _length, _run, _timings, _wrap, ask, config, extract_json, ffbin,
                      read_json, slugify, write_json)

W, H = 1080, 1920
FPS = 30
CACHE = ROOT / "data" / "clipsrc"
CHUNK = 20 * 60  # seconds of transcript per Claude call
PER_CHUNK = 3  # moments asked for per part
MIN_LEN = 20  # shorter picks are stretched to this, if the video allows it
PAD = 2.0  # extra seconds downloaded on each side of a moment
TITLE_SECS = 3.0  # how long the hook title bar shows
BAR_TOP, BAR_H = 440, 170  # white title bar, above the middle picture (picture starts at y 656 in blur mode)
CAP_Y = 1330  # caption line, under the middle picture
GAP_BREAK = 0.6  # a pause this long starts a new caption chunk


def _secs(v):
    """'SS', 'MM:SS' or 'HH:MM:SS' -> seconds (None stays None)."""
    if v in (None, ""):
        return None
    total = 0.0
    for part in str(v).split(":"):
        total = total * 60 + float(part)
    return total


def _clock(t):
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60}:{t % 60:02d}"


# ---------------------------------------------------------------- source + transcript

def source(src):
    """(cache folder, info) for a URL or a local file."""
    p = Path(src)
    if p.exists():
        info = {"id": slugify(p.stem)[:40] or "local", "title": p.stem, "channel": "", "url": "", "local": str(p),
                "duration": _length(p), "extractor": ""}
    else:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as y:
            i = y.extract_info(src, download=False)
        info = {"id": i["id"], "title": i.get("title", ""), "channel": i.get("channel") or i.get("uploader") or "",
                "url": i.get("webpage_url") or src, "local": "", "duration": float(i.get("duration") or 0),
                "extractor": i.get("extractor_key", "")}
    d = CACHE / re.sub(r"[^A-Za-z0-9_-]", "", info["id"])
    d.mkdir(parents=True, exist_ok=True)
    write_json(d / "info.json", info)
    print(f"SOURCE: {info['title']} ({info['channel'] or 'local file'}, {_clock(info['duration'])})", flush=True)
    return d, info


def _json3(path):
    """YouTube json3 captions -> [[seconds, text], ...]."""
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for e in data.get("events", []):
        t = " ".join("".join(s.get("utf8", "") for s in e.get("segs") or []).split())
        if t:
            out.append([round(e.get("tStartMs", 0) / 1000, 1), t])
    return out


def _captions(d, info):
    """The platform's own English captions (manual or auto), or None."""
    if info["local"]:
        return None
    import yt_dlp
    for langs in (["en-orig", "en"], ["en.*"]):
        o = {"quiet": True, "no_warnings": True, "skip_download": True, "writesubtitles": True,
             "writeautomaticsub": True, "subtitleslangs": langs, "subtitlesformat": "json3",
             "outtmpl": str(d / "subs")}
        try:
            with yt_dlp.YoutubeDL(o) as y:
                y.download([info["url"]])
        except Exception as e:
            print(f"clipper: captions failed ({str(e).splitlines()[0][:160]})", flush=True)
        files = sorted(d.glob("subs.*.json3"), key=lambda f: (".en-orig." not in f.name, ".en." not in f.name))
        if files:
            lines = _json3(files[0])
            if lines:
                print(f"TRANSCRIPT: captions ({files[0].name.split('.')[1]}, {len(lines)} lines)", flush=True)
                return lines
    return None


def _wav(src, dst, start=None, dur=None):
    """16 kHz mono wav of src (optionally start..start+dur) for whisper."""
    _run([*(["-ss", f"{start:.2f}"] if start is not None else []), "-i", src,
          *(["-t", f"{dur:.2f}"] if dur is not None else []), "-vn", "-ac", "1", "-ar", "16000", dst])


def _words(wav):
    return _timings(wav)


def _whisper_lines(d, info, lo, hi):
    """No captions: whisper the window lo..hi of the audio. Slow on this PC (about real time or worse)."""
    f = d / f"whisper_{int(lo)}_{int(hi)}.json"
    got = read_json(f, None)
    if got is not None:
        return got
    print(f"TRANSCRIPT: no captions; whisper on {_clock(hi - lo)} of audio (slow on this PC, "
          "use --from/--to for a shorter window)", flush=True)
    wav = d / "window.wav"
    if info["local"]:
        _wav(info["local"], wav, lo, hi - lo)
    else:
        import yt_dlp
        from yt_dlp.utils import download_range_func
        for old in d.glob("audio.*"):
            old.unlink()
        o = {"quiet": True, "no_warnings": True, "noprogress": True, "format": "ba/b",
             "download_ranges": download_range_func(None, [(lo, hi)]), "outtmpl": str(d / "audio.%(ext)s"),
             "ffmpeg_location": ffbin("ffmpeg")}
        with yt_dlp.YoutubeDL(o) as y:
            y.download([info["url"]])
        got_audio = next(iter(d.glob("audio.*")), None)
        if not got_audio:
            raise SystemExit("clipper: could not download the audio")
        _wav(got_audio, wav)
        got_audio.unlink()
    lines, cur = [], None
    for w, s, e in _words(wav):  # words -> lines of about 8 s
        if cur is None or s - cur[0] > 8:
            cur = [round(lo + s, 1), w]
            lines.append(cur)
        else:
            cur[1] += " " + w
    wav.unlink()
    write_json(f, lines)
    return lines


def transcript(d, info, lo, hi):
    f = d / "transcript.json"
    lines = read_json(f, None)
    if lines is None:
        lines = _captions(d, info)
        if lines:
            write_json(f, lines)
    if not lines:
        lines = _whisper_lines(d, info, lo, hi)
    return [ln for ln in lines if lo <= ln[0] <= hi]


# ---------------------------------------------------------------- pick

def _candidates(d, info, lines, max_len, lo, hi, min_len=MIN_LEN):
    cache = d / f"picks_{int(lo)}_{int(hi)}_{max_len}{'' if min_len == MIN_LEN else f'_{min_len}'}.json"
    got = read_json(cache, None)
    if got is not None:
        return got
    if config().get("ai") == "free":
        print("PICK: free picker (no Claude)", flush=True)
        got = free_candidates(lines, min_len, max_len, info.get("duration"))
        write_json(cache, got)
        return got
    template = (ROOT / "prompts" / "clip_pick.md").read_text(encoding="utf-8")
    got, t = [], lo
    while t < hi:
        part = [ln for ln in lines if t <= ln[0] < t + CHUNK]
        if sum(len(x[1].split()) for x in part) > 60:  # skip near-silent parts
            prompt = template.format(title=info["title"], channel=info["channel"] or "unknown", from_t=_clock(t),
                                     to_t=_clock(min(t + CHUNK, hi)), n=PER_CHUNK, min_len=min_len, max_len=max_len,
                                     transcript="\n".join(f"[{x[0]:.0f}] {x[1]}" for x in part))
            try:
                reply = extract_json(ask(prompt, config()["model"], max_tokens=8000))
            except (Exception, SystemExit) as e:  # usage limit, signed out, no key, offline...
                print(f"FALLBACK: Claude could not pick ({str(e)[:120]}); using the free picker instead", flush=True)
                done = [ln for ln in lines if ln[0] >= t]  # keep Claude's picks so far, free-pick the rest
                got += free_candidates(done, min_len, max_len, info.get("duration"))
                write_json(cache, got)  # cached like Claude's picks; delete picks_*.json to re-pick with Claude
                return got
            for m in reply if isinstance(reply, list) else []:
                try:
                    got.append({"start": float(m["start"]), "end": float(m["end"]), "title": str(m["title"])[:95],
                                "hook": str(m.get("hook", "")), "why": str(m.get("why", "")),
                                "score": float(m.get("score", 0))})
                except (KeyError, TypeError, ValueError):
                    continue
            print(f"PICK: {_clock(t)}-{_clock(min(t + CHUNK, hi))}: {len(got)} moments so far", flush=True)
        t += CHUNK
    write_json(cache, got)
    return got


def pick(d, info, lines, count, max_len, lo, hi, min_len=MIN_LEN):
    """The best `count` non-overlapping moments, each min_len..max_len seconds."""
    chosen = []
    for m in sorted(_candidates(d, info, lines, max_len, lo, hi, min_len), key=lambda m: -m["score"]):
        start = max(0.0, m["start"])
        end = min(m["end"], start + max_len, info["duration"] or 1e9)
        if end - start < min_len:
            end = min(start + min_len, info["duration"] or 1e9)
        if end - start < 12 or any(start < c["end"] and end > c["start"] for c in chosen):
            continue
        chosen.append({**m, "start": round(start, 1), "end": round(end, 1)})
        if len(chosen) == count:
            break
    return chosen


# ---------------------------------------------------------------- cut

def cut(out, info, start, end):
    """out/source.mp4 = start-PAD .. end+PAD of the video (with audio). Returns the offset of `start` in it."""
    a, b = max(0.0, start - PAD), end + PAD
    dest = out / "source.mp4"
    if info["local"]:
        _run(["-ss", f"{a:.2f}", "-to", f"{b:.2f}", "-i", info["local"], "-c:v", "libx264", "-preset", "veryfast",
              "-crf", "18", "-c:a", "aac", "-b:a", "192k", dest])
        return start - a
    import yt_dlp
    from yt_dlp.utils import download_range_func
    for old in out.glob("source.*"):
        old.unlink()
    o = {"quiet": True, "no_warnings": True, "noprogress": True, "overwrites": True,
         "format": "bv*[height<=1080]+ba/b[height<=1080]/b", "merge_output_format": "mp4",
         "download_ranges": download_range_func(None, [(a, b)]), "force_keyframes_at_cuts": True,
         "outtmpl": str(out / "source.%(ext)s"), "ffmpeg_location": ffbin("ffmpeg")}
    with yt_dlp.YoutubeDL(o) as y:
        y.download([info["url"]])
    got = next((p for p in out.glob("source.*") if p.suffix in (".mp4", ".mkv", ".webm")), None)
    if not got:
        raise SystemExit("clipper: the clip download failed")
    if got != dest:
        got.rename(dest)
    return start - a


# ---------------------------------------------------------------- pictures

def _title_png(path, text):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, BAR_TOP, W, BAR_TOP + BAR_H], fill=(255, 255, 255, 255))
    size = 76
    while size > 34:
        f = _font("segoeuiz.ttf", size)  # bold italic, same as the Recap bar
        lines = _wrap(d, text.upper().strip(), f, W - 100)
        if len(lines) <= 2:
            break
        size -= 4
    lh = size * 1.12
    y = BAR_TOP + BAR_H / 2 - lh * len(lines) / 2
    for ln in lines:
        d.text((W / 2, y + lh / 2), ln, font=f, fill=(0, 0, 0), anchor="mm")
        y += lh
    im.save(path)


def _key(words):
    """Index of the word drawn yellow: a number, else the longest word of 5+ letters, else none."""
    clean = [re.sub(r"[^A-Za-z0-9$%]", "", w) for w in words]
    for i, w in enumerate(clean):
        if re.search(r"\d", w):
            return i
    best = max(range(len(clean)), key=lambda i: len(clean[i]), default=None)
    return best if best is not None and len(clean[best]) >= 5 else None


def _chunks(words, dur):
    """Whisper words [(w, s, e)] -> caption chunks of up to 3 words; a pause starts a new chunk."""
    out = []
    for w, s, e in words:
        if s >= dur:
            break
        if out and len(out[-1]["words"]) < 3 and s - out[-1]["end"] < GAP_BREAK:
            out[-1]["words"].append(w)
            out[-1]["end"] = e
        else:
            out.append({"words": [w], "start": s, "end": e})
    for a, b in zip(out, out[1:]):
        if b["start"] - a["end"] < GAP_BREAK:
            a["end"] = b["start"]  # no flicker between close chunks
    return out


def _caption_png(path, words):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = _key(words)
    size = 70
    while True:
        f = _font("segoeuib.ttf", size)
        total = d.textlength(" ".join(words), font=f)
        if total <= W - 80 or size <= 40:
            break
        size -= 4
    x = (W - total) / 2
    for i, w in enumerate(words):
        d.text((x, CAP_Y), w, font=f, fill=YELLOW if i == k else (255, 255, 255), stroke_width=6,
               stroke_fill=(0, 0, 0))
        x += d.textlength(w + " ", font=f)
    im.save(path)


def _caption_track(work, chunks, dur):
    """A concat list that plays caption PNGs (and a blank one in the gaps) for the whole clip."""
    blank = work / "blank.png"
    Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(blank)
    rows, t = [], 0.0
    for i, ch in enumerate(chunks):
        start, end = max(ch["start"], t), min(ch["end"], dur)
        if end - start < 0.05:
            continue
        if start > t:
            rows.append((blank, start - t))
        png = work / f"cap{i:03d}.png"
        _caption_png(png, ch["words"])
        rows.append((png, end - start))
        t = end
    rows.append((blank, max(dur - t, 0.1)))
    lst = work / "captions.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\nduration {d:.3f}\n" for p, d in rows)
                   + f"file '{rows[-1][0].as_posix()}'\n", encoding="utf-8")
    return lst


# ---------------------------------------------------------------- render

def _look(layout):
    if layout == "crop":
        return f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}[base]"
    return (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"boxblur=30:2,eq=brightness=-0.12[bg];[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={FPS}[base]")


def render(out):
    s = read_json(out / "script.json", None)
    if not s or s.get("kind") != "clip":
        raise SystemExit(f"clipper: {out / 'script.json'} is not a clip script")
    src = s["source"]
    if not (out / "source.mp4").exists():
        s["offset"] = cut(out, read_json(CACHE / re.sub(r"[^A-Za-z0-9_-]", "", src["id"]) / "info.json", {})
                          or {"url": src["url"], "local": src.get("local", "")}, src["start"], src["end"])
        write_json(out / "script.json", s)
    offset, dur = s["offset"], src["end"] - src["start"]
    work = out / "clip_parts"
    work.mkdir(exist_ok=True)
    wav = work / "voice.wav"
    _wav(out / "source.mp4", wav, offset, dur)
    words = _words(wav)
    print(f"CAPTIONS: {len(words)} words heard", flush=True)
    spoken = " ".join(w for w, _, _ in words)
    if spoken and s.get("script") != spoken:
        s["script"], s["lines"] = spoken, [{"text": spoken}]
        write_json(out / "script.json", s)
    title = work / "title.png"
    _title_png(title, s.get("title_bar") or s["title"])
    caps = _caption_track(work, _chunks(words, dur), dur)
    final = out / "final.mp4"
    _run(["-ss", f"{offset:.2f}", "-t", f"{dur:.2f}", "-i", out / "source.mp4",
          "-loop", "1", "-framerate", FPS, "-t", f"{dur:.2f}", "-i", title,
          "-f", "concat", "-safe", "0", "-i", caps,
          "-filter_complex", _look(s.get("layout", "blur")) + ";"
          f"[base][1:v]overlay=0:0:enable='lt(t,{TITLE_SECS})'[t1];[2:v]format=rgba,fps={FPS}[cap];"
          "[t1][cap]overlay=0:0:eof_action=pass[v];[0:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]",
          "-map", "[v]", "-map", "[a]", "-t", f"{dur:.2f}", "-r", FPS, "-c:v", "libx264", "-preset", "veryfast",
          "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ac", "2", final])
    print(f"DONE: {final} ({dur:.1f} s)", flush=True)
    return final


def _link(info, start):
    url = info["url"]
    if not url or info.get("extractor") != "Youtube":
        return url
    return f"{url}{'&' if '?' in url else '?'}t={int(start)}s"


def _folder(title, info, start):
    base = slugify(title) or f"clip-{info['id']}"
    for n in range(1, 50):
        out = ROOT / "output" / (base if n == 1 else f"{base}-{n}")
        old = read_json(out / "script.json", None)
        if not old or (old.get("source", {}).get("id") == info["id"] and old["source"].get("start") == start):
            return out
    raise SystemExit("clipper: too many folders with this title")


def make(src, count=3, max_len=59, layout="blur", lo=None, hi=None, pick_only=False, campaign=None):
    d, info = source(src)
    min_len = MIN_LEN
    if campaign:
        _allowed(campaign, info)
        min_len, max_len = int(campaign.get("min_len", min_len)), int(campaign.get("max_len", max_len))
        layout = campaign.get("layout", layout)
    lo, hi = _secs(lo) or 0.0, _secs(hi) or info["duration"] or 1e9
    lines = transcript(d, info, lo, hi)
    if not lines:
        raise SystemExit("clipper: no transcript (no captions and whisper heard nothing)")
    moments = pick(d, info, lines, count, max_len, lo, hi, min_len)
    if not moments:
        raise SystemExit("clipper: Claude found no strong moments in this video")
    for i, m in enumerate(moments, 1):
        print(f"MOMENT {i}: {_clock(m['start'])}-{_clock(m['end'])} score {m['score']:g} | {m['title']} | {m['why']}",
              flush=True)
    if pick_only:
        return moments
    made = []
    for i, m in enumerate(moments, 1):
        out = _folder(m["title"], info, m["start"])
        out.mkdir(parents=True, exist_ok=True)
        credit = f"Clip from {info['channel']}'s video \"{info['title']}\"" if info["channel"] else ""
        s = {"kind": "clip", "title": m["title"], "title_bar": m["hook"] or m["title"], "why": m["why"],
             "score": m["score"], "layout": layout,
             "source": {"url": info["url"], "title": info["title"], "channel": info["channel"], "id": info["id"],
                        "local": info["local"], "start": m["start"], "end": m["end"]},
             "script": "", "lines": [],
             "description": "\n\n".join(x for x in (m["title"], f"{credit}: {_link(info, m['start'])}"
                                                    if credit else "", "#shorts #clips") if x)}
        if campaign:
            s["campaign"] = campaign["name"]
            s["description"] = _caption(campaign, m, info)
        write_json(out / "script.json", s)
        if campaign:
            (out / "post.txt").write_text(s["description"] + "\n", encoding="utf-8")
        print(f"CLIP {i}/{len(moments)}: cutting {_clock(m['start'])}-{_clock(m['end'])}", flush=True)
        s["offset"] = cut(out, info, m["start"], m["end"])
        write_json(out / "script.json", s)
        made.append(render(out))
    return made


# ---------------------------------------------------------------- campaigns

def load_campaign(name):
    """campaigns/NAME.json (see _example.json for the fields)."""
    f = ROOT / "campaigns" / f"{name}.json"
    c = read_json(f, None)
    if not c:
        have = ", ".join(p.stem for p in f.parent.glob("*.json") if not p.stem.startswith("_")) or "none yet"
        raise SystemExit(f"clipper: no campaign {f.name} (have: {have})")
    return {**c, "name": name}


def _allowed(c, info):
    """Campaigns only pay for clips of their own creator: stop before spending anything on a wrong source."""
    ok = [x.lower() for x in c.get("allowed_channels", [])]
    if ok and not info["local"] and (info["channel"] or "").lower() not in ok:
        raise SystemExit(f"clipper: channel \"{info['channel']}\" is not allowed in campaign {c['name']} "
                         f"(allowed: {', '.join(c['allowed_channels'])})")


def _caption(c, m, info):
    """The post caption: campaign template + required tag + hashtags."""
    text = c.get("caption", "{title}").format(title=m["title"], hook=m["hook"], channel=info["channel"],
                                              source_title=info["title"])
    tail = " ".join(x for x in (c.get("mention", ""), " ".join(c.get("hashtags", []))) if x)
    return f"{text}\n\n{tail}".strip()


def _newest(url, n=5):
    """Newest n video URLs of a channel/playlist URL (a single video URL comes back as itself)."""
    import yt_dlp
    if "watch?v=" in url or "youtu.be/" in url:
        return [url]
    if re.search(r"youtube\.com/(@|c/|channel/|user/)[^/]+/?$", url):
        url = url.rstrip("/") + "/videos"
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "extract_flat": True, "playlistend": n}) as y:
        i = y.extract_info(url, download=False)
    return [e.get("url") or f"https://www.youtube.com/watch?v={e['id']}" for e in (i.get("entries") or [])][:n]


def _log(c, rows):
    import csv
    f = ROOT / "data" / "campaigns" / c["name"] / "log.csv"
    f.parent.mkdir(parents=True, exist_ok=True)
    new = not f.exists()
    with f.open("a", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        if new:
            w.writerow(["date", "folder", "title", "source", "post_link", "views", "approved", "payout"])
        w.writerows(rows)
    return f


def day(name, count=None, pick_only=False):
    """One clipping session: the newest not-yet-clipped video of each source, cut under the campaign's rules."""
    import datetime
    c = load_campaign(name)
    count = int(count or c.get("count", 5))
    done_f = ROOT / "data" / "campaigns" / name / "done.json"
    done = read_json(done_f, [])
    today = datetime.date.today().isoformat()
    sheet, rows = [f"# Clip day: {name} ({today})", ""], []
    if c.get("whop_url"):
        sheet += [f"Submit links at: {c['whop_url']}", ""]
    for src in c.get("sources", []):
        try:
            todo = next((u for u in _newest(src) if u not in done), None)
        except Exception as e:
            print(f"clipday: could not list {src} ({str(e).splitlines()[0][:160]})", flush=True)
            continue
        if not todo:
            print(f"clipday: nothing new on {src}", flush=True)
            continue
        try:
            got = make(todo, count=count, pick_only=pick_only, campaign=c)
        except SystemExit as e:
            print(f"clipday: skipped {todo} ({e})", flush=True)
            continue
        if pick_only:
            continue
        done.append(todo)
        write_json(done_f, done)
        for final in got:
            s = read_json(final.parent / "script.json", {})
            sheet += [f"## {s.get('title', final.parent.name)}", f"Video: {final}", "", "```",
                      s.get("description", ""), "```", ""]
            rows.append([today, final.parent.name, s.get("title", ""), todo, "", "", "", ""])
    if pick_only:
        return []
    if not rows:
        print("clipday: no clips made today", flush=True)
        return []
    out = ROOT / "output" / f"clipday-{name}-{today}.md"
    out.write_text("\n".join(sheet), encoding="utf-8")
    print(f"CLIPDAY: {len(rows)} clips; post list {out}; tracker {_log(c, rows)}", flush=True)
    return out
