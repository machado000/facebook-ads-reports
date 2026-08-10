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

from datetime import date, datetime, timezone
from requests.exceptions import RequestException
from typing import Any, Dict, Literal, NoReturn
from .exceptions import APIError, AuthenticationError, DataProcessingError, ValidationError
from .retry import retry_on_api_error
from .utils import validate_account_id, convert_keys_case, sanitize_column_name

# Set timeout for all http connections
TIMEOUT_IN_SEC = 60 * 3  # seconds timeout limit
socket.setdefaulttimeout(TIMEOUT_IN_SEC)

# Insights fields that return a list of {"action_type": ..., "value": ...} entries.
# Each entry is hoisted into its own column named `{prefix}{action_type}`.
#
# `actions` stays unprefixed for backward compatibility; every other family carries a
# prefix so that value-bearing metrics (revenue, ROAS, conversion values) do not
# overwrite the action counts that share the same `action_type` key.
ACTION_COLUMN_PREFIXES: dict[str, str] = {
    "actions": "",
    "action_values": "value_",
    "conversions": "conversion_",
    "conversion_values": "conversion_value_",
    "converted_product_quantity": "converted_product_quantity_",
    "converted_product_value": "converted_product_value_",
    "purchase_roas": "roas_",
    "website_purchase_roas": "website_roas_",
    "cost_per_action_type": "cost_per_",
}

# Graph API error codes that indicate the token, not the request, is the problem.
AUTH_ERROR_CODES = {102, 190, 200, 10, 2500}

# Graph API error codes for throttling. These are transient: back off and retry.
# 4 = app-level, 17 = user-level, 32 = page-level, 613 = custom rate limit,
# 800xx = ads insights / ads management throttling.
RATE_LIMIT_ERROR_CODES = {
    4, 17, 32, 613,
    80000, 80001, 80002, 80003, 80004, 80005, 80006, 80008, 80009, 80014,
}


logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)


def _parse_retry_after(header_value: str | None) -> float | None:
    """Parse a Retry-After header expressed in seconds, ignoring HTTP-date form."""
    if not header_value:
        return None
    try:
        return float(header_value)
    except ValueError:
        return None


class MetaAdsReport:
    """
    MetaAdsReport class for interacting with the Facebook Marketing API v25.0.
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
            self.api_version = "v25.0"
            self.api_base_url = f"https://graph.facebook.com/{self.api_version}"

        except Exception as e:
            raise KeyError("credentials_dict must contain 'access_token' key") from e

        # Optional. When both are present, verify_token() authenticates the /debug_token
        # call with an app access token, which is the reliable way to inspect a token
        # the caller does not personally own (for example a Business Manager system user).
        self.app_id = credentials_dict.get("app_id")
        self.app_secret = credentials_dict.get("app_secret")

    def verify_token(self, required_scopes: list[str] | None = None) -> dict[str, Any]:
        """
        Inspect the configured access token via the Graph API `/debug_token` endpoint.

        Surfaces validity, token type, expiry, and granted scopes so that credential
        problems fail fast with a clear message instead of surfacing as an opaque 401
        in the middle of an extraction.

        Args:
            required_scopes (list[str] | None): Scopes that must be present. When given
                and any are missing, AuthenticationError is raised.

        Returns:
            dict[str, Any]: Token metadata with these keys:
                - is_valid (bool)
                - type (str): e.g. 'USER', 'SYSTEM_USER'
                - app_id (str | None), application (str | None), user_id (str | None)
                - expires_at (datetime | None): None when the token never expires
                - never_expires (bool): True for system user tokens
                - data_access_expires_at (datetime | None)
                - scopes (list[str]), granular_scopes (list[dict])
                - missing_scopes (list[str]): empty unless required_scopes was given

        Raises:
            AuthenticationError: If the token is invalid, expired, the debug call fails,
                or required scopes are missing.
        """
        # An app access token ('{app_id}|{app_secret}') can inspect any token issued for
        # that app. Without app credentials, fall back to self-inspection, which only
        # works when the token holder has a role on the app.
        if self.app_id and self.app_secret:
            inspector_token = f"{self.app_id}|{self.app_secret}"
        else:
            inspector_token = self.access_token
            logging.debug("No app_id/app_secret in credentials; inspecting token with itself")

        try:
            response = requests.get(
                f"https://graph.facebook.com/{self.api_version}/debug_token",
                params={"input_token": self.access_token, "access_token": inspector_token},
                timeout=30,
            )
        except RequestException as e:
            raise AuthenticationError("Failed to reach the token debug endpoint", original_error=e) from e

        payload = response.json() if response.content else {}

        if response.status_code != 200:
            error = payload.get("error", {})
            raise AuthenticationError(
                f"Token verification failed: {error.get('message', response.text)}",
                status_code=response.status_code,
                error_code=error.get("code"),
                error_subcode=error.get("error_subcode"),
            )

        data: dict[str, Any] = payload.get("data", {})

        if not data.get("is_valid"):
            error = data.get("error", {})
            raise AuthenticationError(
                f"Access token is not valid: {error.get('message', 'no reason reported')}",
                error_code=error.get("code"),
                error_subcode=error.get("error_subcode"),
            )

        # /debug_token reports 0 (or omits the key) for tokens that never expire.
        def _as_datetime(timestamp: Any) -> datetime | None:
            if not timestamp:
                return None
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)

        expires_at = _as_datetime(data.get("expires_at"))

        if expires_at is not None and expires_at <= datetime.now(tz=timezone.utc):
            raise AuthenticationError(f"Access token expired at {expires_at.isoformat()}")

        scopes: list[str] = data.get("scopes", [])
        missing_scopes = [s for s in (required_scopes or []) if s not in scopes]

        if missing_scopes:
            raise AuthenticationError(
                f"Access token is missing required scopes: {', '.join(missing_scopes)}",
                granted_scopes=scopes,
            )

        result = {
            "is_valid": True,
            "type": data.get("type"),
            "app_id": data.get("app_id"),
            "application": data.get("application"),
            "user_id": data.get("user_id"),
            "expires_at": expires_at,
            "never_expires": expires_at is None,
            "data_access_expires_at": _as_datetime(data.get("data_access_expires_at")),
            "scopes": scopes,
            "granular_scopes": data.get("granular_scopes", []),
            "missing_scopes": missing_scopes,
        }

        expiry_note = "never expires" if result["never_expires"] else f"expires {expires_at.isoformat()}"  # type: ignore[union-attr]  # noqa: E501
        logging.info(f"Token OK - type={result['type']}, {expiry_note}, scopes={', '.join(scopes) or 'none'}")

        return result

    @retry_on_api_error()
    def get_report(self, ad_account_id: str, report_model: Dict[str, Any],
                   start_date: date | None, end_date: date | None,
                   flatten: bool = False, limit: int = 200) -> list[dict[str, Any]]:
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
                self._raise_for_error_response(response, report_name)

        response_data_snake_case = convert_keys_case(response_data, case="snake")

        if flatten:
            flattened_response = self._flatten_facebook_ads_response(
                response_data_snake_case, report_model.get("action_types"))
        else:
            flattened_response = response_data

        cleaned_response = self._clean_text_encoding(flattened_response)

        logging.info(f"Finished fetching full report with {len(cleaned_response)} rows")
        return cleaned_response

    def _raise_for_error_response(self, response: requests.Response, report_name: str) -> NoReturn:
        """
        Translate a non-200 Graph API response into a typed exception.

        Classifies the failure so that `@retry_on_api_error` can decide whether to back
        off and retry. Rate limits and transient server errors become retryable APIError
        instances; token problems become AuthenticationError, which is never retried.

        Args:
            response (requests.Response): The failed response.
            report_name (str): Report being extracted, for error context.

        Raises:
            AuthenticationError: For token/permission failures.
            APIError: For every other non-200 response.
        """
        try:
            error = response.json().get("error", {})
        except ValueError:
            error = {}

        message = error.get("message") or response.text[:200] or "no error message returned"
        error_code = error.get("code")
        error_subcode = error.get("error_subcode")

        # Detail travels in structured context instead of a multi-kilobyte header dump.
        context: dict[str, Any] = {
            "report_name": report_name,
            "status_code": response.status_code,
            "error_code": error_code,
            "error_subcode": error_subcode,
            "error_type": error.get("type"),
            "is_transient": bool(error.get("is_transient", False)),
            "fbtrace_id": error.get("fbtrace_id"),
            "is_rate_limit": error_code in RATE_LIMIT_ERROR_CODES or response.status_code == 429,
            "retry_after": _parse_retry_after(response.headers.get("Retry-After")),
            "throttle": response.headers.get("x-fb-ads-insights-throttle"),
        }

        if error_code in AUTH_ERROR_CODES or response.status_code == 401:
            raise AuthenticationError(
                f"Facebook Marketing API rejected the access token: {message}", **context)

        raise APIError(
            f"Facebook Marketing API request failed ({response.status_code}) "
            f"for {report_name}: {message}", **context)

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

    def _flatten_action_list(self, list_of_dicts: list[dict[str, Any]],
                             prefix: str = "",
                             allowed_action_types: set[str] | None = None) -> dict[str, Any]:
        """
        Flatten a list of {"action_type": ..., "value": ...} entries into columns.

        Args:
            list_of_dicts: The raw action list from the API.
            prefix: Column-name prefix identifying the source field. See
                ACTION_COLUMN_PREFIXES.
            allowed_action_types: When given, only these raw action types are kept.
                Matching happens before the prefix is applied, so a single entry
                controls the count, value and ROAS columns derived from it.

        Returns:
            dict[str, Any]: Mapping of the sanitized `{prefix}{action_type}` to its value.
        """
        if not isinstance(list_of_dicts, list):
            return {}

        flattened_dict: dict[str, Any] = {}

        for item in list_of_dicts:
            if not isinstance(item, dict) or "action_type" not in item:
                continue

            action_type = item["action_type"]

            if allowed_action_types is not None and action_type not in allowed_action_types:
                continue

            column_name = sanitize_column_name(f"{prefix}{action_type}")
            flattened_dict[column_name] = item.get("value")

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

    def _flatten_facebook_ads_response(self, response: list[dict[str, Any]],
                                       action_types: list[str] | None = None) -> list[dict[str, Any]]:
        """
        Flatten nested fields from the Facebook Marketing API `data` payload.

        Parameters:
        - response: The Facebook Marketing API `data` list of dictionaries.
        - action_types: Optional allow-list of raw action types. When empty or omitted,
          every action type returned by the API is kept.

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

            # An empty list means "no filtering", which keeps the parameter optional for
            # every report model that does not declare one.
            allowed_action_types = set(action_types) if action_types else None

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

                for column, prefix in ACTION_COLUMN_PREFIXES.items():
                    if column in flattened_row:
                        logging.debug(f"Flattening column '{column}' with prefix '{prefix}'")

                        # Flatten the list of dicts to a single dict
                        flattened_dict = self._flatten_action_list(
                            flattened_row[column], prefix, allowed_action_types)

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
