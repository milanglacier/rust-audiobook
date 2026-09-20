"""End-to-end run of the CLI entry points on a tiny book built in tmp_path.

The book uses the `mock` provider, so nothing is sent anywhere and nothing is
paid for; the synth and build tests still need ffmpeg and are skipped without it.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from audiobook_lib.cli import build_site, synth, transcript_stats

SKILL_ROOT = Path(__file__).resolve().parents[1]

needs_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not on PATH",
)

BOOK_YAML = """\
title: 测试书
subtitle: 两章样例
author: 测试
language: zh
description: 用来测试整条流水线。
tts:
  provider: mock
  voice: mock-a
  speed: 1.0
  pause_ms:
    paragraph: 400
    heading: 600
"""

CHAPTER_ONE = """\
---
title: 第一章  开头
---

# 第一章  开头

第一段讲的是加噪这件事，它一点也不神秘。

于是我们得到 {{$x_t = \\sqrt{a}\\,x_0$||x t 等于 根号 a 乘以 x zero}}。

$$
x_t = \\sqrt{a}\\,x_0
$$

第二段收个尾，把刚才那句话再说一遍。
"""

CHAPTER_TWO = """\
---
title: 第二章  结尾
---

# 第二章  结尾

反过来看，去噪就是把刚才那一步倒着走一遍。

这里写成 {{$x_0 = y$||x zero 等于 y}}，读起来清楚一些。

$$
x_0 = y
$$

最后一段，讲完收工。
"""


@pytest.fixture
def book_dir(tmp_path: Path) -> Path:
    book = tmp_path / "book"
    (book / "chapters").mkdir(parents=True)
    (book / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
    (book / "chapters" / "01-forward.md").write_text(CHAPTER_ONE, encoding="utf-8")
    (book / "chapters" / "02-reverse.md").write_text(CHAPTER_TWO, encoding="utf-8")
    return book


def run(monkeypatch, main, *argv: str) -> int:
    monkeypatch.setattr("sys.argv", ["prog", *argv])
    return main()


def test_stats_reports_both_chapters(monkeypatch, book_dir, capsys):
    assert run(monkeypatch, transcript_stats.main, str(book_dir), "--json") == 0
    report = json.loads(capsys.readouterr().out)
    assert [c["id"] for c in report["chapters"]] == ["01-forward", "02-reverse"]
    assert all(c["est_minutes"] > 0 for c in report["chapters"])
    assert all(c["spoken_segments"] > 0 for c in report["chapters"])


def test_dry_run_touches_nothing(monkeypatch, book_dir, capsys):
    assert run(monkeypatch, synth.main, str(book_dir), "--dry-run") == 0
    out = capsys.readouterr().out
    assert "mock" in out
    assert not (book_dir / "audio").exists()


@needs_ffmpeg
def test_synth_writes_audio_and_manifest(monkeypatch, book_dir):
    assert run(monkeypatch, synth.main, str(book_dir)) == 0
    for cid in ("01-forward", "02-reverse"):
        mp3 = book_dir / "audio" / f"{cid}.mp3"
        manifest_path = book_dir / "audio" / f"{cid}.json"
        assert mp3.is_file() and mp3.stat().st_size > 0
        manifest = json.loads(manifest_path.read_text("utf-8"))
        assert manifest["audio"] == f"{cid}.mp3"
        assert manifest["duration"] > 0
        spoken = [s for s in manifest["segments"] if s.get("spoken")]
        assert spoken and all(s["end"] > s["start"] for s in spoken)


@needs_ffmpeg
def test_build_site_produces_the_real_player(monkeypatch, book_dir):
    assert run(monkeypatch, synth.main, str(book_dir)) == 0
    assert run(monkeypatch, build_site.main, str(book_dir)) == 0
    site = book_dir / "site"
    book_json = json.loads((site / "book.json").read_text("utf-8"))
    assert [c["id"] for c in book_json["chapters"]] == ["01-forward", "02-reverse"]
    assert all(c["audio"] for c in book_json["chapters"])
    assert all((site / c["audio"]).is_file() for c in book_json["chapters"])
    assert all((site / c["manifest"]).is_file() for c in book_json["chapters"])
    index = (site / "index.html").read_text("utf-8")
    assert "app.js" in index  # the real player, not the placeholder
    assert (site / "app.js").is_file()


def test_build_site_works_before_any_audio(monkeypatch, book_dir):
    """Transcript-only mode: the player can review a book that cost nothing yet."""
    assert run(monkeypatch, build_site.main, str(book_dir)) == 0
    book_json = json.loads((book_dir / "site" / "book.json").read_text("utf-8"))
    assert len(book_json["chapters"]) == 2
    assert all(c["audio"] is None for c in book_json["chapters"])


def test_build_site_bakes_metadata_into_index(monkeypatch, book_dir):
    """Unfurlers and crawlers never run app.js — the head must be real markup."""
    assert run(monkeypatch, build_site.main, str(book_dir)) == 0
    index = (book_dir / "site" / "index.html").read_text("utf-8")
    assert "<title>测试书</title>" in index
    assert '<html lang="zh">' in index
    assert '<meta name="description" content="用来测试整条流水线。">' in index
    assert '<meta property="og:title" content="测试书">' in index
    assert '<meta name="author" content="测试">' in index
    assert index.count("<title>") == 1


def test_build_site_is_not_hardcoded_to_chinese(monkeypatch, tmp_path):
    book = tmp_path / "en-book"
    (book / "chapters").mkdir(parents=True)
    (book / "book.yaml").write_text(
        'title: A Test Book\nauthor: Someone\nlanguage: en-US\n'
        'description: "Quotes \'n\' <angles> survive escaping."\n'
        "tts:\n  provider: mock\n  voice: mock-a\n",
        encoding="utf-8",
    )
    (book / "chapters" / "01-intro.md").write_text(
        "---\ntitle: Intro\n---\n\n# Intro\n\nOne paragraph is enough.\n", encoding="utf-8"
    )
    assert run(monkeypatch, build_site.main, str(book)) == 0
    index = (book / "site" / "index.html").read_text("utf-8")
    assert '<html lang="en-US">' in index
    assert "<title>A Test Book</title>" in index
    assert "&lt;angles&gt;" in index and "<angles>" not in index


def test_default_assets_point_at_the_real_player():
    assets = build_site.default_assets()
    assert (assets / "index.html").is_file()
    assert (assets / "app.js").is_file()
    # either the repo checkout or the copy force-included in the wheel
    assert assets.name == "site" and assets.parent.name in ("assets",)
    assert build_site.REPO_ASSETS == SKILL_ROOT / "assets" / "site"
