# google_sheets_utils.py

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------- Configuration --------------
SPREADSHEET_NAME = "Student_database"  # Change if your sheet name is different
CREDENTIALS_FILE = "my-project-290967-462812-12d7163fd54f.json"  # This is the file you downloaded from Google

# -------------- Setup Connection --------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SPREADSHEET_NAME)

# -------------- Utility Functions --------------
def get_all_rows(sheet_name):
    try:
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return data
    except Exception as e:
        print(f"Error reading {sheet_name}: {e}")
        return []

def write_all_rows(sheet_name, data, header):
    try:
        worksheet = sheet.worksheet(sheet_name)
        worksheet.clear()
        worksheet.append_row(header)
        for row in data:
            worksheet.append_row([row[col] for col in header])
    except Exception as e:
        print(f"Error writing to {sheet_name}: {e}")
