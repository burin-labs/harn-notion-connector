# Changelog

## Unreleased

- Declared each required secret's direction of trust in `harn.toml`.
  `notion/api-token` is `outbound` and `notion/verification-token` is
  `inbound`. Under the legacy undirected form Harn replayed both as outbound,
  so `harn connect status --connector notion --json` reported an installation
  with a valid API token and no webhook verification token as
  `missing_auth`/unusable. That installation is now `healthy`, and signed
  webhook verification remains a separate requirement. Added
  `tests/manifest_secret_directions.harn`, which fails if the manifest returns
  to the bare-string form.

- Repinned the runtime to Harn 0.10.127.
- Renamed the five `tests/*_smoke.harn` entry pipelines from `default` to
  unique `test_*` names. Harn discovers a test only from a `test_`-prefixed
  pipeline name or an `@test` attribute, so all five smoke suites were
  compiled and then skipped. `harn test tests/` ran zero cases while still
  reporting five discovered files, and `harn package verify` passed
  vacuously until Harn 0.10.126 began reporting an empty selection as a
  program failure.
- Repinned the runtime to Harn 0.10.53 and completed the typed capability
  cutover. Every connector runtime export — `init`, `activate`, `shutdown`,
  `normalize_inbound`, `call`, `poll_tick` — now takes the root `Harness` as
  its first parameter, which the connector ABI requires. Metadata exports
  (`provider_id`, `kinds`, `payload_schema`) remain pure.
- Rewrote the `subscription verification` contract fixture against the
  connector's own payload. Harn 0.10.x removed the builtin `notion` provider
  schema, so the payload the connector returns is now the asserted surface
  instead of being renormalized by a host schema first.

## 0.1.1 - 2026-07-06

- Added deterministic artifact helper descriptors:
  `artifact.export_request` supports Notion page metadata, block-tree, markdown,
  and existing file-URL export descriptors, while `artifact.import_request`
  supports page creation, block append, and File Upload API import descriptors.
  Page-to-PDF export now returns an explicit `unsupported_pdf_export` error
  because Notion's public API has no official page-to-PDF export endpoint.
- Bumped the package metadata to `0.1.1` for the artifact-helper and current
  Harn `>=0.9,<0.10` compatibility release.
- Pinned `notion-sdk-harn` to its tagged `v0.1.0` release
  (commit `bad580c5fbe8ede612b2748ad98606642ce2fc02`) instead of a bare
  branch-tip SHA. Fresh installs are now reproducible without depending on
  whoever last pushed to `notion-sdk-harn`'s `main`. Documented the bump
  workflow in [`README.md`](./README.md#updating-the-notion-sdk).
- Cleaned repo-local agent guidance and README examples.
- Swapped deprecated ambient Harn helpers for `harness.*` APIs in the connector
  and tests.
- Adopted current Harn package metadata: explicit compatibility range,
  provider capability coverage, OAuth endpoint metadata, pinned SDK dependency,
  refreshed lockfile provenance, and package pack verification in CI.
- Hardened webhook normalization by accepting retained `raw.raw_body`, requiring
  unsigned bypasses to be `subscription.verification` events, and resolving
  dotted Harn Cloud secret IDs before signature checks.
- Resolved outbound `api_token` secret IDs, required explicit approval for
  write-like `api_call` escape-hatch requests, and kept poll ticks to one Notion
  query page per tick.

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
- Known limitation: signed webhook verification requires the retained request
  body. Parsed JSON alone is not accepted because signature checks must use the
  original provider bytes/text.
