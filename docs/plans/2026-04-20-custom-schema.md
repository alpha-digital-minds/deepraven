# Custom Schema & Prompt Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow accounts to define a custom JSON schema and purpose, auto-generate LLM extraction prompts from them, and use those prompts at runtime instead of the built-in hardcoded ones.

**Architecture:** New `account_config` table (one row per account) stores schema, purpose, and three generated prompts. A meta-LLM call at save time generates all three prompts. The extraction worker checks for account config and takes a separate code path (raw dict) when custom prompts are present; default accounts are completely unaffected.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, Supabase (PostgreSQL + async client), Groq via OpenAI-compat client, Vue 3 + TypeScript + Vite (dashboard)

---

## File Map

| Action | File | What changes |
|--------|------|--------------|
| Create | `db_migrations/migrations/004_account_config.sql` | New table + RLS + trigger |
| Modify | `app/models.py` | Add 4 Pydantic models |
| Modify | `app/supabase_client.py` | Add 6 functions; make `project_id` Optional in `log_llm_usage` |
| Modify | `app/llm.py` | Add `generate_prompts()`, `_safe_merge_dict()`, `extract_and_update_profile_custom()`, `compress_profile_custom()` |
| Create | `app/routers/config.py` | 5 config endpoints |
| Modify | `app/main.py` | Register config router |
| Modify | `app/worker.py` | Dual code path based on account_config |
| Modify | `app/dashboard/src/types.ts` | Add AccountConfig types |
| Modify | `app/dashboard/src/api.ts` | Add 5 config API functions |
| Create | `app/dashboard/src/components/ConfigurationView.vue` | Configuration tab UI |
| Modify | `app/dashboard/src/router.ts` | Add `/configuration` route |
| Modify | `app/dashboard/src/components/AppHeader.vue` | Add Configuration nav link |

---

## Task 1: DB Migration

**Files:**
- Create: `db_migrations/migrations/004_account_config.sql`

- [ ] **Step 1: Create migration file**

```sql
-- 004_account_config.sql
-- Account-level custom schema and generated extraction prompts

CREATE TABLE IF NOT EXISTS account_config (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id           uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  profile_schema       jsonb NOT NULL DEFAULT '{}',
  purpose_industry     text NOT NULL DEFAULT '',
  purpose_agent_type   text NOT NULL DEFAULT '',
  purpose_description  text NOT NULL DEFAULT '',
  prompt_extractor     text NOT NULL DEFAULT '',
  prompt_reviewer      text NOT NULL DEFAULT '',
  prompt_compressor    text NOT NULL DEFAULT '',
  created_at           timestamptz DEFAULT now(),
  updated_at           timestamptz DEFAULT now(),
  UNIQUE(account_id)
);

ALTER TABLE account_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY account_config_owner ON account_config
  FOR ALL USING (account_id = auth.uid());

DROP TRIGGER IF EXISTS account_config_updated_at ON account_config;
CREATE TRIGGER account_config_updated_at
  BEFORE UPDATE ON account_config
  FOR EACH ROW EXECUTE PROCEDURE touch_updated_at();
```

- [ ] **Step 2: Run the migration**

Open the Supabase SQL editor for your project and execute the contents of `db_migrations/migrations/004_account_config.sql`. Confirm the `account_config` table appears in the Table Editor.

- [ ] **Step 3: Commit**

```bash
git add db_migrations/migrations/004_account_config.sql
git commit -m "feat: add account_config migration"
```

---

## Task 2: Pydantic Models

**Files:**
- Modify: `app/models.py`

- [ ] **Step 1: Add models to the end of `app/models.py`**

Append after the last class in the file (after `ResendOtpRequest`):

```python
# ── Account config models ─────────────────────────────────────────────────────

class AccountConfigCreate(BaseModel):
    profile_schema: dict
    purpose_industry: str
    purpose_agent_type: str
    purpose_description: str


class AccountConfig(BaseModel):
    id: str
    account_id: str
    profile_schema: dict
    purpose_industry: str
    purpose_agent_type: str
    purpose_description: str
    prompt_extractor: str
    prompt_reviewer: str
    prompt_compressor: str
    created_at: str
    updated_at: str


class PromptsUpdate(BaseModel):
    prompt_extractor: Optional[str] = None
    prompt_reviewer: Optional[str] = None
    prompt_compressor: Optional[str] = None


class RegenerateRequest(BaseModel):
    comment: Optional[str] = None
```

- [ ] **Step 2: Verify the module loads**

```bash
python -c "from app.models import AccountConfig, AccountConfigCreate, PromptsUpdate, RegenerateRequest; print('OK')"
```
Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/models.py
git commit -m "feat: add AccountConfig Pydantic models"
```

---

## Task 3: Supabase Client Functions

**Files:**
- Modify: `app/supabase_client.py`

- [ ] **Step 1: Make `project_id` Optional in `log_llm_usage`**

Find the existing `log_llm_usage` function (around line 511) and change its signature:

```python
async def log_llm_usage(
    account_id: str,
    project_id: Optional[str],      # was: project_id: str
    contact_id: str | None,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    model: str | None,
) -> None:
```

No other changes to the function body — `project_id` can already be `None` in the insert dict.

- [ ] **Step 2: Add account_config DB functions**

Append a new section after the `# ── Analytics ──` section at the bottom of `app/supabase_client.py`:

```python
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
```

- [ ] **Step 3: Verify module loads**

```bash
python -c "from app.supabase_client import get_account_config, upsert_account_config, get_profile_raw; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/supabase_client.py
git commit -m "feat: add account_config and raw profile DB functions"
```

---

## Task 4: LLM — `generate_prompts()`

**Files:**
- Modify: `app/llm.py`

- [ ] **Step 1: Add `_META_PROMPT` constant**

Add this constant after the existing `_COMPRESSOR_PROMPT` constant (around line 293), before `_build_conversation_text`:

```python
_META_PROMPT = """You are an expert at writing LLM system prompts for AI agent memory and CRM systems.

Given a JSON schema and use-case context, write three system prompts:

1. prompt_extractor — a system prompt that instructs an LLM to extract structured profile data from sales/support conversations and return it as JSON matching the given schema. Include a detailed field guide explaining what to extract for each field. End with: "Return ONLY valid JSON matching the schema above. No markdown, no commentary."

2. prompt_reviewer — a system prompt that instructs an LLM to review a draft JSON profile against the source conversations, identify errors or missing data, and return a corrected profile. The response must be a JSON object with two keys: "critique" (string) and "profile" (the corrected profile JSON matching the schema).

3. prompt_compressor — a system prompt that instructs an LLM to compress a verbose profile JSON into a lean, token-efficient version that retains every actionable fact. Return ONLY valid JSON matching the schema — no markdown, no commentary.

Return ONLY valid JSON with exactly three keys: "prompt_extractor", "prompt_reviewer", "prompt_compressor". No markdown, no commentary."""
```

- [ ] **Step 2: Add `generate_prompts()` function**

Add this function after `_META_PROMPT`:

```python
async def generate_prompts(
    profile_schema: dict,
    purpose_industry: str,
    purpose_agent_type: str,
    purpose_description: str,
    *,
    comment: str | None = None,
    account_id: str | None = None,
) -> dict:
    """Call LLM to generate extractor, reviewer, and compressor prompts.

    Returns dict with keys: prompt_extractor, prompt_reviewer, prompt_compressor.
    """
    import json as _json
    settings = get_settings()
    client = AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
    )

    user_msg = (
        f"SCHEMA:\n{_json.dumps(profile_schema, indent=2)}\n\n"
        f"PURPOSE:\n"
        f"Industry: {purpose_industry}\n"
        f"Agent type: {purpose_agent_type}\n"
        f"Description: {purpose_description}"
    )
    if comment:
        user_msg += f"\n\nINSTRUCTIONS FOR THIS GENERATION: {comment}"

    raw, usage = await _call_llm(client, settings.groq_model, _META_PROMPT, user_msg)

    if account_id and usage:
        from app import supabase_client as db
        await db.log_llm_usage(
            account_id=account_id,
            project_id=None,
            contact_id=None,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            model=settings.groq_model,
        )

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON for prompt generation: {exc}") from exc

    required = {"prompt_extractor", "prompt_reviewer", "prompt_compressor"}
    missing = required - result.keys()
    if missing:
        raise ValueError(f"LLM response missing keys: {missing}")

    return {k: result[k] for k in required}
```

- [ ] **Step 3: Verify module loads**

```bash
python -c "from app.llm import generate_prompts; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/llm.py
git commit -m "feat: add generate_prompts meta-LLM function"
```

---

## Task 5: LLM — Custom-Schema Pipeline

**Files:**
- Modify: `app/llm.py`

- [ ] **Step 1: Add `_safe_merge_dict()` function**

Add this after `_safe_merge()` (around line 353):

```python
def _safe_merge_dict(updated: dict, current: dict) -> dict:
    """Merge LLM output into current profile dict, preserving non-empty existing values."""
    result = dict(current)
    for key, new_val in updated.items():
        old_val = current.get(key)
        if isinstance(new_val, dict) and isinstance(old_val, dict):
            result[key] = _safe_merge_dict(new_val, old_val)
        elif isinstance(new_val, list):
            result[key] = new_val if new_val else (old_val if isinstance(old_val, list) else [])
        elif isinstance(new_val, str):
            result[key] = new_val if new_val else (old_val if isinstance(old_val, str) else "")
        elif new_val is not None:
            result[key] = new_val
        # None → keep old_val unchanged
    return result
```

- [ ] **Step 2: Add `extract_and_update_profile_custom()` function**

Add this after `extract_and_update_profile()`:

```python
async def extract_and_update_profile_custom(
    profile_data: dict,
    conversations: list[ConversationRecord],
    account_config: dict,
    *,
    account_id: str | None = None,
    project_id: str | None = None,
    contact_id: str | None = None,
) -> dict:
    """Extract + review using account's custom prompts. Returns a plain dict."""
    settings = get_settings()
    client = AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
    )

    extractor_prompt = account_config["prompt_extractor"]
    reviewer_prompt = account_config["prompt_reviewer"]
    conv_text = _build_conversation_text(conversations)
    user_msg = (
        f"CURRENT PROFILE:\n{json.dumps(profile_data, indent=2)}\n\n"
        f"RECENT CONVERSATIONS:\n{conv_text}"
    )

    usages = []

    tier1_json, u1 = await _call_llm(client, settings.groq_model, extractor_prompt, user_msg)
    usages.append(u1)

    try:
        review_json, u2 = await _call_llm(
            client, settings.groq_model, reviewer_prompt,
            f"CONVERSATIONS:\n{conv_text}\n\nDRAFT PROFILE:\n{tier1_json}",
        )
        usages.append(u2)
        review_data = json.loads(review_json)
        final_data = review_data.get("profile") or json.loads(tier1_json)
    except Exception:
        logger.exception("Custom Tier 2 review failed — using tier 1 output")
        final_data = json.loads(tier1_json)

    if account_id and project_id:
        from app import supabase_client as db
        total_prompt = sum(u.prompt_tokens for u in usages if u)
        total_completion = sum(u.completion_tokens for u in usages if u)
        await db.log_llm_usage(
            account_id=account_id,
            project_id=project_id,
            contact_id=contact_id,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            total_tokens=total_prompt + total_completion,
            model=settings.groq_model,
        )

    return _safe_merge_dict(final_data, profile_data)
```

- [ ] **Step 3: Add `compress_profile_custom()` function**

Add this after `compress_profile()`:

```python
async def compress_profile_custom(
    profile_data: dict,
    account_config: dict,
    *,
    account_id: str | None = None,
    project_id: str | None = None,
    contact_id: str | None = None,
) -> dict:
    """Compress a custom-schema profile using the account's compressor prompt."""
    settings = get_settings()
    client = AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
    )

    compressor_prompt = account_config["prompt_compressor"]
    profile_json = json.dumps(profile_data, indent=2, ensure_ascii=False)

    compressed_json, usage = await _call_llm(
        client, settings.groq_model, compressor_prompt, profile_json,
    )

    if account_id and project_id and usage:
        from app import supabase_client as db
        await db.log_llm_usage(
            account_id=account_id,
            project_id=project_id,
            contact_id=contact_id,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            model=settings.groq_model,
        )

    try:
        compressed_data = json.loads(compressed_json)
    except json.JSONDecodeError:
        logger.exception("Custom compression returned invalid JSON — keeping original")
        return profile_data

    return _safe_merge_dict(compressed_data, profile_data)
```

- [ ] **Step 4: Verify module loads**

```bash
python -c "from app.llm import _safe_merge_dict, extract_and_update_profile_custom, compress_profile_custom; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Test `_safe_merge_dict` manually**

```bash
python -c "
from app.llm import _safe_merge_dict
current = {'tier': 'gold', 'needs': ['watch'], 'budget': ''}
updated = {'tier': '', 'needs': ['watch', 'bag'], 'budget': '200-500 SAR'}
result = _safe_merge_dict(updated, current)
assert result['tier'] == 'gold', 'should keep non-empty existing value'
assert result['needs'] == ['watch', 'bag'], 'should use non-empty new list'
assert result['budget'] == '200-500 SAR', 'should fill empty existing field'
print('_safe_merge_dict: OK')
"
```
Expected: `_safe_merge_dict: OK`

- [ ] **Step 6: Commit**

```bash
git add app/llm.py
git commit -m "feat: add custom-schema LLM pipeline functions"
```

---

## Task 6: Config Router

**Files:**
- Create: `app/routers/config.py`

- [ ] **Step 1: Create `app/routers/config.py`**

```python
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
```

- [ ] **Step 2: Verify module loads**

```bash
python -c "from app.routers.config import router; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/routers/config.py
git commit -m "feat: add config router with 5 endpoints"
```

---

## Task 7: Register Router

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add import and register config router**

In `app/main.py`, find the existing router imports line:

```python
from app.routers import account_keys, auth, contacts, conversations, profiles, projects, stats
```

Change it to:

```python
from app.routers import account_keys, auth, config, contacts, conversations, profiles, projects, stats
```

Then find the block of `app.include_router(...)` calls and add after `stats`:

```python
app.include_router(config.router, prefix="/api/v1")
```

- [ ] **Step 2: Start the server and check `/docs`**

```bash
./start.sh
```

Open `http://localhost:5100/docs` and confirm a new **config** section appears with `GET /api/v1/config`, `PUT /api/v1/config`, `PATCH /api/v1/config/prompts`, `POST /api/v1/config/regenerate`, `DELETE /api/v1/config`.

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: register config router"
```

---

## Task 8: Worker — Account Config Dual Path

**Files:**
- Modify: `app/worker.py`

- [ ] **Step 1: Update imports at the top of `app/worker.py`**

Find:
```python
from app.llm import compress_profile, extract_and_update_profile
```

Replace with:
```python
from app.llm import (
    compress_profile,
    compress_profile_custom,
    extract_and_update_profile,
    extract_and_update_profile_custom,
)
```

- [ ] **Step 2: Update `run_profile_update()` to use dual code path**

Find the body of `run_profile_update` and replace with:

```python
async def run_profile_update(project_id: str, contact_id: str) -> None:
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
```

- [ ] **Step 3: Update `compression_worker()` to use dual code path**

Find the inner loop inside `compression_worker` where it calls `compress_profile`. Replace:

```python
                    profile = await db.get_profile(contact_id)
                    if not profile:
                        continue
                    project = await db.get_project(project_id)
                    account_id = project.account_id if project else None
                    compressed = await compress_profile(
                        profile,
                        account_id=account_id,
                        project_id=project_id,
                        contact_id=contact_id,
                    )
                    await db.save_profile(contact_id, project_id, compressed)
```

With:

```python
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
```

- [ ] **Step 4: Verify module loads**

```bash
python -c "from app.worker import run_profile_update, compression_worker; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add app/worker.py
git commit -m "feat: load account config in workers and use custom-schema pipeline when present"
```

---

## Task 9: Dashboard — TypeScript Types + API Functions

**Files:**
- Modify: `app/dashboard/src/types.ts`
- Modify: `app/dashboard/src/api.ts`

- [ ] **Step 1: Add types to `app/dashboard/src/types.ts`**

Append to the end of the file:

```typescript
export interface AccountConfig {
  id: string
  account_id: string
  profile_schema: Record<string, unknown>
  purpose_industry: string
  purpose_agent_type: string
  purpose_description: string
  prompt_extractor: string
  prompt_reviewer: string
  prompt_compressor: string
  created_at: string
  updated_at: string
}

export interface AccountConfigCreate {
  profile_schema: Record<string, unknown>
  purpose_industry: string
  purpose_agent_type: string
  purpose_description: string
}

export interface PromptsUpdate {
  prompt_extractor?: string
  prompt_reviewer?: string
  prompt_compressor?: string
}
```

- [ ] **Step 2: Add API functions to `app/dashboard/src/api.ts`**

First add the new types to the import at the top of `api.ts`. Find:

```typescript
import type {
  AuthResponse, Project, Contact, ApiKey, ApiKeyCreated,
  UserProfile, ConversationRecord, StatsOverview,
  DailyConversation, ProjectUsage,
} from './types'
```

Replace with:

```typescript
import type {
  AuthResponse, Project, Contact, ApiKey, ApiKeyCreated,
  UserProfile, ConversationRecord, StatsOverview,
  DailyConversation, ProjectUsage,
  AccountConfig, AccountConfigCreate, PromptsUpdate,
} from './types'
```

Then append the following functions to the end of `api.ts`:

```typescript
// ── Account Config ────────────────────────────────────────────────────────────
export const getConfig = () =>
  api.get<AccountConfig>('/config')

export const saveConfig = (payload: AccountConfigCreate) =>
  api.put<AccountConfig>('/config', payload)

export const updatePrompts = (payload: PromptsUpdate) =>
  api.patch<AccountConfig>('/config/prompts', payload)

export const regeneratePrompts = (comment?: string) =>
  api.post<AccountConfig>('/config/regenerate', { comment: comment ?? null })

export const deleteConfig = () =>
  api.delete('/config')
```

- [ ] **Step 3: Commit**

```bash
git add app/dashboard/src/types.ts app/dashboard/src/api.ts
git commit -m "feat: add AccountConfig types and API functions to dashboard"
```

---

## Task 10: ConfigurationView.vue

**Files:**
- Create: `app/dashboard/src/components/ConfigurationView.vue`

- [ ] **Step 1: Create the component**

```vue
<template>
  <div class="config-view">
    <div class="config-header">
      <h2>Account Configuration</h2>
      <p class="config-sub">Define your contact profile schema and agent purpose. DeepRaven will generate custom extraction prompts tailored to your use case.</p>
    </div>

    <div v-if="loading" class="config-loading">Loading…</div>

    <template v-else>
      <!-- Purpose -->
      <section class="config-card">
        <h3>Purpose</h3>
        <div class="config-row">
          <div class="config-field">
            <label>Industry</label>
            <input v-model="form.purpose_industry" type="text" placeholder="e.g. Luxury Retail" />
          </div>
          <div class="config-field">
            <label>Agent Type</label>
            <input v-model="form.purpose_agent_type" type="text" placeholder="e.g. Sales Agent" />
          </div>
        </div>
        <div class="config-field">
          <label>Description</label>
          <textarea v-model="form.purpose_description" rows="3" placeholder="Describe what your agent does and what profile data matters most…" />
        </div>
      </section>

      <!-- Schema -->
      <section class="config-card">
        <h3>Profile Schema</h3>
        <p class="config-hint">Paste your JSON data model. The LLM will extract conversation data into this structure.</p>
        <textarea
          v-model="schemaText"
          class="config-code"
          :class="{ 'config-code-error': schemaText && !schemaValid }"
          rows="14"
          placeholder='{"field_name": "", "array_field": [], "nested": {}}'
          @input="onSchemaInput"
        />
        <p v-if="schemaText" class="config-validation" :class="schemaValid ? 'ok' : 'err'">
          {{ schemaValid ? '✓ Valid JSON' : '✗ Invalid JSON — fix before saving' }}
        </p>
      </section>

      <!-- Save button -->
      <div class="config-actions">
        <button
          class="btn-sm primary"
          :disabled="saving || !canSave"
          @click="doSave"
        >
          {{ saving ? 'Generating prompts…' : 'Save & Generate Prompts' }}
        </button>
      </div>

      <!-- Generated Prompts -->
      <section v-if="config" class="config-card">
        <div class="prompts-header">
          <div>
            <h3>Generated Prompts</h3>
            <p class="config-hint">Auto-generated from your schema and purpose. Edit directly and click Save Edits.</p>
          </div>
          <div class="regen-row">
            <input
              v-model="regenComment"
              type="text"
              placeholder="Optional guidance for regeneration…"
              class="regen-input"
            />
            <button class="btn-sm" :disabled="regenerating" @click="doRegenerate">
              {{ regenerating ? 'Regenerating…' : '↺ Regenerate' }}
            </button>
          </div>
        </div>

        <div class="prompt-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="prompt-tab"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >{{ tab.label }}</button>
        </div>

        <textarea
          v-model="editedPrompts[activeTab]"
          class="config-code prompt-area"
          rows="18"
        />

        <div class="config-actions" style="margin-top:12px">
          <button class="btn-sm primary" :disabled="savingPrompts" @click="doSavePrompts">
            {{ savingPrompts ? 'Saving…' : 'Save Edits' }}
          </button>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { getConfig, saveConfig, updatePrompts, regeneratePrompts } from '../api'
import type { AccountConfig } from '../types'
import { useToast } from '../composables/useToast'

const { toast } = useToast()

const loading = ref(true)
const saving = ref(false)
const savingPrompts = ref(false)
const regenerating = ref(false)

const config = ref<AccountConfig | null>(null)
const schemaText = ref('')
const schemaValid = ref(true)
const regenComment = ref('')
const activeTab = ref<'prompt_extractor' | 'prompt_reviewer' | 'prompt_compressor'>('prompt_extractor')

const tabs = [
  { key: 'prompt_extractor' as const, label: 'Extractor' },
  { key: 'prompt_reviewer' as const, label: 'Reviewer' },
  { key: 'prompt_compressor' as const, label: 'Compressor' },
]

const form = reactive({
  purpose_industry: '',
  purpose_agent_type: '',
  purpose_description: '',
})

const editedPrompts = reactive({
  prompt_extractor: '',
  prompt_reviewer: '',
  prompt_compressor: '',
})

const canSave = computed(() =>
  form.purpose_industry.trim() &&
  form.purpose_agent_type.trim() &&
  schemaText.value.trim() &&
  schemaValid.value
)

function onSchemaInput() {
  if (!schemaText.value.trim()) { schemaValid.value = true; return }
  try { JSON.parse(schemaText.value); schemaValid.value = true }
  catch { schemaValid.value = false }
}

function applyConfig(c: AccountConfig) {
  config.value = c
  form.purpose_industry = c.purpose_industry
  form.purpose_agent_type = c.purpose_agent_type
  form.purpose_description = c.purpose_description
  schemaText.value = JSON.stringify(c.profile_schema, null, 2)
  schemaValid.value = true
  editedPrompts.prompt_extractor = c.prompt_extractor
  editedPrompts.prompt_reviewer = c.prompt_reviewer
  editedPrompts.prompt_compressor = c.prompt_compressor
}

onMounted(async () => {
  try {
    const res = await getConfig()
    applyConfig(res.data)
  } catch (e: any) {
    if (e?.response?.status !== 404) toast('Failed to load config', 'error')
  } finally {
    loading.value = false
  }
})

async function doSave() {
  if (!canSave.value) return
  saving.value = true
  try {
    const profile_schema = JSON.parse(schemaText.value)
    const res = await saveConfig({
      profile_schema,
      purpose_industry: form.purpose_industry.trim(),
      purpose_agent_type: form.purpose_agent_type.trim(),
      purpose_description: form.purpose_description.trim(),
    })
    applyConfig(res.data)
    toast('Config saved and prompts generated!', 'success')
  } catch {
    toast('Failed to save config — check your connection', 'error')
  } finally {
    saving.value = false
  }
}

async function doSavePrompts() {
  savingPrompts.value = true
  try {
    const res = await updatePrompts({ ...editedPrompts })
    applyConfig(res.data)
    toast('Prompts saved', 'success')
  } catch {
    toast('Failed to save prompts', 'error')
  } finally {
    savingPrompts.value = false
  }
}

async function doRegenerate() {
  if (!confirm('Regenerate all prompts? This will overwrite any manual edits.')) return
  regenerating.value = true
  try {
    const res = await regeneratePrompts(regenComment.value.trim() || undefined)
    applyConfig(res.data)
    regenComment.value = ''
    toast('Prompts regenerated!', 'success')
  } catch {
    toast('Failed to regenerate prompts', 'error')
  } finally {
    regenerating.value = false
  }
}
</script>

<style scoped>
.config-view { max-width: 860px; margin: 0 auto; padding: 24px 20px; display: flex; flex-direction: column; gap: 20px; }
.config-header h2 { font-size: 20px; font-weight: 700; margin-bottom: 6px; }
.config-sub { font-size: 13px; color: var(--muted); }
.config-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 20px; display: flex; flex-direction: column; gap: 14px; }
.config-card h3 { font-size: 14px; font-weight: 700; }
.config-row { display: flex; gap: 14px; flex-wrap: wrap; }
.config-field { flex: 1; min-width: 180px; display: flex; flex-direction: column; gap: 5px; }
.config-field label { font-size: 11px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
.config-field input, .config-field textarea { padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg); color: var(--text); outline: none; resize: vertical; }
.config-field input:focus, .config-field textarea:focus { border-color: var(--primary); }
.config-code { font-family: monospace; font-size: 12px; padding: 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); outline: none; width: 100%; resize: vertical; }
.config-code-error { border-color: var(--red) !important; }
.config-hint { font-size: 12px; color: var(--muted); }
.config-validation { font-size: 11px; margin-top: -8px; }
.config-validation.ok { color: var(--green); }
.config-validation.err { color: var(--red); }
.config-actions { display: flex; justify-content: flex-end; }
.config-loading { color: var(--muted); font-size: 13px; padding: 20px 0; }
.prompts-header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }
.regen-row { display: flex; gap: 8px; align-items: center; }
.regen-input { padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 12px; background: var(--bg); color: var(--text); outline: none; min-width: 220px; }
.regen-input:focus { border-color: var(--primary); }
.prompt-tabs { display: flex; border-bottom: 1px solid var(--border); gap: 0; }
.prompt-tab { padding: 8px 16px; font-size: 12px; font-weight: 500; background: none; border: none; border-bottom: 2px solid transparent; cursor: pointer; color: var(--muted); margin-bottom: -1px; }
.prompt-tab.active { color: var(--primary); border-bottom-color: var(--primary); }
.prompt-area { min-height: 320px; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add app/dashboard/src/components/ConfigurationView.vue
git commit -m "feat: add ConfigurationView dashboard component"
```

---

## Task 11: Router + Nav Link

**Files:**
- Modify: `app/dashboard/src/router.ts`
- Modify: `app/dashboard/src/components/AppHeader.vue`

- [ ] **Step 1: Add `/configuration` route to `app/dashboard/src/router.ts`**

Find the `children` array inside the `'/'` route and add the configuration entry:

```typescript
children: [
  { path: '', component: () => import('./components/HomeDashboard.vue') },
  { path: 'projects/:projectId', component: () => import('./components/ProjectPanel.vue') },
  {
    path: 'projects/:projectId/contacts/:contactId',
    component: () => import('./components/ContactDetail.vue'),
  },
  { path: 'configuration', component: () => import('./components/ConfigurationView.vue') },
],
```

- [ ] **Step 2: Add Configuration link to `app/dashboard/src/components/AppHeader.vue`**

In `AppHeader.vue`, find the `<div class="spacer" />` line and add the nav link immediately after it:

```html
    <div class="spacer" />

    <RouterLink to="/configuration" class="config-link btn-sm">⚙ Configuration</RouterLink>
```

Then add the style to the `<style>` block (or add a `<style scoped>` block if none exists):

```css
.config-link { text-decoration: none; color: var(--text); }
.config-link.active { color: var(--primary); font-weight: 600; }
```

- [ ] **Step 3: Commit**

```bash
git add app/dashboard/src/router.ts app/dashboard/src/components/AppHeader.vue
git commit -m "feat: add Configuration route and nav link to dashboard"
```

---

## Task 12: Build Dashboard + Smoke Test

**Files:**
- Built output: `app/static/dist/`

- [ ] **Step 1: Install dependencies and build**

```bash
cd app/dashboard && npm install && npm run build
```

Expected: Build completes with no errors. `app/static/dist/index.html` is updated.

- [ ] **Step 2: Start the server**

```bash
cd /path/to/deepraven && ./start.sh
```

- [ ] **Step 3: Test GET with no config (expect 404)**

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer <your-jwt>" \
  http://localhost:5100/api/v1/config
```
Expected: `404`

- [ ] **Step 4: Test PUT (save config + generate prompts)**

```bash
curl -s -X PUT http://localhost:5100/api/v1/config \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_schema": {"customer_tier": "", "preferred_brands": [], "budget_range": ""},
    "purpose_industry": "Luxury Retail",
    "purpose_agent_type": "Sales Agent",
    "purpose_description": "Track purchase intent and brand preferences"
  }' | python3 -m json.tool
```
Expected: JSON response with non-empty `prompt_extractor`, `prompt_reviewer`, `prompt_compressor` fields.

- [ ] **Step 5: Test GET (config now exists)**

```bash
curl -s -H "Authorization: Bearer <your-jwt>" \
  http://localhost:5100/api/v1/config | python3 -m json.tool
```
Expected: `200` with the saved config.

- [ ] **Step 6: Test PATCH (edit one prompt)**

```bash
curl -s -X PATCH http://localhost:5100/api/v1/config/prompts \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"prompt_extractor": "Custom extractor prompt text"}' | python3 -m json.tool
```
Expected: `200` with `prompt_extractor` updated to "Custom extractor prompt text".

- [ ] **Step 7: Test POST regenerate**

```bash
curl -s -X POST http://localhost:5100/api/v1/config/regenerate \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"comment": "Focus on upsell signals"}' | python3 -m json.tool
```
Expected: `200` with freshly generated prompts.

- [ ] **Step 8: Open dashboard and verify Configuration tab**

Open `http://localhost:5100/dashboard` — confirm "⚙ Configuration" appears in the header. Click it, confirm the form loads with the saved config pre-filled and prompts visible in the tabbed editor.

- [ ] **Step 9: Push a conversation and verify custom extraction runs**

```bash
curl -s -X POST "http://localhost:5100/api/v1/projects/<pid>/contacts/test-001/conversations" \
  -H "Authorization: Bearer dr_<your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "I want a Rolex Submariner, budget around 12000 USD"}]}'
```

Wait 65+ seconds (extraction delay), then:

```bash
curl -s "http://localhost:5100/api/v1/projects/<pid>/contacts/test-001/profile" \
  -H "Authorization: Bearer dr_<your-api-key>" | python3 -m json.tool
```

Expected: Profile data matches your custom schema shape (e.g., `budget_range`, `preferred_brands` fields), not the default UserProfile shape.

- [ ] **Step 10: Commit built assets**

```bash
git add app/static/dist
git commit -m "chore: rebuild dashboard with Configuration tab"
```

- [ ] **Step 11: Final commit**

```bash
git log --oneline -10
```

Confirm all feature commits are in order. The branch is ready for review.
