from fastapi import APIRouter, Depends

from app.auth import require_jwt
from app import supabase_client as db

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
async def get_overview(account_id: str = Depends(require_jwt)) -> dict:
    """Account-level counts: projects, contacts, conversations, total LLM tokens."""
    return await db.get_account_stats(account_id)


@router.get("/conversations/daily")
async def get_daily_conversations(account_id: str = Depends(require_jwt)) -> list[dict]:
    """Conversation counts per day for the last 30 days."""
    return await db.get_daily_conversations(account_id)


@router.get("/usage")
async def get_usage(account_id: str = Depends(require_jwt)) -> list[dict]:
    """Per-project LLM token usage rollup."""
    return await db.get_usage_by_project(account_id)
