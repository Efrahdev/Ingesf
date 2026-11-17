#!/usr/bin/env bash
# Runs once when the codespace is created: installs every tool the pipeline needs.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== system packages: Poppler (independent PDF reader for the checks), LibreOffice (Office files), fonts"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  poppler-utils libreoffice-writer libreoffice-impress libreoffice-calc \
  fonts-dejavu fonts-liberation fonts-noto-core
echo "== Python packages"
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
echo "== Node packages and the headless browser used by the checks"
npm ci || npm install
npx playwright install --with-deps chromium
mkdir -p workspace
echo "== quick self-test"
python3 -I ingest/tests/run_tests.py --quick || echo "(self-test reported a problem: see above)"
echo "Setup finished. The interface starts on port 8765 (Ports tab: 'Ingesf UI')."
