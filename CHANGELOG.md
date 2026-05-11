# Changelog

## Unreleased

- Added source-rich `payload.triage` normalization for Notion webhook and poll
  events, including stable refs/links, provenance, task metadata, action
  intents, privacy flags, and deterministic fixture coverage for Start My Day
  style inbox workflows.
- Added outbound method capability metadata and structured Notion auth/scope
  failure details so hosts can gate writes and render repair guidance.
- Added the pure-Harn Notion connector surface, webhook HMAC verification,
  canonical event normalization, explicit outbound dispatch, and polling tick
  support.
- Open question: revisit `raw.body_text` and prefer `raw.body_bytes` once
  harn#347 lands so signature verification can operate on the exact raw byte
  stream defensively.
