# Telegram bot setup (Mac)

Message your own Telegram bot; Claude Code on your Mac does the work in this repo and replies.

1. **Create the bot**: in Telegram message **@BotFather**, send `/newbot`, pick a name and a username ending in `bot`. Keep the token private.
2. **Install the plugin** in Claude Code: `/plugin install telegram@claude-plugins-official` (optional: also install `claude-telegram-voice` for voice notes).
3. **Add the token**: run `/telegram:configure` in Claude Code and paste it there.
4. **Start**: double-click `Start Telegram Bot.command` in this folder (or run `claude --channels plugin:telegram@claude-plugins-official` here).
5. **Pair**: message your bot; approve the pairing with `/telegram:access` so only you can use it.

Keep the Mac awake and the Terminal window open while you want the bot answering.
The bot follows `.claude/skills/telegram-workflow/SKILL.md` — edit that file to change how it behaves.

## Things to send it
- a video or YouTube link — "3 clips, 30s"
- `picks <link>` — just the best moments
- `caption clip 2` — post caption + hashtags
- `voice <script>` — ElevenLabs voiceover
- `schedule clip 2 Friday 7pm TikTok and Reels` — needs the Metricool connector
- `status`
