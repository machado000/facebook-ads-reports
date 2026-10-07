# Facebook Ads Reports Helper

A Python ETL driver for Facebook Marketing API v25 data extraction and transformation. Simplifies the process of extracting Facebook Ads data and converting it to structured data formats with comprehensive utility functions.

[![PyPI version](https://img.shields.io/pypi/v/facebook-ads-reports)](https://pypi.org/project/facebook-ads-reports/)
[![Last Commit](https://img.shields.io/github/last-commit/machado000/facebook-ads-reports)](https://github.com/machado000/facebook-ads-reports/commits/main)
[![Issues](https://img.shields.io/github/issues/machado000/facebook-ads-reports)](https://github.com/machado000/facebook-ads-reports/issues)
[![License](https://img.shields.io/badge/License-GPL-yellow.svg)](https://github.com/machado000/facebook-ads-reports/blob/main/LICENSE)

## Features

- **Facebook Marketing API v25**: Latest API version support with full compatibility
- **Robust Error Handling**: Comprehensive error handling with retry logic and specific exceptions
- **Multiple Report Types**: Pre-configured report models for common use cases
- **Custom Reports**: Create custom report configurations
- **Flexible Data Export**: Built-in CSV and JSON export utilities
- **Date Range Utilities**: Helper functions to break date ranges into monthly or weekly periods
- **Lightweight Architecture**: No pandas dependency for faster installations and smaller footprint
- **Type Hints**: Full type hint support with strict mypy compliance for better IDE experience
- **Data Processing Utilities**: Helper functions for data transformation and export
- **Pixel Stats**: `get_pixel_stats()` / `get_pixel_event_hosts()` read the pixel's own event counts, including events Insights never attributes to an ad
- **Token Verification**: `verify_token()` reports validity, type, expiry, and scopes via `/debug_token`
- **Unicode-Safe Text Cleaning**: Response cleanup preserves accents and Unicode while removing null bytes and unsafe control characters
- **Warehouse-Safe Column Names**: Flattened action columns are sanitized to valid identifiers, so `offsite_conversion.fb_pixel_purchase` lands as `offsite_conversion_fb_pixel_purchase`
- **Conversion-Scope Filtering**: `ad_insights_report` ships an `action_types` allow-list keeping Meta's deduplicated `omni_*` metrics and dropping the overlapping attribution scopes that duplicate them

## Installation

```bash
pip install facebook-ads-reports
```

Using uv:

```bash
uv add facebook-ads-reports
```

## Quick Start

### 1. Set up credentials

**Option A: Configuration file**

Create a `secrets/fb_business_config.json` file with your Facebook Ads API credentials:

```json
{
  "app_id": "YOUR_APP_ID",
  "app_secret": "YOUR_APP_SECRET",
  "access_token": "YOUR_ACCESS_TOKEN",
  "ad_account_id": "act_1234567890",
  "base_url": "https://graph.facebook.com/v25.0"
}
```

`access_token` is required. `app_id` and `app_secret` are optional but recommended --
`verify_token()` uses them to authenticate its `/debug_token` call. `base_url` is ignored;
the API version is pinned to v25.0 in the client.

For unattended extraction, use a **Business Manager system user token** rather than a Graph
API Explorer token: user tokens are invalidated by password changes and expire in ~60 days,
and this package has no token-refresh logic. `verify_token()` reports `type: SYSTEM_USER`
and `never_expires: True` for a correctly issued one.

**Option B: Environment variable**

Set the `FACEBOOK_ADS_CONFIG_JSON` environment variable with your credentials as JSON:

```bash
export FACEBOOK_ADS_CONFIG_JSON='{"app_id": "YOUR_APP_ID", "app_secret": "YOUR_APP_SECRET", "access_token": "YOUR_ACCESS_TOKEN", "ad_account_id": "act_1234567890", "base_url": "https://graph.facebook.com/v25.0"}'
```

### 2. Basic usage

```python
from datetime import date, timedelta
from facebook_ads_reports import MetaAdsReport, MetaAdsReportModel
from facebook_ads_reports.utils import load_credentials, save_report_to_csv, save_report_to_json

# Load credentials
credentials = load_credentials()
client = MetaAdsReport(credentials_dict=credentials)

# Fail fast on a bad token instead of hitting an opaque 401 mid-extraction
client.verify_token(required_scopes=["ads_read"])

# Configure report parameters
ad_account_id = "act_1234567890"
start_date = date.today() - timedelta(days=7)
end_date = date.today() - timedelta(days=1)

# Extract report data
data = client.get_report(
  ad_account_id=ad_account_id,
  report_model=MetaAdsReportModel.ad_insights_report,
  start_date=start_date,
  end_date=end_date,
  flatten=True,
  limit=200,
)

# Save to CSV using utility function
save_report_to_csv(data, "ad_insights_report.csv")

# Save to JSON using utility function
save_report_to_json(data, "ad_insights_report.json")
```

With `flatten=True`, `ad_insights_report` expands each `action_type` into its own column.
The `action_types` allow-list in the model caps which columns are possible -- 48 on a live
extract, down from 102 unfiltered -- but a column still only appears when that action
occurred in the window, so **absent is not zero** and loaders must tolerate missing keys.
See [docs/REPORT_FIELDS.md](docs/REPORT_FIELDS.md#the-variable-schema-problem).

Conversion columns use Meta's deduplicated `omni_*` family (`omni_purchase`,
`value_omni_purchase`, `roas_omni_purchase`). The overlapping `offsite_conversion.*`,
`onsite_web_*` and legacy bare scopes are commented out in `models.py` -- uncomment a block
to restore them. See
[docs/REPORT_FIELDS.md](docs/REPORT_FIELDS.md#the-conversion-scope-allow-list).


## Available Report Models

| Model | Returns | Grain (one row per) |
| --- | --- | --- |
| `ad_accounts_report` | Account metadata for every account the token can reach | ad account |
| `campaigns_report` | Campaign setup, objective, budget | campaign |
| `adsets_report` | Ad set config, targeting, learning stage | ad set |
| `ad_summary_report` | Ad metadata, status, targeting | ad |
| `ad_dimensions_report` | Ad attributes with no metrics | ad |
| `ad_images_report` | Image assets, including the only permanent creative URL | image asset |
| `ad_insights_report` | Metrics and actions over time | ad x day x publisher platform x platform position |
| `ad_performance_report` | Backward-compatible alias of `ad_insights_report` | same as above |

Only `ad_insights_report` uses `start_date` / `end_date`; the other models rely on the
`date_preset` in their own params and ignore the dates you pass. `ad_accounts_report`
ignores `ad_account_id` as well, and `ad_images_report` declares no `date_preset` at all.

You can also list models dynamically with `MetaAdsReportModel.list_available_reports()`.

Full field lists, flattening behavior, and output schemas: [docs/REPORT_FIELDS.md](docs/REPORT_FIELDS.md).

## Pixel Stats

Insights returns only the conversions Meta credited to an ad. To count everything a pixel
received (organic, direct and paid alike) read the pixel's `stats` edge:

```python
from facebook_ads_reports import MetaAdsReport

client = MetaAdsReport(credentials)

# Event totals per hour. end_date is inclusive.
rows = client.get_pixel_stats("2082629071758453", "2026-09-07", "2026-10-04", aggregation="event")
# {'pixel_id': ..., 'start_time': '2026-10-01T00:00:00-0300', 'date': '2026-10-01',
#  'hour': 0, 'aggregation': 'event', 'value': 'testride_sucesso', 'count': 3}

# Events crossed with hostname (one request per event).
rows = client.get_pixel_event_hosts("2082629071758453", "2026-09-07", "2026-10-04",
                                    events=["testride_sucesso"], sleep_seconds=15)
# {'pixel_id': ..., 'date': '2026-10-01', 'hour': 0, 'event': 'testride_sucesso',
#  'host': 'www.tripleducati.com.br', 'count': 3}
```

Requirements and caveats (runnable version: [examples/pixel_stats.py](examples/pixel_stats.py)):

- The token's user needs access to the pixel **and** `ads_management`; `ads_read` alone is
  rejected with `(#100) Permission Denied`.
- Failures are handled like `get_report()`: rate limits and transient errors are retried with
  backoff, token errors raise `AuthenticationError`, permission errors raise `APIError`.
- `get_pixel_event_hosts()` costs `1 + number_of_events` requests; pass `events=[...]` to skip
  discovery and `sleep_seconds` to space them out.
- Dates are calendar days in the pixel owner's time zone, read from its owner ad account
  (pass `timezone="America/Sao_Paulo"` to override or when the pixel has no owner account).
  This is the same rule Insights follows with the ad account's time zone. The raw edge reads
  date-only values as UTC, so the client sends local midnight with its offset.
- Buckets are hourly. `date` and `hour` come from the `start_time` string as given, so they
  are local to that same time zone.
- No campaign or ad dimension, and the counts already **include** ad-attributed events.
  Do not add them to Insights conversions.

## Custom Reports

Create custom model metadata templates:

```python
from facebook_ads_reports import create_custom_report

custom_report = create_custom_report(
    report_name="my_custom_report",
    select=["ad_id", "impressions", "spend"],
    from_table="ad_insights"
)

# This helper is intended for custom ETL metadata flows and CANNOT be passed to
# get_report() -- it has no endpoint/fields/params. To define a real custom extraction,
# build a dict in the same shape as the built-in models. See docs/REPORT_FIELDS.md.
```

## Examples

Check the `examples/` directory for comprehensive usage examples:

- `basic_usage.py` - Simple report extraction
- `pixel_stats.py` - Pixel event counts by hour and by hostname, with a daily summary and CSV export


## Requirements

- Python 3.11-3.14
- requests >= 2.32.4
- python-dotenv >= 1.1.1

## Development & Publishing

```bash
# install runtime + dev dependencies
uv sync --all-groups

# quality gates
uv run pytest
uv run mypy facebook_ads_reports

# local build check
uv build
```

`tests/` currently covers the pixel stats methods; `mypy` remains the main quality gate.

Publishing is automated through `.github/workflows/release.yml`, which runs on every push
to `main`: a Python 3.11-3.14 test matrix, then a build-and-publish job that skips PyPI if
the version in `pyproject.toml` already exists. In practice, **releasing is a version bump
merged to `main`**.

For internals and known behaviors, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
For the release runbook, see [docs/RELEASE_PIPELINE_SKILL.md](docs/RELEASE_PIPELINE_SKILL.md)
(note: it documents a release-triggered design that does not match the current workflow).


## License

GPL License. See [LICENSE](LICENSE) file for details.


## Support

- [Architecture & internals](docs/ARCHITECTURE.md)
- [Report field reference](docs/REPORT_FIELDS.md)
- [Changelog](docs/CHANGELOG.md) | [Roadmap](docs/ROADMAP.md)
- [Issues](https://github.com/machado000/facebook-ads-reports/issues)
- [Examples](examples/)


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.