# SEED Platform 120s Showcase Video

This folder contains a local-only Remotion pipeline for a ~120s platform showcase video.

Core narrative:

- `Codex` is an optional shell.
- `Seed-Agent` is the behavioral core.
- `SeedOps MCP` is the execution backbone.
- The loop is proven with real runtime evidence.

## Quick start

1) Check prerequisites:

```bash
cd examples/agent-video
bash scripts/check_prereqs.sh
```

If the local runtime is missing, bootstrap it (no sudo required):

```bash
bash scripts/bootstrap_runtime.sh
bash scripts/bootstrap_ffmpeg.sh
```

2) Install Remotion skill into project-scoped `CODEX_HOME`:

```bash
bash scripts/install_remotion_skill.sh
```

3) Collect/refresh runtime evidence:

```bash
bash scripts/collect_runtime_evidence.sh --work-dir /tmp/seed-agent-video-evidence
```

4) Generate voiceover and subtitles (Gemini-only):

```bash
python scripts/generate_voiceover.py --script assets/narration/zh_cn_script.json --out assets/audio/voiceover.wav --gemini-only
python scripts/build_subtitles.py
```

Notes:

- Voiceover is generated with Gemini TTS (`GEMINI_API_KEY` required).
- `--gemini-only` enforces strict provider usage for audit clarity.

5) Render:

```bash
bash scripts/render_video.sh --quality draft
bash scripts/render_video.sh --quality final --out output/seed_platform_120s.mp4
```

## Outputs

- Final video: `output/seed_platform_120s.mp4`
- TTS manifest: `assets/audio/tts_manifest.json`
- Subtitles: `assets/subtitles/zh.srt`, `assets/subtitles/en.srt`
- Runtime evidence: `assets/evidence/runtime_snapshot.json`, `assets/evidence/log_tail.txt`

## Notes

- Use `python` only (no `python3`).
- This pipeline does not push/upload artifacts.
- Skill/config isolation is project-scoped (`.codex-seed-video`).
