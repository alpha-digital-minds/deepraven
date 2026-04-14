"""
Account-level API key management.

Account keys (prefix: dra_) allow service accounts such as Butler Agent to
authenticate with DeepRaven without a Supabase JWT — no login, no token
expiry, no refresh. They carry the same permissions as a JWT for the account
owner: create/delete projects, create project keys, etc.

All key management endpoints require a Supabase JWT — account keys cannot
manage other account keys (prevents bootstrap / escalation issues).

Endpoints:
  GET    /account/keys            — list active keys
  POST   /account/keys            — create a new key (raw key returned once)
  DELETE /account/keys/{key_id}   — revoke a key
"""
from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_jwt
from app import supabase_client as db
from app.models import AccountApiKey, AccountApiKeyCreate, AccountApiKeyCreateResponse

router = APIRouter(prefix="/account/keys", tags=["account-keys"])


def _generate_account_key(account_id: str) -> str:
    """Generate an account-level API key: dra_<account prefix>_<random hex>"""
    prefix = account_id.replace("-", "")[:8]
    random_part = secrets.token_hex(16)
    return f"dra_{prefix}_{random_part}"


@router.get("", response_model=list[AccountApiKey])
async def list_keys(account_id: str = Depends(require_jwt)) -> list[AccountApiKey]:
    rows = await db.list_account_api_keys(account_id)
    return [AccountApiKey(**row) for row in rows]


@router.post("", response_model=AccountApiKeyCreateResponse, status_code=201)
async def create_key(
    payload: AccountApiKeyCreate,
    account_id: str = Depends(require_jwt),
) -> AccountApiKeyCreateResponse:
    """
    Create a new account-level API key.
    The raw key is returned ONCE and is never stored — save it securely.
    """
    raw_key = _generate_account_key(account_id)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    row = await db.create_account_api_key(account_id, payload.name, key_hash)
    return AccountApiKeyCreateResponse(
        id=row["id"],
        account_id=row["account_id"],
        name=row["name"],
        created_at=row["created_at"],
        key=raw_key,
    )


@router.delete("/{key_id}", status_code=204)
async def revoke_key(
    key_id: str,
    account_id: str = Depends(require_jwt),
) -> None:
    revoked = await db.revoke_account_api_key(key_id, account_id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
