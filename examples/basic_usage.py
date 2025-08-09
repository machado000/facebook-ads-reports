"""
Basic Facebook Ads Report Example

This example demonstrates the basic usage of the google-ads-drv package
to extract data from Facebook Ads API and export it to CSV.
"""
import logging
import os
from datetime import date, timedelta
from dotenv import load_dotenv

from facebook_ads_reports import MetaAdsReport, MetaAdsReportModel
from facebook_ads_reports import create_output_directory, format_report_filename, load_credentials, setup_logging


def main():
    # Setup logging
    setup_logging(level=logging.INFO)

    # Load credentials from the default location
    try:
        # Will look in secrets/fb_business_config.json by default
        credentials = load_credentials("./secrets/fub-sp_config.json")
    except Exception as e:
        logging.error("Could not find Facebook Ads credentials file. Please ensure you have "
                      "a fb_business_config.json file in the secrets/ directory or specify the path.")
        logging.error(f"Error: {e}")
        return

    # Initialize the Facebook Ads client
    meta_api_client = MetaAdsReport(credentials_json=credentials)
    report_model = MetaAdsReportModel.ad_performance_report

    # Report parameters
    load_dotenv()
    AD_ACCOUNT_ID = os.getenv("AD_ACCOUNT_ID") or "1234567890"  # Replace with your actual account ID

    start_date = date.today() - timedelta(days=1)  # Last 7 days
    end_date = date.today() - timedelta(days=1)    # Until yesterday

    try:
        # Extract the report data
        logging.info(f"Extracting '{report_model['report_name']}' for account '{AD_ACCOUNT_ID}'")

        df = meta_api_client.get_insights_report(AD_ACCOUNT_ID, report_model, start_date, end_date)

        # Save to CSV
        output_filename = format_report_filename(
            account_id=AD_ACCOUNT_ID,
            report_name=report_model['report_name'],
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )

        # Save to file
        output_dir = create_output_directory("reports_output")
        file_path = output_dir / output_filename
        df.to_csv(file_path, index=False)

        logging.info(f"Report saved to {output_filename}")

        # Display basic info
        print("\nReport Summary:")
        print(f"- Rows: {len(df)}")
        print(f"- Columns: {len(df.columns)}")
        print(f"- Date range: {start_date} to {end_date}")
        print(f"- Output file: {file_path}")

        # Show column names
        print("\nColumns:")
        print(df.columns.tolist())

        # Show first few rows
        print("\nFirst 5 rows:")
        print(df.head())

    except Exception as e:
        logging.error(f"Error extracting report: {e}")
        raise


if __name__ == "__main__":
    main()
