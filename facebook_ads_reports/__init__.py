"""
Google Ads Driver - A Python ETL module for Google Ads API data extraction.

This package provides tools for extracting, transforming, and loading Google Ads data
using the Google Ads API with pandas DataFrame outputs.
"""
from .client import MetaAdsReport
from .exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    DataProcessingError,
    MetaAdsReportError,
    ValidationError,
)
from .models import MetaAdsReportModel, create_custom_report
from .utils import (
    create_output_directory,
    format_report_filename,
    load_credentials,
    setup_logging,
    validate_account_id,
)

# Main exports
__all__ = [
    "MetaAdsReport",
    "MetaAdsReportModel",
    "create_custom_report",
    "load_credentials",
    "setup_logging",
    "validate_account_id",
    "create_output_directory",
    "format_report_filename",
    # Exceptions
    "MetaAdsReportError",
    "AuthenticationError",
    "ValidationError",
    "APIError",
    "DataProcessingError",
    "ConfigurationError",
]
