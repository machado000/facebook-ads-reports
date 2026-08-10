"""
Facebook Marketing API report models module.

This module contains pre-configured report models for different types of Facebook Marketing API reports.
"""
from typing import Any, Optional


class MetaAdsReportModel:
    """
    MetaAdsReportModel class defines pre-configured report models for Facebook Ads (FBAds).

    Report Models:
    - ad_accounts_report
    - campaigns_report
    - adsets_report
    - ad_summary_report
    - ad_dimensions_report
    - ad_insights_report
    - ad_performance_report (compatibility alias)
    """

    ad_accounts_report = {
        "report_name": "ad_accounts_report",
        "endpoint": "adaccounts",
        "fields": [
            "id",
            "account_id",
            "name",
            "business",
            "tax_id",
            "account_status",
            "age",
            "disable_reason",
            "created_time",
            "timezone_id",
            "timezone_name",
            "currency",
            "is_prepay_account",
            "spend_cap",
            "balance",
            "amount_spent",
            "min_campaign_group_spend_cap",
            "capabilities"
        ],
        "params": {
            "filtering": [],
            "sort": ["tax_id", "name"]
        },
        "table_name": "meta_ads_adaccounts",
        "constraint_column": ["account_id"],
    }

    campaigns_report = {
        "report_name": "campaigns_report",
        "endpoint": "campaigns",
        "fields": [
            "account_id",
            "account_name",
            "id",
            "name",
            "buying_type",
            "objective",
            "configured_status",
            "effective_status",
            "status",
            "bid_strategy",
            "daily_budget",
            "budget_remaining",
            "lifetime_budget",
            "spend_cap",
            "start_time",
            "stop_time",
            "created_time",
            "updated_time",
            "boosted_object_id",
        ],
        "params": {
            "date_preset": "maximum",
            "filtering": [],
            "sort": ["id"]
        },
        "table_name": "meta_ads_campaigns",
        "constraint_column": ["account_id", "id"],
    }

    adsets_report = {
        "report_name": "adsets_report",
        "endpoint": "adsets",
        "fields": [
            "account_id",
            "campaign_id",
            "id",
            "name",
            "status",
            "billing_event",
            "daily_budget",
            "budget_remaining",
            "lifetime_budget",
            "start_time",
            "end_time",
            "created_time",
            "updated_time",
            "targeting",
            "learning_stage_info",
            "recommendations",
        ],
        "params": {
            "date_preset": "maximum",
            "filtering": [],
            "sort": ["created_time"]
        },
        "table_name": "meta_ads_adsets",
        "constraint_column": ["id"],
    }

    ad_summary_report = {
        "report_name": "ad_summary_report",
        "endpoint": "ads",
        "fields": [
            "account_id",
            "campaign_id",
            "adset_id",
            "id",
            "name",
            "bid_type",
            "configured_status",
            "effective_status",
            "status",
            "created_time",
            "updated_time",
            "targeting",
            "recommendations",
        ],
        "params": {
            "date_preset": "maximum",
            "filtering": [],
            "sort": ["id"]
        },
        "table_name": "meta_ads_adsummary",
        "constraint_column": ["id"],
    }

    ad_dimensions_report = {
        "report_name": "ad_dimensions_report",
        "endpoint": "insights",
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
        ],
        "params": {
            "level": "ad",
            "date_preset": "maximum",
            "filtering": [],
            "sort": ["ad_id"]
        },
        "table_name": "meta_ads_addimensions",
        "constraint_column": ["ad_id"],
    }

    ad_insights_report = {
        "report_name": "ad_insights_report",
        "endpoint": "insights",
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
            "objective",
            "optimization_goal",
            "spend",
            "impressions",
            "clicks",
            "reach",
            "frequency",
            "actions",
            "action_values",
            "conversion_values",
            "purchase_roas",
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
            "date_preset": "last_3d",  # overwrited if start_date is passed
            "time_increment": 1,
            "action_breakdowns": ["action_type", "action_video_type"],
            "breakdowns": ["publisher_platform", "platform_position"],
            "filtering": [],
            "sort": ["date_start", "ad_id"]
        },
        # Allow-list applied to every action-list field (`actions`, `action_values`,
        # `purchase_roas`, ...) after the API responds. Filtering is on the raw
        # `action_type`, so one entry controls the count, the value and the ROAS column
        # it produces. An empty list or a missing key keeps every action type.
        #
        # Meta reports the same conversion under several overlapping scopes:
        #   offsite_conversion.*  pixel/CAPI only, on the advertiser's own property
        #   onsite_conversion.*   happened inside Facebook/Instagram/Messenger/WhatsApp
        #   onsite_web_*, web_in_store_*, web_app_in_store_*  partial channel rollups
        #   omni_*                deduplicated total across web, app, offline and Shops
        # `omni_*` is the spine here: it is what Ads Manager reports and what delivery
        # optimises toward. The narrower scopes stay commented out because they are
        # subsets of it, identical row-for-row unless an app, offline uploads or Shops
        # checkout are in play. Uncomment `offsite_conversion.*` to measure pixel
        # coverage gaps as `omni_purchase - offsite_conversion.fb_pixel_purchase`.
        "action_types": [
            # conversions - omni spine
            "omni_purchase",
            "omni_add_to_cart",
            "omni_initiated_checkout",
            "omni_view_content",
            "omni_search",
            "omni_add_to_wishlist",
            "add_payment_info",  # no omni_* variant is reported for this event
            # traffic and engagement
            "link_click",
            "landing_page_view",
            "page_engagement",
            "post_engagement",
            "post_reaction",
            "post",
            "comment",
            "like",
            "post_interaction_gross",
            "post_interaction_net",
            "video_view",
            # "onsite_conversion.messaging_conversation_started_7d",

            # -- pixel-only scope: subset of omni_*, enable to audit pixel coverage --
            # "offsite_conversion.fb_pixel_purchase",
            # "offsite_conversion.fb_pixel_add_to_cart",
            # "offsite_conversion.fb_pixel_initiate_checkout",
            # "offsite_conversion.fb_pixel_view_content",
            # "offsite_conversion.fb_pixel_search",
            # "offsite_conversion.fb_pixel_add_to_wishlist",
            # "offsite_conversion.fb_pixel_add_payment_info",

            # -- partial channel rollups: equal to omni_* without app/offline/Shops --
            # "onsite_web_purchase",
            # "onsite_web_app_purchase",
            # "onsite_web_add_to_cart",
            # "onsite_web_app_add_to_cart",
            # "onsite_web_initiate_checkout",
            # "onsite_web_view_content",
            # "onsite_web_app_view_content",
            # "web_in_store_purchase",
            # "web_app_in_store_purchase",

            # -- legacy bare aggregates: duplicate the omni_* entries above --
            # "purchase",
            # "add_to_cart",
            # "initiate_checkout",
            # "view_content",
            # "search",
            # "add_to_wishlist",
            # "omni_landing_page_view",

            # -- post-level engagement detail --
            # "onsite_conversion.post_save",
            # "onsite_conversion.post_unsave",
            # "onsite_conversion.post_unlike",
            # "onsite_conversion.post_net_like",
            # "onsite_conversion.post_net_save",
            # "onsite_conversion.post_net_comment",
            # "onsite_conversion.total_messaging_connection",
        ],
        "table_name": "meta_ads_adinsights",
        "date_column": "date_start",
        "constraint_column": [
            "account_id", "ad_id", "date_start", "publisher_platform", "platform_position",
        ],
    }

    # Backward-compatible alias kept for existing integrations.
    ad_performance_report = ad_insights_report

    @classmethod
    def get_all_reports(cls) -> dict[str, dict[str, Any]]:
        """
        Get all available report models.

        Returns:
            dict[str, dict[str, Any]]: Dictionary of all report models
        """
        return {
            "ad_accounts_report": cls.ad_accounts_report,
            "campaigns_report": cls.campaigns_report,
            "adsets_report": cls.adsets_report,
            "ad_summary_report": cls.ad_summary_report,
            'ad_dimensions_report': cls.ad_dimensions_report,
            'ad_insights_report': cls.ad_insights_report,
            'ad_performance_report': cls.ad_performance_report,
        }

    @classmethod
    def get_report_by_name(cls, report_name: str) -> Optional[dict[str, Any]]:
        """
        Get a specific report model by name.

        Args:
            report_name (str): The name of the report model

        Returns:
            Optional[dict[str, Any]]: The report model if found, None otherwise
        """
        all_reports = cls.get_all_reports()
        return all_reports.get(report_name)

    @classmethod
    def list_available_reports(cls) -> list[str]:
        """
        List all available report names.

        Returns:
            list[str]: List of available report names
        """
        return sorted(cls.get_all_reports().keys())


# Factory function for creating custom report models

def create_custom_report(
    report_name: str,
    select: list[str],
    from_table: str,
    order_by: Optional[str] = None,
    where: Optional[str] = None,
    table_name: Optional[str] = None,
    date_column: str = "date"
) -> dict[str, Any]:
    """
    Create a custom Facebook Ads report model configuration.

    Args:
        report_name (str): Name of the custom report
        select (list[str]): List of fields to select
        from_table (str): Table to query from
        order_by (Optional[str]): Field to order by (besides date)
        where (Optional[str]): Additional WHERE clause conditions
        table_name (Optional[str]): Target table name for ETL
        date_column (str): Date column name

    Returns:
        dict[str, Any]: Custom report model configuration
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
