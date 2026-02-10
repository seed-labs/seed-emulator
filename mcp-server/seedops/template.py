from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


_TEMPLATE_RE = re.compile(r"{{\s*(.+?)\s*}}")
_FULL_TEMPLATE_RE = re.compile(r"^\s*{{\s*(.+?)\s*}}\s*$")


class TemplateError(ValueError):
    pass


@dataclass(frozen=True)
class _Token:
    kind: str  # "key" | "index"
    value: str | int


def _parse_path(expr: str) -> list[_Token]:
    s = expr.strip()
    if not s:
        raise TemplateError("Empty template expression.")

    i = 0
    out: list[_Token] = []

    def skip_ws() -> None:
        nonlocal i
        while i < len(s) and s[i].isspace():
            i += 1

    def parse_identifier() -> str:
        nonlocal i
        if i >= len(s) or not (s[i].isalpha() or s[i] == "_"):
            raise TemplateError(f"Expected identifier at: {s[i:]!r}")
        start = i
        i += 1
        while i < len(s) and (s[i].isalnum() or s[i] in {"_", "-"}):
            i += 1
        return s[start:i]

    def parse_quoted_string() -> str:
        nonlocal i
        q = s[i]
        i += 1
        buf: list[str] = []
        while i < len(s):
            ch = s[i]
            i += 1
            if ch == q:
                return "".join(buf)
            if ch == "\\" and i < len(s):
                esc = s[i]
                i += 1
                if esc in {q, "\\", "/"}:
                    buf.append(esc)
                elif esc == "n":
                    buf.append("\n")
                elif esc == "r":
                    buf.append("\r")
                elif esc == "t":
                    buf.append("\t")
                else:
                    buf.append(esc)
            else:
                buf.append(ch)
        raise TemplateError("Unterminated string in template expression.")

    def parse_bracket_token() -> _Token:
        nonlocal i
        if s[i] != "[":
            raise TemplateError("Expected '['")
        i += 1
        skip_ws()
        if i >= len(s):
            raise TemplateError("Unterminated '[' in template expression.")
        if s[i] in {"'", '"'}:
            key = parse_quoted_string()
            skip_ws()
            if i >= len(s) or s[i] != "]":
                raise TemplateError("Expected ']' after string key in template expression.")
            i += 1
            return _Token(kind="key", value=key)

        # index
        start = i
        while i < len(s) and s[i].isdigit():
            i += 1
        if start == i:
            raise TemplateError("Expected integer index or quoted key in brackets.")
        idx = int(s[start:i])
        skip_ws()
        if i >= len(s) or s[i] != "]":
            raise TemplateError("Expected ']' after index in template expression.")
        i += 1
        return _Token(kind="index", value=idx)

    skip_ws()
    if i < len(s) and s[i] == "[":
        out.append(parse_bracket_token())
    else:
        out.append(_Token(kind="key", value=parse_identifier()))

    while True:
        skip_ws()
        if i >= len(s):
            break
        if s[i] == ".":
            i += 1
            skip_ws()
            if i < len(s) and s[i] == "[":
                out.append(parse_bracket_token())
            else:
                out.append(_Token(kind="key", value=parse_identifier()))
            continue
        if s[i] == "[":
            out.append(parse_bracket_token())
            continue
        raise TemplateError(f"Unexpected character in template expression: {s[i]!r}")

    return out


def _eval_path(expr: str, context: dict[str, Any]) -> Any:
    cur: Any = context
    for tok in _parse_path(expr):
        if tok.kind == "key":
            key = str(tok.value)
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                raise TemplateError(f"Missing key {key!r} while evaluating: {expr!r}")
        else:
            idx = int(tok.value)  # type: ignore[arg-type]
            if isinstance(cur, list) and 0 <= idx < len(cur):
                cur = cur[idx]
            else:
                raise TemplateError(f"Invalid index {idx} while evaluating: {expr!r}")
    return cur


def _stringify(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, (str, int, float, bool)):
        return str(val)
    return json.dumps(val, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def render_value(value: Any, context: dict[str, Any]) -> Any:
    """Render templates in a value.

    - If a string is exactly `{{ expr }}`, returns the evaluated object (type-preserving).
    - Otherwise, performs string interpolation using `str(...)` / JSON.
    """
    if isinstance(value, dict):
        return {k: render_value(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [render_value(v, context) for v in value]
    if not isinstance(value, str):
        return value

    full = _FULL_TEMPLATE_RE.match(value)
    if full:
        expr = full.group(1)
        return _eval_path(expr, context)

    def repl(m: re.Match[str]) -> str:
        expr = m.group(1)
        return _stringify(_eval_path(expr, context))

    if "{{" not in value:
        return value
    return _TEMPLATE_RE.sub(repl, value)

