# Report Field Reference

Catalog of every built-in model in `MetaAdsReportModel`: what it requests, what grain it
returns, and what the output columns actually look like after flattening.

Observed column counts below come from live extractions against account
`act_701445397317988` with `flatten=True`. Counts for `targeting`-expanding models drift
with what is actually configured on the account — `adsets_report` returned 41 columns in
one run and 42 in another — so treat them as indicative, not fixed.

Mechanics behind the transformations are in [ARCHITECTURE.md](ARCHITECTURE.md).

## At a Glance

| Model | Endpoint | Grain (one row per) | Fields requested | Columns out |
| --- | --- | --- | --- | --- |
| `ad_accounts_report` | `adaccounts` | ad account visible to the token | 18 | 18 |
| `campaigns_report` | `campaigns` | campaign | 19 | 17 |
| `adsets_report` | `adsets` | ad set | 16 | 41-42 |
| `ad_summary_report` | `ads` | ad | 13 | 36 |
| `ad_dimensions_report` | `insights` | ad | 12 | 14 |
| `ad_insights_report` | `insights` | ad × day × publisher platform × platform position | 27 | ~48, varies |

`ad_performance_report` is the same object as `ad_insights_report` (`is`-identical alias),
so it carries `report_name == "ad_insights_report"` and behaves identically.

## Object Models

These read entity configuration, not performance. They ignore `start_date` / `end_date`
and use the `date_preset` in their params.

### `ad_accounts_report`

Account is forced to `me`, so this returns every account the token can reach — the natural
first call for discovering `ad_account_id` values.

`id`, `account_id`, `name`, `business`, `tax_id`, `account_status`, `age`, `disable_reason`,
`created_time`, `timezone_id`, `timezone_name`, `currency`, `is_prepay_account`,
`spend_cap`, `balance`, `amount_spent`, `min_campaign_group_spend_cap`, `capabilities`

Metadata: `meta_ads_adaccounts`, keyed on `account_id`. No `date_preset`.

### `campaigns_report` — `date_preset: maximum`

Identity: `account_id`, `account_name`, `id`, `name`
Setup: `buying_type`, `objective`, `bid_strategy`, `boosted_object_id`
Status: `configured_status`, `effective_status`, `status`
Budget: `daily_budget`, `budget_remaining`, `lifetime_budget`, `spend_cap`
Timestamps: `start_time`, `stop_time`, `created_time`, `updated_time`

Metadata: `meta_ads_campaigns`, keyed on `(account_id, id)`.

Note: the sample extract returns 17 of the 19 requested fields — `account_name` and
`spend_cap` are absent. Meta omits fields that are unset or unsupported on the edge rather
than returning nulls, so **requested ≠ returned** and downstream schemas must tolerate
missing keys.

### `adsets_report` — `date_preset: maximum`

Requested: `account_id`, `campaign_id`, `id`, `name`, `status`, `billing_event`,
`daily_budget`, `budget_remaining`, `lifetime_budget`, `start_time`, `end_time`,
`created_time`, `updated_time`, `targeting`, `learning_stage_info`, `recommendations`

`targeting` and `learning_stage_info` are objects that flattening expands, which is why 16
requested fields become 41 columns:

- From `targeting`, **unprefixed**: `genders`, `age_min`, `age_max`, `user_age_unknown`,
  `user_device`, `user_os`, `device_platforms`, `publisher_platforms`,
  `facebook_positions`, `instagram_positions`, `messenger_positions`, `threads_positions`,
  `whatsapp_positions`, `custom_audiences`, `interests`, `behaviors`, and the geo keys
  `location_types`, `countries`, `regions`, `cities`, `subcities`, `neighborhoods`,
  `places`, `custom_locations`
- From `learning_stage_info`, **prefixed**: `learning_stage_info_status`,
  `learning_stage_info_conversions`, `learning_stage_info_attribution_windows`,
  `learning_stage_info_last_sig_edit_ts`
- `recommendations` is left as a raw JSON blob

Metadata: `meta_ads_adsets`, keyed on `id`.

### `ad_summary_report` — `date_preset: maximum`

Requested: `account_id`, `campaign_id`, `adset_id`, `id`, `name`, `bid_type`,
`configured_status`, `effective_status`, `status`, `created_time`, `updated_time`,
`targeting`, `recommendations`

Same `targeting` expansion as ad sets (13 → 36 columns). Note the sample extract has no
`name` collision issue but does carry ad-level `targeting` inherited from the ad set.

Metadata: `meta_ads_adsummary`, keyed on `id`.

## Insights Models

Both hit the `insights` edge at `level: ad`.

### `ad_dimensions_report` — `date_preset: maximum`, no `time_increment`

Slowly-changing ad attributes with no metrics and no breakdowns, so it collapses to one row
per ad. Useful as a dimension table joined to the fact table by `ad_id`.

`ad_id`, `adset_id`, `campaign_id`, `account_id`, `ad_name`, `adset_name`, `campaign_name`,
`account_name`, `buying_type`, `attribution_setting`, `objective`, `optimization_goal`

The insights edge always appends `date_start` and `date_stop`, so output is 14 columns, not
12. With `maximum` they span the account's full history.

Metadata: `meta_ads_addimensions`, keyed on `ad_id`.

### `ad_insights_report` — the fact table

Params: `level: ad`, `time_increment: 1`, `date_preset: last_3d` (always overridden by
`time_range` when the model is used), `action_breakdowns: [action_type, action_video_type]`,
`breakdowns: [publisher_platform, platform_position]`.

`time_increment: 1` plus the two breakdowns set the grain:
**ad × day × publisher_platform × platform_position**.

Requested fields:

- Identity — `account_id`, `campaign_id`, `adset_id`, `ad_id`
- Names — `account_name`, `campaign_name`, `adset_name`, `ad_name`
- Attributes — `buying_type`, `objective`, `optimization_goal`
- Metrics — `spend`, `impressions`, `clicks`, `reach`, `frequency`
- Nested counts — `actions`
- Nested revenue — `action_values`, `conversion_values`, `purchase_roas`
- Nested video — `video_play_actions`, `video_p25/p50/p75/p100_watched_actions`
- Dates — `date_start`, `date_stop`
- Implicit from breakdowns — `publisher_platform`, `platform_position`

Metadata: `meta_ads_adinsights`, `date_column: date_start`, `constraint_column:
["account_id", "ad_id", "date_start", "publisher_platform", "platform_position"]` — the
composite key implied by `time_increment: 1` plus the two breakdowns, with `account_id`
carried so a single table can hold multiple accounts. Verified twice: 1,258 rows across
the stored sample extracts, and 664 rows from a live single-day pull spanning multiple
publisher platforms — zero duplicate keys, zero null key parts in both.

#### Revenue columns

`actions` gives conversion *counts*; the value-bearing fields give the money. Because all
of them key on the same `action_type`, each family is written under its own prefix (see
[ARCHITECTURE.md](ARCHITECTURE.md#flattening-rules)):

| Column | Source | Meaning |
| --- | --- | --- |
| `omni_purchase` | `actions` | number of purchases, deduplicated across channels |
| `value_omni_purchase` | `action_values` | purchase revenue |
| `conversion_value_omni_purchase` | `conversion_values` | conversion value under the account's attribution setting |
| `roas_omni_purchase` | `purchase_roas` | return on ad spend, as reported by Meta |

Before v2.4.0 these were `purchase` / `value_purchase` — see
[the conversion-scope allow-list](#the-conversion-scope-allow-list) for why the `omni_*`
names are now the default.

ROAS is also derivable as `value_omni_purchase / spend`. On a live row these agree exactly
(`3651.30 / 438.538508 = 8.326065`, matching the reported `roas_omni_purchase` to six
decimal places), but the reported column reflects Meta's own attribution and is the safer
figure to trust.

Coverage is sparse by nature — in a live 664-row day, `actions` appeared on 375 rows,
`action_values` on 207, and `purchase_roas` on 17. Rows without a conversion simply omit
those keys, so **absent is not zero**.

**`conversion_values` is account-dependent.** The API accepts the field and returns no
error, but it only populates for accounts with custom conversions configured; on an account
using standard pixel events it yields nothing (0 of 664 rows in the live test — those
conversions surface through `actions` / `action_values` instead). It is kept in the model
because it costs nothing when empty and populates automatically for accounts that do use
custom conversions.

`conversions` (counts, prefix `conversion_`) is handled by the flattener but not requested
by the model — add the field name to `fields` if you need it.

#### The conversion-scope allow-list

Meta reports the same conversion under several overlapping `action_type` scopes:

| Scope | Counts | Example |
| --- | --- | --- |
| `offsite_conversion.*` | pixel / CAPI only, on the advertiser's own property | `offsite_conversion.fb_pixel_purchase` |
| `onsite_conversion.*` | actions inside Facebook / Instagram / Messenger / WhatsApp | `onsite_conversion.messaging_conversation_started_7d` |
| `onsite_web_*`, `web_in_store_*`, `web_app_in_store_*` | partial channel rollups | `onsite_web_purchase` |
| `omni_*` | deduplicated total across web, app, offline and Shops | `omni_purchase` |
| *bare* | legacy aggregate | `purchase` |

On an account with a single conversion surface these are **identical row-for-row**. In a
live 650-row extract, eight purchase-count columns and six purchase-value columns all
reported the same 24 purchases and the same R$41,655.46. They diverge only when an app,
offline uploads, or Shops checkout are in play — the gap between `omni_purchase` and
`offsite_conversion.fb_pixel_purchase` is exactly what the pixel cannot see.

`ad_insights_report` therefore ships an `action_types` allow-list keeping `omni_*` as the
conversion spine plus the engagement and video metrics that have no omni equivalent.
That takes the extract from **102 columns to 48**. The excluded families
stay in `models.py` as labelled commented blocks — uncomment `offsite_conversion.*` to
measure pixel coverage as `omni_purchase - offsite_conversion.fb_pixel_purchase`.

One entry is deliberately not `omni_*`: `add_payment_info`, because Meta reports no
`omni_add_payment_info` for that event — only the bare name and the pixel variant.

`onsite_conversion.messaging_conversation_started_7d` is present in `models.py` but
commented out. Unlike the other excluded scopes it duplicates nothing — messaging happens
only inside Meta's apps and has no omni equivalent — so uncomment it if the account runs
click-to-message campaigns.

#### The variable-schema problem

The allow-list caps the *universe* of columns, not which appear on a given run. `actions`
still only produces a column when that action occurred in the window. Two sample extracts
one day apart:

- `2026-04-06` carried `onsite_conversion.messaging_conversation_replied_7d`,
  `onsite_conversion.post_unsave`, `onsite_conversion.messaging_user_depth_3_message_send`
- `2026-04-08` carried `onsite_conversion.messaging_first_reply` instead, and dropped those

A fixed `CREATE TABLE` built from the allow-list is safe. Assuming every column is present
on every row is not — **absent is not zero**.

Column names are sanitized before they reach the output, so the dotted `action_type` values
arrive as valid identifiers: `offsite_conversion.fb_pixel_purchase` becomes
`offsite_conversion_fb_pixel_purchase`. See
[ARCHITECTURE.md](ARCHITECTURE.md#column-name-sanitizing).

#### Metrics not currently requested

Worth knowing before the next model revision — none of these are in the model today:

- Efficiency — `cpc`, `cpm`, `ctr`, `cpp`, `cost_per_action_type`, `cost_per_unique_click`
- Revenue — `website_purchase_roas` (`action_values`, `conversion_values`, and
  `purchase_roas` are now requested)
- Conversions — `conversions` (counts). The flattener handles it; the model does not ask.
- Engagement/quality — `inline_link_clicks`, `unique_clicks`, `unique_ctr`,
  `quality_ranking`, `engagement_rate_ranking`, `conversion_rate_ranking`
- Creative — `ad_creative_id` / creative asset fields (would need the `adcreatives` edge)

## Custom Reports

`create_custom_report()` produces SQL-shaped metadata (`report_name`, `select`, `from`,
`date_column`, optional `where` / `order_by` / `table_name`). It has no `endpoint`,
`fields`, or `params`, so it **cannot** be passed to `get_report()` — that raises `KeyError`.

To define a real custom extraction, build the dict in the built-in models' shape:

```python
my_report = {
    "report_name": "my_insights_report",   # not "ad_insights_report" → no time_range injected
    "endpoint": "insights",
    "fields": ["ad_id", "spend", "impressions", "actions", "date_start", "date_stop"],
    "params": {
        "level": "ad",
        "date_preset": "last_7d",
        "time_increment": 1,
        "filtering": [],
    },
    # optional: omit or leave empty to keep every action type
    "action_types": ["omni_purchase", "link_click"],
}
```

Only `report_name == "ad_insights_report"` triggers `time_range` injection from
`start_date` / `end_date`. Any other name falls back to the model's `date_preset`.
