"""
Facebook Marketing API client module.

This module contains the main MetaAdsReport class for interacting with the Facebook Marketing API.
https://developers.facebook.com/docs/business-sdk/getting-started
https://developers.facebook.com/docs/marketing-api/reference/ads-insights
https://developers.facebook.com/tools/debug/accesstoken
"""
import json
import logging
import pandas as pd
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

    def __init__(self, credentials_json: Dict[str, str]):
        """
        Initializes the MetaAdsReport instance.

        Parameters:
        - credentials_json (dict): The JSON credentials for authentication.

        Raises:
        - AuthenticationError: If credentials are invalid or authentication fails
        - ValidationError: If credentials_json format is invalid
        """
        if not isinstance(credentials_json, dict):
            raise ValidationError("credentials_json must be a dictionary")

        if not credentials_json:
            raise ValidationError("credentials_json cannot be empty")

        try:
            self.app_id = credentials_json["app_id"]
            self.access_token = credentials_json["access_token"]
            self.ad_account_id = credentials_json["ad_account_id"]
            self.api_base_url = credentials_json["base_url"]

        except Exception as e:
            raise KeyError("credentials_json must contain 'app_id' and 'access_token' keys") from e

    @retry_on_api_error()
    def get_insights_report(self, ad_account_id: str, report_model: dict,
                            start_date: date, end_date: date, limit: int = 500):
        """
        Get insights report from Facebook Marketing API.

        Parameters:
        - ad_account_id (str): Ad account ID.
        - report_model (dict): Report model containing fields and params.
        - start_date (date): Start date for the report.
        - end_date (date): End date for the report.

        Returns:
        - DataFrame: Report data as a pandas DataFrame.
        """
        # Validate account ID format
        ad_account_id = validate_account_id(ad_account_id)

        # Convert datetime objects to strings
        start_date_format = start_date.strftime("%Y-%m-%d") if isinstance(start_date, (date, datetime)) else start_date
        end_date_format = end_date.strftime("%Y-%m-%d") if isinstance(end_date, (date, datetime)) else end_date

        report_name = report_model["report_name"]
        fields = report_model["fields"]
        params = report_model["params"]
        action_types = report_model.get("action_types")

        # Set time_range parameter if not ads_dimensions_report
        if report_name != "ads_dimensions_report":
            params["time_range"] = {"since": start_date_format, "until": end_date_format}

        # Display request parameters
        print(f"INFO  - Trying to get Ad_Insights report with `{self.api_base_url}`",
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

        df = self._convert_response_to_df(response_data, action_types)

        # Fix data types for database storage
        df = self._fix_data_types(df)

        # Handle missing values
        df = self._handle_missing_values(df, fill_numeric_values=None, fill_datetime_values=None, fill_object_values="")

        # Clean text encoding issues
        df = self._clean_text_encoding(df)

        # Return the final DataFrame
        logging.info(f"Finished fetching full report with {df.shape[0]} rows and {df.shape[1]} columns")
        return df

    @retry_on_api_error()
    def get_campaigns(self, ad_account_id: str, status: Optional[str] = None):
        """
        Get campaigns from the specified ad account using requests and pass the access token as an authorization header.
        """

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        fields = ["id", "name", "buying_type", "objective", "primary_attribution",
                  "budget_remaining", "effective_status", "created_time", "updated_time"]

        params = {
            "fields": ",".join(fields),
            "limit": 100
        }

        if status:
            params["filtering"] = [{"field": "effective_status", "operator": "IN", "value": [status]}]

        url = f"https://graph.facebook.com/v19.0/{ad_account_id}/campaigns"

        logging.info(f"Trying to get Campaigns from account {ad_account_id}")

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            campaigns = data.get("data", [])
            logging.info(f"Fetched list with {len(campaigns)} items")

            df = pd.DataFrame(campaigns)
            ordered_df = df[fields]

        except Exception as e:
            logging.error(e)
            raise Exception

        return ordered_df

    def _flatten_list_of_collections(self, collection_list: list):
        """
        Flattens a list of dictionaries into a single dictionary.

        Parameters:
        - collection_list (list): A list of dictionaries, where each dictionary
        represents a collection with "action_type" and "value" keys.

        Returns:
        - dict or None: A dictionary where "action_type" values are used as keys
        and corresponding "value" values are used as values. Returns None if
        the input is not a list.
        """
        if not isinstance(collection_list, list):
            return None

        flattened_dict = {item["action_type"]: item["value"] for item in collection_list}

        return flattened_dict

    def _extract_columns_from_dict(self, dataframe, dict_column_name: str, keys_to_extract: Optional[list] = None):
        dict_list = []

        for _, row in dataframe.iterrows():
            if row[dict_column_name]:
                dict_list.append(row[dict_column_name])
            else:
                dict_list.append({})

        temp_df = pd.DataFrame(dict_list)

        if not keys_to_extract:
            existing_keys = list(temp_df.columns)
        else:
            existing_keys = [col for col in keys_to_extract if col in temp_df.columns]

        result_df = temp_df.loc[:, existing_keys]
        logging.debug(result_df)

        return result_df

    def _extract_single_column_from_dict(self, dataframe, dict_column_name: str, rename_key: bool = True):
        dict_list = []

        for _, row in dataframe.iterrows():
            if row[dict_column_name]:
                dict_list.append(row[dict_column_name])
            else:
                dict_list.append({})

        temp_df = pd.DataFrame(dict_list)

        if temp_df.shape[1] != 1:
            logging.error(f"More than one key found in column '{dict_column_name}' collections.")
            temp_df = pd.DataFrame()

        if rename_key:
            # Rename the first data column
            temp_df.columns.values[0] = dict_column_name.strip("_actions_flat")

        logging.debug(temp_df)

        return temp_df

    def _extract_unique_keys(self, dict_list: list):
        """
        Extract unique keys from a list of dictionaries.

        Parameters:
        - dict_list (list): A list of dictionaries to extract keys from.

        Returns:
        - list: A list containing unique keys from all dictionaries in dict_list.
        """
        unique_keys = set()

        for row in dict_list:
            if row and isinstance(row, dict):
                unique_keys.update(row.keys())

        unique_keys = list(unique_keys)
        logging.info(f"Extracted {len(unique_keys)} unique_keys.")
        logging.debug(unique_keys)

        return unique_keys

    def _convert_response_to_df(self, response: list[dict[str, Any]],
                                action_types: Optional[list] = None) -> pd.DataFrame:
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
                return pd.DataFrame()

            # Check if response is a list of dictionaries (list[dict[str, Any]])
            if not isinstance(response, list) or not all(isinstance(item, dict) for item in response):
                raise DataProcessingError("API response must be a json like object or a list of dictionaries")

            # Create a DataFrame from the response data
            df = pd.json_normalize(response)

            # Flatten multiple dict column in list
            single_dict_columns = [
                "actions", "conversions", "conversion_values",
                "converted_product_quantity", "converted_product_value",
            ]

            for item in single_dict_columns:
                if item in df.columns.values:
                    logging.debug(f"Flattening column '{item}'")

                    item_flat = f"{item}_flat"
                    df[item_flat] = df[item].apply(self._flatten_list_of_collections)

                    new_df = self._extract_columns_from_dict(
                        dataframe=df, dict_column_name=item_flat, keys_to_extract=action_types)

                    df = df.drop(columns=[item])
                    df = df.drop(columns=[item_flat])
                    df = pd.concat([df, new_df], axis=1)

            # Flatten single dict columns in list
            single_dict_columns = [
                "video_play_actions", "video_p25_watched_actions", "video_p50_watched_actions",
                "video_p75_watched_actions", "video_p100_watched_actions",
            ]

            for item in single_dict_columns:
                if item in df.columns.values:
                    logging.debug(f"Flattening column '{item}'")

                    item_flat = f"{item}_flat"
                    df[item_flat] = df[item].apply(self._flatten_list_of_collections)

                    new_df = self._extract_single_column_from_dict(dataframe=df, dict_column_name=item_flat)

                    df = df.drop(columns=[item])
                    df = df.drop(columns=[item_flat])
                    df = pd.concat([df, new_df], axis=1)

            return df

        except Exception as e:
            raise DataProcessingError(
                "Failed to convert API response to DataFrame", original_error=e) from e

    def _fix_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Optimizes data types for database storage.
        """

        df = df.copy()

        try:
            # 1. Fix date columns (these come as strings from API)
            datetime_terms = ['date', 'time', 'created', 'updated', 'inserted']
            date_columns = [col for col in df.columns if any(term in col for term in datetime_terms)]
            for col in date_columns:
                if col in df.columns and df[col].dtype == 'object':
                    df[col] = pd.to_datetime(df[col], errors='raise')  # Fail fast if dates are invalid
                    logging.debug(f"Converted {col} to datetime")

            # 2. Dynamically find and convert metric columns that come as 'object' but should be numeric
            metrics_to_convert = []

            # Find all columns that do not match exclude_terms and are currently 'object' type
            exclude_terms = ['id', 'name', 'type', 'platform', 'date']
            for col in df.columns:
                if df[col].dtype == 'object' and not any(
                    col == term or
                    col.startswith(f"{term}_") or
                    col.endswith(f"_{term}")
                    for term in exclude_terms
                ):
                    metrics_to_convert.append(col)

            logging.debug(f"Columns considered for numeric conversion: {metrics_to_convert}")

            for col in metrics_to_convert:
                logging.debug(
                    f"Column '{col}' dtype before: {df[col].dtype}, sample values: {df[col].head(5).tolist()}")
                try:
                    # First convert to numeric to see what we get
                    numeric_series = pd.to_numeric(df[col], errors='raise')

                    # Determine if it should be int or float based on the data
                    if self._should_be_integer(numeric_series):
                        df[col] = numeric_series.astype('Int64')
                        logging.debug(f"Converted {col} from numeric to Int64")
                    else:
                        df[col] = numeric_series.astype('float64')
                        logging.debug(f"Converted {col} from numeric to float64")

                except ValueError as e:
                    logging.warning(f"Could not convert {col} to numeric: {e}")
                    # Keep as object type if conversion fails

                logging.debug(f"Column '{col}' dtype after: {df[col].dtype}, sample values: {df[col].head(5).tolist()}")

            return df

        except Exception as e:
            logging.error(f"Data type optimization failed: {e}")
            return df

    def _should_be_integer(self, numeric_series: pd.Series) -> bool:
        """
        Determines if a numeric series should be stored as integer or float.

        Parameters:
        - numeric_series: The pandas Series with numeric data

        Returns:
        - bool: True if should be integer, False if should be float
        """
        # Remove NaN values for analysis
        clean_series = numeric_series.dropna()

        if len(clean_series) == 0:
            return False  # Default to float if no data

        # If all values are whole numbers, use integer
        if (clean_series % 1 == 0).all():
            return True

        return False  # Has decimals, should be float

    def _handle_missing_values(self, df: pd.DataFrame,
                               fill_numeric_values: Optional[str] = None,
                               fill_datetime_values: Optional[str] = None,
                               fill_object_values: str = "") -> pd.DataFrame:
        """
        Handles missing values appropriately based on column types.

        Parameters:
        - fill_numeric_values: Value to fill NaN in numeric columns (empty = preserve NaN)
        - fill_datetime_values: Value to fill NaT in datetime columns (empty = preserve NaT)
        - fill_object_values: Value to fill NaN in object/text columns (empty string by default)
        """

        if not fill_datetime_values and not fill_numeric_values and not fill_object_values:
            logging.debug("No fill values provided, preserving NaN/NaT for numeric and datetime columns")
            return df

        try:
            for col in df.columns:
                # Case 1: Numeric columns (int, float)
                if pd.api.types.is_numeric_dtype(df[col]) and fill_numeric_values not in (None, ""):
                    try:
                        # Attempt to convert to numeric value
                        if fill_numeric_values is not None:
                            fill_val = float(fill_numeric_values)
                            df[col] = df[col].fillna(fill_val)
                    except (ValueError, TypeError):
                        pass  # Keep NaN if conversion fails

                # Case 2: Datetime columns
                elif pd.api.types.is_datetime64_any_dtype(df[col]) and fill_datetime_values not in (None, ""):
                    try:
                        # Attempt to convert to datetime
                        if fill_datetime_values is not None:
                            fill_datetime = pd.to_datetime(fill_datetime_values, errors='raise')
                            df[col] = df[col].fillna(fill_datetime)
                    except (ValueError, TypeError, pd.errors.ParserError):
                        pass  # Keep NaT if conversion fails

                # Case 3: Object columns (text, categorical)
                elif pd.api.types.is_object_dtype(df[col]) and fill_object_values != "":
                    # Always fill object columns with the specified value
                    df[col] = df[col].fillna(fill_object_values)

            return df

        except Exception as e:
            logging.warning(f"Missing value handling failed: {e}")
            return df

    def _clean_text_encoding(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans text columns for character encoding issues.
        """
        try:
            for col in df.select_dtypes(include=['object']).columns:
                if df[col].dtype == 'object':
                    # Handle common encoding issues
                    df[col] = df[col].astype(str)
                    # Remove or replace problematic characters
                    df[col] = df[col].str.replace(r'[^\x00-\x7F]+', '', regex=True)  # Remove non-ASCII
                    df[col] = df[col].str.replace('\x00', '', regex=False)  # Remove null bytes
                    df[col] = df[col].str.replace(r'[\r\n]+', ' ', regex=True)  # Remove line breaks
                    df[col] = df[col].str.strip()  # Remove leading/trailing whitespace
                    # Limit string length for database compatibility (adjust as needed)
                    df[col] = df[col].str[:255]
            return df

        except Exception as e:
            logging.warning(f"Character encoding cleanup failed: {e}")
            return df
