# Project Rules

## Serving

- When serving the audiobook site, bind to `0.0.0.0` (not `127.0.0.1`).

## TTS Provider

- Use MiniMax as the TTS provider. The MiniMax API key is stored in `.env` at the repo root.
- Load env vars with `export $(grep -v '^#' .env | xargs)` **before** running any audiobook command. `source .env` alone does not export the variables into subprocesses (e.g. `nix-shell --run`).

## Running audiobook commands

- The audiobook skill lives in `.agents/skills/make-audiobook`, with `.claude/skills/make-audiobook` as a symlink to it. Either path works for `--project`.
- The commands (`audiobook-synth`, `audiobook-build`, `audiobook-serve`, `audiobook-stats`) are run with `uv run --project .claude/skills/make-audiobook <command>` (or `.agents/skills/make-audiobook`).
- `audiobook-synth` and `audiobook-build` require `ffmpeg`. On Nix systems (NixOS or any machine with Nix installed), wrap the command with `nix-shell -p ffmpeg --run "..."` to provide ffmpeg on the fly. On non-Nix systems, install ffmpeg yourself (e.g. `apt install ffmpeg`, `brew install ffmpeg`) so it is on PATH. Example:
  ```bash
  export $(grep -v '^#' .env | xargs)
  # Nix:
  nix-shell -p ffmpeg --run "uv run --project .claude/skills/make-audiobook audiobook-synth rust-audiobook"
  # Non-Nix (ffmpeg already on PATH):
  uv run --project .claude/skills/make-audiobook audiobook-synth rust-audiobook
  ```
- `audiobook-serve` and `audiobook-stats` do **not** need ffmpeg — `uv run` alone is fine.
- `--list-voices` also does not need ffmpeg.

## Build pipeline

The full rebuild sequence is:
```bash
export $(grep -v '^#' .env | xargs)
nix-shell -p ffmpeg --run "uv run --project .claude/skills/make-audiobook audiobook-synth rust-audiobook"
nix-shell -p ffmpeg --run "uv run --project .claude/skills/make-audiobook audiobook-build rust-audiobook"
uv run --project .claude/skills/make-audiobook audiobook-serve rust-audiobook/site --host 0.0.0.0 --port 8000
```

## Version control

- `.env` is gitignored (contains API keys).
- `.cache/tts/` is gitignored (local paragraph-level TTS cache, keyed by voice+text).
- `audio/` and `site/` are tracked — synthesis costs money and the site is the final deliverable.
