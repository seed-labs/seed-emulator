#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = REPO_ROOT / "docs" / "assets" / "generated"
WIDTH = 3840
HEIGHT = 2160

PALETTE = {
    "bg": (246, 248, 251, 255),
    "panel": (255, 255, 255, 255),
    "shadow": (15, 23, 42, 20),
    "border": (221, 228, 236, 255),
    "title": (15, 23, 42, 255),
    "text": (44, 58, 79, 255),
    "muted": (102, 118, 139, 255),
    "green": (20, 102, 88, 255),
    "green_soft": (230, 246, 241, 255),
    "blue": (39, 101, 183, 255),
    "blue_soft": (232, 241, 251, 255),
    "amber": (181, 104, 17, 255),
    "amber_soft": (252, 241, 225, 255),
    "slate": (71, 85, 105, 255),
    "slate_soft": (240, 244, 248, 255),
    "red_soft": (254, 242, 242, 255),
}

FONT_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def ensure_assets_dir() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def latest_summary(profile: str) -> dict:
    return read_json(
        REPO_ROOT / "output" / "profile_runs" / profile / "latest" / "validation" / "summary.json"
    )


def latest_protocol_health(profile: str) -> dict:
    return read_json(
        REPO_ROOT
        / "output"
        / "profile_runs"
        / profile
        / "latest"
        / "validation"
        / "protocol_health.json"
    )


def wrap_text(draw: ImageDraw.ImageDraw, text: str, text_font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textlength(trial, font=text_font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_panel(
    image: Image.Image,
    xy: tuple[int, int, int, int],
    *,
    radius: int = 36,
    fill=(255, 255, 255, 255),
    border=(221, 228, 236, 255),
    shadow=True,
) -> None:
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    drawer = ImageDraw.Draw(overlay)
    x1, y1, x2, y2 = xy
    if shadow:
        drawer.rounded_rectangle(
            (x1 + 10, y1 + 14, x2 + 10, y2 + 14),
            radius=radius,
            fill=PALETTE["shadow"],
        )
    drawer.rounded_rectangle(xy, radius=radius, fill=fill, outline=border, width=2)
    image.alpha_composite(overlay)


def draw_chip(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, fill, text_fill) -> int:
    text_font = font(FONT_SANS_BOLD, 30)
    padding_x = 26
    padding_y = 14
    bbox = draw.textbbox((0, 0), label, font=text_font)
    width = (bbox[2] - bbox[0]) + padding_x * 2
    height = (bbox[3] - bbox[1]) + padding_y * 2
    draw.rounded_rectangle((x, y, x + width, y + height), radius=22, fill=fill)
    draw.text((x + padding_x, y + padding_y - 4), label, font=text_font, fill=text_fill)
    return width


def draw_arrow(draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, fill) -> None:
    draw.line((x1, y1, x2, y2), fill=fill, width=8)
    draw.polygon(
        [
            (x2, y2),
            (x2 - 28, y2 - 18),
            (x2 - 28, y2 + 18),
        ],
        fill=fill,
    )


def draw_multiline(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    *,
    text_font,
    fill,
    max_width: int,
    line_gap: int = 10,
) -> int:
    current_y = y
    paragraphs = text.splitlines() or [text]
    for paragraph in paragraphs:
        lines = wrap_text(draw, paragraph, text_font, max_width)
        for line in lines:
            draw.text((x, current_y), line, font=text_font, fill=fill)
            bbox = draw.textbbox((x, current_y), line, font=text_font)
            current_y = bbox[3] + line_gap
    return current_y


def status_label(summary: dict) -> str:
    if not summary:
        return "No data"
    return "PASS" if summary.get("failure_code", "") == "" else summary.get("failure_code", "FAIL")


def draw_runtime_overview() -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), PALETTE["bg"])
    draw = ImageDraw.Draw(image)

    title_font = font(FONT_SANS_BOLD, 94)
    sub_font = font(FONT_SANS, 40)
    section_font = font(FONT_SANS_BOLD, 54)
    body_font = font(FONT_SANS, 36)
    body_bold = font(FONT_SANS_BOLD, 36)
    mono_font = font(FONT_MONO, 30)

    draw.text((180, 110), "SEED Emulator runtime overview", font=title_font, fill=PALETTE["title"])
    subtitle = (
        "One topology compiler, two execution tracks: historical Docker Compose for legacy single-host runs, "
        "and evidence-first K3s/Kubernetes for multi-node experimentation."
    )
    draw_multiline(
        draw,
        184,
        235,
        subtitle,
        text_font=sub_font,
        fill=PALETTE["muted"],
        max_width=3200,
        line_gap=8,
    )

    left_box = (140, 380, 1130, 1260)
    mid_box = (1360, 380, 2350, 1260)
    right_box = (2580, 380, 3700, 1260)
    draw_panel(image, left_box, fill=PALETTE["panel"])
    draw_panel(image, mid_box, fill=PALETTE["panel"])
    draw_panel(image, right_box, fill=PALETTE["panel"])

    draw_chip(draw, 180, 430, "1. Compile once", PALETTE["blue_soft"], PALETTE["blue"])
    draw.text((182, 520), "Python example", font=section_font, fill=PALETTE["title"])
    draw_multiline(
        draw,
        182,
        610,
        "Examples under examples/ describe the topology, then compile to concrete runtime manifests.",
        text_font=body_font,
        fill=PALETTE["text"],
        max_width=820,
    )
    draw_panel(image, (190, 790, 1080, 1160), fill=(250, 252, 255, 255), shadow=False)
    draw.text((240, 840), "Compile outputs", font=body_bold, fill=PALETTE["title"])
    for idx, line in enumerate(
        [
            "Docker track: output/docker-compose.yml",
            "K3s track: compiled/k8s.yaml",
            "Image build script: build_images.sh",
        ]
    ):
        draw.text((240, 920 + idx * 76), line, font=mono_font, fill=PALETTE["slate"])

    draw_chip(draw, 1400, 430, "2. Legacy Compose track", PALETTE["amber_soft"], PALETTE["amber"])
    draw.text((1402, 520), "Docker Compose", font=section_font, fill=PALETTE["title"])
    current_y = 610
    for line in [
        "Best for quick single-host runs and historical examples.",
        "Typical flow: build -> up -> manual docker ps/logs/exec checks.",
        "Large topologies may need batched starts to avoid host pressure.",
    ]:
        current_y = (
            draw_multiline(
                draw,
                1402,
                current_y,
                line,
                text_font=body_font,
                fill=PALETTE["text"],
                max_width=830,
            )
            + 22
        )
    draw_panel(image, (1410, 900, 2290, 1160), fill=(255, 250, 244, 255), shadow=False)
    draw.text((1460, 960), "Legacy control loop", font=body_bold, fill=PALETTE["title"])
    draw.text(
        (1460, 1040),
        "docker compose build && docker compose up\n"
        "docker ps / docker logs / docker exec",
        font=mono_font,
        fill=PALETTE["slate"],
        spacing=14,
    )

    draw_chip(draw, 2620, 430, "3. Evidence-first K3s track", PALETTE["green_soft"], PALETTE["green"])
    draw.text((2622, 520), "K3s / Kubernetes", font=section_font, fill=PALETTE["title"])
    current_y = 610
    for line in [
        "Built for multi-node KVM and future multi-server deployment.",
        "Runner manages build, deploy, phased protocol startup, verify, observe, and report.",
        "Every run leaves fixed evidence artifacts for humans and AI.",
    ]:
        current_y = (
            draw_multiline(
                draw,
                2622,
                current_y,
                line,
                text_font=body_font,
                fill=PALETTE["text"],
                max_width=900,
            )
            + 22
        )
    draw_panel(image, (2630, 900, 3640, 1160), fill=(243, 250, 248, 255), shadow=False)
    draw.text((2680, 960), "Unified entry", font=body_bold, fill=PALETTE["title"])
    draw.text(
        (2680, 1040),
        "scripts/seed_k8s_profile_runner.sh <profile> <action>\n"
        "k3sall / k3sup / k3sphase / k3sverify / k3sui",
        font=mono_font,
        fill=PALETTE["slate"],
        spacing=14,
    )

    draw_arrow(draw, left_box[2] + 10, 820, mid_box[0] - 20, 820, PALETTE["border"])
    draw_arrow(draw, mid_box[2] + 10, 820, right_box[0] - 20, 820, PALETTE["border"])

    draw.text((180, 1360), "Current validated profiles", font=section_font, fill=PALETTE["title"])

    profiles = [
        ("mini_internet", latest_summary("mini_internet"), latest_protocol_health("mini_internet"), PALETTE["blue"]),
        ("real_topology_rr", latest_summary("real_topology_rr"), latest_protocol_health("real_topology_rr"), PALETTE["green"]),
        ("real_topology_rr_scale", latest_summary("real_topology_rr_scale"), latest_protocol_health("real_topology_rr_scale"), PALETTE["amber"]),
    ]
    start_x = 140
    card_width = 1130
    gap = 80
    for idx, (profile, summary, health, accent) in enumerate(profiles):
        x1 = start_x + idx * (card_width + gap)
        x2 = x1 + card_width
        draw_panel(image, (x1, 1460, x2, 2020), fill=PALETTE["panel"])
        display_name = {
            "mini_internet": "Mini Internet",
            "real_topology_rr": "Real Topology RR",
            "real_topology_rr_scale": "Real Topology RR Scale",
        }.get(profile, profile)
        draw_chip(draw, x1 + 36, 1498, display_name, accent, (255, 255, 255, 255))
        draw.text((x1 + 36, 1588), profile, font=mono_font, fill=PALETTE["muted"])
        draw.text((x1 + 36, 1660), f"Status: {status_label(summary)}", font=body_bold, fill=PALETTE["title"])
        if summary:
            facts = [
                f"Nodes used: {summary.get('nodes_used', '?')}"
                + (
                    f"   Topology size: {summary.get('topology_size')}"
                    if summary.get("topology_size")
                    else ""
                ),
                f"Startup: {summary.get('bgp_startup_mode', 'n/a')}   Placement: {summary.get('as_placement_mode', summary.get('placement_mode', 'n/a'))}",
                f"Build / up / phase: {summary.get('build_duration_seconds', '?')}s / {summary.get('up_duration_seconds', '?')}s / {summary.get('phase_start_duration_seconds', '?')}s",
            ]
            current_y = 1735
            for fact in facts:
                current_y = draw_multiline(
                    draw,
                    x1 + 36,
                    current_y,
                    fact,
                    text_font=font(FONT_SANS, 33),
                    fill=PALETTE["text"],
                    max_width=card_width - 72,
                    line_gap=8,
                )
        families = (health.get("families") or {}) if health else {}
        proto_box_y = 1880
        draw.rounded_rectangle(
            (x1 + 36, proto_box_y, x2 - 36, proto_box_y + 96),
            radius=22,
            fill=(246, 249, 253, 255),
        )
        draw.text((x1 + 62, proto_box_y + 16), "Healthy protocols", font=font(FONT_SANS_BOLD, 28), fill=PALETTE["slate"])
        proto_line = (
            f"iBGP {families.get('ibgp', {}).get('healthy', 0)}/{families.get('ibgp', {}).get('total', 0)}   "
            f"eBGP {families.get('ebgp', {}).get('healthy', 0)}/{families.get('ebgp', {}).get('total', 0)}   "
            f"OSPF {families.get('ospf', {}).get('healthy', 0)}/{families.get('ospf', {}).get('total', 0)}"
        )
        draw.text((x1 + 62, proto_box_y + 52), proto_line, font=font(FONT_MONO, 24), fill=PALETTE["slate"])

    footer = (
        f"Generated from latest artifacts on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
        f"by tools/generate_k8s_readme_figures.py"
    )
    draw.text((180, 2060), footer, font=font(FONT_SANS, 28), fill=PALETTE["muted"])
    image.convert("RGB").save(ASSET_DIR / "seed-k8s-runtime-overview.png", quality=95)


def draw_evidence_loop() -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), PALETTE["bg"])
    draw = ImageDraw.Draw(image)

    title_font = font(FONT_SANS_BOLD, 94)
    sub_font = font(FONT_SANS, 40)
    section_font = font(FONT_SANS_BOLD, 52)
    body_font = font(FONT_SANS, 34)
    body_bold = font(FONT_SANS_BOLD, 34)
    mono_font = font(FONT_MONO, 30)

    scale_summary = latest_summary("real_topology_rr_scale")
    scale_health = latest_protocol_health("real_topology_rr_scale")

    draw.text((180, 110), "K3s mainline: evidence-first execution loop", font=title_font, fill=PALETTE["title"])
    draw_multiline(
        draw,
        184,
        235,
        "The K3s path is not just deploy-and-pray. It separates Pod bring-up from protocol startup, then writes fixed artifacts for validation, observation, and reporting.",
        text_font=sub_font,
        fill=PALETTE["muted"],
        max_width=3200,
    )

    steps = [
        ("doctor", PALETTE["slate_soft"], PALETTE["slate"]),
        ("build", PALETTE["blue_soft"], PALETTE["blue"]),
        ("start / up", PALETTE["blue_soft"], PALETTE["blue"]),
        ("phase-start", PALETTE["green_soft"], PALETTE["green"]),
        ("verify", PALETTE["green_soft"], PALETTE["green"]),
        ("observe", PALETTE["amber_soft"], PALETTE["amber"]),
        ("report", PALETTE["amber_soft"], PALETTE["amber"]),
        ("showcase", PALETTE["slate_soft"], PALETTE["slate"]),
    ]
    x = 140
    y = 420
    box_w = 410
    box_h = 160
    gap = 46
    for idx, (label, fill, text_fill) in enumerate(steps):
        draw_panel(image, (x, y, x + box_w, y + box_h), fill=fill, border=fill, shadow=False)
        draw.text((x + 44, y + 52), label, font=section_font, fill=text_fill)
        if idx < len(steps) - 1:
            draw_arrow(draw, x + box_w + 6, y + box_h // 2, x + box_w + gap - 6, y + box_h // 2, PALETTE["border"])
        x += box_w + gap

    draw_panel(image, (140, 760, 2250, 1910), fill=PALETTE["panel"])
    draw.text((190, 830), "Artifact contract", font=section_font, fill=PALETTE["title"])
    draw_multiline(
        draw,
        190,
        925,
        "Every formal K3s profile writes the same core evidence set so humans, CI, and AI can all answer the same question: what ran, what passed, and where should we look next?",
        text_font=body_font,
        fill=PALETTE["text"],
        max_width=1880,
    )
    groups = [
        (
            "validation/",
            [
                "summary.json",
                "protocol_health.json",
                "placement_by_as.tsv",
                "connectivity_matrix.tsv",
                "failure_injection_summary.json",
                "resource_summary.json",
                "convergence_timeline.json",
            ],
            190,
            1110,
            PALETTE["blue_soft"],
            PALETTE["blue"],
        ),
        (
            "report/",
            ["report.json"],
            980,
            1110,
            PALETTE["green_soft"],
            PALETTE["green"],
        ),
        (
            "runner/",
            ["runner_summary.json", "diagnostics.json", "next_actions.json"],
            1450,
            1110,
            PALETTE["amber_soft"],
            PALETTE["amber"],
        ),
    ]
    for group_name, files, gx, gy, fill, text_fill in groups:
        draw.rounded_rectangle((gx, gy, gx + 420, gy + 72), radius=20, fill=fill)
        draw.text((gx + 26, gy + 16), group_name, font=body_bold, fill=text_fill)
        current_y = gy + 98
        for line in files:
            draw.rounded_rectangle((gx, current_y, gx + 560, current_y + 76), radius=20, fill=(250, 252, 255, 255))
            draw.text((gx + 28, current_y + 20), line, font=mono_font, fill=PALETTE["slate"])
            current_y += 100

    draw_panel(image, (2450, 760, 3700, 1910), fill=PALETTE["panel"])
    draw.text((2500, 830), "Latest real_topology_rr_scale facts", font=section_font, fill=PALETTE["title"])
    fact_lines = [
        f"Profile kind: {scale_summary.get('profile_kind', 'n/a')}",
        f"bird_autostart: {scale_summary.get('bird_autostart', 'n/a')}",
        f"Startup mode: {scale_summary.get('bgp_startup_mode', 'n/a')}",
        f"Placement mode: {scale_summary.get('as_placement_mode', scale_summary.get('placement_mode', 'n/a'))}",
        f"Registry: {scale_summary.get('registry', 'n/a')}",
        f"CNI: {scale_summary.get('cni_type', 'n/a')} on {scale_summary.get('cni_master_interface', 'n/a')}",
        f"Nodes used / topology size: {scale_summary.get('nodes_used', '?')} / {scale_summary.get('topology_size', '?')}",
        f"Build / up / phase / total: {scale_summary.get('build_duration_seconds', '?')}s / {scale_summary.get('up_duration_seconds', '?')}s / {scale_summary.get('phase_start_duration_seconds', '?')}s / {scale_summary.get('duration_seconds', '?')}s",
    ]
    current_y = 930
    for line in fact_lines:
        current_y = draw_multiline(
            draw,
            2500,
            current_y,
            line,
            text_font=body_font,
            fill=PALETTE["text"],
            max_width=1110,
            line_gap=8,
        ) + 18
    families = scale_health.get("families", {})
    protocol_box_y = 1600
    draw.rounded_rectangle((2500, protocol_box_y, 3640, protocol_box_y + 220), radius=28, fill=PALETTE["green_soft"])
    draw.text((2550, protocol_box_y + 36), "Protocol health sample", font=body_bold, fill=PALETTE["green"])
    proto_lines = [
        f"iBGP  {families.get('ibgp', {}).get('healthy', 0)}/{families.get('ibgp', {}).get('total', 0)} healthy",
        f"eBGP  {families.get('ebgp', {}).get('healthy', 0)}/{families.get('ebgp', {}).get('total', 0)} healthy",
        f"OSPF  {families.get('ospf', {}).get('healthy', 0)}/{families.get('ospf', {}).get('total', 0)} healthy",
    ]
    for idx, line in enumerate(proto_lines):
        draw.text((2550, protocol_box_y + 98 + idx * 42), line, font=mono_font, fill=PALETTE["green"])

    draw_panel(image, (140, 1960, 3700, 2060), fill=PALETTE["panel"], shadow=False)
    draw.text(
        (200, 1989),
        "Profiles currently anchored on this loop: mini_internet, real_topology_rr (214), real_topology_rr_scale (214).",
        font=body_bold,
        fill=PALETTE["title"],
    )
    draw.text(
        (200, 2032),
        "The same artifacts are what the showcase UI reads, and what opencode should inspect before answering operational questions.",
        font=font(FONT_SANS, 28),
        fill=PALETTE["muted"],
    )
    image.convert("RGB").save(ASSET_DIR / "seed-k3s-evidence-loop.png", quality=95)


def main() -> None:
    ensure_assets_dir()
    draw_runtime_overview()
    draw_evidence_loop()
    print(str(ASSET_DIR / "seed-k8s-runtime-overview.png"))
    print(str(ASSET_DIR / "seed-k3s-evidence-loop.png"))


if __name__ == "__main__":
    main()
