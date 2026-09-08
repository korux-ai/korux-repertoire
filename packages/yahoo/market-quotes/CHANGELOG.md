# Changelog — yahoo/market-quotes

## 1.2.0

- Prefer `/v8/finance/chart` per symbol; Yahoo hard-disabled unofficial `/v7/finance/quote`
  (HTTP 401 “User is unable to access this feature”).
- Keep optional crumb-backed v7 attempt as secondary path.
- Clearer PROVIDER error when both paths fail.

## 1.1.0

- Raise symbol cap to 40.
- Add `pct_1d`, optional `pct_5d` (chart), `as_of`, `marketState` / `session_note`, `fetched_at`.
- Add `include_history` param (default true).
- Docs: language-neutral field guidance for compose.

## 1.0.0

- Initial public quote fetch.
