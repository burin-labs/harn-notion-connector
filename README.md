# harn-notion-connector

Pure-Harn Notion connector for the Harn orchestrator. Verifies inbound
webhook signatures, normalizes Notion event payloads to the canonical
`TriggerEvent` shape, and dispatches outbound API calls via
[notion-sdk-harn](https://github.com/burin-labs/notion-sdk-harn).

> **Status: v0.1.0** — production-ready first-party connector package,
> verified with the published `harn-cli` 0.8.19 release.

This is an **inbound + outbound** connector implementing the Harn Connector
Contract v1. Its `payload_schema()` export returns the canonical
`{ harn_schema_name, json_schema }` shape, `normalize_inbound(...)` returns
`NormalizeResult` v1 variants, and `poll_tick(...)` returns Harn-managed
cursor/state updates. It complements the typed SDK at `notion-sdk-harn`, which
it imports for its outbound API surface. See the canonical
[Harn connector authoring docs](https://docs.harnlang.com/connectors/authoring.html)
for the contract and package gate.

## Install

Install the pinned Harn CLI version used by this package:

```sh
cargo install harn-cli --version "$(cat .harn-version)" --locked
harn --version
```

Add the released connector package:

```sh
harn add github.com/burin-labs/harn-notion-connector@v0.1.0
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

## Supported Surface

Inbound webhooks:

- `subscription.verification` returns a normalized verification event without
  requiring a signature.
- Signed Notion webhook payloads are verified with `x-notion-signature` and
  normalized using the Notion `type` field as the event kind. The fixture suite
  covers `page.content_updated`, `database.created`, and `comment.created`.
- Normalized payloads include a provider-neutral `payload.triage` projection for
  Start My Day and other inbox workflows. It carries stable Notion refs, source
  URLs/deep links when available, source timestamps, actors, summaries,
  database/page/comment provenance, task status/assignee/date metadata, privacy
  flags, the event dedupe key, and approval-gated action intents. Provider raw
  data stays separate at `payload.raw`; `payload.triage.raw_ref` points back to
  that field.

Polling:

- `poll_tick(ctx)` supports `resource = "data_source"` and
  `resource = "database"` bindings. It emits normalized `page.content_updated`
  events for changed query results.

Outbound calls:

- Blocks: `blocks.retrieve`, `blocks.update`, `blocks.delete`,
  `blocks.children.list`, `blocks.children.append`.
- Pages: `pages.retrieve`, `pages.create`, `pages.update`,
  `pages.markdown.retrieve`, `pages.markdown.update`, `pages.move`,
  `pages.properties.retrieve`.
- Databases and data sources: `databases.create`, `databases.retrieve`,
  `databases.update`, `databases.query`, `data_sources.create`,
  `data_sources.retrieve`, `data_sources.update`, `data_sources.query`,
  `data_sources.templates.list`.
- Comments, users, files, custom emojis, search, and views:
  `comments.*`, `users.*`, `file_uploads.*`, `custom_emojis.list`,
  `search.query`, `views.*`, `views.queries.*`.
- `api_call` is an escape hatch for Notion endpoints not yet wrapped by
  `notion-sdk-harn`.

Write-capable outbound methods are also exposed through
`method_capabilities()`. Hosts should treat methods marked
`requires_approval = true` as approval-gated operations; the connector does not
auto-edit pages, comments, databases, or task statuses during normalization.

Operational limits:

- Signed webhook normalization requires exact `raw.body_text`; parsed JSON alone
  is rejected because HMAC verification must use the original request body.
- `normalize_inbound(raw)` is deterministic and does not perform network I/O.
- Harn owns webhook routing, poll schedules, leases, retry policy, durable
  cursor/state, and secret resolution. This connector only validates and
  normalizes inbound payloads, dispatches SDK calls, and returns poll results.
- Polling fetches one Notion query page per tick and respects
  `max_batch_size`; capped ticks leave the cursor unchanged for retry-safe
  draining.
- Notion 401/403 and scope/resource-access failures return structured
  `auth_scope_failure` metadata with a recovery hint so hosts can render a
  Connect/Fix path without parsing provider-specific error strings.

Harn Cloud managed ingress:

- Configure the package with `HARN_CLOUD_CONNECTORS_CONFIG` and map
  `verification_token` (or `signing_secret`) to the tenant secret that stores
  the Notion webhook verification token.
- Managed ingress passes those mappings through `raw.metadata.secret_ids`; the
  connector resolves them with `secret_get` during the deterministic
  `normalize_inbound(...)` path.
- The contract fixture named `harn-cloud managed ingress page content updated
  webhook` exercises this load-and-normalize shape without live provider
  credentials.

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
harn connector test "$PWD" --provider notion --run-poll-tick
```

## License

Dual-licensed under MIT and Apache-2.0.

- [LICENSE-MIT](./LICENSE-MIT)
- [LICENSE-APACHE](./LICENSE-APACHE)
