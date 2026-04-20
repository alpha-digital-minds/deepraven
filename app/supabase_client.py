"""
Supabase service-role client and all persistent-data operations.

The service-role client bypasses RLS so it can operate on any row.
All access control is enforced at the API layer (auth.py dependencies).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)

from supabase import AsyncClient, create_async_client

from app.config import get_settings
from app.models import (
    Contact,
    ContactSummary,
    ConversationRecord,
    Project,
    UserProfile,
)

logger = logging.getLogger(__name__)

_client: Optional[AsyncClient] = None


async def get_supabase() -> AsyncClient:
    global _client
    if _client is None:
        s = get_settings()
        _client = await create_async_client(s.supabase_url, s.supabase_secret_key)
    return _client


async def close_supabase() -> None:
    global _client
    _client = None


# ── Projects ──────────────────────────────────────────────────────────────────

async def list_projects(account_id: str) -> list[Project]:
    sb = await get_supabase()
    res = await sb.table("projects").select("*").eq("account_id", account_id).order("created_at").execute()
    return [Project(**row) for row in res.data]


async def create_project(account_id: str, name: str, description: str | None) -> Project:
    sb = await get_supabase()
    res = await sb.table("projects").insert({
        "account_id": account_id,
        "name": name,
        "description": description,
    }).execute()
    return Project(**res.data[0])


async def get_project(project_id: str) -> Optional[Project]:
    sb = await get_supabase()
    res = await sb.table("projects").select("*").eq("id", project_id).execute()
    if not res.data:
        return None
    return Project(**res.data[0])


async def update_project(project_id: str, name: str | None, description: str | None) -> Optional[Project]:
    sb = await get_supabase()
    patch: dict = {}
    if name is not None:
        patch["name"] = name
    if description is not None:
        patch["description"] = description
    if not patch:
        return await get_project(project_id)
    res = await sb.table("projects").update(patch).eq("id", project_id).execute()
    if not res.data:
        return None
    return Project(**res.data[0])


async def delete_project(project_id: str) -> bool:
    sb = await get_supabase()
    res = await sb.table("projects").delete().eq("id", project_id).execute()
    return len(res.data) > 0


# ── API Keys ──────────────────────────────────────────────────────────────────

async def create_api_key(project_id: str, name: str, key_hash: str) -> dict:
    sb = await get_supabase()
    res = await sb.table("api_keys").insert({
        "project_id": project_id,
        "name": name,
        "key_hash": key_hash,
    }).execute()
    return res.data[0]


async def list_api_keys(project_id: str) -> list[dict]:
    sb = await get_supabase()
    res = (
        await sb.table("api_keys")
        .select("id, project_id, name, created_at, last_used_at, revoked_at")
        .eq("project_id", project_id)
        .order("created_at")
        .execute()
    )
    return res.data


async def revoke_api_key(key_id: str, project_id: str) -> bool:
    sb = await get_supabase()
    res = (
        await sb.table("api_keys")
        .update({"revoked_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", key_id)
        .eq("project_id", project_id)
        .execute()
    )
    return len(res.data) > 0


async def lookup_api_key(key_hash: str) -> Optional[dict]:
    """Return the api_key row for an active (non-revoked) key hash, or None."""
    sb = await get_supabase()
    res = (
        await sb.table("api_keys")
        .select("id, project_id")
        .eq("key_hash", key_hash)
        .is_("revoked_at", "null")
        .execute()
    )
    return res.data[0] if res.data else None


async def touch_api_key_used(key_id: str) -> None:
    """Best-effort update of last_used_at — errors are silently swallowed."""
    try:
        sb = await get_supabase()
        await sb.table("api_keys").update({
            "last_used_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", key_id).execute()
    except Exception:
        pass


# ── Account-level API Keys ────────────────────────────────────────────────────

async def create_account_api_key(account_id: str, name: str, key_hash: str) -> dict:
    sb = await get_supabase()
    res = await sb.table("account_api_keys").insert({
        "account_id": account_id,
        "name": name,
        "key_hash": key_hash,
    }).execute()
    return res.data[0]


async def list_account_api_keys(account_id: str) -> list[dict]:
    sb = await get_supabase()
    res = (
        await sb.table("account_api_keys")
        .select("id, account_id, name, created_at, last_used_at, revoked_at")
        .eq("account_id", account_id)
        .order("created_at")
        .execute()
    )
    return res.data


async def lookup_account_api_key(key_hash: str) -> Optional[dict]:
    """Return the account_api_keys row for an active (non-revoked) key hash, or None."""
    sb = await get_supabase()
    res = (
        await sb.table("account_api_keys")
        .select("id, account_id")
        .eq("key_hash", key_hash)
        .is_("revoked_at", "null")
        .execute()
    )
    return res.data[0] if res.data else None


async def revoke_account_api_key(key_id: str, account_id: str) -> bool:
    sb = await get_supabase()
    res = (
        await sb.table("account_api_keys")
        .update({"revoked_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", key_id)
        .eq("account_id", account_id)
        .execute()
    )
    return len(res.data) > 0


async def touch_account_api_key_used(key_id: str) -> None:
    try:
        sb = await get_supabase()
        await sb.table("account_api_keys").update({
            "last_used_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", key_id).execute()
    except Exception:
        pass


# ── Contacts ──────────────────────────────────────────────────────────────────

async def resolve_contact(project_id: str, contact_ref: str) -> Optional[Contact]:
    """
    Look up a contact by internal UUID first (only when ref is UUID-shaped),
    then by external_id. Never creates. Returns None if not found.
    """
    if _UUID_RE.match(contact_ref):
        contact = await get_contact(contact_ref, project_id)
        if contact:
            return contact
    sb = await get_supabase()
    res = (
        await sb.table("contacts")
        .select("*")
        .eq("project_id", project_id)
        .eq("external_id", contact_ref)
        .execute()
    )
    return Contact(**res.data[0]) if res.data else None


async def resolve_or_create_contact(project_id: str, contact_ref: str) -> Contact:
    """
    Find a contact by internal UUID, or get/create by external_id.
    - UUID-shaped ref → try internal lookup first (dashboard passes internal IDs)
    - Non-UUID ref    → skip internal lookup, go straight to get_or_create by external_id
    Prevents ghost contacts AND prevents PostgreSQL UUID parse errors.
    """
    if _UUID_RE.match(contact_ref):
        contact = await get_contact(contact_ref, project_id)
        if contact:
            return contact
    return await get_or_create_contact(project_id, contact_ref)


async def get_or_create_contact(project_id: str, external_id: str) -> Contact:
    sb = await get_supabase()
    res = (
        await sb.table("contacts")
        .select("*")
        .eq("project_id", project_id)
        .eq("external_id", external_id)
        .execute()
    )
    if res.data:
        return Contact(**res.data[0])
    ins = await sb.table("contacts").insert({
        "project_id": project_id,
        "external_id": external_id,
    }).execute()
    return Contact(**ins.data[0])


async def get_contact(contact_id: str, project_id: str) -> Optional[Contact]:
    sb = await get_supabase()
    res = (
        await sb.table("contacts")
        .select("*")
        .eq("id", contact_id)
        .eq("project_id", project_id)
        .execute()
    )
    return Contact(**res.data[0]) if res.data else None


async def list_contacts(project_id: str) -> list[ContactSummary]:
    """
    Return contact summaries for the dashboard sidebar.
    Uses 3 bulk queries regardless of contact count (was 3N+1 before).
    """
    sb = await get_supabase()

    contacts_res = (
        await sb.table("contacts")
        .select("id, external_id, created_at")
        .eq("project_id", project_id)
        .order("created_at")
        .execute()
    )
    if not contacts_res.data:
        return []

    contact_ids = [row["id"] for row in contacts_res.data]

    # Bulk fetch all profiles for this project
    profiles_res = (
        await sb.table("profiles")
        .select("contact_id, data")
        .eq("project_id", project_id)
        .in_("contact_id", contact_ids)
        .execute()
    )
    profile_map = {p["contact_id"]: p["data"] for p in profiles_res.data}

    # Bulk fetch conversation counts (total + unprocessed) in two queries
    total_res = (
        await sb.table("conversations")
        .select("contact_id")
        .eq("project_id", project_id)
        .in_("contact_id", contact_ids)
        .execute()
    )
    unproc_res = (
        await sb.table("conversations")
        .select("contact_id")
        .eq("project_id", project_id)
        .eq("processed", False)
        .in_("contact_id", contact_ids)
        .execute()
    )

    total_map: dict[str, int] = {}
    for row in total_res.data:
        total_map[row["contact_id"]] = total_map.get(row["contact_id"], 0) + 1

    unproc_map: dict[str, int] = {}
    for row in unproc_res.data:
        unproc_map[row["contact_id"]] = unproc_map.get(row["contact_id"], 0) + 1

    summaries = []
    for row in contacts_res.data:
        cid = row["id"]
        personal = profile_map.get(cid, {}).get("personal", {})
        summaries.append(ContactSummary(
            id=cid,
            project_id=project_id,
            external_id=row["external_id"],
            name=personal.get("name", ""),
            company=personal.get("company", ""),
            total_conversations=total_map.get(cid, 0),
            unprocessed_count=unproc_map.get(cid, 0),
        ))

    return summaries


# ── Profiles ──────────────────────────────────────────────────────────────────

async def get_profile(contact_id: str) -> Optional[UserProfile]:
    sb = await get_supabase()
    res = (
        await sb.table("profiles")
        .select("data, contact_id")
        .eq("contact_id", contact_id)
        .execute()
    )
    if not res.data:
        return None
    data = res.data[0]["data"]
    # Inject contact_id as user_id for the model (kept for LLM compatibility)
    data["user_id"] = contact_id
    return UserProfile.model_validate(data)


async def save_profile(contact_id: str, project_id: str, profile: UserProfile) -> None:
    sb = await get_supabase()
    data = profile.model_dump(exclude={"user_id"})
    await sb.table("profiles").upsert({
        "contact_id": contact_id,
        "project_id": project_id,
        "data": data,
    }, on_conflict="contact_id").execute()


async def get_or_create_profile(contact_id: str, project_id: str) -> UserProfile:
    profile = await get_profile(contact_id)
    if profile is None:
        profile = UserProfile(user_id=contact_id)
        await save_profile(contact_id, project_id, profile)
    return profile


async def delete_contact_data(contact_id: str, project_id: str) -> bool:
    """Delete contact + all associated profiles and conversations (cascade)."""
    sb = await get_supabase()
    res = (
        await sb.table("contacts")
        .delete()
        .eq("id", contact_id)
        .eq("project_id", project_id)
        .execute()
    )
    return len(res.data) > 0


async def delete_conversations(contact_id: str, project_id: str) -> int:
    """Delete all conversation records for a contact. Returns number of rows deleted."""
    sb = await get_supabase()
    res = (
        await sb.table("conversations")
        .delete()
        .eq("contact_id", contact_id)
        .eq("project_id", project_id)
        .execute()
    )
    return len(res.data)


async def reset_profile(contact_id: str, project_id: str) -> None:
    """Wipe all extracted profile data, leaving an empty profile in place."""
    empty = UserProfile(user_id=contact_id)
    await save_profile(contact_id, project_id, empty)


# ── Conversations ─────────────────────────────────────────────────────────────

async def append_conversation(
    contact_id: str,
    project_id: str,
    record: ConversationRecord,
) -> None:
    sb = await get_supabase()
    await sb.table("conversations").insert({
        "contact_id": contact_id,
        "project_id": project_id,
        "messages": [m.model_dump() for m in record.messages],
        "metadata": record.metadata,
        "timestamp": record.timestamp,
        "processed": False,
    }).execute()


async def get_recent_conversations(contact_id: str, n: int) -> list[ConversationRecord]:
    sb = await get_supabase()
    res = (
        await sb.table("conversations")
        .select("*")
        .eq("contact_id", contact_id)
        .order("timestamp", desc=True)
        .limit(n)
        .execute()
    )
    records = []
    for row in reversed(res.data):  # restore chronological order
        records.append(ConversationRecord(
            messages=row["messages"],
            metadata=row.get("metadata"),
            timestamp=row["timestamp"],
            processed=row["processed"],
        ))
    return records


async def get_all_conversations_with_ids(contact_id: str) -> list[tuple[str, ConversationRecord]]:
    """Return (db_id, record) for every conversation of a contact."""
    sb = await get_supabase()
    res = (
        await sb.table("conversations")
        .select("*")
        .eq("contact_id", contact_id)
        .order("timestamp")
        .execute()
    )
    return [
        (row["id"], ConversationRecord(
            messages=row["messages"],
            metadata=row.get("metadata"),
            timestamp=row["timestamp"],
            processed=row["processed"],
        ))
        for row in res.data
    ]


async def get_unprocessed_conversations(contact_id: str) -> list[tuple[str, ConversationRecord]]:
    """Return (db_id, record) for all unprocessed conversations."""
    sb = await get_supabase()
    res = (
        await sb.table("conversations")
        .select("*")
        .eq("contact_id", contact_id)
        .eq("processed", False)
        .order("timestamp")
        .execute()
    )
    return [
        (row["id"], ConversationRecord(
            messages=row["messages"],
            metadata=row.get("metadata"),
            timestamp=row["timestamp"],
            processed=row["processed"],
        ))
        for row in res.data
    ]


async def mark_conversations_processed(ids: list[str]) -> None:
    if not ids:
        return
    sb = await get_supabase()
    await sb.table("conversations").update({"processed": True}).in_("id", ids).execute()


# ── LLM usage tracking ─────────────────────────────────────────────────────────

async def log_llm_usage(
    account_id: str,
    project_id: Optional[str],
    contact_id: str | None,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    model: str | None,
) -> None:
    sb = await get_supabase()
    try:
        await sb.table("llm_usage").insert({
            "account_id": account_id,
            "project_id": project_id,
            "contact_id": contact_id,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "model": model,
        }).execute()
    except Exception:
        logger.warning("Failed to log LLM usage", exc_info=True)


# ── Analytics ──────────────────────────────────────────────────────────────────

async def get_account_stats(account_id: str) -> dict:
    sb = await get_supabase()
    res = await sb.rpc("get_account_stats", {"p_account_id": account_id}).execute()
    return res.data or {}


async def get_daily_conversations(account_id: str, days: int = 30) -> list[dict]:
    sb = await get_supabase()
    res = await sb.rpc(
        "get_daily_conversations",
        {"p_account_id": account_id, "p_days": days},
    ).execute()
    return res.data or []


async def get_usage_by_project(account_id: str) -> list[dict]:
    sb = await get_supabase()
    res = await sb.rpc("get_usage_by_project", {"p_account_id": account_id}).execute()
    return res.data or []


async def export_project_profiles(project_id: str) -> list[dict]:
    """Return all contacts + their profiles for a project-wide export."""
    sb = await get_supabase()
    contacts_res = (
        await sb.table("contacts")
        .select("id, external_id, created_at")
        .eq("project_id", project_id)
        .order("created_at")
        .execute()
    )
    if not contacts_res.data:
        return []

    contact_ids = [row["id"] for row in contacts_res.data]
    profiles_res = (
        await sb.table("profiles")
        .select("contact_id, data, updated_at")
        .eq("project_id", project_id)
        .in_("contact_id", contact_ids)
        .execute()
    )
    profile_map = {p["contact_id"]: p for p in profiles_res.data}

    result = []
    for row in contacts_res.data:
        cid = row["id"]
        profile_row = profile_map.get(cid, {})
        result.append({
            "contact_id": cid,
            "external_id": row["external_id"],
            "created_at": row["created_at"],
            "profile_updated_at": profile_row.get("updated_at"),
            "profile": profile_row.get("data", {}),
        })
    return result


async def get_all_contact_project_pairs() -> list[tuple[str, str]]:
    """Return (contact_id, project_id) for every contact that has a profile."""
    sb = await get_supabase()
    res = await sb.table("profiles").select("contact_id, project_id").execute()
    return [(row["contact_id"], row["project_id"]) for row in res.data]


async def count_conversations(contact_id: str) -> int:
    sb = await get_supabase()
    res = (
        await sb.table("conversations")
        .select("id", count="exact")
        .eq("contact_id", contact_id)
        .execute()
    )
    return res.count or 0


# ── Account config ────────────────────────────────────────────────────────────

async def get_account_config(account_id: str) -> Optional[dict]:
    sb = await get_supabase()
    res = (
        await sb.table("account_config")
        .select("*")
        .eq("account_id", account_id)
        .execute()
    )
    return res.data[0] if res.data else None


async def upsert_account_config(account_id: str, data: dict) -> dict:
    sb = await get_supabase()
    payload = {"account_id": account_id, **data}
    res = (
        await sb.table("account_config")
        .upsert(payload, on_conflict="account_id")
        .execute()
    )
    return res.data[0]


async def update_account_prompts(account_id: str, prompts: dict) -> dict:
    sb = await get_supabase()
    res = (
        await sb.table("account_config")
        .update(prompts)
        .eq("account_id", account_id)
        .execute()
    )
    return res.data[0]


async def delete_account_config(account_id: str) -> bool:
    sb = await get_supabase()
    res = (
        await sb.table("account_config")
        .delete()
        .eq("account_id", account_id)
        .execute()
    )
    return len(res.data) > 0


async def get_profile_raw(contact_id: str) -> dict:
    """Return the raw profile JSONB dict, or {} if none exists."""
    sb = await get_supabase()
    res = (
        await sb.table("profiles")
        .select("data")
        .eq("contact_id", contact_id)
        .execute()
    )
    return res.data[0]["data"] if res.data else {}


async def save_profile_raw(contact_id: str, project_id: str, data: dict) -> None:
    """Upsert a raw dict profile (used for custom-schema accounts)."""
    sb = await get_supabase()
    await sb.table("profiles").upsert({
        "contact_id": contact_id,
        "project_id": project_id,
        "data": data,
    }, on_conflict="contact_id").execute()
