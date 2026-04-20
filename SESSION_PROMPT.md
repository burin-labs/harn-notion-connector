# SESSION_PROMPT.md — harn-notion-connector v0

You are picking up the v0 build of `harn-notion-connector`, a pure-Harn
Notion connector for the Harn orchestrator. This file is your
self-contained bootstrap.

## Pivot context (60 seconds)

Harn is moving per-provider connectors **out** of its Rust monorepo and
into external pure-Harn libraries under `burin-labs/`. This repo is one
of the four flagship per-provider connectors (Notion, GitHub, Slack,
Linear). The existing Rust impl at
`/Users/ksinder/projects/harn/crates/harn-vm/src/connectors/notion/mod.rs`
(1514 LOC) is the behavior spec — port its semantics into pure Harn.

Tracking ticket: [Pure-Harn Connectors Pivot epic
#350](https://github.com/burin-labs/harn/issues/350).

## What this repo specifically delivers

A pure-Harn module that implements the Harn Connector interface and is
loadable by the orchestrator runtime as the `notion` provider. Concretely:

- `pub fn provider_id() -> string` returning `"notion"`.
- `pub fn kinds() -> list` returning `["webhook", "poll"]`.
- `pub fn payload_schema() -> dict` returning the canonical normalized
  event schema (event_type, resource_id, parent_id, actor, occurred_at,
  raw).
- Lifecycle: `pub fn init(ctx)`, `pub fn activate(bindings)`,
  `pub fn shutdown()`.
- `pub fn normalize_inbound(raw) -> dict` — verifies HMAC against the
  raw body using `hmac_sha256` + `constant_time_eq` (the upstream
  builtins shipped on `worktree-connectors-pivot-groundwork`), then
  normalizes the Notion event payload to the canonical shape.
- `pub fn call(method, args)` — outbound dispatch into
  `notion-sdk-harn`'s Client. Methods are dotted paths like
  `"databases.query"`, `"pages.retrieve"`.
- `pub fn poll_tick()` (optional) — the polling alternative for bindings
  that opt into `kind: "poll"` instead of webhooks.

## What's blocked

- **[harn#346 (Connector interface contract)](https://github.com/burin-labs/harn/issues/346)** —
  the formal interface (function names, argument shapes, return shapes)
  isn't accepted yet. Implementing in advance is fine; expect API tweaks
  when #346 lands. Match the function names listed above so the surface
  is close to landing-state.
- **[harn#345 (Package management v0)](https://github.com/burin-labs/harn/issues/345)** —
  needed to import `notion-sdk-harn` cleanly. Until it lands, use
  `path = "../notion-sdk-harn"`. **Do not cut a v0.1.0 release tag
  until #345 lands** — file-relative imports are a development
  scaffold, not a distribution path.
- **[harn#347 (Bytes value type + raw inbound body access)](https://github.com/burin-labs/harn/issues/347)** —
  *only* blocking for connectors that need binary payloads. Notion
  always sends UTF-8 JSON, so HMAC verification works fine on
  `raw.body_text` for v0. Document the assumption loudly in
  `normalize_inbound` and revisit when #347 lands so the connector can
  also handle `raw.body_bytes` defensively.

## What's unblocked

- `hmac_sha256(key, message) -> hex_string` — Harn builtin, just shipped.
- `hmac_sha256_base64(key, message) -> base64_string` — Harn builtin.
- `constant_time_eq(a, b) -> bool` — **use this for signature
  comparison**. Plain `==` leaks timing info. Both args should be the
  same encoding (compare hex-to-hex or base64-to-base64).
- All HTTP, JSON, dict, list, regex, datetime stdlib.
- Sibling `notion-sdk-harn` for outbound calls (path import for now).

## v0 milestones (build in order)

### M1 — Connector interface skeleton

- Stub all interface functions in `src/lib.harn` with sensible defaults.
- `provider_id()` returns `"notion"`. `kinds()` returns `["webhook",
  "poll"]`. `payload_schema()` returns the canonical schema dict.
- `init`, `activate`, `shutdown` are no-ops storing/clearing module
  state in a top-level dict.
- Acceptance: `harn check src/lib.harn` exits 0; a smoke test imports
  the module and calls each interface function without error.

### M2 — HMAC verification + normalization

- Port the HMAC verification logic from
  `/Users/ksinder/projects/harn/crates/harn-vm/src/connectors/notion/mod.rs`.
  Notion signs webhook payloads with HMAC-SHA256 and delivers the
  signature in the `x-notion-signature` header (verify the exact header
  name in the Rust impl).
- Use `hmac_sha256(secret, raw.body_text)` and compare with
  `constant_time_eq` against the header value (after stripping any
  `"sha256="` prefix).
- Reject (`Err`) on missing signature, mismatched signature, or missing
  secret in the binding config.
- Normalize the verified payload into the canonical event shape:
  ```harn
  {
    event_type: "page.updated",  // or "database.created", etc.
    resource_id: "...",
    parent_id: "...",
    actor: { id: "...", name: "..." },
    occurred_at: "2026-04-19T...",
    raw: <original payload>,
  }
  ```
- Acceptance: `tests/normalize_smoke.harn` feeds 3+ recorded webhook
  payloads (under `tests/fixtures/webhooks/`) through
  `normalize_inbound`, including one with a tampered signature, and
  asserts the right outcomes (Ok / Err).

### M3 — Outbound dispatch via notion-sdk-harn

- `call("pages.retrieve", { page_id })` dispatches into
  `notion_sdk.Client(...).pages.retrieve({ page_id })` and returns the
  result. Use a small dispatch table (dict of method-string → handler)
  rather than dynamic field access so the surface is auditable.
- The Client should be constructed from the binding's auth config
  during `activate()` and stored in module state.
- Errors propagate as `NotionError` (already normalized by the SDK).
- Acceptance: `tests/call_smoke.harn` activates a connector with a
  mocked SDK client and exercises `call("pages.retrieve", ...)` and
  `call("databases.query", ...)`.

### M4 — Polling fallback

- `poll_tick()` performs one tick of the polling-mode loop: query
  configured databases for new/updated pages since the last cursor,
  emit normalized events for each, and update the cursor in module
  state.
- Per the [harn#346 risk note](https://github.com/burin-labs/harn/issues/346),
  prefer `poll_tick()` over a long-running `tokio::spawn`-equivalent —
  this lets the orchestrator drive cadence and cancel cleanly.
- Acceptance: `tests/poll_smoke.harn` simulates two ticks against a
  mocked Notion API and asserts cursor advancement plus emitted event
  count.

## Recommended workflow

1. **Use a worktree per milestone:**
   ```sh
   cd /Users/ksinder/projects/harn-notion-connector
   git worktree add ../harn-notion-connector-wt-m1 -b m1-skeleton
   ```
2. **Read the Rust impl side-by-side** for each milestone. Don't
   re-derive HMAC details from documentation when there's a working
   implementation already.
3. **Pin webhook fixtures from a Notion sandbox**, never from a
   production workspace. Strip user IDs and database IDs to fake values
   before committing recordings.
4. **Test the unhappy path first.** Tampered signatures, missing
   headers, malformed JSON — these are the easy security bugs.

## Reference materials

- Harn quickref: `/Users/ksinder/projects/harn/docs/llm/harn-quickref.md`.
- Harn language spec: `/Users/ksinder/projects/harn/spec/HARN_SPEC.md`.
- Existing Rust impl (the spec for behavior):
  `/Users/ksinder/projects/harn/crates/harn-vm/src/connectors/notion/mod.rs`.
- Sibling SDK: `/Users/ksinder/projects/notion-sdk-harn/` and its
  `SESSION_PROMPT.md`.
- HMAC builtins conformance fixture (good usage examples):
  `/Users/ksinder/projects/harn/conformance/tests/stdlib/hmac_sha256.harn`.
- Notion webhook docs:
  <https://developers.notion.com/docs/webhooks> (verify the current
  header name and signature format here — Notion has been iterating).

## Testing expectations

- Negative-path tests for HMAC verification are mandatory. Cover:
  missing signature header, wrong-length signature, valid-shape but
  wrong-secret signature, valid signature but tampered body.
- Use `constant_time_eq` for *all* signature comparisons; a regression
  test asserting that the comparison helper is in the call path is
  worth adding.
- Run before committing:
  ```sh
  cd /Users/ksinder/projects/harn
  cargo run --quiet --bin harn -- check /Users/ksinder/projects/harn-notion-connector/src/lib.harn
  cargo run --quiet --bin harn -- lint  /Users/ksinder/projects/harn-notion-connector/src/lib.harn
  cargo run --quiet --bin harn -- fmt --check /Users/ksinder/projects/harn-notion-connector/src/lib.harn
  for t in /Users/ksinder/projects/harn-notion-connector/tests/*.harn; do
    cargo run --quiet --bin harn -- run "$t" || exit 1
  done
  ```

## Definition of done for v0

- [ ] All interface functions implemented and `harn check` clean.
- [ ] HMAC verification uses `constant_time_eq`, with negative-path
      tests proving rejection of tampered payloads.
- [ ] `normalize_inbound` produces the canonical event shape for at
      least 3 distinct Notion event types.
- [ ] `call(method, args)` covers the methods exercised by the example
      in README + at least 2 more.
- [ ] `poll_tick()` advances state correctly across simulated ticks.
- [ ] README usage example matches the actual surface.
- [ ] **No v0.1.0 tag cut until [harn#345](https://github.com/burin-labs/harn/issues/345)
      and [harn#346](https://github.com/burin-labs/harn/issues/346)
      both land.**
- [ ] Open question logged in CHANGELOG: revisit `raw.body_text` →
      `raw.body_bytes` once [harn#347](https://github.com/burin-labs/harn/issues/347)
      lands.
