# Google Ads Driver Examples

This directory contains example scripts demonstrating how to use the `google-ads-drv` package to extract data from the Google Ads API.

## Prerequisites

Before running any examples, ensure you have:

1. **Google Ads API credentials** configured in `secrets/google-ads.yaml`
2. **Valid customer ID** for your Google Ads account
3. **Required dependencies** installed (see `requirements.txt` or `pyproject.toml`)

## Example Scripts

### 1. `basic_usage.py`
**Purpose**: Demonstrates the fundamental usage pattern
**What it does**:
- Loads credentials from the default location
- Extracts a single report (adgroup_ad_report) 
- Saves the data to CSV
- Shows basic report information

**Usage**:
```bash
python examples/basic_usage.py
```

**Key concepts covered**:
- Basic client initialization
- Simple report extraction
- CSV export
- Error handling

---

### 2. `multiple_reports.py`
**Purpose**: Shows how to extract multiple report types efficiently
**What it does**:
- Extracts several different report types
- Creates organized directory structure
- Generates standardized filenames
- Provides detailed extraction summary

**Usage**:
```bash
python examples/multiple_reports.py
```

**Key concepts covered**:
- Batch report extraction
- Directory management
- Filename standardization
- Progress reporting
- Error handling for multiple operations

---

### 3. `custom_reports.py`
**Purpose**: Demonstrates creating custom report configurations
**What it does**:
- Creates custom report models with specific fields
- Shows how to add WHERE clauses and custom ordering
- Demonstrates the `create_custom_report()` function

**Usage**:
```bash
python examples/custom_reports.py
```

**Key concepts covered**:
- Custom report model creation
- Field selection and filtering
- Custom WHERE clauses
- Dynamic report configurations

---

### 4. `error_handling.py`
**Purpose**: Demonstrates proper error handling and recovery patterns
**What it does**:
- Shows different types of exceptions that can occur
- Demonstrates retry behavior for transient errors
- Provides recommended error handling patterns

**Usage**:
```bash
python examples/error_handling.py
```

**Key concepts covered**:
- Custom exception types
- Retry logic for API errors
- Error recovery strategies
- Best practices for error handling

## Configuration

### Customer ID
Replace the placeholder customer ID (`"1234567890"`) in each example with your actual Google Ads customer ID.

### Date Ranges
Examples use relative date ranges (last 7 days, last 30 days, etc.). Modify the `start_date` and `end_date` variables to suit your needs.

### Credentials Location
By default, examples look for credentials in `secrets/google-ads.yaml`. To use a different location:

```python
# Specify custom path
credentials = load_credentials("/path/to/your/google-ads.yaml")
```

## Common Modifications

### Change Output Format
```python
# Save as JSON instead of CSV
df.to_json("report.json", orient="records", indent=2)

# Save as Parquet
df.to_parquet("report.parquet")

# Save as Excel
df.to_excel("report.xlsx", index=False)
```

### Add Data Filtering
```python
# Filter data after extraction
filtered_df = df[df['impressions'] > 1000]

# Or add filters to the report model
custom_report = create_custom_report(
    report_name="high_impression_campaigns",
    select=["campaign.name", "metrics.impressions", "metrics.clicks"],
    from_table="campaign",
    where="metrics.impressions > 1000"
)
```

### Custom Date Ranges
```python
from datetime import date

# Specific date range
start_date = date(2024, 1, 1)
end_date = date(2024, 1, 31)

# This month
from datetime import datetime
today = datetime.now()
start_date = today.replace(day=1).date()
end_date = today.date()
```

## Troubleshooting

### Exception Types

The package provides specific exception types for different error scenarios:

- **`AuthenticationError`**: Invalid credentials or authentication failures
- **`ValidationError`**: Invalid input parameters (customer ID, dates, etc.)
- **`APIError`**: Google Ads API errors (after retries)
- **`DataProcessingError`**: DataFrame conversion or data processing failures
- **`ConfigurationError`**: Configuration file or setup issues

### Error Handling Pattern

```python
from google_ads_reports import (
    GAdsReport, AuthenticationError, ValidationError, 
    APIError, DataProcessingError, ConfigurationError
)

try:
    # Your code here
    df = gads_client.get_gads_report(...)
    
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
    # Check credentials and retry
    
except ValidationError as e:
    print(f"Invalid input: {e.message}")
    # Fix input parameters
    
except APIError as e:
    print(f"API error (after retries): {e.message}")
    # Log error, try different approach
```

### Retry Behavior

The package automatically retries transient API errors with:
- **Max attempts**: 3 (configurable)
- **Base delay**: 1 second
- **Backoff factor**: 2x
- **Max delay**: 30 seconds
- **Jitter**: Random variation to prevent thundering herd

### Common Issues

1. **Import Errors**: Make sure the package is installed or you're running from the correct directory
2. **Credential Errors**: Verify your `google-ads.yaml` file exists and has correct format
3. **API Errors**: Check your customer ID and API access permissions
4. **Empty Results**: Some reports may return no data for certain date ranges or accounts

### Debug Mode
Enable debug logging to see detailed API interactions:

```python
import logging
setup_logging(level=logging.DEBUG)
```

### Check Available Reports
```python
from google_ads_reports import GAdsReportModel

# List all available reports
reports = GAdsReportModel.list_available_reports()
print("Available reports:", reports)

# Get details of a specific report
report_details = GAdsReportModel.get_report_by_name("keyword_report")
print("Keyword report fields:", report_details["select"])
```

## Next Steps

After trying these examples:

1. **Modify** existing examples to match your specific use case
2. **Create** your own custom report models
3. **Integrate** the extraction logic into your data pipeline
4. **Explore** advanced features like data validation and transformation
5. **Schedule** regular extractions using cron or task schedulers

For more advanced usage, check the main package documentation.
