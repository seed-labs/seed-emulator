#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import os
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent.parent


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def get_text_api_key() -> str:
    return _first_env("PAPER_TEXT_API_KEY", "PAPER_ONLY_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY")


def get_text_api_base() -> str:
    return _first_env("PAPER_TEXT_API_BASE", "PAPER_TEXT_BASE", "GOOGLE_API_BASE", "PAPER_GEMINI_BASE")


def get_image_api_key() -> str:
    return _first_env("PAPER_IMAGE_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "PAPER_ONLY_API_KEY")


def get_image_api_base() -> str:
    return _first_env("PAPER_IMAGE_API_BASE", "GOOGLE_IMAGE_API_BASE", "GEMINI_IMAGE_API_BASE")


def build_genai_client(api_key: str, base_url: str, api_version: str):
    from google import genai
    from google.genai import types

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["http_options"] = types.HttpOptions(base_url=base_url, api_version=api_version)
    return genai.Client(**client_kwargs)


async def preflight_model_route(model_name: str, api_key: str, base_url: str, api_version: str, timeout_seconds: int) -> None:
    from google.genai import types

    if not api_key:
        raise RuntimeError(f"Missing credentials for preflight model {model_name}")

    client = build_genai_client(api_key, base_url, api_version)
    is_image = ("image" in model_name or "nanoviz" in model_name)
    if is_image:
        config = types.GenerateContentConfig(
            temperature=0.2,
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="16:9", image_size="1K"),
        )
        prompt = "A minimal white scientific concept figure."
    else:
        config = types.GenerateContentConfig(temperature=0.2)
        prompt = "Reply with OK only."

    response = await asyncio.wait_for(
        asyncio.to_thread(client.models.generate_content, model=model_name, contents=prompt, config=config),
        timeout=timeout_seconds,
    )

    for cand in response.candidates or []:
        for part in cand.content.parts or []:
            if is_image:
                inline = getattr(part, "inline_data", None)
                if inline and getattr(inline, "data", None):
                    return
            elif getattr(part, "text", None):
                return
    raise RuntimeError(f"Preflight model {model_name} returned no usable {'image' if is_image else 'text'} content")


def pil_bytes_to_base64_jpg(image_bytes: bytes) -> str:
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=95)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


async def refine_to_highres(image_bytes: bytes, edit_prompt: str, aspect_ratio: str, image_size: str) -> bytes:
    from google import genai
    from google.genai import types

    api_key = get_image_api_key()
    if not api_key:
        raise RuntimeError("Missing PAPER_IMAGE_API_KEY/GEMINI_API_KEY/GOOGLE_API_KEY/PAPER_ONLY_API_KEY")

    base_url = get_image_api_base()
    api_version = os.getenv("GOOGLE_IMAGE_API_VERSION") or os.getenv("GOOGLE_API_VERSION", "v1beta")
    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["http_options"] = types.HttpOptions(base_url=base_url, api_version=api_version)
    client = genai.Client(**client_kwargs)

    contents = [
        types.Part.from_text(text=edit_prompt),
        types.Part.from_bytes(mime_type="image/jpeg", data=image_bytes),
    ]
    config = types.GenerateContentConfig(
        temperature=0.8,
        max_output_tokens=8192,
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(aspect_ratio=aspect_ratio, image_size=image_size),
    )
    model = os.getenv("PAPER_IMAGE_MODEL", "gemini-3.1-flash-image-preview")
    response = await asyncio.to_thread(client.models.generate_content, model=model, contents=contents, config=config)
    for cand in response.candidates or []:
        for part in cand.content.parts or []:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                return inline.data if isinstance(inline.data, bytes) else base64.b64decode(inline.data)
    raise RuntimeError("No image returned during refinement")


async def run_pipeline(args: argparse.Namespace) -> None:
    os.environ.setdefault("PAPER_TEXT_API_KEY", get_text_api_key())
    os.environ.setdefault("PAPER_TEXT_API_BASE", get_text_api_base())
    os.environ.setdefault("PAPER_IMAGE_API_KEY", get_image_api_key())
    os.environ.setdefault("PAPER_IMAGE_API_BASE", get_image_api_base())

    # Keep legacy variables populated for the patched PaperBanana code path.
    os.environ.setdefault("GOOGLE_API_KEY", os.getenv("PAPER_TEXT_API_KEY", ""))
    if os.getenv("PAPER_TEXT_API_BASE", "").strip():
        os.environ.setdefault("GOOGLE_API_BASE", os.getenv("PAPER_TEXT_API_BASE", ""))
    os.environ.setdefault("GOOGLE_API_VERSION", "v1beta")
    os.environ.setdefault("PAPERBANANA_DRAFT_IMAGE_SIZE", args.draft_image_size)
    if args.style_guide:
        os.environ["PAPERBANANA_STYLE_GUIDE_PATH"] = str(Path(args.style_guide).resolve())

    if not args.skip_preflight:
        await preflight_model_route(
            args.model_name,
            os.getenv("PAPER_TEXT_API_KEY", ""),
            os.getenv("PAPER_TEXT_API_BASE", ""),
            os.getenv("GOOGLE_TEXT_API_VERSION") or os.getenv("GOOGLE_API_VERSION", "v1beta"),
            args.preflight_timeout,
        )
        await preflight_model_route(
            args.image_model_name,
            os.getenv("PAPER_IMAGE_API_KEY", ""),
            os.getenv("PAPER_IMAGE_API_BASE", ""),
            os.getenv("GOOGLE_IMAGE_API_VERSION") or os.getenv("GOOGLE_API_VERSION", "v1beta"),
            args.preflight_timeout,
        )

    pb_root = Path(args.paperbanana_dir).resolve()
    sys.path.insert(0, str(pb_root))

    from utils import config as pb_config
    from utils.paperviz_processor import PaperVizProcessor
    from agents.vanilla_agent import VanillaAgent
    from agents.planner_agent import PlannerAgent
    from agents.visualizer_agent import VisualizerAgent
    from agents.stylist_agent import StylistAgent
    from agents.critic_agent import CriticAgent
    from agents.retriever_agent import RetrieverAgent
    from agents.polish_agent import PolishAgent

    method_text = load_text(Path(args.method_file))
    caption_text = load_text(Path(args.caption_file))
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    exp_config = pb_config.ExpConfig(
        dataset_name="PaperBananaBench",
        task_name="diagram",
        split_name="demo",
        exp_mode=args.exp_mode,
        retrieval_setting=args.retrieval,
        max_critic_rounds=args.max_critic_rounds,
        main_model_name=args.model_name,
        image_gen_model_name=args.image_model_name,
        work_dir=pb_root,
    )

    processor = PaperVizProcessor(
        exp_config=exp_config,
        vanilla_agent=VanillaAgent(exp_config=exp_config),
        planner_agent=PlannerAgent(exp_config=exp_config),
        visualizer_agent=VisualizerAgent(exp_config=exp_config),
        stylist_agent=StylistAgent(exp_config=exp_config),
        critic_agent=CriticAgent(exp_config=exp_config),
        retriever_agent=RetrieverAgent(exp_config=exp_config),
        polish_agent=PolishAgent(exp_config=exp_config),
    )

    data_list = []
    for idx in range(args.candidates):
        data_list.append(
            {
                "filename": f"nsfc_candidate_{idx}",
                "caption": caption_text,
                "content": method_text,
                "visual_intent": caption_text,
                "additional_info": {"rounded_ratio": args.aspect_ratio},
                "max_critic_rounds": args.max_critic_rounds,
                "candidate_id": idx,
            }
        )

    results = []
    async for result in processor.process_queries_batch(data_list, max_concurrent=args.concurrent, do_eval=False):
        results.append(result)

    index_path = out_dir / "results.json"
    index_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    final_keys = []
    for idx, result in enumerate(results):
        final_key = result.get("eval_image_field") or "target_diagram_stylist_desc0_base64_jpg"
        final_keys.append(final_key)
        image_b64 = result.get(final_key)
        if not image_b64 or image_b64 == "Error":
            continue
        raw = base64.b64decode(image_b64)
        (out_dir / f"candidate_{idx}.jpg").write_bytes(raw)

    pick = max(0, min(args.pick, len(results) - 1))
    picked = results[pick]
    picked_key = picked.get("eval_image_field") or final_keys[pick]
    picked_b64 = picked.get(picked_key)
    if not picked_b64 or picked_b64 == "Error":
        raise RuntimeError(f"Selected candidate {pick} did not produce an image")

    selected_jpg = base64.b64decode(picked_b64)
    (out_dir / "selected_candidate.jpg").write_bytes(selected_jpg)

    if args.refine_4k:
        refine_prompt = load_text(Path(args.refine_prompt_file)) if args.refine_prompt_file else "Preserve the conceptual structure and semantics exactly. Upgrade the figure to proposal-grade 4K quality with cleaner hierarchy, stronger whitespace discipline, more refined typography, fewer UI-like details, and a more macro scientific architecture feeling."
        refined = await refine_to_highres(selected_jpg, refine_prompt, args.aspect_ratio, args.refine_resolution)
        (out_dir / f"selected_candidate_{args.refine_resolution}.png").write_bytes(refined)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full PaperBanana workflow for NSFC-style proposal figures")
    parser.add_argument("--paperbanana-dir", required=True)
    parser.add_argument("--method-file", required=True)
    parser.add_argument("--caption-file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--style-guide", default=str(SCRIPT_ROOT / "docs/proposal/prompts/nsfc_concept_figure_style_guide.md"))
    parser.add_argument("--refine-prompt-file", default=str(SCRIPT_ROOT / "docs/proposal/prompts/nsfc_refine_4k_prompt.txt"))
    parser.add_argument("--exp-mode", default="demo_full")
    parser.add_argument("--retrieval", default="none", choices=["auto", "manual", "random", "none"])
    parser.add_argument("--candidates", type=int, default=2)
    parser.add_argument("--concurrent", type=int, default=2)
    parser.add_argument("--max-critic-rounds", type=int, default=2)
    parser.add_argument("--aspect-ratio", default="16:9")
    parser.add_argument("--draft-image-size", default="1K")
    parser.add_argument("--pick", type=int, default=0)
    parser.add_argument("--refine-4k", action="store_true")
    parser.add_argument("--refine-resolution", default="4K")
    parser.add_argument("--model-name", default="gemini-3-pro-preview")
    parser.add_argument("--image-model-name", default="gemini-3.1-flash-image-preview")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--preflight-timeout", type=int, default=12)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run_pipeline(parse_args()))
