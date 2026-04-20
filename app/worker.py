"""
Extraction worker — runs as a background asyncio task for the lifetime of the process.

Flow:
  1. Every POLL_INTERVAL seconds, check Redis for contacts whose batching
     window has closed (deadline ≤ now).
  2. For each due contact, acquire the extraction lock and fire off
     run_profile_update as a separate asyncio task.
  3. run_profile_update fetches ALL unprocessed conversations (accumulated
     during the window), calls the LLM once, updates the profile, and
     marks conversations processed.

The batching window is reset each time a new conversation arrives
(see redis_client.schedule_extraction), so a busy session keeps
pushing the deadline forward and is processed as one unit.
"""
import asyncio
import logging

from datetime import datetime, timezone

from app import redis_client as locks
from app import supabase_client as db
from app.llm import (
    compress_profile,
    compress_profile_custom,
    extract_and_update_profile,
    extract_and_update_profile_custom,
)

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 20  # seconds between schedule checks


async def run_profile_update(project_id: str, contact_id: str) -> None:
    """
    Fetch all unprocessed conversations for a contact, run one LLM call,
    persist the updated profile, mark conversations processed, release lock.
    """
    try:
        unprocessed = await db.get_unprocessed_conversations(contact_id)
        if not unprocessed:
            logger.debug("No unprocessed convos for contact=%s — skipping", contact_id)
            return

        ids = [row_id for row_id, _ in unprocessed]
        conversations = [record for _, record in unprocessed]

        project = await db.get_project(project_id)
        account_id = project.account_id if project else None

        account_config = await db.get_account_config(account_id) if account_id else None

        if account_config and account_config.get("prompt_extractor"):
            profile_data = await db.get_profile_raw(contact_id)
            updated_data = await extract_and_update_profile_custom(
                profile_data, conversations, account_config,
                account_id=account_id,
                project_id=project_id,
                contact_id=contact_id,
            )
            await db.save_profile_raw(contact_id, project_id, updated_data)
        else:
            profile = await db.get_or_create_profile(contact_id, project_id)
            updated = await extract_and_update_profile(
                profile, conversations,
                account_id=account_id,
                project_id=project_id,
                contact_id=contact_id,
            )
            await db.save_profile(contact_id, project_id, updated)

        await db.mark_conversations_processed(ids)
        logger.info(
            "Profile updated: project=%s contact=%s (%d conversations)",
            project_id, contact_id, len(conversations),
        )
    except Exception:
        logger.exception(
            "Profile update failed: project=%s contact=%s", project_id, contact_id
        )
    finally:
        await locks.release_lock(project_id, contact_id)


async def compression_worker(run_hour_utc: int = 23) -> None:
    """
    Long-running task that compresses all profiles once per day at run_hour_utc (UTC).
    Skips contacts that are currently being extracted.
    """
    logger.info("Compression worker started — will run daily at %02d:00 UTC", run_hour_utc)
    while True:
        # Sleep until the next run_hour_utc
        now = datetime.now(timezone.utc)
        next_run = now.replace(hour=run_hour_utc, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run = next_run.replace(day=next_run.day + 1)
        wait_seconds = (next_run - now).total_seconds()
        logger.info("Compression worker sleeping %.0f seconds until %s UTC", wait_seconds, next_run)
        await asyncio.sleep(wait_seconds)

        logger.info("Daily compression run starting")
        try:
            rows = await db.get_all_contact_project_pairs()
            logger.info("Compressing %d profiles", len(rows))
            for contact_id, project_id in rows:
                if await locks.is_locked(project_id, contact_id):
                    logger.debug("Skipping compression for contact=%s — extraction in progress", contact_id)
                    continue
                try:
                    project = await db.get_project(project_id)
                    account_id = project.account_id if project else None
                    account_config = await db.get_account_config(account_id) if account_id else None

                    if account_config and account_config.get("prompt_compressor"):
                        profile_data = await db.get_profile_raw(contact_id)
                        if not profile_data:
                            continue
                        compressed_data = await compress_profile_custom(
                            profile_data, account_config,
                            account_id=account_id,
                            project_id=project_id,
                            contact_id=contact_id,
                        )
                        await db.save_profile_raw(contact_id, project_id, compressed_data)
                    else:
                        profile = await db.get_profile(contact_id)
                        if not profile:
                            continue
                        compressed = await compress_profile(
                            profile,
                            account_id=account_id,
                            project_id=project_id,
                            contact_id=contact_id,
                        )
                        await db.save_profile(contact_id, project_id, compressed)
                    logger.debug("Compressed profile for contact=%s", contact_id)
                except Exception:
                    logger.exception("Compression failed for contact=%s", contact_id)
            logger.info("Daily compression run complete")
        except Exception:
            logger.exception("Daily compression run error")


async def extraction_worker(delay_seconds: int) -> None:
    """
    Long-running task started at app startup.
    Polls Redis every _POLL_INTERVAL seconds and dispatches due extractions.
    """
    logger.info(
        "Extraction worker started — window=%ds poll=%ds",
        delay_seconds, _POLL_INTERVAL,
    )
    while True:
        await asyncio.sleep(_POLL_INTERVAL)
        try:
            due = await locks.get_due_extractions()
            for project_id, contact_id in due:
                if await locks.is_locked(project_id, contact_id):
                    # Extraction already running for this contact; leave it in
                    # the schedule — the worker will retry on the next poll.
                    continue
                acquired = await locks.acquire_lock(project_id, contact_id)
                if not acquired:
                    continue
                # Remove from schedule before launching the task so a new
                # conversation arriving during processing re-schedules cleanly.
                await locks.remove_scheduled_extraction(project_id, contact_id)
                asyncio.create_task(
                    run_profile_update(project_id, contact_id),
                    name=f"extract:{project_id[:8]}:{contact_id[:8]}",
                )
        except Exception:
            logger.exception("Extraction worker poll error")
