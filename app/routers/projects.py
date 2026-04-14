"""
Project management and API key endpoints.
All routes require a valid Supabase JWT (dashboard / account owner access).
"""
from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.auth import require_account_access
from app import supabase_client as db
from app.models import (
    ApiKey,
    ApiKeyCreate,
    ApiKeyCreateResponse,
    Project,
    ProjectCreate,
    ProjectUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["projects"])


def _generate_raw_key(project_id: str) -> str:
    """Generate a human-readable API key: dr_<project prefix>_<random hex>"""
    prefix = project_id.replace("-", "")[:8]
    random_part = secrets.token_hex(16)
    return f"dr_{prefix}_{random_part}"


async def _assert_project_owner(project_id: str, account_id: str) -> Project:
    project = await db.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.account_id != account_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your project")
    return project


# ── Project CRUD ──────────────────────────────────────────────────────────────

@router.get("", response_model=list[Project])
async def list_projects(account_id: str = Depends(require_account_access)) -> list[Project]:
    return await db.list_projects(account_id)


@router.post("", response_model=Project, status_code=201)
async def create_project(
    payload: ProjectCreate,
    account_id: str = Depends(require_account_access),
) -> Project:
    return await db.create_project(account_id, payload.name, payload.description)


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    account_id: str = Depends(require_account_access),
) -> Project:
    return await _assert_project_owner(project_id, account_id)


@router.patch("/{project_id}", response_model=Project)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    account_id: str = Depends(require_account_access),
) -> Project:
    await _assert_project_owner(project_id, account_id)
    updated = await db.update_project(project_id, payload.name, payload.description)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return updated


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    account_id: str = Depends(require_account_access),
) -> None:
    await _assert_project_owner(project_id, account_id)
    deleted = await db.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


# ── API Key management ────────────────────────────────────────────────────────

@router.get("/{project_id}/keys", response_model=list[ApiKey])
async def list_keys(
    project_id: str,
    account_id: str = Depends(require_account_access),
) -> list[ApiKey]:
    await _assert_project_owner(project_id, account_id)
    rows = await db.list_api_keys(project_id)
    return [ApiKey(**row) for row in rows]


@router.post("/{project_id}/keys", response_model=ApiKeyCreateResponse, status_code=201)
async def create_key(
    project_id: str,
    payload: ApiKeyCreate,
    account_id: str = Depends(require_account_access),
) -> ApiKeyCreateResponse:
    """
    Create a new API key for a project.
    The raw key is returned ONCE in this response and is never stored.
    """
    await _assert_project_owner(project_id, account_id)
    import hashlib
    raw_key = _generate_raw_key(project_id)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    row = await db.create_api_key(project_id, payload.name, key_hash)
    return ApiKeyCreateResponse(
        id=row["id"],
        project_id=row["project_id"],
        name=row["name"],
        created_at=row["created_at"],
        key=raw_key,
    )


@router.get("/{project_id}/profiles/export")
async def export_profiles(
    project_id: str,
    account_id: str = Depends(require_account_access),
) -> Response:
    """Download all contact profiles for a project as a single JSON file."""
    project = await _assert_project_owner(project_id, account_id)
    contacts = await db.export_project_profiles(project_id)
    payload = {
        "project_id": project_id,
        "project_name": project.name,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "total_contacts": len(contacts),
        "contacts": contacts,
    }
    safe_name = project.name.replace(" ", "_").replace("/", "_")
    filename = f"profiles_{safe_name}.json"
    return Response(
        content=json.dumps(payload, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{project_id}/keys/{key_id}", status_code=204)
async def revoke_key(
    project_id: str,
    key_id: str,
    account_id: str = Depends(require_account_access),
) -> None:
    await _assert_project_owner(project_id, account_id)
    revoked = await db.revoke_api_key(key_id, project_id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
