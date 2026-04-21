# Custom Schema & Prompt Generation

**Date:** 2026-04-20  
**Product:** DeepRaven  
**Feature:** Account-level custom schema, purpose, and LLM-generated extraction prompts

---

## Summary

Allow accounts to define their own JSON data model (schema) and use-case context (purpose). On save, an LLM meta-call generates three tailored prompts (extractor, reviewer, compressor). Prompts are stored per account, viewable and editable in the dashboard, and can be regenerated at any time with an optional guiding comment. The extraction pipeline uses custom prompts when present and falls back to built-in defaults otherwise.

---

## Data Model

### New table: `account_config`

```sql
CREATE TABLE account_config (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id           uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  profile_schema       jsonb NOT NULL,
  purpose_industry     text NOT NULL,
  purpose_agent_type   text NOT NULL,
  purpose_description  text NOT NULL,
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
```

- One row per account (enforced via UNIQUE constraint).
- `profile_schema` is the customer-defined JSON data model (named `profile_schema` to avoid shadowing Pydantic v2's `model_json_schema()` method).
- `purpose_*` fields form the structured use-case context.
- `prompt_*` fields hold the generated (or manually edited) prompts.
- No changes to existing tables.

---

## API Endpoints

All endpoints are JWT-only, scoped to the authenticated account. New router: `app/routers/config.py`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/config` | Fetch current account config. Returns `404` if none set. |
| `PUT` | `/api/v1/config` | Save schema + purpose → fires meta-LLM call → saves generated prompts. Upserts. |
| `PATCH` | `/api/v1/config/prompts` | Manually edit one or more of the three prompts. |
| `POST` | `/api/v1/config/regenerate` | Re-run meta-LLM call using saved schema + purpose + optional comment. |
| `DELETE` | `/api/v1/config` | Remove account config; extraction falls back to built-in defaults. |

### Pydantic models (`app/models.py`)

```python
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

---

## Prompt Generation (Meta-LLM Call)

### New function: `generate_prompts()` in `app/llm.py`

Fires a single LLM call. Returns a dict with three keys: `prompt_extractor`, `prompt_reviewer`, `prompt_compressor`.

**System prompt (meta-prompt):**
> You are an expert at writing LLM extraction prompts for CRM and AI agent systems. Given a JSON schema and use-case context, write three prompts:
> 1. `prompt_extractor` — instructs an LLM to extract structured data from conversations into the schema
> 2. `prompt_reviewer` — instructs an LLM to review and correct a draft extraction
> 3. `prompt_compressor` — instructs an LLM to compress a profile while retaining all actionable facts
>
> Return ONLY valid JSON with keys `prompt_extractor`, `prompt_reviewer`, `prompt_compressor`. No markdown, no commentary.

**User message:**
```
SCHEMA:
<customer JSON schema>

PURPOSE:
Industry: <purpose_industry>
Agent type: <purpose_agent_type>
Description: <purpose_description>

[REGENERATION COMMENT: <comment>]  ← only included if provided
```

Token usage logged to `llm_usage_logs` (no `project_id` or `contact_id` — account-level operation).

---

## Extraction Pipeline Changes

### `app/llm.py`

- `extract_and_update_profile()` and `compress_profile()` accept a new optional parameter `account_config: dict | None`.
- **Prompt resolution:** if `account_config` is present and its `prompt_*` fields are non-empty, use them. Otherwise use the hardcoded `_SYSTEM_PROMPT`, `_REVIEWER_PROMPT`, `_COMPRESSOR_PROMPT` constants (unchanged).
- **Profile merge for custom schemas:** a new `_safe_merge_dict(updated: dict, current: dict) -> dict` function handles the merge when a custom schema is in use. It recursively merges LLM output into the current profile dict, skipping null/empty values. Returns a plain `dict` (not a `UserProfile` instance).
- Default accounts continue to use `_safe_merge()` with `UserProfile` — no change.

### `app/worker.py`

- `extraction_worker` loads account config from DB once per extraction batch and passes it to `extract_and_update_profile()`.
- `compression_worker` similarly loads config before calling `compress_profile()`.

### `app/supabase_client.py`

New DB functions:
- `get_account_config(account_id) -> dict | None`
- `upsert_account_config(account_id, data) -> dict`
- `update_account_prompts(account_id, prompts) -> dict`
- `delete_account_config(account_id) -> None`

---

## Dashboard UI

A new **"Configuration"** tab added to `app/static/dashboard.html` (existing Vue.js SPA).

### Layout

1. **Purpose section** — industry text input, agent type text input, description textarea (all free-text; no fixed enum values)
2. **Schema section** — JSON textarea with client-side JSON validation indicator
3. **"Save & Generate Prompts"** button — calls `PUT /api/v1/config`, shows loading state during generation
4. **Generated Prompts section** (appears after first save):
   - Tabs: Extractor / Reviewer / Compressor
   - Each tab: editable textarea + "Save Edits" button (calls `PATCH /api/v1/config/prompts`)
   - Regenerate row: optional comment input + "↺ Regenerate" button (calls `POST /api/v1/config/regenerate`)

---

## Migration

One new SQL migration file: `db_migrations/migrations/004_account_config.sql`

- Creates `account_config` table with RLS.
- Adds `updated_at` auto-bump trigger (reuses existing `touch_updated_at()` function).

---

## Constraints & Edge Cases

| Scenario | Behaviour |
|----------|-----------|
| Account has no config | Extraction uses built-in defaults — no change to current behaviour |
| `PUT /api/v1/config` called while extraction is running | Config saved; running extraction uses the old prompts (already in memory). Next extraction picks up new prompts. |
| Meta-LLM call fails | `PUT /api/v1/config` returns `502` with error detail; schema + purpose are NOT saved (atomic: only save when prompts are generated) |
| Customer edits prompts then clicks Regenerate | Regenerated prompts overwrite manual edits — dashboard shows a confirmation dialog first |
| Schema is invalid JSON | `PUT /api/v1/config` returns `422` (Pydantic validation — `schema: dict` rejects non-objects) |

---

## Files Touched

| File | Change |
|------|--------|
| `db_migrations/migrations/004_account_config.sql` | New — creates table + RLS + trigger |
| `app/models.py` | Add `AccountConfigCreate`, `AccountConfig`, `PromptsUpdate`, `RegenerateRequest` |
| `app/llm.py` | Add `generate_prompts()`, `_safe_merge_dict()`, update `extract_and_update_profile()` and `compress_profile()` signatures |
| `app/supabase_client.py` | Add 4 new DB functions for account config CRUD |
| `app/routers/config.py` | New — 5 endpoints |
| `app/main.py` | Register new config router |
| `app/worker.py` | Load account config before calling extraction functions |
| `app/static/dashboard.html` | Add Configuration tab with Vue component |
