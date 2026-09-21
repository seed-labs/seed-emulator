"""Packaged deployment templates for domain-registration services."""

from importlib.resources import files


def load_template(component: str, name: str) -> str:
    """Load one immutable domain-registration deployment template."""
    for value in (component, name):
        assert value and "/" not in value and "\\" not in value, "invalid template name"
    return files(__name__).joinpath(component, name).read_text(encoding="utf-8")


def render_template(component: str, name: str, replacements: dict[str, str]) -> str:
    """Render explicit single-use markers without interpreting script braces."""
    rendered = load_template(component, name)
    for marker, value in replacements.items():
        assert marker.startswith("__SEED_") and rendered.count(marker) == 1, (
            "template marker must occur exactly once"
        )
        rendered = rendered.replace(marker, value)
    return rendered


def load_loom_template(name: str) -> str:
    return load_template("loom", name)


__all__ = ["load_loom_template", "load_template", "render_template"]
