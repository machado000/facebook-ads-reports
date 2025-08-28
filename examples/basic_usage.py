"""
Basic Facebook Ads Report Example

This example demonstrates the basic usage of the facebook-ads-reports package
to extract data from Facebook Ads API and export it to CSV.
"""
import json
import logging
import os
from datetime import date, timedelta
from dotenv import load_dotenv

from facebook_ads_reports import MetaAdsReport, MetaAdsReportModel
from facebook_ads_reports import create_output_directory, format_report_filename, load_credentials, setup_logging


def main() -> None:
    # Setup logging
    setup_logging(level=logging.INFO)

    # Load credentials from the default location
    load_dotenv()
    json_content = os.environ.get('FACEBOOK_ADS_CONFIG_JSON')

    if json_content:
        json_content = json_content.replace('\\n', '\n')  # Convert literal \\n to real newlines
        credentials = json.loads(json_content)
    else:
        try:
            credentials = load_credentials("./secrets/fb_business_config.json")
        except Exception as e:
            logging.error("Could not find credentials. Please ensure you have FACEBOOK_ADS_CONFIG_JSON variable set "
                          "or a 'fb_business_config.json' file in the secrets/ directory.")
            logging.error(f"Error: {e}")
            raise

    # Initialize the Facebook Ads client
    meta_api_client = MetaAdsReport(credentials_dict=credentials)
    report_model = MetaAdsReportModel.ad_performance_report

    # Report parameters
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
            report_name=report_model['report_name'],  # type: ignore
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
