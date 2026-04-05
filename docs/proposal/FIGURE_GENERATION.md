# Proposal Figure Generation Notes

This project can generate proposal-quality conceptual architecture figures through the `right.codes/gemini` proxy using `PAPER_ONLY_API_KEY`.

## What was verified

Direct REST tests against `https://right.codes/gemini/v1beta/models/...:generateContent` succeeded.

Text generation:
- `gemini-3-pro-preview`: works.

Image generation:
- `gemini-2.5-flash-image`: works.
- `gemini-3.1-flash-image-preview`: works.
- `gemini-3-pro-image-preview`: currently not usable on this channel in our test path.

Generated samples are stored under `docs/proposal/generated_figures/`.

## Why not run PaperBanana directly out of the box

PaperBanana is usable as a style and workflow reference, but its current code assumes the standard `google-genai` client path and does not expose a proxy base URL in config.

The good news is that the proxy is compatible with the Gemini SDK once a custom base URL is provided. A minimal adaptation of PaperBanana would be:

1. Add a `google_api_base` field to `configs/model_config.yaml`.
2. Pass that value into `google.genai.Client(..., http_options=types.HttpOptions(base_url=..., api_version='v1beta'))`.
3. Use one of the image models that actually works on the proxy, preferably `gemini-3.1-flash-image-preview`.

## Recommended workflow for proposal figures

1. Start with `docs/proposal/prompts/nsfc_agent_architecture_prompt.txt`.
2. Run `scripts/generate_proposal_figure.sh`.
3. Pick the stronger sample from `docs/proposal/generated_figures/`.
4. If needed, iterate only on composition, palette, and label density.

## Usage

```bash
./scripts/generate_proposal_figure.sh \
  docs/proposal/prompts/nsfc_agent_architecture_prompt.txt \
  docs/proposal/generated_figures/task4_architecture
```

Optional environment overrides:
- `PAPER_IMAGE_MODEL` default: `gemini-3.1-flash-image-preview`
- `PAPER_IMAGE_SIZE` default: `2K`
- `PAPER_ASPECT_RATIO` default: `16:9`
- `PAPER_GEMINI_BASE` default: `https://right.codes/gemini`

## Output

The script writes:
- `<prefix>.response.json`
- `<prefix>_0_0.png` and additional image parts if returned
