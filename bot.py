import os
import requests
import gspread
import google.auth

BALE_TOKEN = os.environ["BALE_TOKEN"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]


# ---------- Test Bale ----------
print("Testing Bale connection...")

url = f"https://tapi.bale.ai/bot{BALE_TOKEN}/getMe"
response = requests.get(url, timeout=20)

print("Bale response:", response.text)

if not response.ok:
    raise Exception("Bale connection failed")


# ---------- Test Google Sheets ----------
print("Testing Google Sheets connection...")

credentials, project = google.auth.default(
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
)

gc = gspread.authorize(credentials)

spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)

print("Google Sheets connected successfully!")
print("Spreadsheet:", spreadsheet.title)

print("All tests passed successfully!")
