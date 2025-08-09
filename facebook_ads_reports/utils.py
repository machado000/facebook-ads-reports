"""
Utility functions for the MetaAdsReport driver module.
"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import json

from .exceptions import ConfigurationError, ValidationError


def load_credentials(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load Facebook Marketing API credentials from JSON file.

    Args:
        config_path (Optional[str]): Path to the credentials file.
                                   If None, tries default locations.

    Returns:
        Dict[str, Any]: Loaded credentials configuration

    Raises:
        FileNotFoundError: If credentials file is not found
        json.JSONDecodeError: If JSON parsing fails
    """
    default_paths = [
        os.path.join("secrets", "fb_business_config.json"),
        os.path.join(os.path.expanduser("~"), ".fb_business_config.json"),
        "fb_business_config.json"
    ]

    if config_path:
        paths_to_try = [config_path]
    else:
        paths_to_try = default_paths

    for path in paths_to_try:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    credentials = json.load(f)

                if not credentials:
                    raise ConfigurationError(f"Credentials file {path} is empty")

                if not isinstance(credentials, dict):
                    raise ConfigurationError(f"Credentials file {path} must contain a JSON dictionary")

                return credentials

            except json.JSONDecodeError as e:
                logging.error(f"Error parsing JSON file {path}: {e}")
                raise ConfigurationError(
                    f"Invalid JSON format in credentials file {path}",
                    original_error=e
                ) from e
            except IOError as e:
                raise ConfigurationError(
                    f"Failed to read credentials file {path}",
                    original_error=e
                ) from e

    raise ConfigurationError(
        f"Could not find credentials file in any of these locations: {paths_to_try}"
    )


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


def validate_account_id(account_id: str) -> str:
    """
    Validate and format a Facebook Ads Account ID as 'act_' plus digits.

    Args:
        account_id (str): The account ID to validate and format

    Returns:
        str: Formatted account ID (e.g., 'act_12345678')

    Raises:
        ValidationError: If account ID format is invalid
    """
    if not account_id or not isinstance(account_id, str):
        raise ValidationError("Account ID must be a non-empty string")

    clean_id = account_id.strip()

    # If already in 'act_' format
    if clean_id.startswith("act_"):
        digits = clean_id[4:]
        if digits.isdigit() and len(digits) >= 8 and len(digits) <= 16:
            return clean_id
        else:
            raise ValidationError(f"Account ID with 'act_' must be followed by at least 8 digits: {account_id}")

    # If only digits
    if clean_id.isdigit() and len(clean_id) >= 8:
        return f"act_{clean_id}"

    raise ValidationError(
        "Account ID must be either at least 8 digits or 'act_' followed by at least 8 digits. "
        f"Got: {account_id}"
    )


def create_output_directory(path: str) -> Path:
    """
    Create output directory if it doesn't exist.

    Args:
        path (str): Directory path to create

    Returns:
        Path: Path object for the created directory
    """
    output_path = Path(path)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def format_report_filename(report_name: str, account_id: str,
                           start_date: str, end_date: str,
                           file_extension: str = "csv") -> str:
    """
    Generate a standardized filename for report exports.

    Args:
        report_name (str): Name of the report
        account_id (str): Facebook Ads account ID
        start_date (str): Report start date
        end_date (str): Report end date
        file_extension (str): File extension (default: csv)

    Returns:
        str: Formatted filename
    """
    # Clean the inputs
    safe_report_name = report_name.replace(" ", "_").lower()
    safe_account_id = validate_account_id(account_id)

    return f"{safe_report_name}_{safe_account_id}_{start_date}_{end_date}.{file_extension}"
