# Full PaperBanana Workflow for NSFC-Style Proposal Figures

This workflow is for article-grade scientific figures, not software-engineering diagrams.

## What this setup does

It uses the full PaperBanana multi-agent path:
- Retriever or no-retrieval mode
- Planner
- Stylist
- Visualizer
- Critic
- final 4K refinement

The goal is to generate a small set of strong conceptual candidates first, then lift the best one to proposal-grade 4K.

## One-time setup

```bash
./scripts/setup_paperbanana_nsfc.sh
```

This clones PaperBanana, installs its environment, and patches it to:
- use `right.codes/gemini`
- accept `PAPER_ONLY_API_KEY`
- support an external NSFC-style figure guide
- work without the PaperBanana dataset when `retrieval=none`

## Required environment

```bash
export PAPER_ONLY_API_KEY='...'
export PAPER_GEMINI_BASE='https://right.codes/gemini'
```

## Recommended defaults

```bash
export PAPERBANANA_STYLE_GUIDE_PATH="$PWD/docs/proposal/prompts/nsfc_concept_figure_style_guide.md"
export PAPERBANANA_DRAFT_IMAGE_SIZE='1K'
```

Use `1K` or `2K` for candidate generation. Use `4K` only for the final refinement stage.

## Run full candidate generation + 4K refinement

```bash
python scripts/run_paperbanana_nsfc.py \
  --paperbanana-dir "$HOME/.cache/paperbanana/PaperBanana" \
  --method-file docs/proposal/prompts/task4_methodology_for_paperbanana.md \
  --caption-file docs/proposal/prompts/task4_caption_for_paperbanana.txt \
  --output-dir /tmp/pb_nsfc_run \
  --exp-mode demo_full \
  --retrieval none \
  --candidates 2 \
  --concurrent 1 \
  --max-critic-rounds 1 \
  --aspect-ratio 16:9 \
  --pick 0 \
  --refine-4k \
  --refine-resolution 4K
```

## Output

The runner writes:
- `results.json`
- `candidate_0.jpg`, `candidate_1.jpg`, ...
- `selected_candidate.jpg`
- `selected_candidate_4K.png`

## Practical advice for proposal figures

- Keep the method text macro and conceptual.
- Keep the caption short and architectural.
- Avoid implementation nouns such as script, endpoint, API convenience, terminal UI, dashboard, and product workflow.
- Ask for three to five large conceptual regions, not many small boxes.
- Use manual selection after candidate generation. That is the professional path.
- Treat 4K refinement as the polishing stage, not the ideation stage.

## What we verified

With the current proxy channel:
- `gemini-3-pro-preview` works for text planning.
- `gemini-3.1-flash-image-preview` works for image generation and 4K refinement.
- `gemini-3-pro-image-preview` is not currently available on this channel.
