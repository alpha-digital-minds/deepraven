"""
Authentication dependencies for FastAPI routes.

Two auth paths:
  1. API Key  — `Authorization: Bearer dr_<key>`
               Resolves to a project_id.  Used for machine-to-machine calls.
  2. JWT      — `Authorization: Bearer eyJ...` (Supabase-issued JWT)
               Resolves to an account_id.  Used for dashboard / management calls.

`require_project_access` accepts either and resolves to a project_id — used
for the profile/conversation endpoints so the dashboard can read them via JWT.

JWT verification uses Supabase's JWKS endpoint (RS256) — the legacy HS256
shared secret is no longer used.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Optional

import httpx
from fastapi import Header, HTTPException, status
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode

from app.config import get_settings
from app import supabase_client as db

logger = logging.getLogger(__name__)

# ── JWKS cache ────────────────────────────────────────────────────────────────
# Fetched once and kept in memory; refreshed on decode failure.
_jwks_cache: Optional[dict] = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    settings = get_settings()
    url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
    _jwks_cache = resp.json()
    return _jwks_cache


async def _decode_jwt(token: str) -> dict:
    """
    Verify and decode a Supabase JWT using the project's JWKS.
    Retries once with a fresh JWKS fetch on failure (handles key rotation).
    """
    global _jwks_cache
    for attempt in range(2):
        keys = await _get_jwks()
        for key_data in keys.get("keys", []):
            try:
                public_key = jwk.construct(key_data)
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=key_data.get("alg", "RS256"),
                    options={"verify_aud": False},
                )
                return payload
            except JWTError:
                continue
        # No key matched — force refresh on next attempt
        _jwks_cache = None
    raise JWTError("Token could not be verified against any JWKS key")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _bearer(authorization: str) -> str:
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header. Expected: Bearer <token>",
        )
    return parts[1]


async def _verify_jwt(token: str) -> str:
    """Decode a Supabase JWT and return the account_id (sub claim)."""
    try:
        payload = await _decode_jwt(token)
    except JWTError as exc:
        logger.debug("JWT decode failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    account_id: str | None = payload.get("sub")
    if not account_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )
    return account_id


# ── Dependencies ──────────────────────────────────────────────────────────────

async def require_api_key(authorization: str = Header(...)) -> str:
    """Validates an API key and returns its project_id."""
    token = _bearer(authorization)
    key_hash = _hash_key(token)
    row = await db.lookup_api_key(key_hash)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )
    await db.touch_api_key_used(row["id"])
    return row["project_id"]


async def require_jwt(authorization: str = Header(...)) -> str:
    """Validates a Supabase JWT (RS256 via JWKS) and returns the account_id."""
    token = _bearer(authorization)
    return await _verify_jwt(token)


async def require_account_access(authorization: str = Header(...)) -> str:
    """
    Accepts either a Supabase JWT or an account-level API key (prefix: dra_).
    Returns the account_id in both cases.

    Use this instead of require_jwt on any endpoint that service accounts
    (e.g. Butler Agent) need to call — it allows long-lived machine keys
    without storing or rotating a JWT.
    """
    token = _bearer(authorization)
    if token.startswith("dra_"):
        key_hash = _hash_key(token)
        row = await db.lookup_account_api_key(key_hash)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked account API key",
            )
        await db.touch_account_api_key_used(row["id"])
        return row["account_id"]
    return await _verify_jwt(token)


async def require_project_access(
    project_id: str,
    authorization: str = Header(...),
) -> str:
    """
    Accepts either an API key or a Supabase JWT.
    Verifies that the caller is authorized for `project_id` and returns it.
    """
    token = _bearer(authorization)

    # ── API key path ──────────────────────────────────────────────────────────
    if token.startswith("dr_"):
        key_hash = _hash_key(token)
        row = await db.lookup_api_key(key_hash)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key",
            )
        if row["project_id"] != project_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key does not belong to this project",
            )
        await db.touch_api_key_used(row["id"])
        return project_id

    # ── JWT path ──────────────────────────────────────────────────────────────
    account_id = await _verify_jwt(token)

    project = await db.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.account_id != account_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your project")

    return project_id
