"""Fail-closed natural-language and normalized-intent security policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Dict, Tuple

from generator.nl.models import BenchmarkIntent


@dataclass(frozen=True)
class SecurityFinding:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class SecurityReport:
    allowed: bool
    findings: Tuple[SecurityFinding, ...]

    def to_dict(self) -> Dict[str, object]:
        return {"allowed": self.allowed, "findings": [asdict(item) for item in self.findings]}


PATTERNS = (
    ("prompt_override", r"(?:ignore|忽略).{0,30}(?:instruction|规则|指令|system|安全)"),
    ("safety_bypass", r"(?:bypass|绕过|关闭|禁用).{0,30}(?:safety|安全|审核|门禁|policy)"),
    ("answer_exfiltration", r"(?:reveal|显示|输出|泄露).{0,30}(?:oracle|标准答案|system prompt|系统提示)"),
    ("host_destructive_command", r"(?:rm\s+-rf|mkfs\b|shutdown\b|reboot\b|sudo\s+)"),
    ("docker_socket_access", r"/var/run/docker\.sock"),
    ("credential_request", r"(?:api[_ -]?key|私钥|private key|密码).{0,30}(?:显示|输出|读取|偷取|reveal|print)"),
)


def inspect_natural_language(text: str) -> SecurityReport:
    findings = []
    if not text.strip():
        findings.append(SecurityFinding("empty_input", "block", "natural-language request is empty"))
    if len(text) > 8000:
        findings.append(SecurityFinding("input_too_long", "block", "request exceeds 8000 characters"))
    if any(ord(character) < 32 and character not in "\n\r\t" for character in text):
        findings.append(SecurityFinding("control_character", "block", "request contains control characters"))
    for code, pattern in PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            findings.append(SecurityFinding(code, "block", "request contains prohibited control or escape intent"))
    return SecurityReport(not findings, tuple(findings))


def inspect_intent(intent: BenchmarkIntent, source_text: str) -> SecurityReport:
    findings = list(inspect_natural_language(intent.objective).findings)
    source = source_text.casefold()
    if intent.publish_requested and not any(item in source for item in ("publish", "release", "正式发布")):
        findings.append(SecurityFinding("unrequested_publish", "block", "model requested publication without user intent"))
    if intent.source_text_sha256 != __import__("hashlib").sha256(
        " ".join(source_text.split()).encode("utf-8")
    ).hexdigest():
        findings.append(SecurityFinding("source_mismatch", "block", "intent is not bound to source text"))
    return SecurityReport(not findings, tuple(findings))
