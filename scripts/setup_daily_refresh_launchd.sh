#!/usr/bin/env bash
set -euo pipefail

# Install weekday launchd job for TailCast daily model refresh.
# Runs before MacroShift merge (default: weekdays 06:00).
#
# Usage:
#   ./scripts/setup_daily_refresh_launchd.sh
#   RUN_HOUR=6 RUN_MINUTE=30 ./scripts/setup_daily_refresh_launchd.sh
#   ./scripts/setup_daily_refresh_launchd.sh uninstall

ACTION="${1:-install}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.kyeongminkim.tailcast.dailyrefresh"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="$ROOT_DIR/logs"
STDOUT_LOG="$LOG_DIR/daily_refresh_launchd.out.log"
STDERR_LOG="$LOG_DIR/daily_refresh_launchd.err.log"

RUN_HOUR="${RUN_HOUR:-6}"
RUN_MINUTE="${RUN_MINUTE:-0}"

mkdir -p "$LOG_DIR"
mkdir -p "$HOME/Library/LaunchAgents"
chmod +x "$ROOT_DIR/scripts/run_daily_refresh.sh"

if [[ "$ACTION" == "uninstall" ]]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  launchctl remove "$LABEL" 2>/dev/null || true
  rm -f "$PLIST_PATH"
  echo "Uninstalled launchd job: $LABEL"
  exit 0
fi

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>cd "$ROOT_DIR" &amp;&amp; ./scripts/run_daily_refresh.sh</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$ROOT_DIR</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>

  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>$RUN_HOUR</integer><key>Minute</key><integer>$RUN_MINUTE</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>$RUN_HOUR</integer><key>Minute</key><integer>$RUN_MINUTE</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>$RUN_HOUR</integer><key>Minute</key><integer>$RUN_MINUTE</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>$RUN_HOUR</integer><key>Minute</key><integer>$RUN_MINUTE</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>$RUN_HOUR</integer><key>Minute</key><integer>$RUN_MINUTE</integer></dict>
  </array>

  <key>StandardOutPath</key>
  <string>$STDOUT_LOG</string>
  <key>StandardErrorPath</key>
  <string>$STDERR_LOG</string>

  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl enable "gui/$(id -u)/$LABEL"

echo "Installed launchd job: $LABEL"
echo "Plist: $PLIST_PATH"
echo "Schedule: weekdays ${RUN_HOUR}:$(printf '%02d' "$RUN_MINUTE")"
echo "Logs: $STDOUT_LOG, $STDERR_LOG"
echo ""
echo "Note: if jobs fail with 'Operation not permitted', grant Full Disk Access to"
echo "      /bin/bash (or Terminal) in System Settings → Privacy & Security."
