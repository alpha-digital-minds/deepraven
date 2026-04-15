# DeepRaven SDK Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate and publish official `deepraven` Python and TypeScript SDKs from the FastAPI OpenAPI spec using Fern, with a GitHub Action to keep them in sync.

**Architecture:** Fern reads a committed `fern/openapi/openapi.json` (exported from FastAPI's built-in spec) and writes generated SDKs into `sdks/python/` and `sdks/typescript/`. A GitHub Action re-exports the spec and regenerates on every API change, opening a PR for review.

**Tech Stack:** Fern CLI (`fern-api` npm package), `fernapi/fern-python-sdk`, `fernapi/fern-typescript-node-sdk`, GitHub Actions, PyPI, npm

---

## File Map

| Action | Path | Purpose |
|---|---|---|
| Create | `fern/fern.config.json` | Fern project identity |
| Create | `fern/generators.yml` | Generator config (Python + TS output paths) |
| Create | `fern/openapi/openapi.json` | OpenAPI spec exported from FastAPI |
| Create (generated) | `sdks/python/` | Python SDK (written by Fern) |
| Create (generated) | `sdks/typescript/` | TypeScript SDK (written by Fern) |
| Create | `.github/workflows/sdk-generate.yml` | Auto-regen + PR on API changes |
| Create | `scripts/export_openapi.py` | Exports spec without starting a server |

---

### Task 1: Export the OpenAPI spec

**Files:**
- Create: `scripts/export_openapi.py`
- Create: `fern/openapi/openapi.json`

FastAPI builds the OpenAPI spec from route decorators and Pydantic models — no running server or DB needed. We export it via a script.

- [ ] **Step 1: Create the export script**

Create `scripts/export_openapi.py`:

```python
#!/usr/bin/env python3
"""Export the FastAPI OpenAPI spec to fern/openapi/openapi.json."""
import json
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app

output_path = Path(__file__).parent.parent / "fern" / "openapi" / "openapi.json"
output_path.parent.mkdir(parents=True, exist_ok=True)

spec = app.openapi()
output_path.write_text(json.dumps(spec, indent=2))
print(f"Spec written to {output_path} ({len(spec['paths'])} paths)")
```

- [ ] **Step 2: Run the script to generate the spec**

```bash
cd /path/to/deepraven
source venv/bin/activate
python scripts/export_openapi.py
```

Expected output:
```
Spec written to fern/openapi/openapi.json (N paths)
```

- [ ] **Step 3: Verify the spec looks correct**

```bash
python -c "import json; spec=json.load(open('fern/openapi/openapi.json')); print(list(spec['paths'].keys())[:5])"
```

Expected: a list of API paths like `['/api/v1/auth/register', '/api/v1/auth/login', ...]`

- [ ] **Step 4: Commit**

```bash
git add scripts/export_openapi.py fern/openapi/openapi.json
git commit -m "feat: add OpenAPI spec export script and initial spec"
```

---

### Task 2: Install Fern and initialize the project

**Files:**
- Create: `fern/fern.config.json`
- Create: `fern/generators.yml`

- [ ] **Step 1: Install the Fern CLI globally**

```bash
npm install -g fern-api
fern --version
```

Expected: prints a version like `0.x.x`

- [ ] **Step 2: Initialize Fern from the OpenAPI spec**

Run from the repo root:

```bash
fern init --openapi fern/openapi/openapi.json
```

This creates `fern/fern.config.json` and a starter `fern/generators.yml`. We will replace `generators.yml` in the next step.

Expected output: `Fern project initialized.` (or similar)

- [ ] **Step 3: Verify fern.config.json was created**

```bash
cat fern/fern.config.json
```

Expected content (organization name may differ — update if needed):
```json
{
  "organization": "deepraven",
  "version": "0.x.x"
}
```

If the organization is wrong, edit it to `"deepraven"`.

- [ ] **Step 4: Replace generators.yml with our config**

Overwrite `fern/generators.yml` with:

```yaml
default-group: local
groups:
  local:
    generators:
      - name: fernapi/fern-python-sdk
        version: latest
        output:
          location: local-file-system
          path: ../sdks/python
        config:
          package_name: deepraven
          async_handlers: true

      - name: fernapi/fern-typescript-node-sdk
        version: latest
        output:
          location: local-file-system
          path: ../sdks/typescript
        config:
          package_name: deepraven
```

- [ ] **Step 5: Commit**

```bash
git add fern/
git commit -m "feat: initialize Fern project config"
```

---

### Task 3: Generate both SDKs

**Files:**
- Create (generated): `sdks/python/`
- Create (generated): `sdks/typescript/`

- [ ] **Step 1: Run Fern generation**

```bash
fern generate --group local
```

Expected: Fern downloads the generators and writes output to `sdks/python/` and `sdks/typescript/`. This takes 1-3 minutes on first run.

- [ ] **Step 2: Verify Python SDK structure**

```bash
ls sdks/python/
```

Expected: directories/files including `deepraven/`, `pyproject.toml`, `README.md` (Fern generates all of these)

- [ ] **Step 3: Verify TypeScript SDK structure**

```bash
ls sdks/typescript/
```

Expected: `src/`, `package.json`, `tsconfig.json`, `README.md`

- [ ] **Step 4: Commit the generated SDKs**

```bash
git add sdks/
git commit -m "feat: generate Python and TypeScript SDKs via Fern"
```

---

### Task 4: Configure Python SDK metadata for PyPI

**Files:**
- Modify: `sdks/python/pyproject.toml`

Fern generates a `pyproject.toml` but the metadata (description, author, homepage) needs to be filled in for a clean PyPI listing.

- [ ] **Step 1: Open and review the generated pyproject.toml**

```bash
cat sdks/python/pyproject.toml
```

- [ ] **Step 2: Update the metadata section**

In `sdks/python/pyproject.toml`, find the `[project]` section and update it to:

```toml
[project]
name = "deepraven"
version = "2.0.0"
description = "Official Python SDK for DeepRaven — long-lasting memory layer for AI sales agents"
readme = "README.md"
license = { text = "Apache-2.0" }
requires-python = ">=3.8"
authors = [
  { name = "Alpha Digital Minds GmbH", email = "hello@adminds.at" }
]
keywords = ["ai", "memory", "sales", "agents", "deepraven"]
classifiers = [
  "Development Status :: 4 - Beta",
  "Intended Audience :: Developers",
  "License :: OSI Approved :: Apache Software License",
  "Programming Language :: Python :: 3",
]

[project.urls]
Homepage = "https://deepraven.ai"
Repository = "https://github.com/AI-Finder-Inc/deepraven"
```

Keep all other sections (dependencies, build system) as Fern generated them — only change the `[project]` metadata block.

- [ ] **Step 3: Commit**

```bash
git add sdks/python/pyproject.toml
git commit -m "feat: update Python SDK PyPI metadata"
```

---

### Task 5: Configure TypeScript SDK metadata for npm

**Files:**
- Modify: `sdks/typescript/package.json`

- [ ] **Step 1: Open and review the generated package.json**

```bash
cat sdks/typescript/package.json
```

- [ ] **Step 2: Update the metadata fields**

In `sdks/typescript/package.json`, update these fields (leave all others as Fern generated):

```json
{
  "name": "deepraven",
  "version": "2.0.0",
  "description": "Official TypeScript SDK for DeepRaven — long-lasting memory layer for AI sales agents",
  "author": "Alpha Digital Minds GmbH <hello@adminds.at>",
  "license": "Apache-2.0",
  "homepage": "https://deepraven.ai",
  "repository": {
    "type": "git",
    "url": "https://github.com/AI-Finder-Inc/deepraven.git",
    "directory": "sdks/typescript"
  },
  "keywords": ["ai", "memory", "sales", "agents", "deepraven"]
}
```

- [ ] **Step 3: Commit**

```bash
git add sdks/typescript/package.json
git commit -m "feat: update TypeScript SDK npm metadata"
```

---

### Task 6: Smoke-test the Python SDK locally

No test suite is configured for this project, so we verify the SDK installs and the client can be instantiated without errors.

- [ ] **Step 1: Install the SDK from the local path**

```bash
source venv/bin/activate
pip install -e sdks/python/
```

Expected: installs successfully with no errors

- [ ] **Step 2: Verify the client imports and instantiates**

```bash
python -c "
from deepraven import DeepRavenClient
client = DeepRavenClient(api_key='dr_test')
print('Client instantiated:', type(client))
print('Available resources:', [r for r in dir(client) if not r.startswith('_')])
"
```

Expected: prints the client type and a list of resources like `['conversations', 'profiles', 'projects', ...]`

- [ ] **Step 3: Verify async client is available**

```bash
python -c "
from deepraven import AsyncDeepRavenClient
client = AsyncDeepRavenClient(api_key='dr_test')
print('Async client instantiated:', type(client))
"
```

Expected: prints the async client type without errors

- [ ] **Step 4: Commit smoke test evidence (none needed — just proceed)**

No files to commit. Move to Task 7.

---

### Task 7: Smoke-test the TypeScript SDK locally

- [ ] **Step 1: Install dependencies**

```bash
cd sdks/typescript
npm install
```

Expected: installs without errors

- [ ] **Step 2: Build the SDK**

```bash
npm run build
```

Expected: compiles TypeScript to `dist/` without errors

- [ ] **Step 3: Verify the client imports**

```bash
node -e "
const { DeepRavenClient } = require('./dist');
const client = new DeepRavenClient({ apiKey: 'dr_test' });
console.log('Client instantiated:', typeof client);
console.log('Has profiles:', typeof client.profiles);
console.log('Has conversations:', typeof client.conversations);
"
```

Expected:
```
Client instantiated: object
Has profiles: object
Has conversations: object
```

- [ ] **Step 4: Return to repo root**

```bash
cd ../..
```

---

### Task 8: Create the GitHub Action for auto-sync

**Files:**
- Create: `.github/workflows/sdk-generate.yml`

This action triggers on any push to `main` that touches API files, re-exports the spec, regenerates the SDKs, and opens a PR.

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/sdk-generate.yml`:

```yaml
name: Regenerate SDKs

on:
  push:
    branches: [main]
    paths:
      - "app/routers/**"
      - "app/models.py"
      - "app/main.py"

jobs:
  regenerate:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Python dependencies
        run: |
          pip install -r requirements.txt

      - name: Export OpenAPI spec
        run: python scripts/export_openapi.py
        env:
          # Minimal env vars needed for app import (no real values needed for spec export)
          REDIS_URL: redis://localhost:6379
          SUPABASE_URL: https://placeholder.supabase.co
          SUPABASE_SECRET_KEY: placeholder
          GROQ_API_KEY: placeholder

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install Fern CLI
        run: npm install -g fern-api

      - name: Generate SDKs
        run: fern generate --group local

      - name: Check for changes
        id: changes
        run: |
          git diff --quiet sdks/ fern/openapi/ || echo "changed=true" >> $GITHUB_OUTPUT

      - name: Open PR with updated SDKs
        if: steps.changes.outputs.changed == 'true'
        uses: peter-evans/create-pull-request@v6
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: "chore: regenerate SDKs from updated OpenAPI spec"
          title: "chore: regenerate SDKs"
          body: |
            Auto-generated by the SDK regeneration workflow.

            Triggered by changes to API routes or models. Please review the diff before merging.
          branch: chore/regenerate-sdks
          delete-branch: true
```

- [ ] **Step 2: Commit the workflow**

```bash
git add .github/workflows/sdk-generate.yml
git commit -m "feat: add GitHub Action to auto-regenerate SDKs on API changes"
```

---

### Task 9: Verify app imports cleanly without full env vars

The GitHub Action imports `app.main` with placeholder env vars to export the spec. Verify this works locally.

- [ ] **Step 1: Test the export script with dummy env vars**

```bash
REDIS_URL=redis://localhost:6379 \
SUPABASE_URL=https://placeholder.supabase.co \
SUPABASE_SECRET_KEY=placeholder \
GROQ_API_KEY=placeholder \
python scripts/export_openapi.py
```

Expected: spec is written successfully — FastAPI builds the spec from code, not from live connections.

If this fails with a connection error, the app is trying to connect at import time. Fix by moving connection calls out of module-level scope in `app/main.py` (into the lifespan function, which is already where they should be per the existing architecture).

- [ ] **Step 2: Commit any fixes made**

```bash
git add -p
git commit -m "fix: ensure app.main imports cleanly without live connections"
```

---

### Task 10: Publish instructions (manual first run)

No automation for the first publish — do it manually to get the package names registered on PyPI and npm.

- [ ] **Step 1: Publish Python SDK to PyPI**

```bash
cd sdks/python
pip install build twine
python -m build
twine upload dist/*
# Enter your PyPI username/password or use an API token
```

Expected: package appears at `https://pypi.org/project/deepraven/`

- [ ] **Step 2: Publish TypeScript SDK to npm**

```bash
cd ../typescript
npm publish --access public
# Must be logged in: npm login
```

Expected: package appears at `https://www.npmjs.com/package/deepraven`

- [ ] **Step 3: Verify installs work from registries**

```bash
pip install deepraven
npm install deepraven
```

- [ ] **Step 4: Update README with install instructions**

Add to `README.md` under a new `## SDKs` section, before the Quick Start:

```markdown
## SDKs

Official clients for the DeepRaven API:

**Python**
\`\`\`bash
pip install deepraven
\`\`\`

**TypeScript / JavaScript**
\`\`\`bash
npm install deepraven
\`\`\`

See [`sdks/python/README.md`](sdks/python/README.md) and [`sdks/typescript/README.md`](sdks/typescript/README.md) for usage examples.
```

- [ ] **Step 5: Commit README update**

```bash
git add README.md
git commit -m "docs: add SDK install instructions to README"
```

---

## Publishing Secrets (for future automation)

When you're ready to automate publishing, add these secrets to the GitHub repo (`Settings → Secrets → Actions`):

| Secret | Value |
|---|---|
| `PYPI_API_TOKEN` | Token from pypi.org → Account Settings → API Tokens |
| `NPM_TOKEN` | Token from npmjs.com → Access Tokens → Automation |

Then add publish steps to the workflow after generation.
