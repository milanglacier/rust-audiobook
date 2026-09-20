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

## Audiobook workflow

- **Always checkpoint after writing chapters.** After drafting new or revised chapter transcripts, run `audiobook-stats`, share the results with the user, and **wait for explicit approval** before proceeding to audio synthesis (`audiobook-synth`). Synthesis costs money and cannot be undone — never skip the review step.

## Version control

- `.env` is gitignored (contains API keys).
- `.cache/tts/` is gitignored (local paragraph-level TTS cache, keyed by voice+text).
- `audio/` and `site/` are tracked — synthesis costs money and the site is the final deliverable.

## Deploying to Vercel

Config is `vercel.json` + `.vercelignore` at the repo root. Two things those files don't tell you:

- `site/` is ~77 MB of mp3, and the Vercel **CLI** source-upload cap is 100 MB on Hobby (1 GB on Pro). A few more chapters will break `vercel deploy`; Git-based deployments don't go through that upload path.
- Do **not** add a SPA rewrite to `index.html`. The player is hash-routed (`#/`), so every route is already the one real `index.html`; a catch-all rewrite would only mask 404s on missing audio/JSON.
