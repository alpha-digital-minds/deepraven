"""
Redis client — distributed locking and extraction scheduling.

All persistent data lives in Supabase. Redis provides:
  - TTL-based locks to prevent duplicate concurrent LLM extraction jobs.
  - A sorted-set schedule that debounces extraction: the deadline for a
    contact is reset each time a new conversation arrives, so all messages
    in the same session are batched into one LLM call.
"""
import time
from typing import Optional

import redis.asyncio as aioredis

from app.config import get_settings

_P = "dr"

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def _lock_key(project_id: str, contact_id: str) -> str:
    return f"{_P}:lock:{project_id}:{contact_id}"


async def acquire_lock(project_id: str, contact_id: str, ttl_seconds: int = 120) -> bool:
    """Returns True if the lock was acquired (no extraction already running)."""
    r = await get_redis()
    acquired = await r.set(_lock_key(project_id, contact_id), "1", nx=True, ex=ttl_seconds)
    return acquired is True


async def release_lock(project_id: str, contact_id: str) -> None:
    r = await get_redis()
    await r.delete(_lock_key(project_id, contact_id))


async def is_locked(project_id: str, contact_id: str) -> bool:
    r = await get_redis()
    return await r.exists(_lock_key(project_id, contact_id)) == 1


# ── Extraction schedule (sorted set, score = unix deadline) ───────────────

_SCHEDULE_KEY = f"{_P}:schedule"


def _schedule_member(project_id: str, contact_id: str) -> str:
    return f"{project_id}:{contact_id}"


async def schedule_extraction(project_id: str, contact_id: str, delay_seconds: int) -> None:
    """
    Set or reset the extraction deadline for a contact.
    Each call pushes the deadline forward by `delay_seconds` from now,
    so rapid consecutive conversations are batched into one LLM call.
    """
    r = await get_redis()
    deadline = time.time() + delay_seconds
    await r.zadd(_SCHEDULE_KEY, {_schedule_member(project_id, contact_id): deadline})


async def get_due_extractions() -> list[tuple[str, str]]:
    """Return (project_id, contact_id) pairs whose deadline has passed."""
    r = await get_redis()
    members = await r.zrangebyscore(_SCHEDULE_KEY, "-inf", time.time())
    result = []
    for m in members:
        project_id, contact_id = m.split(":", 1)
        result.append((project_id, contact_id))
    return result


async def remove_scheduled_extraction(project_id: str, contact_id: str) -> None:
    r = await get_redis()
    await r.zrem(_SCHEDULE_KEY, _schedule_member(project_id, contact_id))
