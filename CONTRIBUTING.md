# Contributing to DeepRaven

Thank you for considering contributing to DeepRaven! This project is open source and we genuinely welcome contributions of all kinds — bug fixes, new features, documentation improvements, and ideas.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Code Style](#code-style)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Bugs](#reporting-bugs)
- [Good First Issues](#good-first-issues)
- [Questions](#questions)

---

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. Set up the development environment (see below)
4. Make your changes on a feature branch
5. Submit a pull request

---

## Development Setup

```bash
git clone https://github.com/<your-fork>/deepraven.git
cd deepraven

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in REDIS_URL, SUPABASE_URL, SUPABASE_SECRET_KEY, GROQ_API_KEY
```

Run the Supabase migrations in the Supabase SQL Editor (see README for details), then:

```bash
./start.sh
# Server at http://localhost:5100
# Swagger at http://localhost:5100/docs
```

---

## How to Contribute

### Bug fixes

Open an issue first if the bug is non-trivial, so we can discuss the best fix. For small, obvious bugs, a PR is fine directly.

### New features

Please **open an issue before starting work** on a significant feature. This avoids situations where two people work on the same thing, or where a feature doesn't align with the project direction. For items already listed in the [Roadmap](README.md#roadmap) or [Good First Issues](#good-first-issues), you can go straight to a PR.

### Documentation

Always welcome. No issue needed — just open a PR.

---

## Code Style

- **Python 3.12+** — use modern type hints (`list[str]` not `List[str]`)
- **Pydantic v2** — `model_validate()` for coercion, `model_copy(update={...})` for shallow copies only
- **async/await everywhere** — all I/O must be async; no blocking calls in request handlers
- **No ORM** — DB operations go in `supabase_client.py` as explicit async functions
- **No new dependencies without discussion** — keep `requirements.txt` lean
- Format with [black](https://github.com/psf/black) if you have it, but it's not enforced

---

## Submitting a Pull Request

1. Branch off `main`: `git checkout -b feat/my-feature`
2. Make focused, atomic commits
3. Update `README.md` if you change any API endpoints, env vars, or behavior
4. Open a PR against `main` with:
   - A clear title describing what changed
   - A short description of **why** — motivation matters more than "what"
   - Steps to test your change manually

We review PRs within a few days. We may request changes or suggest a different approach — please don't take it personally.

---

## Reporting Bugs

Open a GitHub issue with:

- **Environment** — Python version, OS, how you're running DeepRaven
- **Steps to reproduce** — the minimal sequence that triggers the bug
- **Expected behavior** — what should have happened
- **Actual behavior** — what actually happened, including full error output
- **Relevant config** — env vars (redact sensitive values)

---

## Good First Issues

These are well-scoped, self-contained improvements that don't require deep knowledge of the whole codebase:

| Issue | Where to look | Difficulty |
|---|---|---|
| Add OpenAI / Anthropic as LLM backend | `app/llm.py`, `app/config.py` | Medium |
| Webhook push on profile update | `app/worker.py`, new router | Medium |
| Contact search / filter on dashboard | `app/static/dashboard.html` | Easy |
| Export profiles as JSON / CSV | `app/routers/profiles.py` | Easy |
| Rate limiting per API key | `app/auth.py`, middleware | Medium |
| Python SDK client | new repo / `sdk/` directory | Medium |
| Add `updated_at` index to conversations | `db_migrations/` | Easy |
| Improve test coverage | anywhere | Easy–Hard |

---

## Questions

For general questions, open a GitHub Discussion or reach out via [adminds.at](https://adminds.at).

For security issues, **do not open a public issue** — email us directly at the address on [adminds.at](https://adminds.at).

---

Copyright © 2024–2025 Alpha Digital Minds GmbH. Contributions are accepted under the Apache 2.0 License.
