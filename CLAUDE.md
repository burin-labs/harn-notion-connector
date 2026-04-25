# CLAUDE.md — harn-notion-connector

## Quick repo conventions

- File extension: `.harn`. Use `snake_case` for filenames.
- Repo directories use `kebab-case`.
- Entry point: `src/lib.harn`.
- Tests live under `tests/`. Recorded webhook fixtures live under
  `tests/fixtures/webhooks/`.
- SDK dependency: `notion-sdk-harn`, resolved by `harn install`.

## How to test

Install the pinned Harn CLI from crates.io:

```sh
cargo install harn-cli --version "$(cat .harn-version)" --locked
harn --version
```

Run the local CI equivalent:

```sh
harn install
harn check src/lib.harn
harn lint src/lib.harn
harn fmt --check src/lib.harn tests/*.harn
harn connector check .
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
