# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Product:** DeepRaven — Long-lasting memory layer for AI sales agents (multi-tenant SaaS)
**Owner:** Alpha Digital Minds GmbH (Vienna, Austria)
**Domain:** deepraven.ai

## What DeepRaven does

Accepts conversation messages via REST API, runs LLM extraction to build structured contact profiles, and serves those profiles back to downstream agents — replacing full conversation history (~30x token reduction). Think mem0, but purpose-built for sales.

**Data hierarchy:** Account → Projects → Contacts → Conversations / Profile

## Running locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in env vars (see table below)
# Run all migrations in db_migrations/migrations/ in the Supabase SQL editor (in order)
./start.sh   # uvicorn app.main:app --reload --host 0.0.0.0 --port 5100
```

Docker:
```bash
docker compose up
```

No linting or test suite is configured.

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `REDIS_URL` | Yes | Use `redis://` (plain TCP) — **not** `rediss://` |
| `SUPABASE_URL` | Yes | `https://<ref>.supabase.co` |
| `SUPABASE_SECRET_KEY` | Yes | service_role key — never expose to clients |
| `GROQ_API_KEY` | Yes | Groq API key (`gsk_...`) |
| `GROQ_MODEL` | No | Default `llama-3.3-70b-versatile` |
| `GROQ_BASE_URL` | No | Default `https://api.groq.com/openai/v1` — swap for any OpenAI-compatible endpoint |
| `MAX_CONVERSATIONS_CONTEXT` | No | Default `20` — conversations per extraction |
| `EXTRACTION_DELAY_SECONDS` | No | Default `60` — batching window before extraction fires |
| `SUPABASE_MANAGEMENT_TOKEN` | No | For running migrations programmatically |

## Stack

- **FastAPI** — async REST API, port 5100
- **Supabase (PostgreSQL + Auth)** — all persistent data with RLS; JWT RS256 verified via JWKS
- **Redis** (Upstash or self-hosted) — extraction scheduling + distributed locking
- **Groq API** — LLM via OpenAI-compatible client (`openai` package, Groq base URL)
- **Pydantic v2** — models and settings

## Extraction pipeline

Conversation ingest → Redis schedule → background worker → LLM → Supabase:

1. `POST .../conversations` stores messages immediately in Supabase (`processed=False`)
2. Redis sorted set (`dr:schedule`) records extraction deadline = `now + EXTRACTION_DELAY_SECONDS`; each new message resets the deadline, batching concurrent messages
3. `extraction_worker` (runs in FastAPI lifespan, polls every 20s) fetches contacts whose deadline has passed
4. For each due contact, acquires Redis lock `dr:lock:{project_id}:{contact_id}` (TTL 120s)
5. `run_profile_update()` runs the **3-tier LLM pipeline**:
   - **Tier 1 — Extract:** Draft profile from unprocessed conversations
   - **Tier 2 — Review:** Second LLM pass corrects and refines the draft
   - **Tier 3 — Compress:** Daily job (23:00 UTC via `compression_worker`) rewrites the full profile for token efficiency
6. Merged result saved to `profiles` table; conversations marked `processed=True`; lock released

`force=true` on extract endpoints reprocesses all conversations from scratch.

## Authentication

Two modes, both accepted by `require_project_access` in `app/auth.py`:

1. **API key** (`Authorization: Bearer dr_<key>`) — machine-to-machine, scoped to a project
2. **JWT** (`Authorization: Bearer eyJ...`) — Supabase-issued, scoped to an account

**API key design:** Project keys use prefix `dr_`, account keys use prefix `dra_`. Raw format `dr_{project_prefix}_{32_hex}`. Only the SHA-256 digest is stored; raw key returned once on creation, never stored.

## File map

| File | Responsibility |
|---|---|
| `app/main.py` | App factory, lifespan (starts Redis/Supabase + background workers), route registration, serves dashboard |
| `app/config.py` | `Settings` — loads all env vars via Pydantic Settings |
| `app/models.py` | All Pydantic v2 models: `UserProfile`, `Contact`, `Project`, `ConversationRecord`, `AccountConfig`, `AccountConfigCreate`, `PromptsUpdate`, `RegenerateRequest`, etc. |
| `app/auth.py` | `require_api_key`, `require_jwt`, `require_project_access` dependencies |
| `app/supabase_client.py` | All persistent DB ops: projects, contacts, profiles, conversations, API keys, usage logs, account config |
| `app/redis_client.py` | `acquire_lock`, `release_lock`, `is_locked`, `schedule_extraction`, `get_due_extractions` |
| `app/llm.py` | 3-tier pipeline: `extract_and_update_profile()` (extract + review), `compress_profile()` (daily compression), `generate_prompts()` (meta-LLM call), `extract_and_update_profile_custom()`, `compress_profile_custom()`. All system prompts live here. |
| `app/worker.py` | `extraction_worker` (polls Redis schedule every 20s), `compression_worker` (daily 23:00 UTC). Both load account config and use custom-schema pipeline when present. |
| `app/routers/auth.py` | Register, login, refresh, OTP verify, reset/update password (proxy to Supabase Auth) |
| `app/routers/account_keys.py` | Account-level API key management (`dra_` prefix) |
| `app/routers/config.py` | Account config CRUD + prompt regeneration (JWT only) |
| `app/routers/projects.py` | Project CRUD + project-level API key management (JWT only) |
| `app/routers/contacts.py` | List/get contacts (JWT only) |
| `app/routers/conversations.py` | Ingest + list conversations (API key or JWT) |
| `app/routers/profiles.py` | Profile CRUD, extraction, status (API key or JWT) |
| `app/routers/stats.py` | Usage statistics endpoint |
| `app/dashboard/src/` | Vite + Vue 3 + TypeScript dashboard source |
| `app/static/dist/` | Compiled dashboard assets (served by FastAPI) |
| `db_migrations/migrations/001_initial.sql` | Core schema: accounts, projects, contacts, profiles, conversations, api_keys, RLS |
| `db_migrations/migrations/002_llm_usage.sql` | `llm_usage_logs` table |
| `db_migrations/migrations/003_account_api_keys.sql` | Account-level API keys table |
| `db_migrations/migrations/003_butler_rls.sql` | Extended RLS policies |
| `db_migrations/migrations/004_account_config.sql` | `account_config` table + RLS + `updated_at` trigger |

## Supabase schema

Tables: `accounts` (auto-created on Auth signup via trigger), `projects`, `api_keys` (key_hash only), `contacts` (identified by `external_id`), `profiles` (JSONB `UserProfile`), `conversations` (messages + `processed` flag), `llm_usage_logs`, `account_config` (one row per account — custom schema, purpose, generated prompts).

All tables have RLS — each account sees only its own rows.

## API endpoints

```
Auth:
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/reset-password
POST   /api/v1/auth/update-password
POST   /api/v1/auth/verify-otp
POST   /api/v1/auth/resend-otp
GET    /api/v1/auth/confirm          (Supabase redirect handler)

Account keys (JWT):
GET|POST   /api/v1/keys
DELETE     /api/v1/keys/{key_id}

Projects (JWT):
GET|POST              /api/v1/projects
GET|PATCH|DELETE      /api/v1/projects/{id}
GET|POST              /api/v1/projects/{id}/keys
DELETE                /api/v1/projects/{id}/keys/{key_id}

Contacts (JWT):
GET    /api/v1/projects/{pid}/contacts
GET    /api/v1/projects/{pid}/contacts/{cid}

Conversations (API key or JWT):
POST   /api/v1/projects/{pid}/contacts/{cid}/conversations
GET    /api/v1/projects/{pid}/contacts/{cid}/conversations

Profiles (API key or JWT):
GET    /api/v1/projects/{pid}/contacts/{cid}/profile
GET    /api/v1/projects/{pid}/contacts/{cid}/profile/status
POST   /api/v1/projects/{pid}/contacts/{cid}/profile/extract
POST   /api/v1/projects/{pid}/contacts/{cid}/profile/extract/sync
DELETE /api/v1/projects/{pid}/contacts/{cid}/contact

Config (JWT):
GET    /api/v1/config
PUT    /api/v1/config
PATCH  /api/v1/config/prompts
POST   /api/v1/config/regenerate
DELETE /api/v1/config

Stats (JWT):
GET    /api/v1/stats

System:
GET    /health
GET    /dashboard
GET    /docs
```

## Important gotchas

**Pydantic v2 merge:** `model_copy(update={...})` does NOT coerce nested dicts into model instances. Always use `UserProfile.model_validate(merged_dict)` when merging LLM output into a profile.

**Redis URL:** Must be `redis://` (plain TCP). Using `rediss://` causes SSL errors with Upstash free tier.

**Workers are not separate processes:** `extraction_worker` and `compression_worker` run inside FastAPI's lifespan context (not Celery/RQ). Single-server deployment only.

**Contacts created implicitly:** Pushing a conversation to an unknown `external_id` auto-creates the contact. The dashboard won't show contacts until at least one conversation is pushed.

## Common issues

| Problem | Fix |
|---|---|
| 401 on API calls | Use `Bearer dr_...` for API key or `Bearer eyJ...` for JWT |
| SSL error on Redis | Change `rediss://` → `redis://` in `REDIS_URL` |
| `'dict' object has no attribute 'pain_points'` | Use `UserProfile.model_validate(merged)` not `model_copy` |
| 500 on startup | Supabase or Redis unreachable — check env vars |
