# SEED Agent Stage Pack

This folder is the single entry for the stage report, live operation, evidence review, and proposal material.

## What to open first

1. `TALK_TRACK_CN.md`
2. `LIVE_RUNBOOK.md`
3. `EVIDENCE_SUMMARY.md`
4. `FIGURE_PROMPTS_READY.md`

## Folder layout

- `TALK_TRACK_CN.md`: Chinese speaking script for the report
- `LIVE_RUNBOOK.md`: live demo path, backup path, and emergency switches
- `EVIDENCE_SUMMARY.md`: metrics and evidence pointers
- `FIGURE_PROMPTS_READY.md`: direct prompts for manual Gemini image generation
- `prompts/`: source prompt materials
- `evidence/`: copied evidence used in the report
- `proposal/`: current proposal draft copy
- `assets/`: current architecture figure copy

## Final figure picks

- Architecture figure: `assets/final_architecture_4k.jpeg`
- Principle figure: `assets/final_principle_4k.jpeg`
- Original exported files are kept as `assets/1.jpeg` and `assets/2.jpeg`

## Fast claim

SEED now supports supervised agentic operation on already-running network experiments through the closed loop:

`attach -> inspect -> decide -> operate -> verify -> summarize`

This is not only topology generation. It is runtime maintenance and controlled experimentation over live SEED outputs.
