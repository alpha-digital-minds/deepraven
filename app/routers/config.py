"""
Account-level configuration: custom schema, purpose, and generated prompts.
All routes require a valid Supabase JWT.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_account_access
from app import supabase_client as db
from app.llm import generate_prompts
from app.models import AccountConfig, AccountConfigCreate, PromptsUpdate, RegenerateRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/config", tags=["config"])


def _row_to_model(row: dict) -> AccountConfig:
    return AccountConfig(
        id=row["id"],
        account_id=row["account_id"],
        profile_schema=row["profile_schema"],
        purpose_industry=row["purpose_industry"],
        purpose_agent_type=row["purpose_agent_type"],
        purpose_description=row["purpose_description"],
        prompt_extractor=row["prompt_extractor"],
        prompt_reviewer=row["prompt_reviewer"],
        prompt_compressor=row["prompt_compressor"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("", response_model=AccountConfig)
async def get_config(account_id: str = Depends(require_account_access)) -> AccountConfig:
    row = await db.get_account_config(account_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No config found")
    return _row_to_model(row)


@router.put("", response_model=AccountConfig, status_code=200)
async def save_config(
    payload: AccountConfigCreate,
    account_id: str = Depends(require_account_access),
) -> AccountConfig:
    try:
        prompts = await generate_prompts(
            profile_schema=payload.profile_schema,
            purpose_industry=payload.purpose_industry,
            purpose_agent_type=payload.purpose_agent_type,
            purpose_description=payload.purpose_description,
            account_id=account_id,
        )
    except Exception as exc:
        logger.exception("Prompt generation failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Prompt generation failed: {exc}",
        ) from exc

    row = await db.upsert_account_config(account_id, {
        "profile_schema": payload.profile_schema,
        "purpose_industry": payload.purpose_industry,
        "purpose_agent_type": payload.purpose_agent_type,
        "purpose_description": payload.purpose_description,
        **prompts,
    })
    return _row_to_model(row)


@router.patch("/prompts", response_model=AccountConfig)
async def update_prompts(
    payload: PromptsUpdate,
    account_id: str = Depends(require_account_access),
) -> AccountConfig:
    existing = await db.get_account_config(account_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No config found")

    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not patch:
        return _row_to_model(existing)

    row = await db.update_account_prompts(account_id, patch)
    return _row_to_model(row)


@router.post("/regenerate", response_model=AccountConfig)
async def regenerate_prompts(
    payload: RegenerateRequest,
    account_id: str = Depends(require_account_access),
) -> AccountConfig:
    existing = await db.get_account_config(account_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No config found")

    try:
        prompts = await generate_prompts(
            profile_schema=existing["profile_schema"],
            purpose_industry=existing["purpose_industry"],
            purpose_agent_type=existing["purpose_agent_type"],
            purpose_description=existing["purpose_description"],
            comment=payload.comment,
            account_id=account_id,
        )
    except Exception as exc:
        logger.exception("Prompt regeneration failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Prompt regeneration failed: {exc}",
        ) from exc

    row = await db.update_account_prompts(account_id, prompts)
    return _row_to_model(row)


@router.delete("", status_code=204)
async def delete_config(account_id: str = Depends(require_account_access)) -> None:
    await db.delete_account_config(account_id)
