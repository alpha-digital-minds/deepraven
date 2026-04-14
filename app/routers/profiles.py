import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response

from app.auth import require_project_access
from app import supabase_client as db
from app import redis_client as locks
from app.llm import compress_profile, extract_and_update_profile
from app.models import ProfileUpdateStatus, UserProfile

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/projects/{project_id}/contacts/{contact_id}",
    tags=["profiles"],
)


@router.get("/profile", response_model=UserProfile)
async def get_profile(
    project_id: str,
    contact_id: str,
    _: str = Depends(require_project_access),
) -> UserProfile:
    """Return the current profile for a contact. Creates an empty one if new."""
    contact = await db.resolve_or_create_contact(project_id, contact_id)
    return await db.get_or_create_profile(contact.id, project_id)


@router.get("/profile/status", response_model=ProfileUpdateStatus)
async def get_profile_status(
    project_id: str,
    contact_id: str,
    _: str = Depends(require_project_access),
) -> ProfileUpdateStatus:
    """Check whether profile extraction is currently running for this contact."""
    contact = await db.resolve_or_create_contact(project_id, contact_id)
    locked = await locks.is_locked(project_id, contact.id)
    return ProfileUpdateStatus(
        contact_id=contact_id,
        status="processing" if locked else "idle",
    )


@router.post("/profile/extract", response_model=ProfileUpdateStatus)
async def trigger_extraction(
    project_id: str,
    contact_id: str,
    background_tasks: BackgroundTasks,
    force: bool = False,
    _: str = Depends(require_project_access),
) -> ProfileUpdateStatus:
    """
    Trigger LLM profile extraction in the background. Returns immediately.

    - **force=false** (default): only processes new unprocessed conversations.
    - **force=true**: reprocesses ALL conversations from scratch, fully overwrites the profile.
    """
    contact = await db.resolve_or_create_contact(project_id, contact_id)
    internal_id = contact.id

    if force:
        indexed = await db.get_all_conversations_with_ids(internal_id)
        if not indexed:
            raise HTTPException(status_code=404, detail="No conversations found for this contact")
    else:
        indexed = await db.get_unprocessed_conversations(internal_id)
        if not indexed:
            raise HTTPException(status_code=404, detail="No unprocessed conversations found")

    acquired = await locks.acquire_lock(project_id, internal_id)
    if not acquired:
        return ProfileUpdateStatus(contact_id=contact_id, status="processing")

    project = await db.get_project(project_id)
    account_id = project.account_id if project else None

    async def _run():
        try:
            ids = [row_id for row_id, _ in indexed]
            conversations = [record for _, record in indexed]
            if force:
                base_profile = UserProfile(user_id=internal_id)
            else:
                base_profile = await db.get_or_create_profile(internal_id, project_id)
            updated = await extract_and_update_profile(
                base_profile, conversations,
                account_id=account_id,
                project_id=project_id,
                contact_id=internal_id,
            )
            await db.save_profile(internal_id, project_id, updated)
            await db.mark_conversations_processed(ids)
            logger.info("Extraction done: contact=%s force=%s", contact_id, force)
        except Exception:
            logger.exception("Extraction failed: contact=%s", contact_id)
        finally:
            await locks.release_lock(project_id, internal_id)

    background_tasks.add_task(_run)
    return ProfileUpdateStatus(contact_id=contact_id, status="processing")


@router.post("/profile/extract/sync", response_model=UserProfile)
async def trigger_extraction_sync(
    project_id: str,
    contact_id: str,
    force: bool = False,
    _: str = Depends(require_project_access),
) -> UserProfile:
    """
    Same as /extract but synchronous — blocks until done and returns the updated profile.
    """
    contact = await db.resolve_or_create_contact(project_id, contact_id)
    internal_id = contact.id

    if force:
        indexed = await db.get_all_conversations_with_ids(internal_id)
        if not indexed:
            raise HTTPException(status_code=404, detail="No conversations found for this contact")
    else:
        indexed = await db.get_unprocessed_conversations(internal_id)
        if not indexed:
            raise HTTPException(status_code=404, detail="No unprocessed conversations found")

    if await locks.is_locked(project_id, internal_id):
        raise HTTPException(status_code=409, detail="Extraction already in progress")

    acquired = await locks.acquire_lock(project_id, internal_id)
    if not acquired:
        raise HTTPException(status_code=409, detail="Extraction already in progress")

    project = await db.get_project(project_id)
    account_id = project.account_id if project else None

    try:
        ids = [row_id for row_id, _ in indexed]
        conversations = [record for _, record in indexed]
        if force:
            base_profile = UserProfile(user_id=internal_id)
        else:
            base_profile = await db.get_or_create_profile(internal_id, project_id)
        updated = await extract_and_update_profile(
            base_profile, conversations,
            account_id=account_id,
            project_id=project_id,
            contact_id=internal_id,
        )
        await db.save_profile(internal_id, project_id, updated)
        await db.mark_conversations_processed(ids)
        return updated
    finally:
        await locks.release_lock(project_id, internal_id)


@router.get("/profile/export", include_in_schema=True)
async def export_profile(
    project_id: str,
    contact_id: str,
    _: str = Depends(require_project_access),
) -> Response:
    """Download a single contact's profile as a JSON file."""
    contact = await db.resolve_contact(project_id, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    profile, indexed = await asyncio.gather(
        db.get_profile(contact.id),
        db.get_all_conversations_with_ids(contact.id),
    )
    messages = [
        {"role": msg.role, "content": msg.content}
        for _, record in indexed
        for msg in record.messages
    ]
    payload = {
        "contact_id": contact.id,
        "external_id": contact.external_id,
        "project_id": project_id,
        "profile": profile.model_dump(exclude={"user_id"}) if profile else {},
        "messages": messages,
    }
    safe_name = contact.external_id.replace("/", "_").replace("\\", "_")
    filename = f"profile_{safe_name}.json"
    return Response(
        content=json.dumps(payload, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/profile/compress", response_model=UserProfile)
async def compress_profile_endpoint(
    project_id: str,
    contact_id: str,
    _: str = Depends(require_project_access),
) -> UserProfile:
    """
    Run compression on the current profile — trim bloat, newer wins.
    Safe to call at any time; intended to be triggered manually or by the daily scheduler.
    """
    contact = await db.resolve_contact(project_id, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    profile = await db.get_profile(contact.id)
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found for this contact")

    project = await db.get_project(project_id)
    account_id = project.account_id if project else None

    compressed = await compress_profile(
        profile,
        account_id=account_id,
        project_id=project_id,
        contact_id=contact.id,
    )
    await db.save_profile(contact.id, project_id, compressed)
    return compressed


@router.delete("/profile", status_code=204)
async def erase_profile(
    project_id: str,
    contact_id: str,
    _: str = Depends(require_project_access),
) -> None:
    """GDPR: Wipe all extracted profile data for a contact, leaving an empty profile."""
    contact = await db.resolve_contact(project_id, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await db.reset_profile(contact.id, project_id)


@router.delete("/contact", status_code=204)
async def delete_contact(
    project_id: str,
    contact_id: str,
    _: str = Depends(require_project_access),
) -> None:
    """Delete all data (contact, profile, conversations) for a contact."""
    contact = await db.resolve_contact(project_id, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await db.delete_contact_data(contact.id, project_id)
