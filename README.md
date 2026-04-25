# harn-notion-connector

Pure-Harn Notion connector for the Harn orchestrator. Verifies inbound
webhook signatures, normalizes Notion event payloads to the canonical
`TriggerEvent` shape, and dispatches outbound API calls via
[notion-sdk-harn](https://github.com/burin-labs/notion-sdk-harn).

> **Status: pre-alpha** — actively developed in tandem with
> [burin-labs/harn](https://github.com/burin-labs/harn). See the
> [Pure-Harn Connectors Pivot epic #350](https://github.com/burin-labs/harn/issues/350).

This is an **inbound + outbound** connector implementing the Harn Connector
interface defined in
[harn#346](https://github.com/burin-labs/harn/issues/346). It complements
the typed SDK at `notion-sdk-harn`, which it imports for its outbound API
surface.

## Install

With Harn 0.7.39 or newer:

```sh
harn add github.com/burin-labs/harn-notion-connector@main
```

For local development, depend on this checkout via a path import:

```toml
[dependencies]
harn-notion-connector = { path = "../harn-notion-connector" }
```

## Usage

```harn
import notion_connector from "harn-notion-connector/default"

trigger watch_database on notion {
  source = {
    kind: "webhook",
    database_id: env("NOTION_DATABASE_ID"),
    verification_token: env("NOTION_VERIFICATION_TOKEN"),
  }
  on event {
    let page = notion_connector.call("pages.retrieve", {
      page_id: event.resource_id,
      api_token: env("NOTION_TOKEN"),
    })
    println("Updated: ${page.properties.Title.title[0].plain_text}")
  }
}
```

The connector exports the standard Harn Connector interface:
`provider_id()`, `kinds()`, `payload_schema()`, `init(ctx)`,
`activate(bindings)`, `shutdown()`, `normalize_inbound(raw)`,
`call(method, args)`, and (optionally) `poll_tick()`.

## Development

Install the pinned Harn CLI from crates.io:

```sh
cargo install harn-cli --version "$(cat .harn-version)" --locked
harn --version
```

Run the local CI equivalent from this repo:

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

## License

Dual-licensed under MIT and Apache-2.0.

- [LICENSE-MIT](./LICENSE-MIT)
- [LICENSE-APACHE](./LICENSE-APACHE)
