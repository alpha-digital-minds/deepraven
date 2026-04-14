"""
Contact listing endpoints (JWT-auth — for the dashboard).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_jwt
from app import supabase_client as db
from app.models import Contact, ContactSummary

router = APIRouter(prefix="/projects/{project_id}/contacts", tags=["contacts"])


async def _assert_project_owner(project_id: str, account_id: str) -> None:
    project = await db.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.account_id != account_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your project")


@router.get("", response_model=list[ContactSummary])
async def list_contacts(
    project_id: str,
    account_id: str = Depends(require_jwt),
) -> list[ContactSummary]:
    await _assert_project_owner(project_id, account_id)
    return await db.list_contacts(project_id)


@router.get("/{contact_id}", response_model=Contact)
async def get_contact(
    project_id: str,
    contact_id: str,
    account_id: str = Depends(require_jwt),
) -> Contact:
    await _assert_project_owner(project_id, account_id)
    contact = await db.get_contact(contact_id, project_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact
