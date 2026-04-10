"""
OIDC JWT validation via OIDC discovery + JWKS.
Tokens are standard RS256-signed JWTs. Works with any OIDC-compliant provider
(Zitadel, Keycloak, Auth0, Okta, etc.).
"""

import asyncio
import logging
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()
_optional_security = HTTPBearer(auto_error=False)

_discovery_cache: dict | None = None
_jwks_cache: dict | None = None
# Cache display names by sub so we only hit UserInfo once per process lifetime
_display_name_cache: dict[str, str] = {}

_discovery_lock = asyncio.Lock()
_jwks_lock = asyncio.Lock()
_display_name_lock = asyncio.Lock()


async def _get_discovery() -> dict:
    global _discovery_cache
    if _discovery_cache is not None:
        return _discovery_cache
    async with _discovery_lock:
        if _discovery_cache is not None:
            return _discovery_cache
        url = f"{settings.oidc_issuer}/.well-known/openid-configuration"
        logger.info("Fetching OIDC discovery document from %s", url)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                _discovery_cache = resp.json()
            logger.info("OIDC discovery document fetched successfully")
        except httpx.ConnectTimeout:
            logger.error(
                "Timeout connecting to OIDC provider at %s"
                " — is OIDC_ISSUER reachable from the container?",
                url,
            )
            raise
        except httpx.HTTPStatusError as exc:
            logger.error(
                "OIDC discovery returned HTTP %s: %s",
                exc.response.status_code,
                url,
            )
            raise
        except Exception as exc:
            logger.error("Failed to fetch OIDC discovery from %s: %s", url, exc)
            raise
    return _discovery_cache


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    async with _jwks_lock:
        if _jwks_cache is not None:
            return _jwks_cache
        discovery = await _get_discovery()
        jwks_uri = discovery["jwks_uri"]
        logger.info("Fetching JWKS from %s", jwks_uri)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                jwks_resp = await client.get(jwks_uri)
                jwks_resp.raise_for_status()
                _jwks_cache = jwks_resp.json()
            logger.info(
                "JWKS fetched and cached (%d keys)",
                len(_jwks_cache.get("keys", [])),
            )
        except Exception as exc:
            logger.error("Failed to fetch JWKS from %s: %s", jwks_uri, exc)
            raise
    return _jwks_cache


async def get_display_name(token: str, payload: dict) -> str:
    """
    Return a human-readable name for the authenticated user.
    Tries JWT claims first; if absent, calls the UserInfo endpoint
    (cached by sub).
    """
    sub = payload["sub"]

    # 1. Try claims already present in the JWT
    name = (
        payload.get("preferred_username") or payload.get("name") or payload.get("email")
    )
    if name:
        return name

    # 2. Try the in-process cache
    if sub in _display_name_cache:
        return _display_name_cache[sub]

    # 3. Call the UserInfo endpoint with the bearer token
    async with _display_name_lock:
        if sub in _display_name_cache:
            return _display_name_cache[sub]
        try:
            discovery = await _get_discovery()
            userinfo_url = discovery["userinfo_endpoint"]
            logger.debug("Fetching UserInfo for sub=%s", sub)
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    userinfo_url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                resp.raise_for_status()
                info = resp.json()
            name = (
                info.get("preferred_username")
                or info.get("name")
                or info.get("email")
                or sub
            )
        except Exception as exc:
            logger.warning("UserInfo lookup failed for sub=%s: %s", sub, exc)
            name = sub

        _display_name_cache[sub] = name
    return name


async def validate_token(token: str) -> dict[str, Any]:
    """
    Validate a JWT and return the decoded payload.
    Raises HTTP 401 on any validation failure.
    """
    try:
        jwks = await _get_jwks()
        decode_options: dict[str, Any] = {"verify_at_hash": False}
        decode_kwargs: dict[str, Any] = {
            "algorithms": ["RS256"],
            "issuer": settings.oidc_issuer,
        }
        if settings.oidc_audience:
            decode_kwargs["audience"] = settings.oidc_audience
        else:
            # Some providers (e.g. Zitadel) put a project resource ID in aud
            # rather than the OAuth client ID — skip verification in that case.
            decode_options["verify_aud"] = False
        decode_kwargs["options"] = decode_options

        payload = jwt.decode(token, jwks, **decode_kwargs)
        # Stash the raw token so callers can use it for UserInfo lookups
        payload["_access_token"] = token
        logger.debug("JWT validated for sub=%s", payload.get("sub", "?"))
        return payload
    except JWTError as exc:
        logger.warning("JWT validation failed (%s): %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    return await validate_token(credentials.credentials)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_security),
) -> dict[str, Any] | None:
    """
    Returns the authenticated user, or None for unauthenticated requests when
    PUBLIC_ACCESS is enabled. Raises 401 when PUBLIC_ACCESS is disabled.
    """
    if credentials is None:
        if settings.public_access:
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    try:
        return await validate_token(credentials.credentials)
    except HTTPException:
        if settings.public_access:
            return None
        raise
