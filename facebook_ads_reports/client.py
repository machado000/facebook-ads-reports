"""
Facebook Marketing API client module.

This module contains the main MetaAdsReport class for interacting with the Facebook Marketing API.
https://developers.facebook.com/docs/business-sdk/getting-started
https://developers.facebook.com/docs/marketing-api/reference/ads-insights
https://developers.facebook.com/tools/debug/accesstoken
"""
import json
import logging
import requests
import socket

from datetime import date, datetime
from typing import Any, Dict
from .exceptions import DataProcessingError, ValidationError
from .retry import retry_on_api_error
from .utils import validate_account_id

# Set timeout for all http connections
TIMEOUT_IN_SEC = 60 * 3  # seconds timeout limit
socket.setdefaulttimeout(TIMEOUT_IN_SEC)

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)


class MetaAdsReport:
    """
    MetaAdsReport class for interacting with the Facebook Marketing API v23.0.
    """

    def __init__(self, credentials_dict: Dict[str, str]) -> None:
        """
        Initializes the MetaAdsReport instance.

        Args:
            credentials_dict (dict): The JSON credentials for authentication.

        Raises:
            AuthenticationError: If credentials are invalid or authentication fails.
            ValidationError: If credentials_dict format is invalid.
        """
        if not isinstance(credentials_dict, dict):
            raise ValidationError("credentials_dict must be a dictionary")

        if not credentials_dict:
            raise ValidationError("credentials_dict cannot be empty")

        try:
            self.access_token = credentials_dict["access_token"]
            self.api_version = "v23.0"
            self.api_base_url = f"https://graph.facebook.com/{self.api_version}"

        except Exception as e:
            raise KeyError("credentials_dict must contain 'access_token' key") from e

    @retry_on_api_error()
    def get_report(self, ad_account_id: str, report_model: Dict[str, Any],
                   start_date: date | None, end_date: date | None,
                   flatten: bool = True, limit: int = 200) -> list[dict[str, Any]]:
        """
        Get a report from Facebook Marketing API using a report model configuration.

        Parameters:
        - ad_account_id (str): Ad account ID.
        - report_model (dict): Report model containing endpoint, fields, and params.
        - start_date (date | None): Start date for insights-based reports.
        - end_date (date | None): End date for insights-based reports.
        - flatten (bool): Whether to flatten nested JSON structures in the response.
        - limit (int): Number of records to fetch per API call (pagination limit).

        Returns:
        - list[dict[str, Any]]: Report data as a list of dictionaries.
        """

        report_name = report_model["report_name"]
        endpoint = report_model["endpoint"]
        fields = report_model["fields"]
        # Copy params so model class definitions are not mutated across calls.
        params = report_model["params"].copy()

        if report_name == "ad_accounts_report":
            # For ad accounts report, we can use "me" to get all accounts accessible by the token
            ad_account_id = "me"
        else:
            # Validate account ID format
            ad_account_id = validate_account_id(ad_account_id)

        # Convert datetime objects to strings
        start_date_format = start_date.strftime("%Y-%m-%d") if isinstance(start_date, (date, datetime)) else start_date
        end_date_format = end_date.strftime("%Y-%m-%d") if isinstance(end_date, (date, datetime)) else end_date

        # Set time_range parameter if ad_insights_report
        if report_name == "ad_insights_report":
            params["time_range"] = {"since": start_date_format, "until": end_date_format}
            date_range_str = f"from {start_date_format} to {end_date_format}"
        else:
            date_range_str = report_model.get('params', {}).get('date_preset') or 'unspecified'

        # Display request parameters
        print(f"INFO - Trying to get Meta Ads report with `{self.api_base_url}`\n",
              "[ Request parameters ]",
              f"Ad_Account_id: {ad_account_id}",
              f"Report_model: {report_name}",
              f"Num of params: {len(params)} | Num of fields: {len(fields)}",
              f"Date range: {date_range_str}\n",
              sep="\n")

        # Convert fields list to comma-separated string
        fields_comma_separated = ','.join(fields)

        # Construct the API request URL
        url = "/".join(s.strip("/") for s in [self.api_base_url, ad_account_id, endpoint])

        # Set up the Authorization header
        headers = {'Authorization': f'Bearer {self.access_token}'}

        # Prepare query parameters
        query_params = {
            'fields': fields_comma_separated,
            **params
        }

        # Convert nested structures to JSON strings for query parameters
        for key in ['time_range', 'action_breakdowns', 'breakdowns']:
            if key in query_params:
                query_params[key] = json.dumps(query_params[key])

        # Include limit in query parameters
        query_params['limit'] = limit

        response_data = []
        page_count = 0
        total_pages = None

        while url:
            # Send the GET request with Authorization header
            response = requests.get(url, headers=headers, params=query_params)

            # Check for successful response
            if response.status_code == 200:
                # Parse the response JSON payload and append current page data.
                response_json = response.json()
                response_data.extend(response_json['data'])

                # Calculate total pages on the first response
                if total_pages is None:
                    total_count = response_json.get('summary', {}).get('total_count')
                    if total_count:
                        total_pages = (total_count + limit - 1) // limit
                    else:
                        total_pages = 'unknown'

                page_count += 1
                if total_pages != 'unknown':
                    logging.info(f"Fetching page {page_count} of {total_pages}")
                else:
                    logging.info(f"Fetching page {page_count}")

                url = response_json.get('paging', {}).get('next')

                quota_info = response.headers.get('x-business-use-case-usage')
                logging.debug(f"Remaining quota: {quota_info}")

            else:
                raise Exception(
                    f"""API request failed with Error code: {response.status_code}, header: {response.headers}, body: {response.text}""")  # noqa

        if flatten:
            flattened_response = self._flatten_facebook_ads_response(response_data)
        else:
            flattened_response = response_data

        cleaned_response = self._clean_text_encoding(flattened_response)

        logging.info(f"Finished fetching full report with {len(cleaned_response)} rows")
        return cleaned_response

    def _clean_text_encoding(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Cleans text values in a list of dictionaries for character encoding issues.

        Parameters:
        - data: List of dictionaries to clean

        Returns:
        - list[dict]: Cleaned list of dictionaries
        """
        try:
            cleaned_data = []

            for row in data:
                cleaned_row = {}

                for key, value in row.items():
                    # Only process string values
                    if isinstance(value, str):
                        # Handle common encoding issues
                        cleaned_value = str(value)
                        # Remove or replace problematic characters
                        cleaned_value = cleaned_value.encode('ascii', 'ignore').decode('ascii')  # Remove non-ASCII
                        cleaned_value = cleaned_value.replace('\x00', '')  # Remove null bytes
                        cleaned_value = cleaned_value.replace('\r', ' ').replace('\n', ' ')  # Remove line breaks
                        cleaned_value = cleaned_value.strip()  # Remove leading/trailing whitespace
                        # Limit string length for database compatibility (adjust as needed)
                        cleaned_value = cleaned_value[:255]
                        cleaned_row[key] = cleaned_value
                    else:
                        # Keep non-string values as-is
                        cleaned_row[key] = value

                cleaned_data.append(cleaned_row)

            return cleaned_data

        except Exception as e:
            logging.warning(f"Character encoding cleanup failed: {e}")
            return data

    def _flatten_action_list(self, list_of_dicts: list[dict[str, Any]]) -> dict[str, Any]:

        if not isinstance(list_of_dicts, list):
            return {}

        flattened_dict = {item["action_type"]: item["value"] for item in list_of_dicts}

        return flattened_dict

    def _flatten_video_play_action(self, column_name: str, list_of_dicts: list[dict[str, Any]]) -> Dict[str, Any]:

        if not isinstance(list_of_dicts, list) or not list_of_dicts:
            return {}

        # Take the first item's value (assuming single action type per video column)
        first_item = list_of_dicts[0]
        value = first_item.get("value", "")

        # Clean the column name by removing "_actions" suffix
        clean_key = column_name.replace("_actions", "")

        return {clean_key: value}

    def _collect_values_by_key(self, obj: Any, target_key: str) -> list[Any]:
        """
        Recursively collect values for a target key across nested dict/list structures.
        """
        collected: list[Any] = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == target_key:
                    collected.append(value)
                collected.extend(self._collect_values_by_key(value, target_key))
        elif isinstance(obj, list):
            for item in obj:
                collected.extend(self._collect_values_by_key(item, target_key))

        return collected

    def _normalize_extracted_values(self, values: list[Any]) -> Any:
        """
        Return a scalar when a single value is found, otherwise return all values.
        """
        if not values:
            return None
        if len(values) == 1:
            return values[0]
        return values

    def _flatten_facebook_ads_response(self, response: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Flatten nested fields from the Facebook Marketing API `data` payload.

        Parameters:
        - response: The Facebook Marketing API `data` list of dictionaries.

        Returns:
        - list[dict[str, Any]]: Flattened report rows.

        Raises:
        - DataProcessingError: If response flattening fails.
        """
        try:
            if not response:
                logging.info("Response is empty, returning empty list")
                return []

            # Check if response is a list of dictionaries (list[dict[str, Any]])
            if not isinstance(response, list) or not all(isinstance(item, dict) for item in response):
                raise DataProcessingError("API response must be a json like object or a list of dictionaries")

            # Create a copy to avoid modifying the original
            flattened_response = []

            action_columns = [
                "actions", "conversions", "conversion_values",
                "converted_product_quantity", "converted_product_value",
            ]

            video_actions_columns = [
                "video_play_actions", "video_p25_watched_actions", "video_p50_watched_actions",
                "video_p75_watched_actions", "video_p100_watched_actions",
            ]

            targeting_nested_fields = [
                'genders',   # targeting_
                'age_max',  # targeting_
                'age_min',  # targeting_
                'location_types',  # targeting_geo_locations_
                'countries',  # targeting_geo_locations_
                'regions',  # targeting_geo_locations_
                'cities',  # targeting_geo_locations_
                'subcities',  # targeting_geo_locations_
                'neighborhoods',  # targeting_geo_locations_
                'places',  # targeting_geo_locations_
                'custom_locations',  # targeting_geo_locations_
                'device_platforms',  # targeting_
                'publisher_platforms',  # targeting_
                'instagram_positions',  # targeting_
                'facebook_positions',  # targeting_
                'messenger_positions',  # targeting_
                'threads_positions',  # targeting_
                'whatsapp_positions',  # targeting_
                'user_age_unknown',  # targeting_
                'user_device',  # targeting_
                'user_os',  # targeting_
                'custom_audiences',   # targeting_
                'interests',  # targeting_flexible_spec_
                'behaviors',  # targeting_flexible_spec_
            ]

            learning_stage_info_nested_fields = [
                'attribution_windows',  # learning_stage_info_
                'conversions',  # learning_stage_info_
                'last_sig_edit_ts',  # learning_stage_info_
                'status',  # learning_stage_info_
            ]

            for row in response:
                flattened_row = row.copy()

                for column in action_columns:
                    if column in flattened_row:
                        logging.debug(f"Flattening column '{column}'")

                        # Flatten the list of dicts to a single dict
                        flattened_dict = self._flatten_action_list(flattened_row[column])

                        # Remove the original column
                        del flattened_row[column]

                        for key, value in flattened_dict.items():
                            flattened_row[key] = value

                for column in video_actions_columns:
                    if column in flattened_row:
                        logging.debug(f"Flattening column '{column}'")

                        # Flatten the list of dicts to a single dict
                        flattened_dict = self._flatten_video_play_action(column, flattened_row[column])

                        # Remove the original column
                        del flattened_row[column]

                        for key, value in flattened_dict.items():
                            flattened_row[key] = value

                if 'targeting' in flattened_row:
                    targeting_data = flattened_row['targeting']

                    for nested_field in targeting_nested_fields:
                        logging.debug(f"Extracting nested field '{nested_field}' from targeting")

                        extracted_values = self._collect_values_by_key(targeting_data, nested_field)
                        normalized_value = self._normalize_extracted_values(extracted_values)

                        if normalized_value is not None:
                            flattened_row[f"{nested_field}"] = normalized_value

                    del flattened_row['targeting']

                if 'learning_stage_info' in flattened_row:
                    learning_stage_info_data = flattened_row['learning_stage_info']

                    for nested_field in learning_stage_info_nested_fields:
                        logging.debug(f"Extracting nested field '{nested_field}' from learning_stage_info")

                        extracted_values = self._collect_values_by_key(learning_stage_info_data, nested_field)
                        normalized_value = self._normalize_extracted_values(extracted_values)

                        if normalized_value is not None:
                            flattened_row[f"learning_stage_info_{nested_field}"] = normalized_value

                    del flattened_row['learning_stage_info']

                # Add the flattened row to the response
                flattened_response.append(flattened_row)

            return flattened_response

        except Exception as e:
            raise DataProcessingError(
                "Failed to flatten API response", original_error=e) from e
