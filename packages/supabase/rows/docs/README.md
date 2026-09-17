# supabase/rows

Governed **PostgREST row access** for Staff workflows that need a Supabase database.

## When to propose

- Persist / load workflow state, leads, notes, config rows.
- Not for web search, mail, or social publish.

## Actions

| action | Notes |
|--------|--------|
| `select` | Filters + limit; empty result → `ok: true`, `empty: true` |
| `insert` | Requires `row`; human gate |
| `update` | Requires `row` + `filters` (no full-table update) |
| `upsert` | Optional `on_conflict` |

## Owner setup

1. Vault bind `supabase/rows`
2. Governance → `allowed_tables` (deny-all until set)
3. Prefer human review on first write workflows
