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
- **Lightweight Architecture**: No pandas dependency for faster installations and smaller footprint
- **Type Hints**: Full type hint support with strict mypy compliance for better IDE experience
- **Data Processing Utilities**: Helper functions for data transformation and export
- **Unicode-Safe Text Cleaning**: Response cleanup preserves accents and Unicode while removing null bytes and unsafe control characters

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


## Available Report Models

- `MetaAdsReportModel.ad_accounts_report` - Ad account metadata available for the token
- `MetaAdsReportModel.campaigns_report` - Campaign setup, objective, and budget fields
- `MetaAdsReportModel.adsets_report` - Ad set configuration and targeting payloads
- `MetaAdsReportModel.ad_summary_report` - Ad-level metadata and status
- `MetaAdsReportModel.ad_dimensions_report` - Ad dimensions and aggregate context fields
- `MetaAdsReportModel.ad_insights_report` - Ad metrics and actions over time
- `MetaAdsReportModel.ad_performance_report` - Backward-compatible alias of `ad_insights_report`

You can also list models dynamically with `MetaAdsReportModel.list_available_reports()`.

## Custom Reports

Create custom model metadata templates:

```python
from facebook_ads_reports import create_custom_report

custom_report = create_custom_report(
    report_name="my_custom_report",
    select=["ad_id", "impressions", "spend"],
    from_table="ad_insights"
)

# This helper is intended for custom ETL metadata flows.
# For API extraction with get_report(), use a model that contains endpoint/fields/params.
```

## Examples

Check the `examples/` directory for comprehensive usage examples:

- `basic_usage.py` - Simple report extraction


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

Release publishing is automated through GitHub Actions:

- CI workflow: `.github/workflows/test.yml` runs tests and mypy on push/PR to `main`
- Release workflow: `.github/workflows/release.yml` runs on published GitHub Releases (`vX.Y.Z`), updates `pyproject.toml` and `docs/CHANGELOG.md`, builds artifacts, and publishes to PyPI

- Release note: this repository is prepared for the `2.3.0` minor release that updates the Facebook Marketing API to v25 and standardizes report `date_preset` values to `last_3d`.

For release runbook details, see `docs/RELEASE_PIPELINE_SKILL.md`.


## License

GPL License. See [LICENSE](LICENSE) file for details.


## Support

- [Documentation](https://github.com/machado000/facebook-ads-reports#readme)
- [Issues](https://github.com/machado000/facebook-ads-reports/issues)
- [Examples](examples/)


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.