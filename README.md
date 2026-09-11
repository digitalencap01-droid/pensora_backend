# Pensora Backend

An AI-powered content platform: give it a topic and it researches the
live web, plans a keyword strategy, builds a structured content brief,
writes a full long-form article section-by-section, generates complete
SEO metadata, and renders a sanitized, publish-ready HTML page — every
claim in the article traceable back to a real source the model was
actually given.

Built on FastAPI, PostgreSQL (Supabase-hosted), and the OpenAI
Responses API.

> **Authentication is currently disabled.** Every endpoint is open —
> there is no login, no bearer token, no per-user data. This is a
> single-tenant app for local development. Do not deploy it behind a
> public URL as-is. See [Authentication](#authentication) below.

---

## Project structure

```text
pensora_backend/
├── app/
│   ├── main.py                     # FastAPI app + router registration
│   ├── routers/                    # FastAPI routers (one per resource)
│   │   ├── content.py              # POST /content/generate — runs the full pipeline
│   │   ├── projects.py             # list/get/edit/version/restore/rebuild/usage/sitemap
│   │   ├── documents.py            # document upload + RAG grounding
│   │   ├── images.py               # direct image upload + vision grounding
│   │   ├── research.py             # standalone research endpoint
│   │   ├── keywords.py             # standalone keyword strategy endpoint
│   │   ├── content_brief.py        # standalone content brief endpoint
│   │   ├── articles.py             # standalone article generation endpoint
│   │   ├── seo.py                  # standalone SEO metadata endpoint
│   │   ├── html.py                 # standalone HTML render endpoint
│   │   ├── linkedin.py             # LinkedIn OAuth connect + publish
│   │   ├── linkedin_callback.py    # LinkedIn OAuth callback (mounted sub-app)
│   │   └── webflow.py              # Webflow CMS connect + publish
│   │
│   ├── services/                   # one service per pipeline stage + orchestrator
│   │   ├── content_pipeline_service.py    # orchestrates all 6 stages end-to-end
│   │   ├── research_service.py            # web search + synthesis
│   │   ├── document_research_service.py   # RAG over an uploaded document
│   │   ├── image_research_service.py      # vision-based research over uploaded images
│   │   ├── keyword_service.py             # keyword strategy
│   │   ├── content_brief_service.py       # outline / content brief
│   │   ├── article_service.py             # section-by-section writing + citation sanitization
│   │   ├── seo_service.py                 # metadata, JSON-LD, readiness score
│   │   ├── html_service.py                # markdown -> sanitized HTML rendering
│   │   ├── project_management_service.py  # versioning: edit/restore/regenerate/rebuild
│   │   ├── document_service.py            # upload -> chunk -> embed for RAG
│   │   ├── image_upload_service.py        # direct image upload/normalize
│   │   ├── image_placement.py             # distributes images across article sections
│   │   ├── image_vision_service.py        # vision analysis of uploaded images
│   │   ├── linkedin_service.py            # LinkedIn OAuth + publish + content generation
│   │   ├── webflow_service.py             # Webflow CMS publish
│   │   ├── crypto.py                      # Fernet encryption for stored OAuth tokens
│   │   ├── research_merge.py              # merges document/image research with web research
│   │   └── openai_service.py              # shared AsyncOpenAI client/model (with retries)
│   │
│   ├── core/
│   │   ├── config.py               # pydantic-settings
│   │   ├── rate_limit.py           # sliding-window limiter for /content/generate
│   │   ├── exceptions.py           # ContentPipelineError
│   │   └── monitoring.py           # optional Sentry wiring
│   ├── prompts/                    # system prompts, one module per stage
│   ├── schemas/                    # Pydantic request/response + LLM output schemas
│   ├── db/
│   │   ├── models.py                # SQLAlchemy models (projects, versions, SEO, files...)
│   │   ├── database.py              # async engine + session factory
│   │   ├── base.py                  # declarative base + TimestampMixin
│   │   ├── repository.py            # ContentRepository — all persistence in one place
│   │   ├── linkedin_repository.py   # single global LinkedIn connection row
│   │   └── webflow_repository.py    # single global Webflow config row
│   └── templates/                  # Jinja2 templates for the final article HTML
│
├── tests/                          # pytest — citation stripping, SEO scoring, rate limiting
├── migrations/                     # Alembic environment + versions
├── requirements.txt                # runtime dependencies
├── requirements-dev.txt            # + pytest/ruff/respx for local development
├── alembic.ini
├── Dockerfile
├── LICENSE
├── SECURITY.md
└── .env.example
```

---

## Getting started

### Prerequisites

- Python 3.12+
- A [Supabase](https://supabase.com) project (or any PostgreSQL
  database — Supabase is just where connection-string normalization
  and storage buckets are wired up) with the `pgvector` extension
  available
- An [OpenAI](https://platform.openai.com) API key with access to the
  Responses API and the `web_search` tool

### Setup

```powershell
# From this directory

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # PowerShell / cmd
# source venv/Scripts/activate   # Git Bash

# Install dependencies (add -r requirements-dev.txt for tests/lint too)
pip install -r requirements-dev.txt

# Configure environment variables
copy .env.example .env
# then fill in OPENAI_API_KEY, SUPABASE_DB_URL, SUPABASE_URL, etc.

# Run database migrations
alembic upgrade head
```

### Run

```powershell
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

API docs are served at `http://127.0.0.1:8000/docs`, and every route
there can be called directly — no `Authorization` header needed.

### Run tests

```powershell
venv\Scripts\activate
pytest
ruff check .
```

---

## Authentication

There is currently **no authentication anywhere in this app**:

- `app/main.py` registers no auth dependency.
- No router requires a bearer token or any other credential.
- The database has no `user_id` column and no Row-Level Security
  policy — every table is effectively shared, single-tenant storage.
- `LinkedInConnection` and `WebflowConfig` are both single global rows
  (see `app/db/linkedin_repository.py` / `app/db/webflow_repository.py`)
  rather than per-user connections — only one LinkedIn account and one
  Webflow destination can be connected at a time.
- `app/core/rate_limit.py` rate-limits `/content/generate` globally
  (one shared counter), not per user, since there's no user identity
  to key it by.

This is intentional for local development. **Do not deploy this
behind a public URL as-is** — anyone who can reach it can read and
write everything. Reintroducing auth (verifying a bearer token on
every request, scoping rows by user, per-user LinkedIn/Webflow
connections) is future work, not yet implemented.

---

## Environment variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Model used for every generation call, default `gpt-4.1-mini` |
| `SUPABASE_URL` | Used only to build public storage URLs for uploaded documents/images |
| `SUPABASE_DB_URL` | Runtime database connection string (`postgres://`/`postgresql://` auto-normalized to `postgresql+psycopg://`; `sslmode=require` auto-applied for Supabase hosts) |
| `SUPABASE_MIGRATION_DB_URL` | Optional direct (non-pooled) connection string for running Alembic against a pooled connection; falls back to `SUPABASE_DB_URL` |
| `SUPABASE_SERVICE_ROLE_KEY` | Required for document/image upload (Supabase Storage). Leave blank to disable that feature. |
| `GENERATE_RATE_LIMIT_COUNT` / `GENERATE_RATE_LIMIT_WINDOW_SECONDS` | Global cap on `/content/generate` calls, default 5 per 3600s |
| `SENTRY_DSN` | Optional. Enables error monitoring when set; no-op when blank |
| `DB_SCHEMA` | Postgres schema used for all tables, default `ai_blog` |
| `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` / `LINKEDIN_REDIRECT_URI` / `LINKEDIN_STATE_SECRET` / `LINKEDIN_TOKEN_ENCRYPTION_KEY` | LinkedIn publishing. Leave blank to disable. |
| `WEBFLOW_TOKEN` | Webflow publishing. Leave blank to disable. |

See `.env.example` for the full list with placeholder values.

---

## API reference

All routes are prefixed `/api/v1`. Full interactive docs are served
at `/docs`.

| Method | Path | Description |
|---|---|---|
| `POST` | `/content/generate` | Run the full 6-stage pipeline for a new topic |
| `GET` | `/projects` | Paginated list of projects |
| `GET` | `/projects/{id}` | Project detail |
| `GET` | `/projects/{id}/artifacts` | Latest research, keywords, brief, article, SEO, HTML |
| `GET` | `/projects/{id}/article/versions` | List all article versions |
| `GET` | `/projects/{id}/article/versions/{version_number}` | Fetch one article version |
| `PUT` | `/projects/{id}/article` | Save a manually edited draft as a new version |
| `POST` | `/projects/{id}/article/regenerate-section` | Regenerate a single section as a new version |
| `POST` | `/projects/{id}/article/versions/{version_number}/restore` | Restore an older version |
| `POST` | `/projects/{id}/rebuild-output` | Re-run SEO metadata + HTML rendering |
| `GET` | `/projects/usage-summary` | Generation counts and total words written |
| `GET` | `/projects/sitemap.xml` / `/projects/robots.txt` | Export sitemap/robots for completed posts |
| `POST` | `/documents/upload` | Upload a document (PDF/DOCX/TXT/MD) for RAG grounding |
| `GET` | `/documents` / `/documents/{id}/images` | List uploaded documents / extracted images |
| `POST` | `/images/upload` | Upload a batch of images for vision-grounded generation |
| `PUT` | `/images/{id}` | Replace one uploaded image |
| `POST` | `/research`, `/keywords`, `/content-brief`, `/articles/generate`, `/seo/generate`, `/html/render` | Standalone endpoints for each pipeline stage |
| `GET`/`POST`/`DELETE` | `/linkedin/*` | LinkedIn connect/status/publish/generate |
| `GET`/`POST`/`DELETE` | `/webflow/*` | Webflow connect/status/publish |

---

## Design decisions & known limitations

- **No authentication.** See [Authentication](#authentication) above.
- **Rate limiting is in-process and global, not distributed.**
  `app/core/rate_limit.py` tracks calls in memory per server process
  — correct for a single-instance deployment, but a multi-instance
  deployment would need a shared store (e.g. Redis) instead.
- **Article writing is sequential, not parallel.** Sections are
  generated one at a time (deliberately, to keep each section aware
  of a running summary of the ones before it).
- **Saved HTML lives on local disk.** `output/*.html` is written to
  the backend's local filesystem; on an ephemeral or multi-instance
  deployment, only the copy stored in Postgres (`generated_files`
  table) is guaranteed durable.
- **LinkedIn and Webflow are single global connections**, not
  per-user — a consequence of running without authentication.
