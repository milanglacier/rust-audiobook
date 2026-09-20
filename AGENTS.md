# Project Rules

- When serving the audiobook site, bind to `0.0.0.0` (not `127.0.0.1`).
- Use MiniMax as the TTS provider. The MiniMax API key is stored in `.env` at the repo root — load it with `export $(grep -v '^#' .env | xargs)` before running synthesis commands.
