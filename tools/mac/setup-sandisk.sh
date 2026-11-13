#!/bin/bash
# One-time Mac setup for the content machine, using an external drive (e.g. a SanDisk SSD).
#
#   bash <(curl -fsSL https://raw.githubusercontent.com/tyesco94/Claude-to-CTO/claude/god-page-ai/tools/mac/setup-sandisk.sh)
#
# 1. Shows what is using space on this Mac and saves the report to the drive.
# 2. Offers, one folder at a time, to move Downloads and Movies to the drive (asks first; nothing moves on "n").
# 3. Puts the free God page tool on the drive and makes all 45 days of videos (no Claude, no credits).
# 4. Adds a nightly job (3:15 am) that finishes any days still missing, so it keeps going on its own.
# Never deletes anything that has not been copied to the drive first. Safe to run again.
set -u
say() { printf "\n\033[1m%s\033[0m\n" "$*"; }
ask() { read -r -p "$1 [y/N] " a </dev/tty; [[ "$a" =~ ^[Yy] ]]; }

# ---------- find the drive
DRIVES=()
while IFS= read -r v; do DRIVES+=("$v"); done < <(
  for v in /Volumes/*; do
    [ -d "$v" ] || continue
    [ "$(readlink "$v")" = "/" ] && continue                       # the Mac's own disk
    diskutil info "$v" 2>/dev/null | grep -qE "Internal:\s+No|Device Location:\s+External|Removable Media:\s+(Removable|Yes)" && echo "$v"
  done)
if [ ${#DRIVES[@]} -eq 0 ]; then
  echo "No external drive found. Plug in the SanDisk (USB-C port on the back) and run this again."; exit 1
fi
DRIVE="${DRIVES[0]}"
if [ ${#DRIVES[@]} -gt 1 ]; then
  echo "External drives:"; i=1; for d in "${DRIVES[@]}"; do echo "  $i) $d"; i=$((i+1)); done
  read -r -p "Which one? " n </dev/tty; DRIVE="${DRIVES[$((n-1))]}"
fi
touch "$DRIVE/.write-test" 2>/dev/null && rm -f "$DRIVE/.write-test" || {
  echo "Can't write to $DRIVE. If it is NTFS-formatted, erase it as exFAT or APFS in Disk Utility first."; exit 1; }
HOME_ON_DRIVE="$DRIVE/MacOffload"
mkdir -p "$HOME_ON_DRIVE"
say "Using drive: $DRIVE  ($(df -h "$DRIVE" | awk 'NR==2{print $4}') free)"

# ---------- 1. space report
say "1) What is using space on this Mac"
REPORT="$HOME_ON_DRIVE/space-report-$(date +%Y%m%d-%H%M).txt"
{
  echo "Mac disk: $(df -h / | awk 'NR==2{print $3" used, "$4" free of "$2}')"
  du -sh ~/Downloads ~/Movies ~/Pictures ~/Music ~/Documents ~/Desktop \
        ~/Library/Application\ Support/MobileSync ~/Library/Caches 2>/dev/null | sort -hr
} | tee "$REPORT"
echo "(Saved to $REPORT — send Claude a photo of this list.)"

# ---------- 2. offer to move big folders
say "2) Move folders to the drive (you choose)"
move_folder() {  # copies, verifies, then removes only files that copied successfully
  local src="$1" dst="$HOME_ON_DRIVE/$(basename "$1")"
  [ -d "$src" ] || return
  local size; size=$(du -sh "$src" 2>/dev/null | cut -f1)
  ask "Move $src ($size) to $dst? An alias is left in its place." || { echo "  skipped"; return; }
  [ -e "$dst" ] && dst="$dst-$(date +%Y%m%d-%H%M)"
  mkdir -p "$dst"
  echo "  copying..."
  local item ok=1
  for item in "$src"/* "$src"/.[!.]*; do
    [ -e "$item" ] || continue
    case "$(basename "$item")" in .DS_Store|.localized) continue;; esac
    cp -Rp "$item" "$dst/" || ok=0
  done
  echo "  checking every file..."
  for item in "$src"/* "$src"/.[!.]*; do
    [ -e "$item" ] || continue
    case "$(basename "$item")" in .DS_Store|.localized) continue;; esac
    diff -rq "$item" "$dst/$(basename "$item")" >/dev/null 2>&1 || { ok=0; echo "  differs: $item"; }
  done
  if [ $ok = 1 ]; then
    for item in "$src"/* "$src"/.[!.]*; do
      [ -e "$item" ] || continue
      case "$(basename "$item")" in .DS_Store|.localized) continue;; esac
      rm -rf "$item"
    done
    osascript -e "tell application \"Finder\" to make alias file to (POSIX file \"$dst\") at (POSIX file \"$src\")" >/dev/null 2>&1
    echo "  moved. Find it in Finder > $(basename "$DRIVE") > MacOffload, or the alias in $src."
  else
    echo "  Not everything copied the same, so NOTHING was removed from $src. The copy is in $dst."
  fi
}
move_folder ~/Downloads
move_folder ~/Movies
echo "Photos library: move it from Photos > Settings > General, not here. iPhone backups: leave them."

# ---------- 3. tools
say "3) God page videos (free: public-domain paintings + landscape photos, KJV verses)"
if ! command -v brew >/dev/null && [ ! -x /opt/homebrew/bin/brew ] && [ ! -x /usr/local/bin/brew ]; then
  echo "Installing Homebrew (needed for ffmpeg). It asks for your Mac password; typing shows nothing."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/tty
fi
eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv 2>/dev/null)"
command -v ffmpeg >/dev/null || brew install ffmpeg
command -v git >/dev/null || xcode-select --install
python3 -m pip install --user -q --upgrade Pillow 2>/dev/null || python3 -m pip install --user -q --break-system-packages Pillow

TOOL="$DRIVE/god-page-tool"
if [ -d "$TOOL/.git" ]; then git -C "$TOOL" pull -q --ff-only || true
else git clone -q -b claude/god-page-ai https://github.com/tyesco94/Claude-to-CTO.git "$TOOL"; fi
cd "$TOOL" || exit 1
[ -f output/god-page/plan.json ] || python3 tools/scripture/ai_posts.py plan --draft tools/scripture/god_page_45.json --days 45

# ---------- 4. nightly job
say "4) Nightly job: finishes missing days at 3:15 am (runs only while the drive is plugged in)"
RUNNER="$TOOL/run-nightly.sh"
cat > "$RUNNER" <<EOF
#!/bin/bash
[ -d "$TOOL" ] || exit 0
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "$TOOL" && git pull -q --ff-only 2>/dev/null
python3 tools/scripture/free_posts.py >> "$TOOL/nightly.log" 2>&1
EOF
chmod +x "$RUNNER"
PLIST=~/Library/LaunchAgents/com.godpage.nightly.plist
mkdir -p ~/Library/LaunchAgents
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.godpage.nightly</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$RUNNER</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>3</integer><key>Minute</key><integer>15</integer></dict>
</dict></plist>
EOF
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null
launchctl bootstrap "gui/$(id -u)" "$PLIST" && echo "Nightly job on. To turn it off: launchctl bootout gui/\$(id -u) $PLIST"

say "Making the videos now (stop any time with Control-C; finished days are kept)"
python3 tools/scripture/free_posts.py
open "$TOOL/output/god-page"
say "Done. Videos, posts and captions.csv are in: $TOOL/output/god-page"
