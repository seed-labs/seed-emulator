#!/usr/bin/env python

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SAMPLE_RATE = 24_000
DEFAULT_GAP_SEC = 0.0
GEMINI_PREBUILT_VOICES = {
    "Zephyr",
    "Puck",
    "Charon",
    "Kore",
    "Fenrir",
    "Leda",
    "Orus",
    "Aoede",
    "Callirrhoe",
    "Autonoe",
    "Enceladus",
    "Iapetus",
}
EDGE_TTS_DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
HTTP_USER_AGENT = "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


@dataclass
class AudioChunk:
    segment_id: str
    text: str
    pcm: bytes
    sample_rate: int
    start_sec: float
    end_sec: float
    provider: str
    voice: str
    model: str


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON must be object: {path}")
    return data


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "").isalnum():
            continue
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", HTTP_USER_AGENT)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        msg = raw[:1200].decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {msg}") from exc


def _can_connect(url: str, timeout: int) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            _ = resp.read(1)
        return True
    except Exception:
        return False


def _gemini_tts_pcm(*, api_key: str, model: str, voice: str, text: str, timeout: int) -> bytes:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    prompt = (
        "Read the following in clear, professional Mandarin Chinese, at a steady pace. "
        "Do not add extra words. Text:\n"
        f"{text}"
    )
    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }
    raw, _headers = _post_json(url, headers={"x-goog-api-key": api_key}, payload=payload, timeout=timeout)
    obj = json.loads(raw.decode("utf-8"))
    candidates = obj.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini TTS returned no candidates")
    content = (candidates[0] or {}).get("content") or {}
    parts = content.get("parts") or []
    if not parts:
        raise RuntimeError("Gemini TTS returned empty content parts")
    inline = (parts[0] or {}).get("inlineData") or (parts[0] or {}).get("inline_data") or {}
    data = inline.get("data")
    if not isinstance(data, str) or not data:
        raise RuntimeError("Gemini TTS returned no inlineData.data")
    return base64.b64decode(data)


def _openai_compat_tts_pcm(*, base_url: str, api_key: str, model: str, voice: str, text: str, timeout: int) -> bytes:
    base_url = base_url.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    url = f"{base_url}/audio/speech"

    payload: dict[str, Any] = {
        "model": model,
        "voice": voice,
        "input": text,
        "response_format": "pcm",
        "format": "pcm",
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", HTTP_USER_AGENT)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = (resp.headers.get("content-type") or "").lower()
            data = resp.read()
            if "application/json" in content_type or data[:1] in (b"{", b"["):
                msg = data[:1200].decode("utf-8", errors="ignore")
                raise RuntimeError(f"openai-compat TTS returned JSON, not audio: {msg}")
            return data
    except urllib.error.HTTPError as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        msg = raw[:1200].decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {msg}") from exc


def _write_wav(path: Path, *, pcm: bytes, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)


def _fit_pcm_to_duration(pcm: bytes, *, sample_rate: int, duration_sec: float) -> bytes:
    target_frames = max(int(round(sample_rate * max(duration_sec, 0.05))), 1)
    current_frames = len(pcm) // 2
    if current_frames == target_frames:
        return pcm
    if current_frames > target_frames:
        return pcm[: target_frames * 2]
    pad_frames = target_frames - current_frames
    return pcm + (b"\x00\x00" * pad_frames)


def _edge_tts_pcm(*, text: str, voice: str, timeout: int) -> bytes:
    try:
        import asyncio
        import edge_tts  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"edge-tts not installed: {exc}") from exc

    local_ffmpeg = Path(__file__).resolve().parents[1] / ".runtime/ffmpeg/bin/ffmpeg"
    ffmpeg = os.environ.get("FFMPEG_PATH") or (str(local_ffmpeg) if local_ffmpeg.exists() else "") or shutil.which("ffmpeg") or ""
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found (set FFMPEG_PATH or ensure ffmpeg is on PATH)")

    async def _run() -> bytes:
        communicate = edge_tts.Communicate(text=text, voice=voice)
        chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                chunks.append(chunk.get("data") or b"")
        return b"".join(chunks)

    mp3_bytes = asyncio.run(asyncio.wait_for(_run(), timeout=timeout))
    if not mp3_bytes:
        raise RuntimeError("edge-tts returned no audio bytes")

    with tempfile.TemporaryDirectory(prefix="seed-video-tts-") as tmp:
        mp3_path = Path(tmp) / "seg.mp3"
        pcm_path = Path(tmp) / "seg.pcm"
        mp3_path.write_bytes(mp3_bytes)

        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(mp3_path),
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            str(DEFAULT_SAMPLE_RATE),
            str(pcm_path),
        ]
        try:
            subprocess.run(cmd, check=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("ffmpeg decode timed out") from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"ffmpeg decode failed (rc={exc.returncode})") from exc

        data = pcm_path.read_bytes() if pcm_path.exists() else b""
        if not data:
            raise RuntimeError("ffmpeg produced empty pcm output")
        return data


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ~120s voiceover using Gemini TTS (fallback to LLM gateway)")
    parser.add_argument("--script", required=True, help="Path to zh_cn_script.json")
    parser.add_argument("--out", required=True, help="Output WAV path (repo-relative or absolute)")
    parser.add_argument("--manifest", default="assets/audio/tts_manifest.json")
    parser.add_argument("--public-out", default="public/voiceover.wav")
    parser.add_argument("--env-file", default="", help="Optional env file (defaults to repo-root .env if present)")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--gap-sec", type=float, default=DEFAULT_GAP_SEC)
    parser.add_argument("--gemini-only", action="store_true", help="Only use Gemini TTS; disable all fallback providers.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    repo_root = root.parents[1]
    if args.env_file:
        env_path = Path(args.env_file)
        if not env_path.is_absolute():
            env_path = (repo_root / env_path).resolve()
    else:
        env_path = (repo_root / ".env").resolve()
    _load_env_file(env_path)

    script_path = Path(args.script)
    if not script_path.is_absolute():
        script_path = (root / script_path).resolve()
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = (root / out_path).resolve()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (root / manifest_path).resolve()
    public_out = Path(args.public_out)
    if not public_out.is_absolute():
        public_out = (root / public_out).resolve()

    script_obj = _load_json(script_path)
    segments = script_obj.get("segments") or []
    if not isinstance(segments, list) or not segments:
        raise ValueError("script.segments missing or invalid")

    target_sec = float(script_obj.get("target_duration_sec") or 90.0)
    sample_rate = int(script_obj.get("sample_rate_hz") or DEFAULT_SAMPLE_RATE)

    gemini_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    configured_tts_model = os.environ.get("LLM_TTS_MODEL") or ""
    gemini_model = (
        os.environ.get("GEMINI_TTS_MODEL")
        or (configured_tts_model if ("gemini" in configured_tts_model and "tts" in configured_tts_model) else "")
        or "gemini-2.5-flash-preview-tts"
    )
    raw_voice = os.environ.get("LLM_TTS_VOICE") or ""
    gemini_voice = os.environ.get("GEMINI_TTS_VOICE") or (raw_voice if raw_voice in GEMINI_PREBUILT_VOICES else "Charon")

    llm_base_url = os.environ.get("LLM_BASE_URL") or os.environ.get("OPENAI_API_BASE") or ""
    llm_api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    llm_model = os.environ.get("LLM_TTS_MODEL_FALLBACK") or os.environ.get("OPENAI_TTS_MODEL") or "gpt-4o-mini-tts"
    llm_voice = os.environ.get("LLM_TTS_VOICE_FALLBACK") or raw_voice or "alloy"
    openai_api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY") or ""
    openai_enabled = bool(openai_api_key) and _can_connect("https://api.openai.com/v1/models", timeout=3)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "script": str(script_path),
                    "segments": len(segments),
                    "target_sec": target_sec,
                    "gemini_model": gemini_model,
                    "gemini_voice": gemini_voice,
                    "gemini_only": bool(args.gemini_only),
                    "llm_base_url_set": bool(llm_base_url),
                    "env_loaded": str(env_path) if env_path.exists() else None,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    chunks: list[AudioChunk] = []
    seg_dir = (root / "assets/audio/segments").resolve()
    seg_dir.mkdir(parents=True, exist_ok=True)

    gemini_enabled = bool(gemini_api_key)
    if not gemini_enabled:
        print("[warn] GEMINI_API_KEY not set; using fallback TTS path.", flush=True)

    cursor = 0.0
    for item in segments:
        if not isinstance(item, dict):
            continue
        seg_id = str(item.get("id") or "")
        zh = str(item.get("zh") or "").strip()
        if not seg_id or not zh:
            raise ValueError(f"invalid segment: id/zh required (id={seg_id!r})")
        target_seg_sec = float(item.get("duration_sec") or 0.5)

        pcm: bytes | None = None
        provider = ""
        model = ""
        voice = ""

        # Primary: Gemini TTS
        if gemini_enabled:
            try:
                pcm = _gemini_tts_pcm(api_key=gemini_api_key, model=gemini_model, voice=gemini_voice, text=zh, timeout=args.timeout)
                provider = "gemini"
                model = gemini_model
                voice = gemini_voice
            except Exception as exc:
                pcm = None
                provider = "gemini_failed"
                model = gemini_model
                voice = gemini_voice
                print(f"[warn] Gemini TTS failed for {seg_id}: {exc}", flush=True)
                gemini_enabled = False

        # Fallback: OpenAI-compatible / gateway TTS (PCM)
        if pcm is None and (not args.gemini_only) and llm_base_url and llm_api_key and llm_model:
            try:
                pcm = _openai_compat_tts_pcm(
                    base_url=llm_base_url,
                    api_key=llm_api_key,
                    model=llm_model,
                    voice=llm_voice,
                    text=zh,
                    timeout=args.timeout,
                )
                provider = "llm_gateway"
                model = llm_model
                voice = llm_voice
            except Exception as exc:
                pcm = None
                provider = "llm_gateway_failed"
                model = llm_model
                voice = llm_voice
                print(f"[warn] LLM gateway TTS failed for {seg_id}: {exc}", flush=True)

        # Fallback-2: OpenAI official endpoint (if reachable)
        if pcm is None and (not args.gemini_only) and openai_enabled:
            try:
                pcm = _openai_compat_tts_pcm(
                    base_url="https://api.openai.com",
                    api_key=openai_api_key,
                    model=llm_model,
                    voice=llm_voice,
                    text=zh,
                    timeout=args.timeout,
                )
                provider = "openai_official"
                model = llm_model
                voice = llm_voice
            except Exception as exc:
                pcm = None
                print(f"[warn] OpenAI official TTS failed for {seg_id}: {exc}", flush=True)

        # Fallback-3: Edge TTS (local account-less)
        if pcm is None and args.gemini_only:
            raise RuntimeError(f"Gemini-only mode failed for {seg_id}; aborting render.")

        if pcm is None:
            try:
                pcm = _edge_tts_pcm(text=zh, voice=os.environ.get("EDGE_TTS_VOICE") or EDGE_TTS_DEFAULT_VOICE, timeout=max(args.timeout, 30))
                provider = "edge_tts"
                model = "edge_tts"
                voice = os.environ.get("EDGE_TTS_VOICE") or EDGE_TTS_DEFAULT_VOICE
            except Exception as exc:
                pcm = None
                print(f"[warn] Edge TTS failed for {seg_id}: {exc}", flush=True)

        if pcm is None:
            # Deterministic placeholder: 0.5s silence for this segment (keeps pipeline renderable).
            silence_frames = int(sample_rate * target_seg_sec)
            pcm = b"\x00\x00" * silence_frames
            provider = "silence"
            model = "n/a"
            voice = "n/a"

        pcm = _fit_pcm_to_duration(pcm, sample_rate=sample_rate, duration_sec=target_seg_sec)
        start = cursor
        cursor += target_seg_sec
        end = cursor

        chunks.append(
            AudioChunk(
                segment_id=seg_id,
                text=zh,
                pcm=pcm,
                sample_rate=sample_rate,
                start_sec=start,
                end_sec=end,
                provider=provider,
                voice=voice,
                model=model,
            )
        )

        _write_wav(seg_dir / f"{seg_id}.wav", pcm=pcm, sample_rate=sample_rate)
        time.sleep(0.2)
        print(f"[ok] segment {seg_id} -> {provider} ({target_seg_sec:.2f}s)", flush=True)

    pcm_all = b"".join([c.pcm for c in chunks])
    expected_bytes = int(round(target_sec * sample_rate)) * 2
    if len(pcm_all) < expected_bytes:
        pcm_all += b"\x00\x00" * ((expected_bytes - len(pcm_all)) // 2)
    if len(pcm_all) > expected_bytes:
        pcm_all = pcm_all[:expected_bytes]

    _write_wav(out_path, pcm=pcm_all, sample_rate=sample_rate)
    public_out.parent.mkdir(parents=True, exist_ok=True)
    public_out.write_bytes(out_path.read_bytes())

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "script": str(script_path),
        "provider_primary": "gemini",
        "provider_fallback": "llm_gateway",
        "sample_rate_hz": sample_rate,
        "gap_sec": float(args.gap_sec),
        "target_duration_sec": target_sec,
        "actual_pcm_bytes": len(pcm_all),
        "actual_duration_sec": len(pcm_all) / 2 / sample_rate,
        "sha256": _sha256(pcm_all),
        "segments": [
            {
                "id": seg.segment_id,
                "provider": seg.provider,
                "model": seg.model,
                "voice": seg.voice,
                "start_sec": seg.start_sec,
                "end_sec": seg.end_sec,
                "duration_sec": seg.end_sec - seg.start_sec,
                "sha256": _sha256(seg.pcm),
                "text_preview": seg.text[:80],
            }
            for seg in chunks
        ],
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"out": str(out_path), "public_out": str(public_out), "manifest": str(manifest_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
