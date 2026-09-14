import os
import time
import uuid
from datetime import datetime

import requests
import gspread
import google.auth


# =========================================================
# SETTINGS
# =========================================================

BALE_TOKEN = os.environ["BALE_TOKEN"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]

BASE_URL = f"https://tapi.bale.ai/bot{BALE_TOKEN}"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# =========================================================
# GOOGLE SHEETS CONNECTION
# =========================================================

credentials, _ = google.auth.default(scopes=SCOPES)
gc = gspread.authorize(credentials)

spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)

users_sheet = spreadsheet.worksheet("Users")
staff_sheet = spreadsheet.worksheet("Staff")
employees_sheet = spreadsheet.worksheet("Employees")
products_sheet = spreadsheet.worksheet("Products")
assigned_products_sheet = spreadsheet.worksheet("Assignments")
control_days_sheet = spreadsheet.worksheet("Control Days")

print("Google Sheets connected successfully.")


# =========================================================
# GLOBAL STATE
# =========================================================

waiting_for_code = set()


# =========================================================
# GENERAL HELPERS
# =========================================================

def today_date():
    return time.strftime("%Y-%m-%d")


def current_datetime():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def clean(value):
    return str(value or "").strip()


def is_true(value):
    value = clean(value).upper()

    return value in (
        "TRUE",
        "1",
        "YES",
        "Y",
        "ACTIVE",
        "فعال",
    )


def safe_int(value, default=50):
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


# =========================================================
# BALE API
# =========================================================

def send_message(chat_id, text, keyboard=None):

    data = {
        "chat_id": chat_id,
        "text": text,
    }

    if keyboard:
        data["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True,
            "one_time_keyboard": False,
        }

    try:
        response = requests.post(
            f"{BASE_URL}/sendMessage",
            json=data,
            timeout=30,
        )

        print(
            "Send message:",
            response.status_code,
            response.text,
        )

    except Exception as error:
        print("Send message error:", error)


def main_menu():

    return [
        [{"text": "📦 شروع شمارش موجودی"}],
        [{"text": "📋 کالاهای اختصاص‌یافته"}],
        [{"text": "👤 اطلاعات کاربر"}],
        [{"text": "❓ راهنما"}],
    ]


# =========================================================
# USERS / STAFF
# =========================================================

def find_user(chat_id):

    records = users_sheet.get_all_records()

    for row_number, user in enumerate(records, start=2):

        saved_chat_id = clean(
            user.get("Chat ID", "")
        )

        if saved_chat_id == clean(chat_id):
            return row_number, user

    return None, None


def find_staff(personnel_code):

    personnel_code = clean(personnel_code)

    records = staff_sheet.get_all_records()

    for row_number, staff in enumerate(records, start=2):

        staff_code = clean(
            staff.get("کد پرسنلی", "")
        )

        status = clean(
            staff.get("وضعیت", "")
        )

        if (
            staff_code == personnel_code
            and status == "فعال"
        ):
            return row_number, staff

    return None, None


def code_already_registered(personnel_code):

    personnel_code = clean(personnel_code)

    records = users_sheet.get_all_records()

    for user in records:

        saved_code = clean(
            user.get("کد پرسنلی", "")
        )

        if saved_code == personnel_code:
            return True

    return False


def register_user(
    chat_id,
    personnel_code,
    staff,
    username,
):

    full_name = clean(
        staff.get("نام و نام خانوادگی", "")
    )

    parts = full_name.split()

    first_name = parts[0] if parts else ""
    last_name = " ".join(parts[1:])

    users_sheet.append_row(
        [
