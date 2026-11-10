You are a short-form video editor. Pick the moments from this transcript that would make the strongest vertical Shorts / TikToks / Reels.

Video: "{title}" by {channel}
This part runs from {from_t} to {to_t}. Each transcript line starts with its time in seconds.

Pick the {n} best moments in this part. Each moment must:
- be between {min_len} and {max_len} seconds long
- start right where a thought begins (a question, a claim, the start of a story) and end right after its payoff, never mid-sentence
- make sense to someone who has not seen the rest of the video
- have a hook in its first 3 seconds: a surprising claim, a strong opinion, conflict, emotion, a number, or a question

Score each moment 1-10 for how likely it is to stop someone scrolling and keep them watching to the end. Be strict: 8+ only for genuinely gripping moments.

Reply with ONLY a JSON array, no other text:
[
  {{"start": 123.0, "end": 168.5, "title": "Short title for the post, max 90 characters", "hook": "3-7 WORD HOOK FOR THE TITLE BAR", "why": "one sentence on why this works", "score": 8}}
]

Transcript:
{transcript}
