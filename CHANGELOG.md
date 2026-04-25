# Changelog

## Unreleased

- Added the pure-Harn Notion connector surface, webhook HMAC verification,
  canonical event normalization, explicit outbound dispatch, and polling tick
  support.
- Open question: revisit `raw.body_text` and prefer `raw.body_bytes` once
  harn#347 lands so signature verification can operate on the exact raw byte
  stream defensively.
