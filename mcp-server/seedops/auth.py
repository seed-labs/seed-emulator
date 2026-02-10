from __future__ import annotations

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings


class StaticTokenVerifier(TokenVerifier):
    """A minimal TokenVerifier for Bearer auth using a static shared secret."""

    def __init__(self, expected_token: str):
        self._expected_token = expected_token

    async def verify_token(self, token: str) -> AccessToken | None:
        if token != self._expected_token:
            return None
        return AccessToken(
            token=token,
            client_id="seedops-static-token",
            scopes=[],
            expires_at=None,
            resource=None,
        )


def build_auth_settings(public_url: str) -> AuthSettings:
    """Build minimal AuthSettings required for FastMCP to enforce Bearer auth.

    Note: We are not enabling OAuth flows in Phase 1. This is only used to
    activate the built-in auth middleware and produce standards-compliant
    WWW-Authenticate headers.
    """
    return AuthSettings(
        issuer_url=public_url,
        resource_server_url=public_url,
        required_scopes=[],
    )

