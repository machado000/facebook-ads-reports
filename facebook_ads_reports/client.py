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
import unicodedata

from datetime import date, datetime
from typing import Any, Dict, Literal
from .exceptions import DataProcessingError, ValidationError
from .retry import retry_on_api_error
from .utils import validate_account_id, convert_keys_case

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
        Retrieve a report from the Facebook Marketing API using a report model configuration.

        This method handles pagination automatically, converts nested JSON structures,
        and optionally flattens the response data. It supports both account-level and
        insights-based reports with configurable date ranges.

        Args:
            ad_account_id (str): The Facebook Ad Account ID. Ignored for ad_accounts_report.
            report_model (Dict[str, Any]): Report configuration containing:
                - report_name (str): Name of the report type (e.g., 'ad_insights_report').
                - endpoint (str): API endpoint path.
                - fields (list): Fields to retrieve from the API.
                - params (dict): Additional query parameters.
            start_date (date | None): Report start date. Required for insights-based reports.
            end_date (date | None): Report end date. Required for insights-based reports.
            flatten (bool, optional): Whether to flatten nested JSON structures. Defaults to True.
            limit (int, optional): Number of records per API request (pagination size). Defaults to 200.

            list[dict[str, Any]]: List of report records with snake_case keys and cleaned text encoding.

        Raises:
            Exception: If the API request fails (non-200 status code).

        Note:
            - Automatically handles pagination through all available pages.
            - Converts field names to snake_case and cleans text encoding.
            - Logs detailed information about request parameters, pagination progress, and quota usage.
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
            logging.debug(f"Making API request to URL: {url} with params: {query_params}")
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

        response_data_snake_case = convert_keys_case(response_data, case="snake")

        if flatten:
            flattened_response = self._flatten_facebook_ads_response(response_data_snake_case)
        else:
            flattened_response = response_data

        cleaned_response = self._clean_text_encoding(flattened_response)

        logging.info(f"Finished fetching full report with {len(cleaned_response)} rows")
        return cleaned_response

    def _clean_text_encoding(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Clean text values without removing Unicode characters.

        Behavior:
        - Preserve accents and all valid Unicode.
        - Normalize to NFC for consistency.
        - Remove NULL and other problematic control chars.
        - Keep line breaks by default (optional to collapse).
        - No truncation by default.
        """
        def _sanitize_string(
            value: str,
            *,
            normalize_form: Literal["NFC", "NFD", "NFKC", "NFKD"] = "NFC",
            strip_controls: bool = True,
            collapse_line_breaks: bool = False,
            trim_whitespace: bool = True,
            max_length: int | None = None,
        ) -> str:
            s = unicodedata.normalize(normalize_form, value)

            if strip_controls:
                # Keep tab/newline/carriage-return unless explicitly collapsed.
                allowed = {"\t", "\n", "\r"}
                s = "".join(
                    ch for ch in s
                    if ch >= " " or ch in allowed
                )
                # Always remove NULL explicitly
                s = s.replace("\x00", "")

            if collapse_line_breaks:
                s = s.replace("\r", " ").replace("\n", " ")

            if trim_whitespace:
                s = s.strip()

            if max_length is not None:
                s = s[:max_length]

            return s

        def _sanitize_value(v: Any) -> Any:
            if isinstance(v, str):
                return _sanitize_string(v)
            if isinstance(v, list):
                return [_sanitize_value(item) for item in v]
            if isinstance(v, dict):
                return {k: _sanitize_value(val) for k, val in v.items()}
            return v

        try:
            return [_sanitize_value(row) for row in data]
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
