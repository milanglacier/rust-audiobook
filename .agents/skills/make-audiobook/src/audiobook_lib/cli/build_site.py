"""Assemble the static web player.

    audiobook-build BOOK_DIR [--out DIR] [--site-assets DIR]

Works before a single second of audio exists: a chapter with no manifest is
written in transcript-only mode (null start/end, null audio) so the whole book
can be reviewed in the player before any money is spent.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from importlib.resources import files as resource_files
from pathlib import Path
from typing import Any

from audiobook_lib import audio as A
from audiobook_lib.book import Book, Chapter, load_book

# The repo checkout, for an editable install or a `uv run --project` run.
SKILL_DIR = Path(__file__).resolve().parents[3]
REPO_ASSETS = SKILL_DIR / "assets" / "site"


def default_assets() -> Path:
    """Player assets: inside the wheel first, then the repo checkout.

    A built wheel ships `assets/site` under the package (see the
    `force-include` in pyproject.toml); a checkout keeps it at the repo root.
    """
    try:
        packaged = Path(str(resource_files("audiobook_lib") / "assets" / "site"))
        if packaged.is_dir():
            return packaged
    except (ModuleNotFoundError, TypeError, OSError):
        pass
    return REPO_ASSETS


DEFAULT_ASSETS = default_assets()

PLACEHOLDER = """<!doctype html>
<html lang="{lang}">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
 body {{ font: 16px/1.7 system-ui, sans-serif; max-width: 40rem; margin: 3rem auto; padding: 0 1rem; }}
 .note {{ background: #fffbe6; border: 1px solid #e8d98a; padding: .75rem 1rem; border-radius: .5rem; }}
 li {{ margin: .4rem 0; }}
</style>
<h1>{title}</h1>
<p>{subtitle}</p>
<p class="note">Placeholder page: <code>assets/site/</code> had no
<code>index.html</code> when this site was built. The data files below are the
real output and the player can be dropped in later.</p>
<ul>
{items}
</ul>
<p><a href="book.json">book.json</a></p>
"""


def _mtime(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


def copy_assets(assets: Path, out: Path) -> bool:
    """Returns True when real assets were copied."""
    if not assets.is_dir() or not any(assets.iterdir()):
        return False
    for item in assets.iterdir():
        if item.name.startswith("."):
            continue
        dest = out / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)
    return (out / "index.html").exists()


def link_or_copy(src: Path, dest: Path) -> None:
    """Hardlink when possible — a book is hundreds of MB of audio."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    try:
        os.link(src, dest)
    except OSError:
        shutil.copy2(src, dest)


def transcript_manifest(book: Book, ch: Chapter) -> dict[str, Any]:
    """A manifest with no timing, for chapters that have not been synthesized."""
    segments = []
    for seg in ch.segments(book.pronunciations):
        entry: dict[str, Any] = {
            "i": seg.i, "kind": seg.kind, "start": None, "end": None, "html": seg.html,
        }
        if seg.level:
            entry["level"] = seg.level
        if seg.spoken:
            entry["spoken"] = seg.spoken
        segments.append(entry)
    return {
        "id": ch.id, "title": ch.title, "audio": None, "duration": None,
        "language": book.language, "segments": segments,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book_dir")
    ap.add_argument("--out", help="output directory (default BOOK_DIR/site)")
    ap.add_argument("--site-assets", help=f"player assets (default {DEFAULT_ASSETS})")
    args = ap.parse_args()

    book = load_book(args.book_dir)
    out = Path(args.out).expanduser().resolve() if args.out else book.dir / "site"
    assets = Path(args.site_assets).expanduser().resolve() if args.site_assets else DEFAULT_ASSETS
    out.mkdir(parents=True, exist_ok=True)
    (out / "chapters").mkdir(exist_ok=True)

    have_assets = copy_assets(assets, out)
    if not have_assets:
        print(f"notice: no player assets in {assets} — writing a placeholder index.html")

    chapters_meta: list[dict[str, Any]] = []
    stale: list[str] = []
    for ch in book.chapters:
        manifest_src = book.audio_dir / f"{ch.id}.json"
        if manifest_src.exists():
            manifest = json.loads(manifest_src.read_text("utf-8"))
            if _mtime(manifest_src) < _mtime(ch.path):
                stale.append(ch.id)
        else:
            manifest = transcript_manifest(book, ch)

        # the manifest names the file, extension and all: mp3, opus or m4a
        audio_rel: str | None = None
        named = str(manifest.get("audio") or "")
        if named:
            src = book.audio_dir / Path(named).name
            if src.exists() and src.suffix.lower() in A.AUDIO_EXTS:
                audio_rel = f"audio/{src.name}"
                link_or_copy(src, out / "audio" / src.name)
        manifest["audio"] = audio_rel

        (out / "chapters" / f"{ch.id}.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        chapters_meta.append(
            {
                "id": ch.id,
                "title": ch.title,
                "audio": audio_rel,
                "duration": manifest.get("duration"),
                "manifest": f"chapters/{ch.id}.json",
            }
        )

    book_json = {
        "title": book.title,
        "subtitle": book.subtitle,
        "author": book.author,
        "description": book.description,
        "language": book.language,
        "depth": book.depth,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chapters": chapters_meta,
    }
    (out / "book.json").write_text(json.dumps(book_json, ensure_ascii=False, indent=1), encoding="utf-8")

    if not have_assets:
        items = "\n".join(
            f'  <li><a href="{c["manifest"]}">{c["id"]}</a> — {c["title"]}'
            + (
                f' (<a href="{c["audio"]}">{Path(c["audio"]).suffix.lstrip(".")}</a>)'
                if c["audio"] else " — no audio yet"
            )
            + "</li>"
            for c in chapters_meta
        )
        (out / "index.html").write_text(
            PLACEHOLDER.format(
                lang=book.language, title=book.title,
                subtitle=book.subtitle or book.description, items=items,
            ),
            encoding="utf-8",
        )

    with_audio = sum(1 for c in chapters_meta if c["audio"])
    print(
        f"built {out}: {len(chapters_meta)} chapters, {with_audio} with audio, "
        f"{len(chapters_meta) - with_audio} transcript-only"
    )
    for cid in stale:
        print(f"  warning: {cid}: audio/{cid}.json is older than chapters/{cid}.md — re-run audiobook-synth")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
