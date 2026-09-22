#!/bin/sh
# Vercel build: regenerate rust-audiobook/site, which is gitignored build output.
set -eu

SKILL=.agents/skills/make-audiobook
VENV=/tmp/audiobook-venv

# Vercel's build image ships a Python that uv itself manages, so `pip3 install uv`
# dies under PEP 668 (externally-managed-environment). Use the image's own uv when
# it is on PATH, and fall back to the standalone installer otherwise.
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

# `uv run` failed on Vercel with `Failed to spawn: audiobook-build` — it resolved an
# environment that did not contain the console script, and that was not reproducible
# in a fresh local clone. So pin the environment path instead of letting uv infer it,
# and invoke the script by absolute path so nothing goes through PATH resolution.
# audiobook-build needs no ffmpeg, and uv fetches its own CPython.
export UV_PROJECT_ENVIRONMENT="$VENV"
uv sync --frozen --no-dev --python 3.12 --project "$SKILL"

exec "$VENV/bin/audiobook-build" rust-audiobook
