import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_project_access
from app import supabase_client as db
from app import redis_client as locks
from app.config import get_settings
from app.models import (
    AddConversationResponse,
    ConversationInput,
    ConversationRecord,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/projects/{project_id}/contacts/{contact_id}",
    tags=["conversations"],
)


@router.post("/conversations", response_model=AddConversationResponse)
async def add_conversations(
    project_id: str,
    contact_id: str,
    payload: ConversationInput,
    _: str = Depends(require_project_access),
) -> AddConversationResponse:
    """
    Ingest conversation messages for a contact.
    Stores immediately, then (re)sets the extraction window in Redis.
    The worker processes all accumulated conversations once the window closes.
    Accepts an API key or a JWT that owns the project.
    """
    if not payload.messages:
        raise HTTPException(status_code=422, detail="messages list cannot be empty")

    # Resolve by internal UUID (dashboard) or get/create by external_id (API clients)
    contact = await db.resolve_or_create_contact(project_id, contact_id)
    internal_id = contact.id

    record = ConversationRecord(messages=payload.messages, metadata=payload.metadata)
    await db.append_conversation(internal_id, project_id, record)

    # (Re)schedule extraction — resets the deadline, batching this conversation
    # with any others that arrive within the same window.
    delay = get_settings().extraction_delay_seconds
    await locks.schedule_extraction(project_id, internal_id, delay)

    return AddConversationResponse(
        contact_id=contact_id,
        project_id=project_id,
        conversations_added=len(payload.messages),
        profile_update="scheduled",
    )


@router.get("/conversations", response_model=list[ConversationRecord])
async def get_conversations(
    project_id: str,
    contact_id: str,
    limit: int = 20,
    _: str = Depends(require_project_access),
) -> list[ConversationRecord]:
    """Return the most recent N conversation records for a contact."""
    limit = min(limit, 100)
    contact = await db.resolve_contact(project_id, contact_id)
    if not contact:
        return []
    return await db.get_recent_conversations(contact.id, limit)


@router.delete("/conversations", status_code=204)
async def delete_conversations(
    project_id: str,
    contact_id: str,
    _: str = Depends(require_project_access),
) -> None:
    """GDPR: Erase all conversation history for a contact."""
    contact = await db.resolve_contact(project_id, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await db.delete_conversations(contact.id, project_id)
