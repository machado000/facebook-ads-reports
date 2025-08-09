# Google Ads Reports Helper

A Python ETL driver for Google Ads API v20 data extraction and transformation. Simplifies the process of extracting Google Ads data and converting it to database-ready pandas DataFrames with comprehensive optimization features.

[![PyPI version](https://img.shields.io/pypi/v/google-ads-reports)](https://pypi.org/project/google-ads-reports/)
[![Issues](https://img.shields.io/github/issues/machado000/google-ads-reports)](https://github.com/machado000/google-ads-reports/issues)
[![Last Commit](https://img.shields.io/github/last-commit/machado000/google-ads-reports)](https://github.com/machado000/google-ads-reports/commits/main)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/machado000/google-ads-reports/blob/main/LICENSE)

## Features

- **Google Ads API v20**: Latest API version support with full compatibility
- **Database-Ready DataFrames**: Optimized data types and encoding for seamless database storage
- **Flexible Column Naming**: Choose between snake_case or camelCase column conventions
- **Smart Type Detection**: Dynamic conversion of metrics to appropriate int64/float64 types
- **Configurable Missing Values**: Granular control over NaN/NaT handling by column type
- **Character Encoding Cleanup**: Automatic text sanitization for database compatibility
- **Zero Impression Filtering**: Robust filtering handling multiple zero representations
- **Multiple Report Types**: Pre-configured report models for common use cases
- **Custom Reports**: Create custom report configurations with full GAQL support
- **Robust Error Handling**: Comprehensive error handling with retry logic and specific exceptions
- **Pagination Support**: Automatic handling of large datasets with pagination
- **Type Hints**: Full type hint support for better IDE experience

## Installation

```bash
pip install google-ads-reports
```

## Quick Start

### 1. Set up credentials

Create a `secrets/google-ads.yaml` file with your Google Ads API credentials:

```yaml
developer_token: "YOUR_DEVELOPER_TOKEN"
client_id: "YOUR_CLIENT_ID"
client_secret: "YOUR_CLIENT_SECRET"
refresh_token: "YOUR_REFRESH_TOKEN"
```
References:\
https://developers.google.com/google-ads/api/docs/get-started/introduction
https://developers.google.com/google-ads/api/docs/get-started/dev-token
https://developers.google.com/workspace/guides/create-credentials#service-account


### 2. Basic usage

```python
from datetime import date, timedelta
from google_ads_reports import GAdsReport, GAdsReportModel, load_credentials

# Load credentials
credentials = load_credentials()
client = GAdsReport(credentials)

# Configure report parameters
customer_id = "1234567890"
start_date = date.today() - timedelta(days=7)
end_date = date.today() - timedelta(days=1)

# Extract report data with database optimization
df = client.get_gads_report(
    customer_id=customer_id,
    report_model=GAdsReportModel.keyword_report,
    start_date=start_date,
    end_date=end_date,
    filter_zero_impressions=True,  # Remove rows with zero impressions
    column_naming="snake_case"     # Choose column naming: "snake_case" or "camelCase"
)

# Save to CSV
df.to_csv("keyword_report.csv", index=False)
```

### Column Naming Options

Choose between snake_case (database-friendly) or camelCase (API-consistent) column names:

```python
# Snake case (default) - metrics.impressions → impressions
df_snake = client.get_gads_report(
    customer_id=customer_id,
    report_model=GAdsReportModel.keyword_report,
    start_date=start_date,
    end_date=end_date,
    column_naming="snake_case"  # Default
)

# CamelCase - metrics.impressions → metricsImpressions  
df_camel = client.get_gads_report(
    customer_id=customer_id,
    report_model=GAdsReportModel.keyword_report,
    start_date=start_date,
    end_date=end_date,
    column_naming="camelCase"
)
```

## Available Report Models

- `GAdsReportModel.adgroup_ad_report` - Ad group ad performance
- `GAdsReportModel.keyword_report` - Keyword performance
- `GAdsReportModel.search_terms_report` - Search terms analysis
- `GAdsReportModel.conversions_report` - Conversion tracking
- `GAdsReportModel.video_report` - Video ad performance
- `GAdsReportModel.assetgroup_report` - Asset group performance

## Custom Reports

Create custom report configurations:

```python
from google_ads_reports import create_custom_report

custom_report = create_custom_report(
    report_name="campaign_performance",
    select=[
        "campaign.name",
        "campaign.status", 
        "segments.date",
        "metrics.impressions",
        "metrics.clicks",
        "metrics.cost_micros"
    ],
    from_table="campaign",
    where="metrics.impressions > 100"
)

df = client.get_gads_report(customer_id, custom_report, start_date, end_date)
```

## Database Optimization Features

The package automatically optimizes DataFrames for database storage:

### Data Type Optimization
- **Automatic Date Conversion**: String dates → `datetime64[ns]`
- **Dynamic Metrics Conversion**: Object metrics → `int64` or `float64` based on data
- **Smart Integer Detection**: Whole numbers become `int64`, decimals become `float64`

### Missing Value Handling
- **Preserve NULL Compatibility**: NaN/NaT preserved for database NULL mapping
- **Configurable by Type**: Different strategies for numeric, datetime, and text columns
- **Safe Conversion**: Invalid values gracefully ignored

### Character Encoding Cleanup
- **ASCII Sanitization**: Removes non-ASCII characters for database compatibility  
- **Null Byte Removal**: Strips problematic null bytes (`\x00`)
- **Length Limiting**: Truncates text to 255 characters (configurable)
- **Whitespace Trimming**: Removes leading/trailing whitespace

### Zero Impression Filtering
Handles multiple zero representations:
```python
df = client.get_gads_report(
    customer_id=customer_id,
    report_model=report_model,
    start_date=start_date,
    end_date=end_date,
    filter_zero_impressions=True  # Removes: 0, "0", 0.0, "0.0", None, NaN
)
```

### Flexible Column Naming
Choose your preferred column naming convention:

**Snake Case (Default - Database Friendly):**
- `metrics.impressions` → `impressions`
- `segments.date` → `date`  
- `adGroupCriterion.keyword` → `keyword`

**CamelCase (API Consistent):**
- `metrics.impressions` → `metricsImpressions`
- `segments.date` → `segmentsDate`
- `adGroupCriterion.keyword` → `adGroupCriterionKeyword`

```python
# Choose naming convention
df = client.get_gads_report(
    customer_id=customer_id,
    report_model=report_model,
    start_date=start_date,
    end_date=end_date,
    column_naming="snake_case"  # or "camelCase"
)
```

## Error Handling

The package provides specific exception types for different scenarios:

```python
from google_ads_reports import (
    GAdsReport, 
    AuthenticationError, 
    ValidationError, 
    APIError,
    DataProcessingError,
    ConfigurationError
)

try:
    df = client.get_gads_report(customer_id, report_model, start_date, end_date)
except AuthenticationError:
    # Handle credential issues
    pass
except ValidationError:
    # Handle input validation errors
    pass
except APIError:
    # Handle API errors (after retries)
    pass
```

## Examples

Check the `examples/` directory for comprehensive usage examples:

- `basic_usage.py` - Simple report extraction
- `multiple_reports.py` - Batch report processing  
- `custom_reports.py` - Custom report creation
- `error_handling.py` - Error handling patterns

## Configuration

### Retry Settings

API calls automatically retry on transient errors with configurable settings:

- **Max attempts**: 3 (default)
- **Base delay**: 1 second
- **Backoff factor**: 2x exponential
- **Max delay**: 30 seconds

### Logging

Configure logging level:

```python
from google_ads_reports import setup_logging
import logging

setup_logging(level=logging.DEBUG)  # Enable debug logging
```

## Requirements

- Python 3.9-3.12
- google-ads >= 24.0.0 (Google Ads API v20 support)
- pandas >= 2.0.0
- PyYAML >= 6.0.0
- python-dotenv >= 1.0.0
- tqdm >= 4.65.0

## Development

For development installation:

```bash
git clone https://github.com/machado000/google-ads-reports
cd google-ads-reports
pip install -e ".[dev]"
```

## License

MIT License. See [LICENSE](LICENSE) file for details.

## Support

- [Documentation](https://github.com/machado000/google-ads-reports#readme)
- [Issues](https://github.com/machado000/google-ads-reports/issues)
- [Examples](examples/)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
