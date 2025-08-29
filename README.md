# Facebook Ads Reports Helper

A Python ETL driver for Facebook Marketing API v23 data extraction and transformation. Simplifies the process of extracting Facebook Ads data and converting it to structured data formats with comprehensive utility functions.

[![PyPI version](https://img.shields.io/pypi/v/facebook-ads-reports)](https://pypi.org/project/facebook-ads-reports/)
[![Last Commit](https://img.shields.io/github/last-commit/machado000/facebook-ads-reports)](https://github.com/machado000/facebook-ads-reports/commits/main)
[![Issues](https://img.shields.io/github/issues/machado000/facebook-ads-reports)](https://github.com/machado000/facebook-ads-reports/issues)
[![License](https://img.shields.io/badge/License-GPL-yellow.svg)](https://github.com/machado000/facebook-ads-reports/blob/main/LICENSE)

## Features

- **Facebook Marketing API v23**: Latest API version support with full compatibility
- **Robust Error Handling**: Comprehensive error handling with retry logic and specific exceptions
- **Multiple Report Types**: Pre-configured report models for common use cases
- **Custom Reports**: Create custom report configurations
- **Flexible Data Export**: Built-in CSV and JSON export utilities
- **Lightweight Architecture**: No pandas dependency for faster installations and smaller footprint
- **Type Hints**: Full type hint support with strict mypy compliance for better IDE experience
- **Data Processing Utilities**: Helper functions for data transformation and export

## Installation

```bash
pip install facebook-ads-reports
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
  "base_url": "https://graph.facebook.com/v23.0"
}
```

**Option B: Environment variable**

Set the `FACEBOOK_ADS_CONFIG_JSON` environment variable with your credentials as JSON:

```bash
export FACEBOOK_ADS_CONFIG_JSON='{"app_id": "YOUR_APP_ID", "app_secret": "YOUR_APP_SECRET", "access_token": "YOUR_ACCESS_TOKEN", "ad_account_id": "act_1234567890", "base_url": "https://graph.facebook.com/v23.0"}'
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
data = client.get_insights_report(
        ad_account_id=ad_account_id,
        report_model=MetaAdsReportModel.ad_performance_report,
        start_date=start_date,
        end_date=end_date
)

# Save to CSV using utility function
save_report_to_csv(data, "ad_performance_report.csv")

# Save to JSON using utility function
save_report_to_json(data, "ad_performance_report.json")
```


## Available Report Models

- `MetaAdsReportModel.ad_dimensions_report` - Ad dimensions and metadata
- `MetaAdsReportModel.ad_performance_report` - Ad performance and actions metrics

## Custom Reports

Create custom report configurations:

```python
from facebook_ads_reports import create_custom_report

custom_report = create_custom_report(
    report_name="my_custom_report",
    select=["ad_id", "impressions", "spend"],
    from_table="ad_insights"
)

# Usage:
# data = client.get_insights_report(ad_account_id, custom_report, start_date, end_date)
```

## Examples

Check the `examples/` directory for comprehensive usage examples:

- `basic_usage.py` - Simple report extraction


## Requirements

- Python 3.10-3.12
- requests >= 2.32.4


## License

GPL License. See [LICENSE](LICENSE) file for details.


## Support

- [Documentation](https://github.com/machado000/facebook-ads-reports#readme)
- [Issues](https://github.com/machado000/facebook-ads-reports/issues)
- [Examples](examples/)


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.