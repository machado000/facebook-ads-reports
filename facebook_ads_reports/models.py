"""
Google Ads report models module.

This module contains pre-configured report models for different types of Google Ads reports.
"""
from typing import Any, Dict, List, Optional


class MetaAdsReportModel:
    """
    MetaAdsReportModel class defines pre-configured report models for Facebook Ads (FBAds).

    Report Models:
    - ad_dimensions_report
    - ad_performance_report
    """

    ad_dimensions_report = {
        "report_name": "ad_dimensions_report",
        "fields": [
            "ad_id",
            "adset_id",
            "campaign_id",
            "account_id",
            "ad_name",
            "adset_name",
            "campaign_name",
            "account_name",
            "buying_type",
            "attribution_setting",
            "objective",
            "optimization_goal",
            "date_start",
            "date_stop",
            "updated_time",
            "created_time",
        ],
        "params": {
            "level": "ad",
            "time_range": {"since": "yesterday", "until": "yesterday"},
            # "breakdowns": ["publisher_platform", "platform_position", "media_destination_url"],
            # "filtering": [],
            # "sort": ["ad_id"]
        },
        "action_types": [],
        "table_name": "olap__meta_ad_dimensions",
        "constraint_column": ["ad_id"],
    }

    ad_performance_report = {
        "report_name": "ad_performance_report",
        "fields": [
            "account_id",
            "campaign_id",
            "adset_id",
            "ad_id",
            "account_name",
            "campaign_name",
            "adset_name",
            "ad_name",
            "buying_type",
            "spend",
            "impressions",
            # "cpm",
            "clicks",
            # "cpc",
            "reach",
            "frequency",
            "actions",
            "video_play_actions",
            "video_p25_watched_actions",
            "video_p50_watched_actions",
            "video_p75_watched_actions",
            "video_p100_watched_actions",
            "date_start",
            "date_stop",
        ],
        "params": {
            "level": "ad",
            "time_range": {"since": "yesterday", "until": "yesterday"},  # overwrited if start_date is passed
            "time_increment": 1,
            "action_breakdowns": ["action_type"],
            "breakdowns": ["publisher_platform", "platform_position"],
            # "filtering": [],
            # "sort": ["ad_id"]
        },
        "action_types": [
            "add_payment_info",
            "add_to_cart",
            "comment",
            "complete_registration",
            "initiate_checkout",
            "landing_page_view",
            "lead",
            "link_click",
            "page_engagement",
            "post_engagement",
            "post_reaction",
            "post",
            "purchase",
            "view_content",
        ],
        "table_name": "olap__meta_ad_performance",
        "date_column": "date_start",
    }

    @classmethod
    def get_all_reports(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get all available report models.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of all report models
        """
        return {
            'ad_dimensions_report': cls.ad_dimensions_report,
            'ad_performance_report': cls.ad_performance_report,
        }

    @classmethod
    def get_report_by_name(cls, report_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific report model by name.

        Args:
            report_name (str): The name of the report model

        Returns:
            Optional[Dict[str, Any]]: The report model if found, None otherwise
        """
        all_reports = cls.get_all_reports()
        return all_reports.get(report_name)

    @classmethod
    def list_available_reports(cls) -> List[str]:
        """
        List all available report names.

        Returns:
            List[str]: List of available report names
        """
        return list(cls.get_all_reports().keys())


# Factory function for creating custom report models
def create_custom_report(report_name: str, select: List[str], from_table: str,
                         order_by: Optional[str] = None, where: Optional[str] = None,
                         table_name: Optional[str] = None,
                         date_column: str = "date") -> Dict[str, Any]:
    """
    Create a custom report model.

    Args:
        report_name (str): Name of the custom report
        select (List[str]): List of fields to select
        from_table (str): Table to query from
        order_by (Optional[str]): Field to order by (besides date)
        where (Optional[str]): Additional WHERE clause conditions
        table_name (Optional[str]): Target table name for ETL
        date_column (str): Date column name

    Returns:
        Dict[str, Any]: Custom report model configuration
    """
    report_model = {
        "report_name": report_name,
        "select": select,
        "from": from_table,
        "date_column": date_column,
    }

    if order_by:
        report_model["order_by"] = order_by

    if where:
        report_model["where"] = where

    if table_name:
        report_model["table_name"] = table_name

    return report_model
