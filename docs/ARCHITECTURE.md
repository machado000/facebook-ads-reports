# Architecture & Internals

Working context for `facebook-ads-reports`. Describes how the package is laid out,
what `get_report()` actually does to a payload, and the behaviors that are easy to
get wrong when extending it.

For the per-model field catalog and output schemas, see [REPORT_FIELDS.md](REPORT_FIELDS.md).

## Module Map

| Module | Responsibility |
| --- | --- |
| `client.py` | `MetaAdsReport` — auth, request building, pagination, flattening, text cleanup |
| `models.py` | `MetaAdsReportModel` — declarative report definitions; `create_custom_report()` |
| `utils.py` | Credential loading, ID validation, date-range splitting, key casing, column-name sanitizing, CSV/JSON export |
| `retry.py` | `@retry_on_api_error` — exponential backoff with jitter on transient failures |
| `exceptions.py` | `MetaAdsReportError` hierarchy (`Authentication`, `Validation`, `API`, `DataProcessing`, `Configuration`) |
| `__init__.py` | Public re-exports (`__all__`) and `setup_logging()` |

There is no persistence layer. Every extraction returns `list[dict[str, Any]]`; loading
into a warehouse is the caller's job. `table_name` / `constraint_column` / `date_column`
in the models are metadata *for* that caller — the package never reads them.

## Token Verification

`MetaAdsReport.verify_token(required_scopes=None)` inspects the configured token via
`/debug_token` and raises `AuthenticationError` on an invalid, expired, or under-scoped
token. Call it once at startup so credential problems fail fast instead of surfacing as an
opaque 401 mid-extraction.

It authenticates the debug call with an app access token (`{app_id}|{app_secret}`) when
both are present in the credentials — the only two consumers of those keys — and otherwise
falls back to self-inspection, which requires the token holder to have a role on the app.

Returns `is_valid`, `type`, `app_id`, `application`, `user_id`, `expires_at`,
`never_expires`, `data_access_expires_at`, `scopes`, `granular_scopes`, `missing_scopes`.
A system user token reports `type: SYSTEM_USER` and `never_expires: True`.

## Request Pipeline

`MetaAdsReport.get_report(ad_account_id, report_model, start_date, end_date, flatten, limit)`

1. **Model unpack** — `report_name`, `endpoint`, `fields`, `params`. `params` is shallow-copied
   so the class-level dicts are never mutated across calls.
2. **Account resolution** — `ad_accounts_report` overrides the account to `me` (lists every
   account the token can see). All other models run `validate_account_id()`, which normalizes
   `1234567890` → `act_1234567890` and rejects anything outside 8–16 digits.
3. **Date handling** — only `ad_insights_report` gets an explicit `time_range`
   (`{"since": ..., "until": ...}`). Every other model relies on the `date_preset` baked
   into its `params`.
4. **URL assembly** — `{base_url}/{account_id}/{endpoint}`, fields joined comma-separated,
   `time_range` / `action_breakdowns` / `breakdowns` JSON-encoded, `limit` appended.
   Auth travels as `Authorization: Bearer <access_token>`.
5. **Pagination** — follows `paging.next` until absent, accumulating `data`. Non-200 goes to
   `_raise_for_error_response()`, which raises a typed `APIError` / `AuthenticationError`
   (see [Error Handling and Retries](#error-handling-and-retries)).
6. **Key casing** — `convert_keys_case(..., "snake")` over the raw rows.
7. **Flattening** — `_flatten_facebook_ads_response()` when `flatten=True`, passing the
   model's optional `action_types` allow-list (see below).
8. **Text cleanup** — `_clean_text_encoding()`: NFC-normalize, drop control characters
   (keeping `\t`, `\n`, `\r`), strip NULs, trim. Accents and Unicode are preserved.

### API version

Pinned in code: `MetaAdsReport.__init__` hardcodes `self.api_version = "v25.0"`. The
`base_url` key in the credentials file is **not** read — only `access_token` is.

## Flattening Rules

`flatten=True` rewrites nested structures into top-level columns. Four distinct rules apply:

| Source | Rule | Resulting column |
| --- | --- | --- |
| the `ACTION_COLUMN_PREFIXES` families | each `{action_type, value}` becomes its own column, named `sanitize_column_name(f"{prefix}{action_type}")`, subject to the model's `action_types` allow-list | `omni_purchase`, `value_omni_purchase`, `roas_omni_purchase`, … |
| `video_play_actions`, `video_p25/p50/p75/p100_watched_actions` | first list item's `value`, `_actions` suffix stripped | `video_play`, `video_p25_watched`, … |
| `targeting` | recursive key search over 26 known nested fields, hoisted **without prefix** | `genders`, `age_min`, `countries`, `interests`, … |
| `learning_stage_info` | recursive key search over 4 known fields, hoisted **with prefix** | `learning_stage_info_status`, `learning_stage_info_conversions`, … |

`ACTION_COLUMN_PREFIXES` (module-level in `client.py`) maps each action-shaped field to
its column prefix. `actions` maps to `""` for backward compatibility; every other family
carries a prefix so that value-bearing metrics do not overwrite the action counts that
share the same `action_type`:

| Field | Prefix | Example column |
| --- | --- | --- |
| `actions` | *(none)* | `purchase` |
| `action_values` | `value_` | `value_purchase` |
| `conversions` | `conversion_` | `conversion_purchase` |
| `conversion_values` | `conversion_value_` | `conversion_value_purchase` |
| `converted_product_quantity` | `converted_product_quantity_` | `converted_product_quantity_purchase` |
| `converted_product_value` | `converted_product_value_` | `converted_product_value_purchase` |
| `purchase_roas` | `roas_` | `roas_omni_purchase` |
| `website_purchase_roas` | `website_roas_` | `website_roas_offsite_conversion_fb_pixel_purchase` |
| `cost_per_action_type` | `cost_per_` | `cost_per_purchase` |

A field only produces columns when the model requests it; the map is a superset of what
any built-in model asks for. Entries lacking an `action_type` key are skipped rather than
raising.

The recursive helpers (`_collect_values_by_key` → `_normalize_extracted_values`) return a
scalar when exactly one match is found and a list when several are — so a given column's
Python type varies row to row.

### Column-name sanitizing

Ordering matters: `convert_keys_case()` runs *before* flattening and only touches top-level
row keys, so action-derived names are **never** snake_cased. Meta's `action_type` values are
free-form and routinely contain dots — `offsite_conversion.fb_pixel_purchase`,
`onsite_conversion.messaging_conversation_started_7d`.

`sanitize_column_name()` (in `utils.py`, re-exported from the package root) folds every
character outside `[0-9A-Za-z_]` to an underscore and prefixes a leading digit, so those
become `offsite_conversion_fb_pixel_purchase` and
`onsite_conversion_messaging_conversation_started_7d`. Names that are already valid
identifiers pass through untouched, so column names do not churn between runs.

Verified against a live 102-column extract: 19 names rewritten, 83 unchanged, zero
collisions. Callers that need to predict a column name should call the same function rather
than reimplement the rule.

### The `action_types` allow-list

A model may declare `action_types`, an allow-list applied to every
`ACTION_COLUMN_PREFIXES` family after the API responds. Matching is on the **raw**
`action_type`, before the prefix and before sanitizing, so a single entry controls the
count, value and ROAS columns derived from it — `omni_purchase` yields `omni_purchase`,
`value_omni_purchase` and `roas_omni_purchase` together.

An empty list or a missing key means no filtering. Only `ad_insights_report` declares one
today; every other model is unaffected.

The shipped list keeps `omni_*` as the conversion spine. Meta reports the same conversion
under several overlapping scopes — `offsite_conversion.*` (pixel/CAPI only),
`onsite_conversion.*` (inside Meta's own apps), `onsite_web_*` / `web_in_store_*` /
`web_app_in_store_*` (partial channel rollups), and `omni_*` (deduplicated across web, app,
offline and Shops). On an account with a single conversion surface every scope collapses to
the same number: in a live 650-row extract, eight purchase columns and six purchase-value
columns were identical row-for-row. Filtering to `omni_*` took that extract from 102 columns
to 48. The excluded families stay in `models.py` as commented blocks.

Video columns take a different code path (`_flatten_video_play_action`) and are not filtered.

## Error Handling and Retries

A non-200 response never becomes a bare `Exception`. `_raise_for_error_response()` parses
the Graph error payload and raises one of two typed errors, both carrying structured
`context` (`status_code`, `error_code`, `error_subcode`, `is_transient`, `is_rate_limit`,
`retry_after`, `fbtrace_id`, `throttle`, `report_name`):

- `AuthenticationError` for token problems — codes `102, 190, 200, 10, 2500` or HTTP 401.
  Never retried; credentials do not fix themselves.
- `APIError` for everything else.

`@retry_on_api_error` then catches **both** `APIError` and `RequestException`. An `APIError`
is retried when the payload says `is_transient`, when it is a known throttling code
(`4, 17, 32, 613, 800xx`), when the status is `429/500/502/503/504`, or when the code is
`1`/`2` ("API Unknown"/"API Service", documented as temporary).

Delay selection, in precedence order:

1. A `Retry-After` header, if the server sent one.
2. `rate_limit_delay` (default 60s) as a floor for throttling errors — a few seconds of
   backoff against an app-level limit just burns more quota.
3. Otherwise exponential backoff: `base_delay * backoff_factor ** attempt`, capped at
   `max_delay`, with jitter.

When attempts are exhausted, the raised `APIError` inherits the last error's context, so
the final exception is self-describing without unwrapping `original_error`.

This matters because the pre-fix behavior was the opposite of what the docstrings implied:
`requests` does not raise on 4xx/5xx, so every API error fell through to a generic
`except Exception` and was re-raised un-retried. A transient `code: 4` throttle killed a
six-model extraction on its first attempt.

## Sharp Edges

These are current behaviors, verified against the source and the sample extracts in
`reports_output/`. Treat them as known constraints rather than mysteries.

- **Insights output has a variable schema, now bounded.** Action columns only exist when
  that action occurred in the window, so consecutive days of `ad_insights_report` produce
  different column sets — two sample extracts one day apart differ by several
  `onsite_conversion.*` columns. The `action_types` allow-list caps the *universe* of
  possible columns, but not which of them appear on a given run: a loader still sees a
  subset that varies day to day, and **absent is not zero**. A fixed `CREATE TABLE` built
  from the allow-list is now safe; assuming every column is present on every run is not.
- **`flatten=False` skips snake_casing.** The `else` branch returns the pre-casing
  `response_data`, not `response_data_snake_case`. In practice the Graph API already
  returns snake_case keys, so no difference has been observed in real payloads — the
  casing pass is defensive and the gap is latent rather than active.
- **`ad_insights_report` requires dates.** `time_range` is set unconditionally for that
  model; passing `start_date=None` sends `{"since": null, "until": null}` alongside the
  leftover `date_preset`, which the API will reject.
- **Page totals are always unknown.** `summary=true` is never requested, so
  `response_json['summary']['total_count']` is absent and progress logs cannot show a
  denominator.
- **Pagination re-sends params.** The `paging.next` URL already carries the full query
  string, and `query_params` is passed again on each iteration, duplicating parameters.
- **`sort` is likely inert.** The Marketing API expects insights sort keys in
  `<field>_ascending` / `<field>_descending` form, and the object endpoints
  (`campaigns`, `adsets`, `ads`) do not accept `sort` at all.
- **`create_custom_report()` is not usable with `get_report()`.** It emits SQL-shaped
  metadata (`select` / `from` / `where`) with no `endpoint`, `fields`, or `params`, so
  `get_report()` raises `KeyError`. It exists for external ETL metadata flows.
- **`action_video_type` detail is lost.** `action_breakdowns` includes
  `action_video_type`, so the API can return several entries sharing one `action_type`.
  `_flatten_action_list()` keys only on `action_type`, so all but the last are dropped.
- **`action_types` filters client-side, not at the API.** The allow-list is applied after
  the response arrives, so it reduces output columns but not payload size or quota cost.
  Meta's `filtering` parameter can filter `action_type` server-side; the package does not
  use it, because it also affects sibling metrics in ways that are hard to predict.
- **Targeting fields are unprefixed.** `genders`, `countries`, `status`-adjacent keys and
  friends land at top level, so a future top-level API field of the same name would collide.

## Development

```bash
uv sync --all-groups
uv run pytest                      # no tests/ directory exists yet
uv run mypy facebook_ads_reports   # strict: disallow_untyped_defs, warn_return_any
uv build
```

`mypy` is configured strictly in `pyproject.toml` and is the effective quality gate —
there is currently no test suite, and CI treats pytest exit code 5 (no tests collected)
as success.

## CI/CD Reality

`.github/workflows/release.yml` ("Build and Publish") is the **only** workflow. It runs on
every push to `main`: a 3.11–3.14 pytest matrix, then a `release`-environment job that
builds, checks PyPI for the version already existing, and publishes with `PYPI_TOKEN`
when it does not.

Consequence: **releasing is a `pyproject.toml` version bump merged to `main`** — not a
GitHub Release. `docs/RELEASE_PIPELINE_SKILL.md` describes a `test.yml` + release-triggered
design that does not match the workflow on disk.

## API Access Tier

Responses carry `x-ad-account-usage` and `x-fb-ads-insights-throttle` headers reporting
`ads_api_access_tier`. An app on **`development_access`** has substantially lower rate
limits and will hit `code: 4, "Application request limit reached"` after a handful of
full-history extractions. Running all six models back to back is enough to trip it.

Request **Advanced Access** for `ads_read` via App Review before relying on this in
production, and stagger large backfills.

## Credentials

`load_credentials()` searches, in order: an explicit path, then
`secrets/fb_business_config.json`, `~/.fb_business_config.json`, `./fb_business_config.json`.
`examples/basic_usage.py` prefers the `FACEBOOK_ADS_CONFIG_JSON` environment variable and
falls back to the file. `secrets/`, `.env`, and `reports_output/` are all gitignored.
