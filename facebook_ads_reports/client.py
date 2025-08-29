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
from typing import Any, Dict, Optional
from .exceptions import DataProcessingError, ValidationError
from .retry import retry_on_api_error
from .utils import validate_account_id

# Set timeout for all http connections
TIMEOUT_IN_SEC = 60 * 3  # seconds timeout limit
socket.setdefaulttimeout(TIMEOUT_IN_SEC)


class MetaAdsReport:
    """
    MetaAdsReport class for interacting with the Facebook Marketing API v22.
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
            self.app_id = credentials_dict["app_id"]
            self.access_token = credentials_dict["access_token"]
            self.api_base_url = credentials_dict.get("base_url", "https://graph.facebook.com/v23.0")

        except Exception as e:
            raise KeyError("credentials_dict must contain 'app_id' and 'access_token' keys") from e

    @retry_on_api_error()
    def get_insights_report(self, ad_account_id: str, report_model: Dict[str, Any],
                            start_date: date, end_date: date, limit: int = 500) -> list[dict[str, Any]]:
        """
        Get insights report from Facebook Marketing API.

        Parameters:
        - ad_account_id (str): Ad account ID.
        - report_model (dict): Report model containing fields and params.
        - start_date (date): Start date for the report.
        - end_date (date): End date for the report.

        Returns:
        - list[dict[str, Any]]: Report data as a list of dictionaries.
        """
        # Validate account ID format
        ad_account_id = validate_account_id(ad_account_id)

        # Convert datetime objects to strings
        start_date_format = start_date.strftime("%Y-%m-%d") if isinstance(start_date, (date, datetime)) else start_date
        end_date_format = end_date.strftime("%Y-%m-%d") if isinstance(end_date, (date, datetime)) else end_date

        report_name = report_model["report_name"]
        fields = report_model["fields"]
        params = report_model["params"]
        action_types = report_model.get("action_types")  # noqa

        # Set time_range parameter if not ads_dimensions_report
        if report_name != "ads_dimensions_report":
            params["time_range"] = {"since": start_date_format, "until": end_date_format}

        # Display request parameters
        print(f"INFO - Trying to get Ad_Insights report with `{self.api_base_url}`\n",
              "[ Request parameters ]",
              f"Ad_Account_id: {ad_account_id}",
              f"Report_model: {report_name}",
              f"Num of params: {len(params)} | Num of fields: {len(fields)}",
              f"Date range: from {start_date.isoformat()} to {end_date.isoformat()}\n",
              sep="\n")

        # Convert fields list to comma-separated string
        fields_comma_separated = ','.join(fields)

        # Construct the API request URL
        url = "/".join(s.strip("/") for s in [self.api_base_url, ad_account_id, "insights"])

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
                # Parse the response JSON into a DataFrame
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

                # quota_info = response.headers.get('x-business-use-case-usage')
                # logging.info(f"Remaining quota: {quota_info}")

            else:
                raise Exception(
                    f"""API request failed with Error code: {response.status_code}, header: {response.headers}, body: {response.text}""")  # noqa

        flattened_response = self._flatten_facebook_ads_response(response_data)

        cleaned_response = self._clean_text_encoding(flattened_response)

        logging.info(f"Finished fetching full report with {len(cleaned_response)} rows")
        return cleaned_response

    @retry_on_api_error()
    def get_campaigns(self, ad_account_id: str, status: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Get campaigns from the specified ad account using requests and pass the access token as an authorization header.
        """

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        fields = ["id", "name", "buying_type", "objective", "primary_attribution",
                  "budget_remaining", "effective_status", "created_time", "updated_time"]

        params: dict[str, Any] = {
            "fields": ",".join(fields),
            "limit": 100
        }

        if status:
            params["filtering"] = json.dumps([{"field": "effective_status", "operator": "IN", "value": [status]}])

        url = f"https://graph.facebook.com/v19.0/{ad_account_id}/campaigns"

        logging.info(f"Trying to get Campaigns from account {ad_account_id}")

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            campaigns_data = data.get("data", [])
            logging.info(f"Fetched list with {len(campaigns_data)} items")

            # Filter campaigns to only include specified fields
            filtered_campaigns = [{field: campaign.get(field) for field in fields} for campaign in campaigns_data]

        except Exception as e:
            logging.error(e)
            raise Exception

        return filtered_campaigns

    def _flatten_action_list(self, list_of_dicts: list[dict[str, Any]]) -> dict[str, Any]:

        if not isinstance(list_of_dicts, list):
            return None

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

    def _flatten_facebook_ads_response(self, response: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Converts the Facebook Marketing API json response key `data` to dataFrame.

        Parameters:
        - response: The Facebook Marketing API response key `data` in json dict format.

        Returns:
        - DataFrame: Pandas DataFrame containing MetaAds report data.

        Raises:
        - DataProcessingError: If DataFrame conversion fails
        """
        try:
            if not response:
                logging.info("Response is empty, creating empty DataFrame")
                return []

            # Check if response is a list of dictionaries (list[dict[str, Any]])
            if not isinstance(response, list) or not all(isinstance(item, dict) for item in response):
                raise DataProcessingError("API response must be a json like object or a list of dictionaries")

            # Create a copy to avoid modifying the original
            flattened_response = []

            list_of_dict_columns = [
                "actions", "conversions", "conversion_values",
                "converted_product_quantity", "converted_product_value",
            ]

            video_actions_columns = [
                "video_play_actions", "video_p25_watched_actions", "video_p50_watched_actions",
                "video_p75_watched_actions", "video_p100_watched_actions",
            ]

            for row in response:
                flattened_row = row.copy()

                for column in list_of_dict_columns:
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

                # Add the flattened row to the response
                flattened_response.append(flattened_row)

            return flattened_response

        except Exception as e:
            raise DataProcessingError(
                "Failed to convert API response to DataFrame", original_error=e) from e
