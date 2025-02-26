import threading
import logging
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDS = Credentials.from_service_account_file("alertbot/utils/credentials.json", scopes=SCOPES)
GS_CLIENT = gspread.authorize(CREDS)
def append_alert_to_sheet(alert_details):
    try:
        spreadsheet = GS_CLIENT.open_by_key("1kIUrs21cNtg2Zu3lNg5IKTGCgAzLayqUUIEXhS-HcNI")
        worksheet = spreadsheet.worksheet("AlertData")
        row = [
            alert_details.get('date'),
            alert_details.get('time'),
            alert_details.get('product'),
            alert_details.get('playbook'),
            alert_details.get('direction'),
            alert_details.get('alert_price'),
            alert_details.get('target'),
            alert_details.get('score'),
        ]
        existing_data = worksheet.get_all_values()
        if len(existing_data) < 2:
            worksheet.insert_row(row, index=2)
        else:
            worksheet.append_row(row)
        logger.info(f"{alert_details.get('playbook')} {alert_details.get('direction')} logged to Google Sheets.")
    except Exception as e:
        logger.error(f"Error appending alert to sheet: {e}")
def log_alert_async(alert_details):
    threading.Thread(target=append_alert_to_sheet, args=(alert_details,), daemon=True).start()