# supabase/rows — Vault credential

Bind tool name **`supabase/rows`** on Staff agents that need a governed workflow database.

## Prerequisites

1. Create a [Supabase](https://supabase.com/) project.
2. Enable the Data API (PostgREST) for your schema (usually `public`).
3. Prefer a **service role / secret** key for Staff-side workflows (bypasses RLS).
4. Enable RLS on tables anyway (defense in depth). Korux **must** still set `allowed_tables`.

Never put the service role key in a browser or this git repo.

## Vault JSON

Secret kind / binding tool: `supabase/rows`

```json
{
  "project_url": "https://xxxx.supabase.co",
  "api_key": "eyJhbGciOi…service_role_or_secret…",
  "schema": "public"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `project_url` | yes | Project origin (`https://<ref>.supabase.co`) |
| `api_key` | yes | Service role / secret key |
| `schema` | no | Postgres schema (default `public`) |

## Governance (Owner)

| Config | Suggested |
|--------|-----------|
| `allowed_tables` | **Required** — empty deny-all. List only tables workflows may touch |
| `max_rows` | Cap select fan-out (default 50, hard 200) |
| `require_human_on_read` | Optional — force human gate on `select` |

Writes (`insert` / `update` / `upsert`) always require human confirmation via Track B.

## Local / CI

```bash
KORUX_CAPABILITY_HTTP_MOCK=1
```

## Out of scope

- Arbitrary SQL
- RPC / Edge Functions
- Storage / Realtime
- `delete` (not in v1.0.0)
