"""
Pixel Stats Example

Insights only returns conversions that Meta credited to an ad. The pixel's own `stats` edge
counts every event it received (paid, organic and direct), which is the only Graph API source
for events such as form completions or WhatsApp clicks that no ad got credit for.

This example reads hourly event counts, crosses them with the hostname, prints a daily
summary and exports both extracts to CSV.

The token's user needs access to the pixel AND the `ads_management` permission;
`ads_read` alone fails with "(#100) Permission Denied".

Pixel counts already include ad-attributed events. Do not add them to Insights conversions.
"""
import json
import logging
import os
from collections import defaultdict
from datetime import date, timedelta
from dotenv import load_dotenv

from facebook_ads_reports import APIError, MetaAdsReport, validate_pixel_id
from facebook_ads_reports.utils import create_output_directory, load_credentials, save_report_to_csv


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Load credentials from env first (CI-friendly), then fall back to local secrets file.
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

    meta_api_client = MetaAdsReport(credentials_dict=credentials)

    # PIXEL_ID is a bare string of digits (no "act_" prefix). validate_pixel_id raises early on typos.
    PIXEL_ID = validate_pixel_id(os.getenv("PIXEL_ID") or "1234567890")  # Replace with your actual pixel ID

    # Dates are calendar days in the pixel owner's time zone, resolved automatically (pass
    # `timezone="America/Sao_Paulo"` to override), the same rule Insights applies with the ad
    # account's time zone. end_date is inclusive; the API's exclusive end_time is handled internally.
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=6)

    output_dir = create_output_directory("reports_output")

    try:
        # 1) Event totals per hour. One row per (hour bucket, event name).
        event_rows = meta_api_client.get_pixel_stats(PIXEL_ID, start_date, end_date, aggregation="event")

        # 2) Events crossed with hostname. The API cannot group by both at once, so this makes
        #    one request per event. Passing `events` reuses the names found above instead of
        #    discovering them again; `sleep_seconds` spaces the requests out.
        event_names = sorted({str(row["value"]) for row in event_rows if row["value"]})
        host_rows = meta_api_client.get_pixel_event_hosts(PIXEL_ID, start_date, end_date,
                                                          events=event_names, sleep_seconds=2)
    except APIError as e:
        # Permission failures arrive as APIError with error_code 100 and are never retried.
        if e.context.get("error_code") == 100:
            logging.error("The token's user lacks access to this pixel or the `ads_management` permission.")
        raise

    for report_name, rows in (("pixel_stats_event", event_rows), ("pixel_stats_event_host", host_rows)):
        # format_report_filename() is for account IDs and would prefix the pixel ID with "act_".
        filename = f"{report_name}_{PIXEL_ID}_{start_date.isoformat()}_{end_date.isoformat()}.csv"
        if rows:
            save_report_to_csv(rows, str(output_dir / filename))
            logging.info(f"{len(rows)} rows saved to {filename}")
        else:
            logging.warning(f"No rows for '{report_name}' in the window; nothing saved")

    # `date` and `hour` are local to that same time zone, so a daily rollup is a plain sum.
    daily: dict[tuple[str, str], int] = defaultdict(int)
    for row in event_rows:
        daily[(row["date"], str(row["value"]))] += row["count"]

    print(f"\nPixel {PIXEL_ID}: {start_date} to {end_date}")
    print(f"- Hourly event rows: {len(event_rows)}")
    print(f"- Hourly event/host rows: {len(host_rows)}")
    print("\nDaily totals (date, event, count):")
    for (day, event_name), count in sorted(daily.items()):
        print(f"  {day}  {event_name:<30} {count}")


if __name__ == "__main__":
    main()
