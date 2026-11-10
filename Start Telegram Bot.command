#!/bin/bash
# Double-click to start Claude Code with the Telegram bot on, in this folder.
cd "$(dirname "$0")" || exit 1
mkdir -p input
exec claude --channels plugin:telegram@claude-plugins-official
