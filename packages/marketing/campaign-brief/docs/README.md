# marketing/campaign-brief

Catalog **skill** (no `runtime/`). Korux Propose/kernel turns NL into a structured campaign brief; this package does not call vendor APIs.

## When to use

- User asks to plan a launch, promo, awareness, or lead-gen campaign
- Need a shared brief before compose / channel mix / external publish

## Suggested downstream

1. Optional `marketing/channel-mix`
2. Internal compose / `marketing`-style copy steps on the platform
3. Connectors: `linkedin/publish`, `instagram/publish`, `mailchimp/campaign`, `wordpress/post`, …
4. Measure: `google/analytics-report`

## Output shape

Prefer markdown or JSON-like content covering: goal, audience, offer, channels, KPIs, timeline, constraints, open questions.

No Vault binding required (`auth.required=false`).
