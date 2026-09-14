import os
import time
import uuid

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
assignments_sheet = spreadsheet.worksheet("Assignments")
control_days_sheet = spreadsheet.worksheet("Control Days")

print("Google Sheets connected successfully.")


# =========================================================
# GLOBAL STATE
# =========================================================

waiting_for_code = set()


# =========================================================
# HELPERS
# =========================================================

def clean(value):
    return str(value or "").strip()


def today_date():
    return time.strftime("%Y-%m-%d")


def current_datetime():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def safe_int(value, default=50):

    try:
        return int(float(value))

    except (ValueError, TypeError):
        return default


def is_active(value):

    value = clean(value).upper()

    return value in (
        "TRUE",
        "1",
        "YES",
        "Y",
        "ACTIVE",
        "فعال",
    )


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
# USERS AND STAFF
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
            clean(chat_id),
            personnel_code,
            first_name,
            last_name,
            username,
            "فعال",
        ],
        value_input_option="USER_ENTERED",
    )


# =========================================================
# EMPLOYEES
# =========================================================

def get_active_employees():

    records = employees_sheet.get_all_records()

    employees = []

    for employee in records:

        active = employee.get("Active", "")

        if is_active(active):

            employees.append(employee)

    return employees


def find_employee_by_chat_id(chat_id):

    records = employees_sheet.get_all_records()

    for row_number, employee in enumerate(
        records,
        start=2,
    ):

        saved_chat_id = clean(
            employee.get("Bale_Chat_ID", "")
        )

        if saved_chat_id == clean(chat_id):

            return row_number, employee

    return None, None


# =========================================================
# PRODUCTS
# =========================================================

def get_available_products():

    records = products_sheet.get_all_records()

    products = []

    for product in records:

        active = product.get("Active", "")

        if is_active(active):

            product_id = clean(
                product.get("Product_ID", "")
            )

            product_name = clean(
                product.get("Product_Name", "")
            )

            if product_id and product_name:

                products.append(product)

    def get_score(product):

        value = product.get(
            "Selection_Score",
            0,
        )

        try:

            return float(value or 0)

        except (ValueError, TypeError):

            return 0

    products.sort(
        key=get_score,
        reverse=True,
    )

    return products


# =========================================================
# CONTROL DAYS
# =========================================================

def get_active_control_day():

    records = control_days_sheet.get_all_records()

    today = today_date()

    for row in records:

        control_date = clean(
            row.get("Control_Date", "")
        )

        status = clean(
            row.get("Status", "")
        ).upper()

        if (
            control_date == today
            and status in (
                "ACTIVE",
                "OPEN",
                "فعال",
            )
        ):

            return row

    return None


# =========================================================
# ASSIGNMENTS
# =========================================================

def assignment_exists(control_date):

    records = assignments_sheet.get_all_records()

    for row in records:

        existing_date = clean(
            row.get("Control_Date", "")
        )

        if existing_date == clean(control_date):

            return True

    return False


def create_assignments(control_date):

    print(
        f"Starting assignment creation for {control_date}"
    )

    if assignment_exists(control_date):

        print(
            f"Assignments already exist for {control_date}"
        )

        return False

    employees = get_active_employees()
    products = get_available_products()

    if not employees:

        print("No active employees found.")

        return False

    if not products:

        print("No active products found.")

        return False

    total_required = 0

    for employee in employees:

        daily_target = safe_int(
            employee.get("Daily_Target", 50),
            default=50,
        )

        if daily_target > 0:

            total_required += daily_target

    if len(products) < total_required:

        print(
            "Not enough active products. "
            f"Required: {total_required}, "
            f"Available: {len(products)}"
        )

        return False

    rows = []
    product_index = 0

    for employee in employees:

        employee_id = clean(
            employee.get("Employee_ID", "")
        )

        employee_name = clean(
            employee.get("Employee_Name", "")
        )

        daily_target = safe_int(
            employee.get("Daily_Target", 50),
            default=50,
        )

        if not employee_id:

            print(
                f"Skipped employee without ID: "
                f"{employee_name}"
            )

            continue

        if daily_target <= 0:

            continue

        for sequence in range(
            1,
            daily_target + 
