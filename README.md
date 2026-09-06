# harn-notion-connector

Notion connector for Harn. It verifies inbound webhook signatures, normalizes
Notion event payloads to the canonical `TriggerEvent` shape, and dispatches
outbound API calls through
[notion-sdk-harn](https://github.com/burin-labs/notion-sdk-harn).

Status: v0.1.1. This package is verified with the `harn-cli` version pinned in
`.harn-version`.

This is an **inbound + outbound** connector implementing the Harn Connector
Contract v1. Its `payload_schema()` export returns the canonical
`{ harn_schema_name, json_schema }` shape, `normalize_inbound(...)` returns
`NormalizeResult` v1 variants, and `poll_tick(...)` returns Harn-managed
cursor/state updates. It imports `notion-sdk-harn` for outbound API methods.
See the canonical
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
harn add github.com/burin-labs/harn-notion-connector@v0.1.1
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
      page_id: event.payload.resource_id,
      api_token: env("NOTION_TOKEN"),
    })
    println("Updated: ${page.properties.Title.title[0].plain_text}")
  }
}
```

The connector exports the standard Harn Connector interface:
`provider_id()`, `kinds()`, `payload_schema()`, `init(harness, ctx)`,
`activate(harness, bindings)`, `shutdown(harness)`,
`normalize_inbound(harness, raw)`, `call(harness, method, args)`,
`poll_tick(harness, ctx)`, and `method_capabilities()`.

Every runtime export takes the root `Harness` as its first parameter and
attenuates it to the handles it needs. The metadata exports stay pure.

## Supported surface

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
  `resource = "database"` bindings. Each tick emits normalized
  `page.content_updated` events for changed query results.

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
- OAuth token helpers: `oauth.token.create`, `oauth.token.introspect`, and
  `oauth.token.revoke` use Notion OAuth client credentials and keep the target
  token in the request body only for introspection/revocation.
- Artifact helpers: `artifact.export_request` and `artifact.import_request`
  build deterministic descriptors for page metadata export, block-tree export,
  Notion file URL download, page creation, block append, and File Upload API
  import flows. Page-to-PDF export returns `unsupported_pdf_export` because
  Notion's public API does not provide an official page-to-PDF export endpoint.
- `api_call` is an escape hatch for Notion endpoints not yet wrapped by
  `notion-sdk-harn`. Non-GET `api_call` requests require `approved = true`.

Write-capable outbound methods are also exposed through
`method_capabilities()`. Hosts should treat methods marked
`requires_approval = true` as approval-gated operations; the connector does not
auto-edit pages, comments, databases, or task statuses during normalization.

Operational limits:

- Signed webhook normalization requires the exact retained request body. The
  connector prefers `raw.raw_body` when the host supplies it and falls back to
  `raw.body_text`; parsed JSON alone is rejected because HMAC verification must
  use the original request body.
- `normalize_inbound(harness, raw)` is deterministic and does not perform
  network I/O.
- Harn owns webhook routing, poll schedules, leases, retry policy, durable
  cursor/state, and secret storage. This connector validates and normalizes
  inbound payloads, resolves Harn-managed secret IDs passed in binding or
  managed-ingress metadata, dispatches SDK calls, and returns poll results.
- Polling fetches one Notion query page per tick and respects
  `max_batch_size`; capped ticks leave the cursor unchanged for retry-safe
  draining.
- Notion 401/403 and scope/resource-access failures return structured
  `auth_scope_failure` metadata with a recovery hint so hosts can render a
  Connect/Fix path without parsing provider-specific error strings.
- `secrets.api_token`, `verification_token`, and `signing_secret` may be
  literal values or Harn secret IDs. Secret IDs with slash or dotted Harn Cloud
  names are resolved with `secret_get` before use.

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

## Polling fallback

Use a `kind = "poll"` Notion binding when webhooks are unavailable or as a
fallback watcher. Harn owns the schedule, lease, cursor, and connector state;
the connector only reads `ctx.cursor` / `ctx.state` and returns the next
`{ events, cursor, state }`.

```toml
[[triggers]]
id = "notion.poll"
provider = "notion"
kind = "poll"
handler = "on_notion_page_change"

[triggers.poll]
interval = "5m"
jitter = "30s"
state_key = "notion:workspace:tasks"
max_batch_size = 50
resource = "data_source"
data_source_id = "$NOTION_DATA_SOURCE_ID"
high_water_mark = "last_edited_time"
page_size = 50

[triggers.secrets]
api_token = "notion/api-token"
```

`poll.interval` may also be supplied as `interval_ms` or `interval_secs`.
`state_key` can be written as `cursor_state_key`; it chooses the durable Harn
cursor/state slot shared across ticks. The returned poll events use the same
normalized payload shape and dedupe key as webhook-ingested Notion events.

## Configuration

### Required secrets

The connector requires two secrets, and they are independent. The manifest
declares each one's direction of trust, so an installation that needs only one
of the two surfaces stores only that surface's secret:

| Secret | Direction | Needed for |
| --- | --- | --- |
| `notion/api-token` | `outbound` | Outbound API calls and polling |
| `notion/verification-token` | `inbound` | Verifying signed webhook deliveries |

`harn connect status --connector notion --json` reports outbound readiness. An
installation with a valid `notion/api-token` and no verification token is
usable for outbound calls and polling; it simply cannot verify signed webhooks.
Storing a verification token does not substitute for the API token, and the two
are never shared.

#### Inbound: signed webhooks

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

#### Outbound: API calls and polling

For outbound calls and polling, store a Notion internal integration token or
OAuth access token and pass it as `api_token`, `token`, or
`secrets.api_token`. The connector also reads `NOTION_TOKEN` for local
development.

```harn
init(harness, {
  api_token: harness.env.get("NOTION_TOKEN"),
  notion_version: "2026-03-11",
})
```

### Notion capabilities

Grant the minimum Notion capabilities for the methods you call. Most workflows
start with:

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

### Local webhook testing

Use `normalize_inbound(harness, raw)` with the exact retained request body
received by
your HTTP listener. Signature verification is computed over `raw.raw_body` when
present, otherwise `raw.body_text`; parsed JSON alone is intentionally rejected
for signed webhook events.

```harn
let body_text = harness.fs.read_text(
  "tests/fixtures/webhooks/page_content_updated.json",
)
let raw = {
  verification_token: harness.env.get("NOTION_VERIFICATION_TOKEN"),
  body_text: body_text,
  headers: {
    ["x-notion-signature"]: "sha256=...",
    ["request-id"]: "req_local",
  },
}
let result = notion_connector.normalize_inbound(harness, raw)
```

The package also declares `[[connector_contract.fixtures]]` in `harn.toml`.
`harn connector test "$PWD" --provider notion --run-poll-tick` runs those
signed fixtures through the same `normalize_inbound` adapter used by Harn
connector hosts.

## Development

Use the pinned Harn CLI from the install step. Then run the local CI equivalent
from this repo:

```sh
harn install
harn connector test "$PWD" --provider notion --run-poll-tick
```

### Updating the Notion SDK

`harn.toml` pins `notion-sdk-harn` to a tagged release (currently
[`v0.1.0`](https://github.com/burin-labs/notion-sdk-harn/releases/tag/v0.1.0)).
To bump:

```sh
# 1. Edit harn.toml — bump the rev = "vX.Y.Z" pin.
# 2. Refresh the lockfile from the new tag.
harn install --refetch notion-sdk-harn --locked
# 3. Note the bump in CHANGELOG.md (Unreleased section) with the SDK version
#    and the commit SHA the lockfile now records.
```

Never track `branch = "main"` here — every release of the SDK should
correspond to an entry in `burin-labs/harn-cloud/package-index/`, and only
tagged pins reproduce across the team and CI.

## License

Dual-licensed under MIT and Apache-2.0.

- [LICENSE-MIT](./LICENSE-MIT)
- [LICENSE-APACHE](./LICENSE-APACHE)
