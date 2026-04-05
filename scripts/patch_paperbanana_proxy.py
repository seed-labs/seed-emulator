#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


def ensure_import(text: str, needle: str, insert_after: str, path: Path) -> str:
    if needle in text:
        return text
    if insert_after not in text:
        raise RuntimeError(f"Could not place import in {path}: {insert_after!r}")
    return text.replace(insert_after, insert_after + needle, 1)


def patch_generation_utils(root: Path) -> None:
    path = root / "utils" / "generation_utils.py"
    text = path.read_text(encoding="utf-8")
    desired = '''# Initialize clients lazily or with robust defaults
def _first_env(*names):
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _build_gemini_client(api_key, base_url, api_version):
    if not api_key:
        return None
    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["http_options"] = types.HttpOptions(
            base_url=base_url,
            api_version=api_version,
        )
    return genai.Client(**client_kwargs)


text_api_key = _first_env("PAPER_TEXT_API_KEY", "PAPER_ONLY_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY") or get_config_val("api_keys", "google_api_key", "GOOGLE_API_KEY", "")
text_api_base = _first_env("PAPER_TEXT_API_BASE", "PAPER_TEXT_BASE", "GOOGLE_API_BASE", "PAPER_GEMINI_BASE") or get_config_val("google_api", "base_url", "GOOGLE_API_BASE", "")
text_api_version = _first_env("GOOGLE_TEXT_API_VERSION", "GOOGLE_API_VERSION") or get_config_val("google_api", "api_version", "GOOGLE_API_VERSION", "v1beta")

image_api_key = _first_env("PAPER_IMAGE_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "PAPER_ONLY_API_KEY") or text_api_key
image_api_base = _first_env("PAPER_IMAGE_API_BASE", "GOOGLE_IMAGE_API_BASE", "GEMINI_IMAGE_API_BASE")
image_api_version = _first_env("GOOGLE_IMAGE_API_VERSION", "GOOGLE_API_VERSION") or text_api_version

gemini_text_client = _build_gemini_client(text_api_key, text_api_base, text_api_version)
gemini_image_client = _build_gemini_client(image_api_key, image_api_base, image_api_version)
gemini_client = gemini_text_client or gemini_image_client

if gemini_text_client is not None:
    via_msg = f" via {text_api_base}" if text_api_base else ""
    print(f"Initialized Gemini text client{via_msg}")
else:
    print("Warning: Could not initialize Gemini text client. Missing credentials.")

if gemini_image_client is not None:
    via_msg = f" via {image_api_base}" if image_api_base else " via native Gemini"
    print(f"Initialized Gemini image client{via_msg}")
else:
    print("Warning: Could not initialize Gemini image client. Missing credentials.")
'''
    if desired not in text:
        pattern = re.compile(
            r"# Initialize clients lazily or with robust defaults\n.*?(?=\nanthropic_api_key\s*=)",
            re.S,
        )
        match = pattern.search(text)
        if not match:
            raise RuntimeError(f"Could not find Gemini init block in {path}")
        text = text[: match.start()] + desired + text[match.end() :]
    text = text.replace(
        "Please set GOOGLE_API_KEY in environment, or configure api_keys.google_api_key in configs/model_config.yaml.",
        "Please set PAPER_TEXT_API_KEY/PAPER_ONLY_API_KEY for text models and PAPER_IMAGE_API_KEY/GEMINI_API_KEY for image models, or configure api_keys.google_api_key in configs/model_config.yaml.",
    )
    text = text.replace(
        '''    if gemini_client is None:
        raise RuntimeError(
            "Gemini client was not initialized: missing Google API key. "
            "Please set GOOGLE_API_KEY, GEMINI_API_KEY, or PAPER_ONLY_API_KEY in environment, or configure api_keys.google_api_key in configs/model_config.yaml."
        )
''',
        '''    is_image_model = ("nanoviz" in model_name or "image" in model_name)
    client = gemini_image_client if is_image_model else gemini_text_client
    if client is None:
        route = "image" if is_image_model else "text"
        raise RuntimeError(
            f"Gemini {route} client was not initialized. "
            "Please set PAPER_TEXT_API_KEY/PAPER_ONLY_API_KEY for text models and PAPER_IMAGE_API_KEY/GEMINI_API_KEY for image models."
        )
''',
    )
    text = text.replace(
        '''            # Use global client
            client = gemini_client

            # Convert generic content list to Gemini's format right before the API call
''',
        '''            # Convert generic content list to Gemini's format right before the API call
''',
    )
    text = text.replace(
        '''            # If we are using Image Generation models to generate images
            if (
                "nanoviz" in model_name
                or "image" in model_name
            ):
''',
        '''            # If we are using Image Generation models to generate images
            if is_image_model:
''',
    )
    text = text.replace(
        '''            response = await client.aio.models.generate_content(
                model=model_name, contents=gemini_contents, config=config
            )
''',
        '''            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model_name, contents=gemini_contents, config=config
                ),
                timeout=int(os.getenv("PAPER_GEMINI_TIMEOUT_SECONDS", "60")),
            )
''',
    )
    text = text.replace(
        '''    result_list = []
    target_candidate_count = config.candidate_count
''',
        '''    max_attempts = int(os.getenv("PAPER_GEMINI_MAX_ATTEMPTS", str(max_attempts)))
    retry_delay = int(os.getenv("PAPER_GEMINI_RETRY_DELAY_SECONDS", str(retry_delay)))

    result_list = []
    target_candidate_count = config.candidate_count
''',
    )
    path.write_text(text, encoding="utf-8")


def patch_demo(root: Path) -> None:
    path = root / "demo.py"
    text = path.read_text(encoding="utf-8")
    new = '''    google_api_key = os.getenv("PAPER_IMAGE_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip() or get_config_val("api_keys", "google_api_key", "GOOGLE_API_KEY", "") or os.getenv("PAPER_ONLY_API_KEY", "").strip()
    google_api_base = os.getenv("PAPER_IMAGE_API_BASE", "").strip() or os.getenv("GOOGLE_IMAGE_API_BASE", "").strip() or os.getenv("GEMINI_IMAGE_API_BASE", "").strip()
    google_api_version = os.getenv("GOOGLE_IMAGE_API_VERSION", "").strip() or get_config_val("google_api", "api_version", "GOOGLE_API_VERSION", "v1beta")
    project_id = get_config_val("google_cloud", "project_id", "GOOGLE_CLOUD_PROJECT", "")

    if google_api_key:
        client_kwargs = {"api_key": google_api_key}
        if google_api_base:
            client_kwargs["http_options"] = types.HttpOptions(
                base_url=google_api_base,
                api_version=google_api_version,
            )
        client = genai.Client(**client_kwargs)
        via = "Google API key"
    elif project_id:
        location = get_config_val("google_cloud", "location", "GOOGLE_CLOUD_LOCATION", "global")
        client = genai.Client(vertexai=True, project=project_id, location=location)
        via = "Vertex AI"
    else:
        return None, "❌ Error: No image credentials configured. Set PAPER_IMAGE_API_KEY or GEMINI_API_KEY, or configure Vertex AI project in configs/model_config.yaml."
'''
    if new not in text:
        pattern = re.compile(
            r'    google_api_key = .*?\n'
            r'    google_api_base = .*?\n'
            r'    google_api_version = .*?\n'
            r'    project_id = get_config_val\("google_cloud", "project_id", "GOOGLE_CLOUD_PROJECT", ""\)\n\n'
            r'    if google_api_key:\n'
            r'        client_kwargs = \{"api_key": google_api_key\}\n'
            r'        if google_api_base:\n'
            r'            client_kwargs\["http_options"\] = types\.HttpOptions\(\n'
            r'                base_url=google_api_base,\n'
            r'                api_version=google_api_version,\n'
            r'            \)\n'
            r'        client = genai\.Client\(\*\*client_kwargs\)\n'
            r'        via = "Google API key"\n'
            r'    elif project_id:\n'
            r'        location = get_config_val\("google_cloud", "location", "GOOGLE_CLOUD_LOCATION", "global"\)\n'
            r'        client = genai\.Client\(vertexai=True, project=project_id, location=location\)\n'
            r'        via = "Vertex AI"\n'
            r'    else:\n'
            r'        return None, ".*?"\n',
            re.S,
        )
        text, count = pattern.subn(new, text, count=1)
        if count == 0:
            raise RuntimeError(f"Could not find refine client block in {path}")
    text = text.replace(
        '''        response = await asyncio.to_thread(
            client.models.generate_content,
            model=image_model,
            contents=contents,
            config=gen_config,
        )
''',
        '''        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.models.generate_content,
                model=image_model,
                contents=contents,
                config=gen_config,
            ),
            timeout=int(os.getenv("PAPER_GEMINI_TIMEOUT_SECONDS", "60")),
        )
''',
    )
    path.write_text(text, encoding="utf-8")


def patch_image_size_files(root: Path) -> None:
    for rel in [
        Path("agents/visualizer_agent.py"),
        Path("agents/vanilla_agent.py"),
        Path("agents/polish_agent.py"),
    ]:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        text = ensure_import(text, "import os\n", "from google.genai import types\n", path)
        text = text.replace('image_size="1k",', 'image_size=os.getenv("PAPERBANANA_DRAFT_IMAGE_SIZE", "1K"),')
        text = text.replace('image_size="1K",', 'image_size=os.getenv("PAPERBANANA_DRAFT_IMAGE_SIZE", "1K"),')
        path.write_text(text, encoding="utf-8")


def patch_stylist_agent(root: Path) -> None:
    path = root / "agents" / "stylist_agent.py"
    text = path.read_text(encoding="utf-8")
    old = '''        with open(self.exp_config.work_dir / f"style_guides/neurips2025_{task_name}_style_guide.md", "r", encoding="utf-8") as f:
            style_guide = f.read()
'''
    new = '''        style_guide_override = os.getenv("PAPERBANANA_STYLE_GUIDE_PATH", "").strip()
        style_guide_path = Path(style_guide_override) if style_guide_override else self.exp_config.work_dir / f"style_guides/neurips2025_{task_name}_style_guide.md"
        with open(style_guide_path, "r", encoding="utf-8") as f:
            style_guide = f.read()
'''
    if new not in text:
        if old not in text:
            raise RuntimeError(f"Could not find stylist style-guide block in {path}")
        text = text.replace(old, new, 1)
    text = text.replace(
        "You are a Lead Visual Designer for top-tier AI conferences (e.g., NeurIPS 2025).",
        "You are a Lead Visual Designer for high-level scientific proposals and top-tier academic venues.",
    )
    text = text.replace("[NeurIPS 2025 Style Guidelines]", "[Scientific Figure Style Guidelines]")
    path.write_text(text, encoding="utf-8")


def patch_planner_agent(root: Path) -> None:
    path = root / "agents" / "planner_agent.py"
    text = path.read_text(encoding="utf-8")
    old = '''        if not examples:
            retrieved_ids = data.get("top10_references", [])
            with open(self.exp_config.work_dir / f"data/PaperBananaBench/{cfg['task_name']}/ref.json", "r", encoding="utf-8") as f:
                candidate_pool = json.load(f)
            id_to_item = {item["id"]: item for item in candidate_pool}
            examples = [id_to_item[ref_id] for ref_id in retrieved_ids if ref_id in id_to_item]
'''
    new = '''        if not examples:
            retrieved_ids = data.get("top10_references", [])
            if retrieved_ids:
                with open(self.exp_config.work_dir / f"data/PaperBananaBench/{cfg['task_name']}/ref.json", "r", encoding="utf-8") as f:
                    candidate_pool = json.load(f)
                id_to_item = {item["id"]: item for item in candidate_pool}
                examples = [id_to_item[ref_id] for ref_id in retrieved_ids if ref_id in id_to_item]
            else:
                examples = []
'''
    if new not in text:
        if old not in text:
            raise RuntimeError(f"Could not find planner retrieval block in {path}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def patch_model_template(root: Path) -> None:
    path = root / "configs" / "model_config.template.yaml"
    text = path.read_text(encoding="utf-8")
    if "google_api:" not in text:
        text += '''

# Optional proxy/base URL for Gemini-compatible gateways.
google_api:
  base_url: "" # e.g. "https://right.codes/gemini"
  api_version: "v1beta"
'''
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Patch PaperBanana for Gemini proxy and proposal-grade generation")
    parser.add_argument("target_dir", type=Path)
    args = parser.parse_args()

    root = args.target_dir.resolve()
    if not (root / "README.md").exists() or not (root / "utils" / "generation_utils.py").exists():
        raise SystemExit(f"Not a PaperBanana checkout: {root}")

    patch_generation_utils(root)
    patch_demo(root)
    patch_image_size_files(root)
    patch_stylist_agent(root)
    patch_planner_agent(root)
    patch_model_template(root)
    print(f"Patched PaperBanana at {root}")


if __name__ == "__main__":
    main()
