# Rust Audiobook for beginner

**Listen at: <https://rust-audiobook.vercel.app>**

## What it is

A Chinese-language audiobook that teaches Rust by ear — one chapter at a
time, made for the commute. It walks through ownership, borrowing and
lifetimes, structs and enums, error handling, traits, iterators and closures,
concurrency, smart pointers, async and Tokio, and finally the wider
ecosystem. Every chapter has a transcript alongside the narration, so you can
listen anywhere and read along when you want to.

## What the website supports

- **Chapter list** with progress, and a *Continue* button that picks up where you stopped.
- **Transcript view** for each chapter: the paragraph being spoken is highlighted and kept in view.
- **Tap any paragraph** to jump straight to that moment.
- **Player controls**: play/pause, skip ±15/30 seconds, playback speed from 0.8× to 2×, and a sleep timer (15/30/45/60 min).
- **Auto-play** into the next chapter, so a whole book plays back to back.
- **Remembers your position** between visits, with lock-screen and headset controls on mobile.
- **Works on a phone** in the browser — no app to install.

## How to build it

Synthesis needs a TTS API key in `.env` and costs real money, so only run
`audiobook-synth` when you actually want to (re)generate audio.

```bash
export $(grep -v '^#' .env | xargs)

# 1. Synthesize / update the audio (needs ffmpeg; skips unchanged paragraphs)
nix-shell -p ffmpeg --run "uv run --project .claude/skills/make-audiobook audiobook-synth rust-audiobook"

# 2. Build the static player into rust-audiobook/site/
uv run --project .claude/skills/make-audiobook audiobook-build rust-audiobook

# 3. Serve locally (reachable from your phone on the same network)
uv run --project .claude/skills/make-audiobook audiobook-serve rust-audiobook/site --host 0.0.0.0 --port 8000
```

Or review the script before spending anything:

```bash
uv run --project .claude/skills/make-audiobook audiobook-stats rust-audiobook
```

