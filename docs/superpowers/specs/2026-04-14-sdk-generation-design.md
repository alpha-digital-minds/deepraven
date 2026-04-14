# DeepRaven SDK Generation — Design Spec

**Date:** 2026-04-14
**Status:** Approved
**Scope:** Auto-generated Python and TypeScript SDKs via Fern, published to PyPI and npm

---

## Overview

Add official `deepraven` SDKs for Python and TypeScript, auto-generated from the FastAPI OpenAPI spec using Fern. SDKs live in the same repo under `/sdks/`, stay in sync with the API via a GitHub Action, and publish as `deepraven` on both PyPI and npm.

---

## Repo Structure

```
deepraven/
├── sdks/
│   ├── python/          # pip install deepraven
│   │   ├── deepraven/
│   │   ├── pyproject.toml
│   │   └── README.md
│   └── typescript/      # npm install deepraven
│       ├── src/
│       ├── package.json
│       └── README.md
├── fern/
│   ├── fern.config.json
│   ├── openapi/
│   │   └── openapi.json     # Exported from FastAPI, committed
│   └── generators.yml
└── .github/
    └── workflows/
        └── sdk-generate.yml
```

---

## Tooling: Fern

**Why Fern:** Produces idiomatic, well-typed Python and TypeScript code that looks hand-written. Free tier, no Java runtime, GitHub Action support. Used by Cohere, ElevenLabs, and others.

**Alternatives considered:**
- `openapi-generator-cli` — requires Java, verbose output, poor DX
- `Stainless` — highest quality but paid/waitlist, overkill for now

---

## Fern Configuration

`fern/generators.yml`:

```yaml
default-group: local
groups:
  local:
    generators:
      - name: fernapi/fern-python-sdk
        version: 4.x.x
        output:
          location: local-file-system
          path: ../sdks/python
        config:
          package_name: deepraven
          async_handlers: true

      - name: fernapi/fern-typescript-node-sdk
        version: 0.x.x
        output:
          location: local-file-system
          path: ../sdks/typescript
        config:
          package_name: deepraven
```

Key decisions:
- `async_handlers: true` — Python SDK exposes both sync and async clients
- `package_name: deepraven` — consistent name on both registries
- Local output (free tier) — no Fern cloud account needed

---

## OpenAPI Spec Export

FastAPI auto-generates an OpenAPI spec at `GET /openapi.json`. The spec is exported once from a running instance and committed to `fern/openapi/openapi.json`. It is re-exported as part of the GitHub Action on every API change.

```bash
curl http://localhost:5100/openapi.json > fern/openapi/openapi.json
```

---

## Generation

```bash
npm install -g fern-api       # one-time global install
fern generate --group local   # writes to sdks/python + sdks/typescript
```

---

## Publishing

**Python → PyPI:**
```bash
cd sdks/python
pip install build twine
python -m build
twine upload dist/*
```

**TypeScript → npm:**
```bash
cd sdks/typescript
npm publish --access public
```

**Versioning:** SDK versions mirror the API version (e.g. API `2.1.0` → SDK `2.1.0` on both registries). Bump and publish both together on every API release.

---

## GitHub Action

File: `.github/workflows/sdk-generate.yml`

**Trigger:** Any push to `main` that modifies `app/routers/**` or `app/models.py`.

**Steps:**
1. Start FastAPI (with test env vars)
2. Export fresh `openapi.json` from `/openapi.json`
3. Run `fern generate --group local`
4. Open a PR with the updated SDK code for review before merge

This ensures SDKs are always in sync with the live API surface.

---

## Developer Experience

**Python:**
```python
from deepraven import DeepRavenClient

client = DeepRavenClient(api_key="dr_...")

# Push a conversation
client.conversations.create(
    project_id="proj_123",
    contact_id="contact_456",
    messages=[
        {"role": "user", "content": "I need a gift under $200"},
        {"role": "assistant", "content": "Sure, what occasion?"}
    ]
)

# Get profile
profile = client.profiles.get(project_id="proj_123", contact_id="contact_456")
print(profile.sales.pain_points)
```

**TypeScript:**
```typescript
import { DeepRavenClient } from "deepraven";

const client = new DeepRavenClient({ apiKey: "dr_..." });

const profile = await client.profiles.get({
  projectId: "proj_123",
  contactId: "contact_456",
});
```

Both SDKs are fully typed — IDE autocomplete works out of the box. Python exposes sync and async clients.

---

## Out of Scope

- SDK-level retries / rate limiting (handled by Fern defaults)
- SDK versioning automation (manual publish for now)
- SDKs for other languages (can be added to `generators.yml` later)
