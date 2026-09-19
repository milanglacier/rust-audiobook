"""Per-segment audio cache.

Keyed by everything that can change the clip, so editing one paragraph
re-synthesizes exactly that paragraph and nothing else. The cache is also the
single normalization point: whatever a provider returns is passed through
ffmpeg once on the way in and stored as canonical WAV (mono, 16-bit, the
configured sample rate), so assembly only ever sees identical formats.

Chapter-level settings (`format`, `loudnorm`, `bitrate_kbps`) are deliberately
*not* in the key — they change how a chapter is encoded, not how a clip
sounds, and they are covered by the chapter's `source_hash` instead.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from . import audio as A
from .tts.base import SynthResult


def cache_key(cfg: dict[str, Any], text: str) -> str:
    payload = {
        "provider": cfg.get("provider"),
        "model": cfg.get("model"),
        "voice": cfg.get("voice"),
        "speed": cfg.get("speed"),
        "instructions": cfg.get("instructions"),
        "sample_rate": cfg.get("sample_rate"),
        "text": text,
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class Cache:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def path(self, key: str) -> Path:
        return self.root / f"{key}.wav"

    def _words_path(self, key: str) -> Path:
        return self.root / f"{key}.words.json"

    def load(self, key: str) -> A.Clip | None:
        wav = self.path(key)
        if not wav.exists():
            return None
        try:
            frames, rate = A.wav_info(wav)
        except Exception:
            return None
        return A.Clip(path=wav, frames=frames, sample_rate=rate, words=self._words(key))

    def _words(self, key: str) -> list[tuple[float, float, str]] | None:
        wpath = self._words_path(key)
        if not wpath.exists():
            return None
        try:
            return [tuple(w) for w in json.loads(wpath.read_text("utf-8"))]
        except Exception:
            return None

    def store(self, key: str, result: SynthResult, sample_rate: int) -> A.Clip:
        """Normalize through ffmpeg and land the WAV atomically."""
        self.root.mkdir(parents=True, exist_ok=True)
        final = self.path(key)
        tmp = self.root / f".{key}.part.wav"
        try:
            clip = A.normalize_to_wav(
                result.data, result.format, tmp,
                sample_rate=sample_rate, src_rate=result.sample_rate,
            )
            os.replace(tmp, final)
        finally:
            tmp.unlink(missing_ok=True)
        clip.path = final
        clip.words = result.words
        if result.words:
            self._words_path(key).write_text(
                json.dumps([list(w) for w in result.words], ensure_ascii=False),
                encoding="utf-8",
            )
        return clip
