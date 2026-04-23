# CLAUDE.md — harn-notion-connector

**Read [SESSION_PROMPT.md](./SESSION_PROMPT.md) first.** It contains the
pivot context, the connector interface contract, what's blocked on
upstream tickets, and the v0 milestones.

## Quick repo conventions

- File extension: `.harn`. Use `snake_case` for filenames.
- Repo directories use `kebab-case`.
- Entry point: `src/lib.harn`.
- Tests live under `tests/`. Recorded webhook fixtures live under
  `tests/fixtures/webhooks/`.
- SDK dependency: `notion-sdk-harn`, resolved by `harn install`.

## How to test

Install the pinned Harn CLI from crates.io and run the local gate:

```sh
cargo install harn-cli --version "$(cat .harn-version)" --locked
harn install
harn check src
harn lint src
harn fmt --check src tests
for test in tests/*.harn; do
  harn run "$test" || exit 1
done
```

## Reference Rust impl

The existing 1514-LOC Rust connector at
`/Users/ksinder/projects/harn/crates/harn-vm/src/connectors/notion/mod.rs`
is the **behavior spec**. When in doubt about HMAC details, payload
normalization, or pollback semantics, port from there.

## Upstream conventions

For general Harn coding conventions and project layout, defer to
[`/Users/ksinder/projects/harn/CLAUDE.md`](/Users/ksinder/projects/harn/CLAUDE.md).

## Don't

- Don't import `harn-notion-connector` from `notion-sdk-harn` — the
  dependency only flows the other direction.
- Don't add outbound REST endpoint definitions here — those belong in
  `notion-sdk-harn`. This connector wraps the SDK; it doesn't replicate it.
- Don't hand-edit `LICENSE-*` or `.gitignore`.
