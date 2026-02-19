#!/usr/bin/env python

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Segment:
    segment_id: str
    start_sec: float
    end_sec: float
    zh: str
    en: str


def _ts_to_srt(t: float) -> str:
    t = max(t, 0.0)
    hours = int(t // 3600)
    minutes = int((t % 3600) // 60)
    seconds = int(t % 60)
    millis = int(round((t - math.floor(t)) * 1000.0))
    if millis >= 1000:
        seconds += 1
        millis -= 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _write_srt(path: Path, segments: list[Segment], *, language: str) -> None:
    lines: list[str] = []
    for idx, seg in enumerate(segments, start=1):
        text = seg.zh if language == "zh" else seg.en
        lines.append(str(idx))
        lines.append(f"{_ts_to_srt(seg.start_sec)} --> {_ts_to_srt(seg.end_sec)}")
        lines.append(text.strip())
        lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON must be object: {path}")
    return data


def _segments_from_manifest(script_obj: dict[str, Any], manifest_obj: dict[str, Any] | None) -> list[Segment]:
    script_segments = script_obj.get("segments") or []
    if not isinstance(script_segments, list) or not script_segments:
        raise ValueError("script.segments missing or invalid")

    segments: list[Segment] = []
    cursor = 0.0
    for item in script_segments:
        if not isinstance(item, dict):
            continue
        seg_id = str(item.get("id") or "")
        zh = str(item.get("zh") or "").strip()
        en = str(item.get("en") or "").strip()
        if not seg_id or not zh or not en:
            raise ValueError(f"invalid segment fields: id/zh/en required (id={seg_id!r})")

        duration = float(item.get("duration_sec") or 0.1)
        start_sec = cursor
        end_sec = cursor + max(duration, 0.1)
        cursor = end_sec

        segments.append(Segment(segment_id=seg_id, start_sec=start_sec, end_sec=end_sec, zh=zh, en=en))

    # Normalize: ensure monotonic, non-overlapping.
    normalized: list[Segment] = []
    prev_end = 0.0
    for seg in segments:
        start = max(seg.start_sec, prev_end)
        end = max(seg.end_sec, start + 0.05)
        normalized.append(Segment(segment_id=seg.segment_id, start_sec=start, end_sec=end, zh=seg.zh, en=seg.en))
        prev_end = end
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Build bilingual subtitles + Remotion timeline JSON")
    parser.add_argument("--script", default="assets/narration/zh_cn_script.json")
    parser.add_argument("--manifest", default="assets/audio/tts_manifest.json")
    parser.add_argument("--out-zh", default="assets/subtitles/zh.srt")
    parser.add_argument("--out-en", default="assets/subtitles/en.srt")
    parser.add_argument("--out-timeline", default="assets/subtitles/timeline.json")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    script_path = (root / args.script).resolve()
    manifest_path = (root / args.manifest).resolve()
    out_zh = (root / args.out_zh).resolve()
    out_en = (root / args.out_en).resolve()
    out_timeline = (root / args.out_timeline).resolve()

    script_obj = _load_json(script_path)
    manifest_obj = _load_json(manifest_path) if manifest_path.exists() else None
    segments = _segments_from_manifest(script_obj, manifest_obj)

    timeline = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "fps": int(args.fps),
        "segments": [
            {
                "id": seg.segment_id,
                "start_sec": seg.start_sec,
                "end_sec": seg.end_sec,
                "duration_sec": seg.end_sec - seg.start_sec,
                "zh": seg.zh,
                "en": seg.en,
            }
            for seg in segments
        ],
    }

    if args.validate_only:
        json.dumps(timeline)  # ensure serializable
        return 0

    out_zh.parent.mkdir(parents=True, exist_ok=True)
    out_en.parent.mkdir(parents=True, exist_ok=True)
    out_timeline.parent.mkdir(parents=True, exist_ok=True)

    _write_srt(out_zh, segments, language="zh")
    _write_srt(out_en, segments, language="en")
    out_timeline.write_text(json.dumps(timeline, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
