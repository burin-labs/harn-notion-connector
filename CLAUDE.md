# CLAUDE.md - harn-notion-connector

Pure-Harn Notion connector package for webhooks, polling, and outbound Notion API calls.

Shared Harn connector authoring rules live in the canonical guide:

- https://github.com/burin-labs/harn/blob/main/docs/src/connectors/authoring.md

Keep this file limited to provider-specific notes and local hazards. Add shared connector guidance
to the Harn guide first.

## Provider Notes

- Outbound REST endpoint definitions belong in `notion-sdk-harn`; this connector wraps that SDK and
  should not duplicate its generated API surface.
- Signed webhooks use `x-notion-signature`; subscription verification events intentionally do not
  require a signature.
- Polling supports database and data source resources and should preserve Harn-managed cursor/state
  handoff across ticks.
- `harn-notion-connector` must not be imported from `notion-sdk-harn`; the dependency only flows
  from connector to SDK.
