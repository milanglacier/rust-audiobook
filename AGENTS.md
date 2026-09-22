# Project Rules

## Serving

- When serving the audiobook site, bind to `0.0.0.0` (not `127.0.0.1`).

## TTS Provider

- Use MiniMax as the TTS provider. The MiniMax API key is stored in `.env` at the repo root.
- Load env vars with `export $(grep -v '^#' .env | xargs)` **before** running any audiobook command. `source .env` alone does not export the variables into subprocesses (e.g. `nix-shell --run`).

## Running audiobook commands

- The audiobook skill lives in `.agents/skills/make-audiobook`, with `.claude/skills/make-audiobook` as a symlink to it. Either path works for `--project`.
- The commands (`audiobook-synth`, `audiobook-build`, `audiobook-serve`, `audiobook-stats`) are run with `uv run --project .claude/skills/make-audiobook <command>` (or `.agents/skills/make-audiobook`).
- `audiobook-synth` requires `ffmpeg`. On Nix systems (NixOS or any machine with Nix installed), wrap the command with `nix-shell -p ffmpeg --run "..."` to provide ffmpeg on the fly. On non-Nix systems, install ffmpeg yourself (e.g. `apt install ffmpeg`, `brew install ffmpeg`) so it is on PATH. Example:
  ```bash
  export $(grep -v '^#' .env | xargs)
  # Nix:
  nix-shell -p ffmpeg --run "uv run --project .claude/skills/make-audiobook audiobook-synth rust-audiobook"
  # Non-Nix (ffmpeg already on PATH):
  uv run --project .claude/skills/make-audiobook audiobook-synth rust-audiobook
  ```
- `audiobook-build`, `audiobook-serve` and `audiobook-stats` do **not** need ffmpeg — `uv run` alone is fine.
  `build_site.py` imports `audiobook_lib.audio` only for the `AUDIO_EXTS` constant; the ffmpeg
  lookup is lazy, inside the encode helpers. This is what lets Vercel build the site (see below).
- `--list-voices` also does not need ffmpeg.

## Build pipeline

The full rebuild sequence is:
```bash
export $(grep -v '^#' .env | xargs)
nix-shell -p ffmpeg --run "uv run --project .claude/skills/make-audiobook audiobook-synth rust-audiobook"
uv run --project .claude/skills/make-audiobook audiobook-build rust-audiobook
uv run --project .claude/skills/make-audiobook audiobook-serve rust-audiobook/site --host 0.0.0.0 --port 8000
```

## Audiobook workflow

- **STOP: Do NOT run `audiobook-synth` without explicit user approval.**
  After drafting new or revised chapter transcripts:
  1. Run `audiobook-stats` and share the results.
  2. **STOP and wait.** Do not proceed until the user explicitly says to synthesize (e.g. "go ahead", "synth it", "approved").
  3. Only then run `audiobook-synth`.
  Synthesis costs real money and cannot be undone. Skipping the review step or assuming approval is never acceptable — not even if the stats show zero warnings, not even if the user said "do everything", not even if you think the chapters are obviously fine. Always wait for the explicit go-ahead.

## Version control

- `.env` is gitignored (contains API keys).
- `.cache/tts/` is gitignored (local paragraph-level TTS cache, keyed by voice+text).
- `audio/` is tracked — synthesis costs money, so the mp3s and their timing JSON are the one
  thing that must never be lost.
- `site/` is **not** tracked (gitignored): it is pure build output, regenerated from `audio/` +
  `chapters/` + `book.yaml` by `audiobook-build`, which Vercel now runs on every deploy.

## Deploying to Vercel

Config is `vercel.json` + `.vercelignore` at the repo root. Things those files don't tell you:

- **Git-based deploys only.** `site/` is gitignored, so Vercel builds it with the `buildCommand`
  in `vercel.json`: `pip3 install uv` then `uv run --python 3.12 --project
  .agents/skills/make-audiobook audiobook-build rust-audiobook`.
