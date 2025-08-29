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
from facebook_ads_reports.utils import (create_output_directory, format_report_filename,
                                        get_unique_keys_from_response, load_credentials,
                                        save_report_to_csv)


def main() -> None:
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    report_model = MetaAdsReportModel.ad_dimensions_report

    # Report parameters
    AD_ACCOUNT_ID = os.getenv("AD_ACCOUNT_ID") or "1234567890"  # Replace with your actual account ID

    start_date = date.today() - timedelta(days=2)
    end_date = date.today() - timedelta(days=2)

    try:
        # Extract the report data
        logging.info(f"Extracting '{report_model['report_name']}' for account '{AD_ACCOUNT_ID}'")

        report = meta_api_client.get_insights_report(AD_ACCOUNT_ID, report_model, start_date, end_date)

        # Save report as a local JSON file
        output_dir = create_output_directory("reports_output")

        # Save to CSV
        output_filename = format_report_filename(
            account_id=AD_ACCOUNT_ID,
            report_name=report_model['report_name'],  # type: ignore
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            file_extension="csv"
        )

        # Save to file
        file_path = output_dir / output_filename
        save_report_to_csv(report, str(file_path))

        logging.info(f"Report saved to {output_filename}")

        # Display basic info
        unique_keys = get_unique_keys_from_response(report)

        print("\nReport Summary:")
        print(f"- Rows: {len(report)}")
        print(f"- Columns: {len(unique_keys)}")
        print(f"- Date range: {start_date} to {end_date}")
        print(f"- Output file: {file_path}")

        # Show column names
        print("\nColumns:")
        print(unique_keys)

    except Exception as e:
        logging.error(f"Error extracting report: {e}")
        raise


if __name__ == "__main__":
    main()
