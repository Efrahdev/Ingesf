#!/usr/bin/env bash
# Runs every time the codespace starts: starts the web interface in the background.
cd "$(dirname "$0")/.."
mkdir -p workspace
if ! pgrep -f "ui/server.py" >/dev/null; then
  nohup python3 -I ui/server.py --port 8765 > workspace/ui.log 2>&1 &
fi
echo "Ingesf UI running on port 8765 (log: workspace/ui.log)"
