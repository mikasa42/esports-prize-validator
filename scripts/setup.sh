#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 -m venv .venv
.venv/bin/python -m pip install --no-cache-dir -r requirements.txt
npm --prefix frontend ci --legacy-peer-deps --cache "${TMPDIR:-/tmp}/esports-prize-validator-npm-cache"
npm --prefix frontend-public ci --legacy-peer-deps --cache "${TMPDIR:-/tmp}/esports-prize-validator-npm-cache"
printf '\nAmbiente pronto. Ative com: source .venv/bin/activate\nInicie front e back com: npm run dev\n'
