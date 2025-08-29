"""
Utility functions for the MetaAdsReport driver module.
"""
import calendar
import csv
import json
import logging
import os

from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional
from .exceptions import ConfigurationError, ValidationError


def load_credentials(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load Facebook Marketing API credentials from JSON file.

    Args:
        config_path (Optional[str]): Path to the credentials file. If None, tries default locations.

    Returns:
        dict[str, Any]: Loaded credentials configuration

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


def get_month_date_pairs(start_date: date, end_date: date) -> list[tuple[date, date]]:
    """
    Breaks a date range into monthly (start_date, end_date) pairs.

    Args:
        start_date (date): The start date of the range.
        end_date (date): The end date of the range.

    Returns:
        list[tuple[date, date]]: List of (start_date, end_date) tuples for each month in the range.
    """
    # Ensure input dates are date objects
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()

    if end_date < start_date:
        raise ValueError("ERROR - Invalid dates: 'end_date' precedes 'start_date'")

    # Initialize the list to store the month periods
    month_periods = []

    # Iterate through each month
    current_date = start_date
    while current_date <= end_date:
        # Get the first day of the current month
        month_start = max(current_date, date(current_date.year, current_date.month, 1))

        # Get the last day of the current month using calendar.monthrange
        last_day = calendar.monthrange(current_date.year, current_date.month)[1]
        month_end = min(end_date, date(current_date.year, current_date.month, last_day))

        month_periods.append((month_start, month_end))

        # Move to the first day of the next month
        if current_date.month == 12:
            current_date = date(current_date.year + 1, 1, 1)
        else:
            current_date = date(current_date.year, current_date.month + 1, 1)

    return month_periods


def get_unique_keys_from_response(response: list[dict[str, Any]]) -> list[str]:
    """
    Extract all unique keys from a list of dictionaries response.

    Parameters:
    - response: List of dictionaries containing API response data

    Returns:
    - list[str]: Sorted list of unique keys found across all dictionaries

    Raises:
    - ValidationError: If response format is invalid
    """
    try:
        if not response:
            logging.warning("Response is empty, returning empty list")
            return []

        # Validate response format
        if not isinstance(response, list) or not all(isinstance(item, dict) for item in response):
            raise ValidationError("Response must be a list of dictionaries")

        # Collect all unique keys
        unique_keys: set[str] = set()

        for row in response:
            unique_keys.update(row.keys())

        # Return sorted list for consistent ordering
        sorted_keys = sorted(list(unique_keys))

        logging.debug(f"Found {len(sorted_keys)} unique keys in response")
        logging.debug(f"Unique keys: {sorted_keys}")

        return sorted_keys

    except Exception as e:
        raise ValidationError(f"Failed to extract unique keys from response: {str(e)}") from e


def save_report_to_csv(data: list[dict[str, Any]], filepath: str) -> str:
    """
    Save report data to CSV file.

    Parameters:
    - data: List of dictionaries containing report data
    - filepath: Path where to save the CSV file

    Returns:
    - str: Full path of the saved CSV file

    Raises:
    - ConfigurationError: If CSV writing fails
    """
    try:
        # Add .csv extension if not present
        if not filepath.endswith('.csv'):
            filepath += '.csv'

        if not data:
            logging.warning("No data to save to CSV")
            # Create empty CSV file
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                csvfile.write('')
            return filepath

        # Get all unique keys from all dictionaries to use as fieldnames
        fieldnames_set: set[str] = set()
        for row in data:
            fieldnames_set.update(row.keys())
        fieldnames = sorted(list(fieldnames_set))

        # Write to CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        logging.debug(f"Successfully saved {len(data)} rows to {filepath}")
        return filepath

    except Exception as e:
        raise ConfigurationError("Failed to save CSV file:", original_error=e) from e


def save_report_to_json(data: list[dict[str, Any]], filepath: str, indent: int = 2) -> str:
    """
    Save report data to JSON file.

    Parameters:
    - data: List of dictionaries containing report data
    - filepath: Path where to save the JSON file
    - indent: JSON indentation level (default: 2)

    Returns:
    - str: Full path of the saved JSON file

    Raises:
    - ConfigurationError: If JSON writing fails
    """
    try:
        # Add .json extension if not present
        if not filepath.endswith('.json'):
            filepath += '.json'

        # Write to JSON
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=indent, ensure_ascii=False, default=str)

        logging.debug(f"Successfully saved {len(data)} rows to {filepath}")
        return filepath

    except Exception as e:
        raise ConfigurationError("Failed to save JSON file:", original_error=e) from e
