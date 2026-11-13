"""Free moment picker: no Claude, no API, no cost. Scores stretches of the transcript for comedy and
viral signals so the clipper keeps working when Claude's usage limit is reached (or with "ai": "free").

Signals, per transcript line: laughter/applause markers in the captions ([Laughter], (laughs), haha),
questions and exclamations, punchy words, numbers, and how fast people are talking. A moment starts where
a thought starts (after a pause, or on a question) and ends a few seconds after its best payoff.
Not as smart as Claude, but it never stops."""
import re

LAUGH = re.compile(r"\[(laughter|laughs?|laughing|applause|cheering|crowd)[^\]]*\]|\((laughs?|laughing|applause)\)|"
                   r"\b(ha){2,}\b|\bhaha\w*\b|\blmao\b|\blol\b", re.I)
PUNCH = re.compile(r"\b(never|always|crazy|insane|worst|best|funniest|nobody|everybody|bro|wait|what\??|stop|"
                   r"literally|honestly|secret|truth|lie|lied|wrong|fight|money|million|broke|fired|caught|"
                   r"embarrass\w*|scared|shocked|can't believe|no way|oh my god|deadass|for real)\b", re.I)
HOOK_START = re.compile(r"^(so|okay|listen|look|wait|bro|yo|man|you know what|let me tell you|the thing is|"
                        r"here's the thing|what|why|how|who|did you|have you|i swear|nah)\b", re.I)
STARTER = re.compile(r"^[A-Z\[\(\"']|^(so|okay|listen|look|wait|bro|yo|you know)\b", re.I)


def _line_score(text):
    laughs = len(LAUGH.findall(text))
    return (6.0 * laughs + 1.5 * text.count("?") + 1.0 * text.count("!") + 1.2 * len(PUNCH.findall(text))
            + 0.6 * bool(re.search(r"\d", text)))


def _clean(text):
    return " ".join(LAUGH.sub(" ", text).replace(">>", " ").split())


def _title_bits(lines):
    words = " ".join(_clean(t) for _, t in lines).split()
    first = " ".join(words[:14]).rstrip(",.;:")
    hook = " ".join(words[:6]).upper().rstrip(",.;:!?")
    return (first[:90] or "Funny moment"), (hook or "WAIT FOR IT")


def free_candidates(lines, min_len, max_len, duration=None, top=30):
    """Lines [[seconds, text], ...] -> moments like Claude's picks (start, end, title, hook, why, score)."""
    lines = [ln for ln in lines if ln[1].strip()]
    if len(lines) < 3:
        return []
    end_of = lambda i: lines[i + 1][0] if i + 1 < len(lines) else lines[i][0] + 4
    scores = [_line_score(t) for _, t in lines]
    out = []
    for i, (s, text) in enumerate(lines):
        gap = s - lines[i - 1][0] if i else 99
        if not (gap > 1.5 or HOOK_START.search(text) or STARTER.search(text)):
            continue  # start where a thought starts
        j, best_j, best = i, i, 0.0
        total = 0.0
        while j < len(lines) and end_of(j) - s <= max_len:
            total += scores[j]
            if scores[j] >= best and end_of(j) - s >= min_len * 0.6:
                best, best_j = scores[j], j
            j += 1
        if best_j == i and j > i:
            best_j = j - 1
        e = min(end_of(best_j) + (2.5 if LAUGH.search(lines[best_j][1]) else 0.8), s + max_len)
        if duration:
            e = min(e, duration)
        if e - s < 12:
            continue
        span = lines[i:best_j + 1]
        words = sum(len(_clean(t).split()) for _, t in span)
        pace = words / max(e - s, 1)  # words per second; lively talk is about 2.5-3.5
        hook_bonus = 3.0 if HOOK_START.search(text) or "?" in text else 0.0
        if max(scores[i:best_j + 1]) < 2.5:  # needs a real payoff: a laugh, or a question plus a punchy line
            continue
        raw = total + hook_bonus + 2.0 * min(pace, 3.5) - 0.02 * max(0, (e - s) - 45)
        title, hook = _title_bits(span)
        laughs = sum(len(LAUGH.findall(t)) for _, t in span)
        why = (f"{laughs} laugh/applause marker(s), " if laughs else "") + f"{pace:.1f} words/s, free picker"
        out.append({"start": round(s, 1), "end": round(e, 1), "title": title, "hook": hook, "why": why, "raw": raw})
    if not out:
        return []
    hi = max(m["raw"] for m in out) or 1
    for m in out:
        m["score"] = round(1 + 8 * max(m.pop("raw"), 0) / hi, 1)  # 1-9: Claude's 10s stay rarer
    return sorted(out, key=lambda m: -m["score"])[:top]
