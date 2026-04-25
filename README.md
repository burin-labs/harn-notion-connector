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
`call(method, args)`, and `poll_tick(ctx)`.

## Polling Fallback

Use a `kind = "poll"` Notion binding when webhooks are unavailable or as a
fallback watcher. Harn owns the schedule, lease, cursor, and connector state;
the connector only reads `ctx.cursor` / `ctx.state` and returns the next
`{ events, cursor, state }`.

```toml
provider = "notion"
kind = "poll"
handler = "on_notion_page_change"
poll = { interval = "5m", jitter = "30s", state_key = "notion:workspace:tasks", max_batch_size = 50, resource = "data_source", data_source_id = "$NOTION_DATA_SOURCE_ID", high_water_mark = "last_edited_time", page_size = 50 }
secrets = { api_token = "notion/api-token" }
```

`poll.interval` may also be supplied as `interval_ms` or `interval_secs`.
`state_key` can be written as `cursor_state_key`; it chooses the durable Harn
cursor/state slot shared across ticks. The returned poll events use the same
normalized payload shape and dedupe key as webhook-ingested Notion events.

## Configuration

### Required Secrets

For inbound webhooks, store the Notion webhook `verification_token` captured
during subscription verification and pass it through the trigger binding as
`secrets.verification_token`:

```toml
[[triggers]]
id = "notion.webhook"
provider = "notion"
kind = "webhook"
handler = "handlers/notion.handle"

[triggers.match]
path = "/hooks/notion"

[triggers.secrets]
verification_token = "notion/verification-token"
```

For outbound calls and polling, store a Notion internal integration token or
OAuth access token and pass it as `api_token`, `token`, or
`secrets.api_token`. The connector also reads `NOTION_TOKEN` for local
development.

```harn
init({
  api_token: env("NOTION_TOKEN"),
  notion_version: "2026-03-11",
})
```

### Notion Capabilities

Grant the minimum Notion capabilities for the methods you call. The common MVP
set is:

- `Read content` for retrieving blocks, pages, databases, data sources, search,
  views, polling queries, and markdown reads.
- `Insert content` for creating pages, databases, data sources, blocks, file
  uploads, and views.
- `Update content` for updating pages, blocks, databases, data sources, views,
  moving pages, and markdown updates.
- `Read comments` for listing or retrieving comments.
- `Insert comments` for creating, updating, or deleting comments.
- User information access when calling `users.*` methods or when workflows need
  actor names/emails.

See Notion's official docs for
[integration capabilities](https://developers.notion.com/reference/capabilities),
[webhook verification](https://developers.notion.com/reference/webhooks), and
[comments capabilities](https://developers.notion.com/guides/data-apis/working-with-comments).

### Local Webhook Testing

Use `normalize_inbound(raw)` with the exact raw body text received by your HTTP
listener. Signature verification is computed over `raw.body_text`; parsed JSON
alone is intentionally rejected for signed webhook events.

```harn
let raw = {
  verification_token: env("NOTION_VERIFICATION_TOKEN"),
  body_text: read_file("tests/fixtures/webhooks/page_content_updated.json"),
  headers: {
    ["x-notion-signature"]: "sha256=...",
    ["request-id"]: "req_local",
  },
}
let result = notion_connector.normalize_inbound(raw)
```

The package also declares `[[connector_contract.fixtures]]` in `harn.toml`.
`harn connector check .` runs those signed fixtures through the same
`normalize_inbound` adapter used by Harn connector hosts.

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
harn connector check . --provider notion --run-poll-tick
for test in tests/*.harn; do
  harn run "$test" || exit 1
done
```

## License

Dual-licensed under MIT and Apache-2.0.

- [LICENSE-MIT](./LICENSE-MIT)
- [LICENSE-APACHE](./LICENSE-APACHE)
