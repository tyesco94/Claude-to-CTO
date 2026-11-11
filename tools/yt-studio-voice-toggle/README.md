# Character Voices for YouTube Studio

A Chrome extension that adds a **New character voice** toggle to YouTube Studio,
right under the **Extras** section. Switch it on, name the character, then
either describe the voice ("deep, gravelly old man, slow") or upload a short
sound clip. It saves the voice in [VoiceStudio](https://github.com/debpalash/VoiceStudio)
on your Mac, ready for your voiceovers.

Everything stays on your computer. YouTube never sees VoiceStudio or your clips.

## Set up on your Mac (once)

1. **Install VoiceStudio.** In Terminal:
   ```bash
   curl -fsSL https://voicestudio.sh/install | sh
   ```
   Open it once and let it download the default voice model when it asks.
2. **Get this folder.** Download this repository (green **Code** button → **Download ZIP**) and unzip it.
3. **Load the extension.** In Chrome (Edge, Brave and Arc work too), go to
   `chrome://extensions`, switch on **Developer mode** (top right), click
   **Load unpacked**, and choose the `tools/yt-studio-voice-toggle` folder.
4. Open YouTube Studio and go to a video's details page. The toggle is under **Extras**.

VoiceStudio must be open whenever you use the toggle.

## Using it

- **Describe it**: type how the character sounds. VoiceStudio turns the words it
  understands (gender, age, pitch, style, accent) into a voice and tells you which
  words it couldn't use.
- **Upload a sound**: 5–20 seconds of clear speech works best. Only use your own
  voice, or a voice you have permission to use.
- The new voice appears in VoiceStudio's voice list. Use it there, or ask Claude
  (with VoiceStudio connected over MCP at `http://localhost:3900/mcp/`) to read your script in that voice.

## Settings

Click the extension's icon to change:

- **Section name**: if YouTube labels the section differently in your language or
  layout, type that name instead of "Extras". If no section with that name is on the
  page, the toggle shows as a small floating box in the bottom-right corner.
- **VoiceStudio address**: `http://127.0.0.1:3900` by default.

## Phone and tablet

Browser extensions can't run inside the YouTube Studio app, or in Chrome on a
phone. On a phone or tablet, connect the Claude app to VoiceStudio and ask Claude
to "design a voice called …". Your Mac must be on with VoiceStudio open, and
VoiceStudio's network sharing switched on (Settings → Sharing & Remote Access).

## How it works

- `content.js` adds the toggle to `studio.youtube.com` inside a shadow DOM, so
  Studio's styles can't break it, and re-adds it when Studio redraws the page.
- `background.js` makes every VoiceStudio call (`/design/describe`, `/profiles`)
  outside the YouTube page.
- VoiceStudio refuses requests from websites it doesn't know. `rules.json` removes
  the `Origin` header **only** from this extension's own requests to
  `127.0.0.1`/`localhost`, so other websites stay blocked. The `key` in
  `manifest.json` fixes the extension ID (`flllokpfklmhinhgphhdjekbgjfhfled`) that
  the rule is tied to.
