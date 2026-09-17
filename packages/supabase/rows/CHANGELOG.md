# Changelog — supabase/rows

## 1.0.0

- Initial connector: PostgREST `select` / `insert` / `update` / `upsert`
- Owner `allowed_tables` (empty = deny all) via Track B governor
- Human gate on writes; optional human on select
- Closed failure classes + trilingual label/description/propose_guide
