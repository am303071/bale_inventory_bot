print("### BOT.PY LOADED ###", flush=True)

import os
import time
import uuid
import requests
import gspread
import google.auth

print("### IMPORTS COMPLETED ###", flush=True)

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
control_days_sheet = spreadsheet.worksheet("Control_Days")

print("Google Sheets connected successfully.")


# =========================================================
# GLOBAL STATE
# =========================================================

waiting_for_code = set()
waiting_for_real_stock = {}
waiting_for_online_stock = {}


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


def normalize_number(value):
    try:
        number = float(str(value).replace(",", "").strip())

        if number.is_integer():
            return int(number)

        return number

    except (ValueError, TypeError):
        return None


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


def send_main_menu(chat_id):

    send_message(
        chat_id,
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        main_menu(),
    )

# =========================================================
# USERS AND STAFF
# =========================================================

def find_user(chat_id):

    records = users_sheet.get_all_records()

    for row_number, user in enumerate(records, start=2):

        saved_chat_id = clean(
            user.get("Chat_ID", "")
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
    username="",
):
    # -----------------------------------------------------
    # Get full name from Staff
    # -----------------------------------------------------

    full_name = clean(
        staff.get(
            "نام و نام خانوادگی",
            ""
        )
    )

    # -----------------------------------------------------
    # Split name
    # -----------------------------------------------------

    parts = full_name.split()

    first_name = parts[0] if parts else ""
    last_name = " ".join(parts[1:])

    # -----------------------------------------------------
    # Register user in Users sheet
    # -----------------------------------------------------

    users_sheet.append_row(
        [
            clean(chat_id),
            personnel_code,
            first_name,
            last_name,
            clean(username),
            "فعال",
        ],
        value_input_option="USER_ENTERED",
    )

    print(
        f"User registered in Users: {personnel_code}"
    )

    # -----------------------------------------------------
    # Find employee in Employees by name
    # -----------------------------------------------------

    employee_row = None
    employee = None

    employee_records = employees_sheet.get_all_records()

    for row_number, emp in enumerate(
        employee_records,
        start=2
    ):
        employee_name = clean(
            emp.get(
                "Employee_Name",
                ""
            )
        )

        if employee_name == full_name:
            employee_row = row_number
            employee = emp
            break

    # -----------------------------------------------------
    # Save Bale Chat ID in Employees
    # -----------------------------------------------------

    if employee_row:

        headers = employees_sheet.row_values(1)

        if "Bale_Chat_ID" in headers:

            column = headers.index(
                "Bale_Chat_ID"
            ) + 1

            employees_sheet.update_cell(
                employee_row,
                column,
                clean(chat_id),
            )

            print(
                f"Bale_Chat_ID updated for "
                f"Employee_ID={employee.get('Employee_ID', '')}"
            )

        else:

            print(
                "ERROR: Bale_Chat_ID column not found"
            )

    else:

        print(
            f"ERROR: Employee not found by name: {full_name}"
        )


def update_user_chat_id(
    row_number,
    chat_id,
    username,
):

    try:

        headers = users_sheet.row_values(1)

        if "Chat ID" in headers:

            col = headers.index("Chat ID") + 1

            users_sheet.update_cell(
                row_number,
                col,
                clean(chat_id),
            )

        if "Username" in headers:

            col = headers.index("Username") + 1

            users_sheet.update_cell(
                row_number,
                col,
                clean(username),
            )

    except Exception as error:

        print(
            "Update user error:",
            error,
        )


# =========================================================
# EMPLOYEES
# =========================================================

def get_active_employees():

    records = employees_sheet.get_all_records()

    employees = []

    for employee in records:

        active = employee.get(
            "Active",
            "",
        )

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
            employee.get(
                "Bale_Chat_ID",
                "",
            )
        )

        if saved_chat_id == clean(chat_id):

            return row_number, employee

    return None, None


def find_employee_by_id(employee_id):
    employee_id = clean(employee_id)

    records = employees_sheet.get_all_records()

    for row_number, employee in enumerate(records, start=2):
        saved_id = clean(employee.get("Employee_ID", ""))

        if saved_id == employee_id:
            return row_number, employee

    return None, None


# =========================================================
# PRODUCTS
# =========================================================

def get_available_products():

    records = products_sheet.get_all_records()

    products = []

    for product in records:

        active = product.get(
            "Active",
            "",
        )

        if is_active(active):

            product_id = clean(
                product.get(
                    "Product_ID",
                    "",
                )
            )

            product_name = clean(
                product.get(
                    "Product_Name",
                    "",
                )
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
            row.get(
                "Control_Date",
                "",
            )
        )

        status = clean(
            row.get(
                "Status",
                "",
            )
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
            row.get(
                "Control_Date",
                "",
            )
        )

        if existing_date == clean(control_date):

            return True

    return False


def get_employee_assignments(
    employee_id,
    control_date,
):

    records = assignments_sheet.get_all_records()

    result = []

    for row in records:

        row_employee_id = clean(
            row.get(
                "Employee_ID",
                "",
            )
        )

        row_date = clean(
            row.get(
                "Control_Date",
                "",
            )
        )

        if (
            row_employee_id == clean(employee_id)
            and row_date == clean(control_date)
        ):

            result.append(row)

    return result


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

        print(
            "No active employees found."
        )

        return False

    if not products:

        print(
            "No active products found."
        )

        return False

    total_required = 0

    for employee in employees:

        daily_target = safe_int(
            employee.get(
                "Daily_Target",
                50,
            ),
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
            employee.get(
                "Employee_ID",
                "",
            )
        )

        employee_name = clean(
            employee.get(
                "Employee_Name",
                "",
            )
        )

        daily_target = safe_int(
            employee.get(
                "Daily_Target",
                50,
            ),
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
            daily_target + 1,
        ):

            if product_index >= len(products):

                break

            product = products[product_index]

            product_id = clean(
                product.get(
                    "Product_ID",
                    "",
                )
            )

            product_name = clean(
                product.get(
                    "Product_Name",
                    "",
                )
            )

            assignment_id = str(
                uuid.uuid4()
            )

            rows.append(
                [
                    assignment_id,
                    control_date,
                    employee_id,
                    employee_name,
                    sequence,
                    product_id,
                    product_name,
                    "",
                    "",
                    "",
                    "PENDING",
                    "",
                ]
            )

            product_index += 1

    if not rows:

        print(
            "No assignment rows created."
        )

        return False

    try:

        assignments_sheet.append_rows(
            rows,
            value_input_option="USER_ENTERED",
        )

        print(
            f"{len(rows)} assignment rows created."
        )

        return True

    except Exception as error:

        print(
            "Assignment creation error:",
            error,
        )

        return False


def ensure_today_assignments():

    control_day = get_active_control_day()

    if not control_day:

        print(
            "No active control day for today."
        )

        return False

    control_date = clean(
        control_day.get(
            "Control_Date",
            "",
        )
    )

    if assignment_exists(control_date):

        return True

    return create_assignments(
        control_date
    )


# =========================================================
# ASSIGNMENT LOOKUP
# =========================================================

def get_pending_assignment(
    employee_id,
    control_date,
):

    records = assignments_sheet.get_all_records()

    for row_number, row in enumerate(
        records,
        start=2,
    ):

        row_employee_id = clean(
            row.get(
                "Employee_ID",
                "",
            )
        )

        row_date = clean(
            row.get(
                "Control_Date",
                "",
            )
        )

        status = clean(
            row.get(
                "Status",
                "",
            )
        ).upper()

        if (
            row_employee_id == clean(employee_id)
            and row_date == clean(control_date)
            and status == "PENDING"
        ):

            row["_row_number"] = row_number

            return row

    return None

# =========================================================
# ASSIGNMENT UPDATE
# =========================================================

def update_assignment_real_stock(
    row_number,
    real_stock,
):

    headers = assignments_sheet.row_values(1)

    if "Real_Stock" not in headers:
        return False

    column = headers.index(
        "Real_Stock"
    ) + 1

    assignments_sheet.update_cell(
        row_number,
        column,
        real_stock,
    )

    return True


def update_assignment_online_stock(
    row_number,
    online_stock,
):

    headers = assignments_sheet.row_values(1)

    if "Online_Stock" not in headers:
        return False

    column = headers.index(
        "Online_Stock"
    ) + 1

    assignments_sheet.update_cell(
        row_number,
        column,
        online_stock,
    )

    return True


def update_assignment_difference(
    row_number,
    difference,
):

    headers = assignments_sheet.row_values(1)

    if "Difference" not in headers:
        return False

    column = headers.index(
        "Difference"
    ) + 1

    assignments_sheet.update_cell(
        row_number,
        column,
        difference,
    )

    return True


def update_assignment_status(
    row_number,
    status,
):

    headers = assignments_sheet.row_values(1)

    if "Status" not in headers:
        return False

    column = headers.index(
        "Status"
    ) + 1

    assignments_sheet.update_cell(
        row_number,
        column,
        status,
    )

    return True


def update_assignment_registered_at(
    row_number,
):

    headers = assignments_sheet.row_values(1)

    if "Registered_At" not in headers:
        return False

    column = headers.index(
        "Registered_At"
    ) + 1

    assignments_sheet.update_cell(
        row_number,
        column,
        current_datetime(),
    )

    return True


def complete_assignment(
    row_number,
    real_stock,
    online_stock,
):

    difference = (
        real_stock - online_stock
    )

    update_assignment_real_stock(
        row_number,
        real_stock,
    )

    update_assignment_online_stock(
        row_number,
        online_stock,
    )

    update_assignment_difference(
        row_number,
        difference,
    )

    update_assignment_status(
        row_number,
        "COMPLETED",
    )

    update_assignment_registered_at(
        row_number,
    )

    return difference


# =========================================================
# USER / EMPLOYEE INFORMATION
# =========================================================
 
def get_user_employee(chat_id):

    user_row, user = find_user(chat_id)

    if not user:
        return None, None, None

    employee_row, employee = find_employee_by_chat_id(
        chat_id
    )

    return user, employee_row, employee


# =========================================================
# PROGRESS
# =========================================================

def get_employee_progress(
    employee_id,
    control_date,
):

    assignments = get_employee_assignments(
        employee_id,
        control_date,
    )

    total = len(assignments)

    completed = 0

    for assignment in assignments:

        status = clean(
            assignment.get(
                "Status",
                "",
            )
        ).upper()

        if status == "COMPLETED":

            completed += 1

    pending = total - completed

    return total, completed, pending


def show_progress(
    chat_id,
    employee_id,
    control_date,
):

    total, completed, pending = (
        get_employee_progress(
            employee_id,
            control_date,
        )
    )

    send_message(
        chat_id,
        "📊 وضعیت شمارش امروز\n\n"
        f"کل کالاها: {total}\n"
        f"تکمیل‌شده: {completed}\n"
        f"باقی‌مانده: {pending}",
    )

# =========================================================
# REGISTRATION
# =========================================================

def handle_start(
    chat_id,
    username,
):

    row_number, user = find_user(chat_id)

    if user:

        send_message(
            chat_id,
            "✅ شما قبلاً در سیستم ثبت شده‌اید.",
            main_menu(),
        )

        return

    waiting_for_code.add(
        clean(chat_id)
    )

    send_message(
        chat_id,
        "👋 سلام!\n\n"
        "برای استفاده از سیستم کنترل موجودی، "
        "لطفاً کد پرسنلی خود را ارسال کنید.",
    )


def handle_personnel_code(chat_id, personnel_code):
    
    print("### HANDLE_PERSONNEL_CODE START ###")
    print("CHAT_ID:", chat_id)
    print("PERSONNEL_CODE:", personnel_code)
    
    personnel_code = clean(personnel_code)

    # پیدا کردن پرسنل در Staff
    staff_row, staff = find_staff(personnel_code)

    if not staff:
        send_message(
            chat_id,
            "❌ کد پرسنلی پیدا نشد یا پرسنل فعال نیست."
        )
        return

    # جلوگیری از ثبت کد تکراری
    if code_already_registered(personnel_code):
        send_message(
            chat_id,
            "⚠️ این کد پرسنلی قبلاً ثبت شده است."
        )
        waiting_for_code.discard(chat_id)
        send_main_menu(chat_id)
        return

    # نام کامل از Staff
    staff_name = clean(
        staff.get("نام و نام خانوادگی", "")
    )

    # پیدا کردن شخص در Employees بر اساس نام
    employee_row = None
    employee = None

    employee_records = employees_sheet.get_all_records()

    for row_number, emp in enumerate(employee_records, start=2):
        employee_name = clean(
            emp.get("Employee_Name", "")
        )

        if employee_name == staff_name:
            employee_row = row_number
            employee = emp
            break

    if not employee:
        send_message(
            chat_id,
            "❌ اطلاعات شما در بخش Employees پیدا نشد.\n\n"
            f"نام در Staff: {staff_name}"
        )
        return

    # پیدا کردن ستون Bale_Chat_ID
    headers = employees_sheet.row_values(1)

    if "Bale_Chat_ID" not in headers:
        send_message(
            chat_id,
            "❌ ستون Bale_Chat_ID در Employees وجود ندارد."
        )
        return

    bale_chat_col = headers.index("Bale_Chat_ID") + 1

    # ثبت Chat ID در Employees
    employees_sheet.update_cell(
        employee_row,
        bale_chat_col,
        str(chat_id)
    )

    # ثبت کاربر در Users
    register_user(
      chat_id,
      personnel_code,
      staff,
      username="",
    )

    waiting_for_code.discard(chat_id)

    send_message(
        chat_id,
        "✅ ثبت‌نام شما با موفقیت انجام شد.\n\n"
        f"👤 {employee.get('Employee_Name', '')}\n"
        f"🆔 کد پرسنلی: {personnel_code}\n"
        f"🔗 Employee ID: {employee.get('Employee_ID', '')}\n\n"
        "حالا می‌توانید گزینه «📦 شروع شمارش موجودی» را انتخاب کنید."
    )

    send_main_menu(chat_id)


# =========================================================
# START COUNTING
# =========================================================

def handle_start_counting(
    chat_id,
):

    user, employee_row, employee = (
        get_user_employee(chat_id)
    )

    if not user:

        handle_start(
            chat_id,
            "",
        )

        return

    if not employee:

        send_message(
            chat_id,
            "❌ اطلاعات پرسنل شما در بخش Employees پیدا نشد.",
        )

        return

    control_day = get_active_control_day()

    if not control_day:

        send_message(
            chat_id,
            "ℹ️ امروز روز کنترل موجودی نیست یا "
            "روز کنترل هنوز فعال نشده است.",
        )

        return

    control_date = clean(
        control_day.get(
            "Control_Date",
            "",
        )
    )

    ensure_today_assignments()

    employee_id = clean(
        employee.get(
            "Employee_ID",
            "",
        )
    )

    assignment = get_pending_assignment(
        employee_id,
        control_date,
    )

    if not assignment:

        total, completed, pending = (
            get_employee_progress(
                employee_id,
                control_date,
            )
        )

        if total > 0 and pending == 0:

            send_message(
                chat_id,
                "🎉 شمارش شما برای امروز کامل شده است.",
                main_menu(),
            )

        else:

            send_message(
                chat_id,
                "❌ در حال حاضر کالایی برای شمارش شما پیدا نشد.",
            )

        return

    assignment_id = clean(
        assignment.get(
            "Assignment_ID",
            "",
        )
    )

    product_name = clean(
        assignment.get(
            "Product_Name",
            "",
        )
    )

    product_id = clean(
        assignment.get(
            "Product_ID",
            "",
        )
    )

    sequence = clean(
        assignment.get(
            "Sequence",
            "",
        )
    )

    waiting_for_real_stock[
        clean(chat_id)
    ] = assignment

    send_message(
        chat_id,
        "📦 ثبت موجودی واقعی\n\n"
        f"کالا {sequence}\n"
        f"نام کالا: {product_name}\n"
        f"کد کالا: {product_id}\n\n"
        "🔢 موجودی واقعی شمارش‌شده را وارد کنید:",
    )


# =========================================================
# REAL STOCK
# =========================================================

def handle_real_stock(
    chat_id,
    text,
):

    assignment = waiting_for_real_stock.get(
        clean(chat_id)
    )

    if not assignment:

        return

    real_stock = normalize_number(text)

    if real_stock is None or real_stock < 0:

        send_message(
            chat_id,
            "❌ مقدار واردشده صحیح نیست.\n\n"
            "لطفاً فقط عدد موجودی واقعی را وارد کنید.",
        )

        return

    waiting_for_real_stock.pop(
        clean(chat_id),
        None,
    )

    waiting_for_online_stock[
        clean(chat_id)
    ] = {
        "assignment": assignment,
        "real_stock": real_stock,
    }

    send_message(
        chat_id,
        "💻 ثبت موجودی آنلاین\n\n"
        "لطفاً موجودی آنلاین همین کالا "
        "را طبق نرم‌افزار سوپر اپ وارد کنید:",
    )


# =========================================================
# ONLINE STOCK
# =========================================================

def handle_online_stock(
    chat_id,
    text,
):

    data = waiting_for_online_stock.get(
        clean(chat_id)
    )

    if not data:

        return

    online_stock = normalize_number(text)

    if online_stock is None or online_stock < 0:

        send_message(
            chat_id,
            "❌ مقدار واردشده صحیح نیست.\n\n"
            "لطفاً فقط عدد موجودی آنلاین را وارد کنید.",
        )

        return

    waiting_for_online_stock.pop(
        clean(chat_id),
        None,
    )

    assignment = data["assignment"]
    real_stock = data["real_stock"]

    row_number = assignment.get(
        "_row_number"
    )

    if not row_number:

        send_message(
            chat_id,
            "❌ خطا در پیدا کردن ردیف کالا.",
        )

        return

    difference = complete_assignment(
        row_number,
        real_stock,
        online_stock,
    )

    product_name = clean(
        assignment.get(
            "Product_Name",
            "",
        )
    )

    if difference == 0:

        difference_text = "✅ بدون مغایرت"

    elif difference > 0:

        difference_text = (
            f"🟢 مازاد: +{difference}"
        )

    else:

        difference_text = (
            f"🔴 کسری: {difference}"
        )

    employee_id = clean(
        assignment.get(
            "Employee_ID",
            "",
        )
    )

    control_date = clean(
        assignment.get(
            "Control_Date",
            today_date(),
        )
    )

    total, completed, pending = (
        get_employee_progress(
            employee_id,
            control_date,
        )
    )

    send_message(
        chat_id,
        "✅ اطلاعات با موفقیت ثبت شد.\n\n"
        f"📦 کالا: {product_name}\n"
        f"📊 موجودی واقعی: {real_stock}\n"
        f"💻 موجودی آنلاین: {online_stock}\n"
        f"📌 مغایرت: {difference_text}\n\n"
        f"📈 پیشرفت امروز:\n"
        f"{completed} از {total} کالا تکمیل شده\n"
        f"باقی‌مانده: {pending}",
        main_menu(),
    )

# =========================================================
# ASSIGNED PRODUCTS
# =========================================================

def handle_assigned_products(
    chat_id,
):

    user, employee_row, employee = (
        get_user_employee(chat_id)
    )

    if not user or not employee:

        send_message(
            chat_id,
            "❌ ابتدا باید ثبت‌نام کنید.",
        )

        return

    control_day = get_active_control_day()

    if not control_day:

        send_message(
            chat_id,
            "ℹ️ امروز روز کنترل موجودی نیست.",
        )

        return

    control_date = clean(
        control_day.get(
            "Control_Date",
            "",
        )
    )

    employee_id = clean(
        employee.get(
            "Employee_ID",
            "",
        )
    )

    assignments = get_employee_assignments(
        employee_id,
        control_date,
    )

    if not assignments:

        send_message(
            chat_id,
            "📋 برای امروز کالایی به شما اختصاص داده نشده است.",
        )

        return

    total = len(assignments)
    completed = 0

    lines = []

    for index, assignment in enumerate(
        assignments,
        start=1,
    ):

        product_name = clean(
            assignment.get(
                "Product_Name",
                "",
            )
        )

        status = clean(
            assignment.get(
                "Status",
                "",
            )
        ).upper()

        if status == "COMPLETED":

            completed += 1
            icon = "✅"

        else:

            icon = "⬜"

        lines.append(
            f"{icon} {index}. {product_name}"
        )

    text = (
        "📋 کالاهای اختصاص‌یافته امروز\n\n"
        f"تاریخ: {control_date}\n"
        f"تعداد کل: {total}\n"
        f"تکمیل‌شده: {completed}\n"
        f"باقی‌مانده: {total - completed}\n\n"
        + "\n".join(lines[:100])
    )

    send_message(
        chat_id,
        text,
    )


# =========================================================
# USER INFORMATION
# =========================================================

def handle_user_info(
    chat_id,
):

    user, employee_row, employee = (
        get_user_employee(chat_id)
    )

    if not user:

        send_message(
            chat_id,
            "❌ شما هنوز ثبت‌نام نکرده‌اید.",
        )

        return

    first_name = clean(
        user.get(
            "First Name",
            "",
        )
    )

    last_name = clean(
        user.get(
            "Last Name",
            "",
        )
    )

    personnel_code = clean(
        user.get(
            "کد پرسنلی",
            "",
        )
    )

    username = clean(
        user.get(
            "Username",
            "",
        )
    )

    send_message(
        chat_id,
        "👤 اطلاعات کاربر\n\n"
        f"نام: {first_name} {last_name}\n"
        f"کد پرسنلی: {personnel_code}\n"
        f"Username: {username or '-'}",
    )


# =========================================================
# HELP
# =========================================================

def handle_help(
    chat_id,
):

    send_message(
        chat_id,
        "❓ راهنمای سیستم کنترل موجودی\n\n"
        "1️⃣ از گزینه «شروع شمارش موجودی» استفاده کنید.\n\n"
        "2️⃣ کالا به شما نمایش داده می‌شود.\n\n"
        "3️⃣ موجودی واقعی شمارش‌شده را وارد کنید.\n\n"
        "4️⃣ سپس موجودی آنلاین کالا را از نرم‌افزار وارد کنید.\n\n"
        "5️⃣ سیستم مغایرت را به‌صورت خودکار محاسبه می‌کند.\n\n"
        "6️⃣ سپس کالای بعدی را شمارش کنید.",
        main_menu(),
    )


# =========================================================
# MESSAGE HANDLER
# =========================================================

def handle_message(message):

    if not message:

        return

    chat = message.get(
        "chat",
        {},
    )

    chat_id = chat.get(
        "id"
    )

    if chat_id is None:

        return

    chat_id = clean(chat_id)

    text = clean(
        message.get(
            "text",
            "",
        )
    )

    from_user = message.get(
        "from",
        {},
    )

    username = clean(
        from_user.get(
            "username",
            "",
        )
    )

    if not text:

        return

    print(
        f"Incoming message from {chat_id}: {text}"
    )

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    if text == "/start":

        handle_start(
            chat_id,
            username,
        )

        return

    # -----------------------------------------------------
    # REGISTRATION
    # -----------------------------------------------------

    if chat_id in waiting_for_code:

        handle_personnel_code(
            chat_id,
            text,
            username,
        )

        return

    # -----------------------------------------------------
    # REAL STOCK
    # -----------------------------------------------------

    if chat_id in waiting_for_real_stock:

        handle_real_stock(
            chat_id,
            text,
        )

        return

    # -----------------------------------------------------
    # ONLINE STOCK
    # -----------------------------------------------------

    if chat_id in waiting_for_online_stock:

        handle_online_stock(
            chat_id,
            text,
        )

        return

    # -----------------------------------------------------
    # MAIN MENU
    # -----------------------------------------------------

    if text == "📦 شروع شمارش موجودی":

        handle_start_counting(
            chat_id,
        )

        return

    if text == "📋 کالاهای اختصاص‌یافته":

        handle_assigned_products(
            chat_id,
        )

        return

    if text == "👤 اطلاعات کاربر":

        handle_user_info(
            chat_id,
        )

        return

    if text == "❓ راهنما":

        handle_help(
            chat_id,
        )

        return

    # -----------------------------------------------------
    # UNKNOWN MESSAGE
    # -----------------------------------------------------

    send_message(
        chat_id,
        "دستور موردنظر پیدا نشد.\n"
        "لطفاً از منوی اصلی استفاده کنید.",
        main_menu(),
    )


# =========================================================
# BALE UPDATE
# =========================================================

def get_updates(offset=None):

    params = {
        "timeout": 30,
    }

    if offset is not None:

        params["offset"] = offset

    try:

        response = requests.get(
            f"{BASE_URL}/getUpdates",
            params=params,
            timeout=40,
        )

        print(
            "Get updates:",
            response.status_code,
            response.text,
        )

        if response.status_code != 200:

            return []

        data = response.json()

        if not data.get("ok"):

            return []

        return data.get(
            "result",
            []
        )

    except Exception as error:

        print(
            "Get updates error:",
            error,
        )

        return []


# =========================================================
# STARTUP TEST
# =========================================================

def test_bale_connection():

    try:

        response = requests.get(
            f"{BASE_URL}/getMe",
            timeout=30,
        )

        print(
            "Testing Bale connection..."
        )

        print(
            "Bale response:",
            response.status_code,
            response.text,
        )

        return response.status_code == 200

    except Exception as error:

        print(
            "Bale connection error:",
            error,
        )

        return False


print("### REACHED MAIN DEFINITION ###", flush=True)

# =========================================================
# MAIN LOOP
# =========================================================

def main():

    print("=" * 60)
    print("Bale Inventory Control Bot")
    print("=" * 60)

    if not test_bale_connection():

        print(
            "WARNING: Bale connection test failed."
        )

    print(
        "Bot started..."
    )

    offset = None

    while True:

        try:

            updates = get_updates(
                offset
            )

            for update in updates:

                update_id = update.get(
                    "update_id"
                )

                if update_id is not None:

                    offset = update_id + 1

                try:

                    message = update.get(
                        "message"
                    )

                    if message:

                        handle_message(
                            message
                        )

                except Exception as error:

                    print(
                        "Message handling error:",
                        error,
                    )

            time.sleep(1)

        except KeyboardInterrupt:

            print(
                "Bot stopped manually."
            )

            break

        except Exception as error:

            print(
                "Main loop error:",
                error,
            )

            time.sleep(5)


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    print("### CALLING MAIN ###", flush=True)

    main()
    
