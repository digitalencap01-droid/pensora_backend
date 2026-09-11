# Security

## Reporting an issue

This is a solo-maintained project. If you find a security issue, open
a private report to the maintainer rather than a public GitHub issue.

## Secrets in this project

`.env` (gitignored, never committed) currently holds, in plaintext:

- `OPENAI_API_KEY`
- `SUPABASE_DB_URL` (contains the database password)
- `SUPABASE_SERVICE_ROLE_KEY` (bypasses Row-Level Security — treat as
  a master key, not a routine credential)

That's an acceptable posture for solo local development. It stops
being acceptable the moment this app is deployed anywhere shared
(a server, a teammate's machine, CI). Before that happens:

1. **Move secrets into a real secrets manager** for the deployment
   target (e.g. your host's built-in secrets/environment config,
   or a dedicated manager) instead of shipping a `.env` file.
2. **Never let `SUPABASE_SERVICE_ROLE_KEY` reach a frontend.** It's
   currently only read by backend code (`app/core/config.py`) — keep
   it that way.
3. **Rotate on any suspected exposure** — Supabase project settings
   (API keys, DB password) and the OpenAI dashboard (API key) both
   support regenerating a credential without downtime if you update
   the deployed environment immediately after.

## Rotation checklist

Run through this whenever a key may have leaked (pasted in chat,
committed by accident, shared in a screenshot, etc.):

- [ ] Regenerate the specific credential at its source (Supabase
      Project Settings → API, or platform.openai.com → API keys)
- [ ] Update `.env` (and any deployed environment config) with the
      new value
- [ ] Restart the backend so it picks up the new value
      (`pydantic-settings` reads `.env` once at process start)
- [ ] Revoke/delete the old credential once you've confirmed the new
      one works
- [ ] If it was the Supabase DB password: also update
      `SUPABASE_MIGRATION_DB_URL` if you keep a separate direct
      connection string

## Authentication model

**There is currently no authentication.** Every endpoint is open —
anyone who can reach this server can read and write every row in the
database. This is intentional for now (early local development), but
it means:

- Do not deploy this behind a public URL as-is.
- There is no per-user data scoping — this is a single-tenant app.
- Reintroducing auth (e.g. verifying a Supabase bearer token on every
  request, plus Row-Level Security policies scoping rows by user) is
  tracked as follow-up work, not yet implemented.
