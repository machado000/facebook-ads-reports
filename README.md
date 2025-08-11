# Facebook Ads Reports Helper

A Python ETL driver for Facebook Marketing API v22 data extraction and transformation. Simplifies the process of extracting Facebook Ads data and converting it to database-ready pandas DataFrames with comprehensive optimization features.

[![PyPI version](https://img.shields.io/pypi/v/facebook-ads-reports)](https://pypi.org/project/facebook-ads-reports/)
[![Last Commit](https://img.shields.io/github/last-commit/machado000/facebook-ads-reports)](https://github.com/machado000/facebook-ads-reports/commits/main)
[![Issues](https://img.shields.io/github/issues/machado000/facebook-ads-reports)](https://github.com/machado000/facebook-ads-reports/issues)
[![License](https://img.shields.io/badge/License-GPL-yellow.svg)](https://github.com/machado000/facebook-ads-reports/blob/main/LICENSE)

## Features

- **Facebook Marketing API v22**: Latest API version support with full compatibility
- **Robust Error Handling**: Comprehensive error handling with retry logic and specific exceptions
- **Multiple Report Types**: Pre-configured report models for common use cases
- **Custom Reports**: Create custom report configurations
- **Database-Ready DataFrames**: Optimized data types and encoding for seamless database storage
- **Smart Type Detection**: Dynamic conversion of metrics to appropriate int64/float64 types
- **Configurable Missing Values**: Granular control over NaN/NaT handling by column type
- **Character Encoding Cleanup**: Automatic text sanitization for database compatibility
- **Zero Impression Filtering**: Robust filtering handling multiple zero representations
- **Type Hints**: Full type hint support for better IDE experience

## Installation

```bash
pip install facebook-ads-reports
```

## Quick Start

### 1. Set up credentials

Create a `secrets/fb_business_config.json` file with your Facebook Ads API credentials:

```json
{
  "app_id": "YOUR_APP_ID",
  "access_token": "YOUR_ACCESS_TOKEN",
  "base_url": "https://graph.facebook.com/v22.0"
  "ad_account_id": "act_1234567890",
}
```

### 2. Basic usage

```python
from datetime import date, timedelta
from facebook_ads_reports import MetaAdsReport, MetaAdsReportModel, load_credentials

# Load credentials
credentials = load_credentials()
client = MetaAdsReport(credentials)

# Configure report parameters
ad_account_id = "act_1234567890"
start_date = date.today() - timedelta(days=7)
end_date = date.today() - timedelta(days=1)

# Extract report data with database optimization
df = client.get_insights_report(
        ad_account_id=ad_account_id,
        report_model=MetaAdsReportModel.ad_performance_report,
        start_date=start_date,
        end_date=end_date
)

# Save to CSV
df.to_csv("ad_performance_report.csv", index=False)
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
# df = client.get_insights_report(ad_account_id, custom_report, start_date, end_date)
```

## Database Optimization Features

- **Automatic Date Conversion**: String dates → `datetime64[ns]`
- **Dynamic Metrics Conversion**: Object metrics → `int64` or `float64` based on data
- **Preserve NULL Compatibility**: NaN/NaT preserved for database NULL mapping
- **Safe Conversion**: Invalid values gracefully ignored
- **ASCII Sanitization**: Removes non-ASCII characters for database compatibility
- **Length Limiting**: Truncates text to 255 characters (configurable)
- **Whitespace Trimming**: Removes leading/trailing whitespace


## Examples

Check the `examples/` directory for comprehensive usage examples:

- `basic_usage.py` - Simple report extraction


## Requirements

- Python 3.10-3.12
- pandas >= 2.0.0
- python-dotenv >= 1.0.0
- requests >= 2.32.4
- tqdm >= 4.65.0


## License

MIT License. See [LICENSE](LICENSE) file for details.


## Support

- [Documentation](https://github.com/machado000/facebook-ads-reports#readme)
- [Issues](https://github.com/machado000/facebook-ads-reports/issues)
- [Examples](examples/)


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.