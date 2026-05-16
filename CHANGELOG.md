# Changelog

## 0.1.0 - 2026-05-16

- Added source-rich `payload.triage` normalization for Notion webhook and poll
  events, including stable refs/links, provenance, task metadata, action
  intents, privacy flags, and deterministic fixture coverage for Start My Day
  style inbox workflows.
- Added outbound method capability metadata and structured Notion auth/scope
  failure details so hosts can gate writes and render repair guidance.
- Added harn-cloud managed-ingress secret alias coverage so hosted webhook
  delivery can resolve Notion verification tokens through `secret_get`.
- Added connector contract payload-subset assertions for supported Notion
  webhook events to keep Rust-provider compatibility shape stable.
- Added the pure-Harn Notion connector surface, webhook HMAC verification,
  canonical event normalization, explicit outbound dispatch, and polling tick
  support.
- Known limitation: signed webhook verification currently requires
  `raw.body_text`; when Harn exposes raw body bytes to pure-Harn connectors,
  signature verification should prefer the byte stream supplied by the host.
