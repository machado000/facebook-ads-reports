"""
Facebook Ads Reports Driver - A Python ETL module for Facebook Marketing API data extraction.

This package provides tools for extracting, transforming, and loading Facebook Ads data
using the Facebook Marketing API with pandas DataFrame outputs.
"""
import logging
from typing import Optional

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
    load_credentials,
    validate_account_id,
    create_output_directory,
    format_report_filename,
    get_month_date_pairs
)

# Main exports
__all__ = [
    "MetaAdsReport",
    # Models
    "MetaAdsReportModel",
    "create_custom_report",
    # Exceptions
    "MetaAdsReportError",
    "AuthenticationError",
    "ValidationError",
    "APIError",
    "DataProcessingError",
    "ConfigurationError",
    # Utils
    "load_credentials",
    "validate_account_id",
    "create_output_directory",
    "format_report_filename",
    "get_month_date_pairs",
    # __init__
    "setup_logging",
]


def setup_logging(level: int = logging.INFO,
                  format_string: Optional[str] = None) -> None:
    """
    Setup logging configuration.

    Args:
        level (int): Logging level (default: INFO)
        format_string (Optional[str]): Custom format string
    """
    if format_string is None:
        format_string = '%(levelname)s - %(message)s'

    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=[
            logging.StreamHandler(),
        ]
    )
