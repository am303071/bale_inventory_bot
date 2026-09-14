import os
import time
import requests
import gspread
import google.auth

BALE_TOKEN = os.environ["BALE_TOKEN"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]

BASE_URL = f"https://tapi.bale.ai/bot{BALE_TOKEN}"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

credentials, _ = google.auth.default(scopes=SCOPES)
gc = gspread.authorize(credentials)

spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)

users_sheet = spreadsheet.worksheet("Users")
staff_sheet = spreadsheet.worksheet("Staff")
employees_sheet = spreadsheet.worksheet("Employees")
products_sheet = spreadsheet.worksheet("Products")
assigned_products_sheet = spreadsheet.worksheet("Assigned Products")

print("Google Sheets connected successfully.")

waiting_for_code = set()


def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True,
            "one_time_keyboard": False
        }

    response = requests.post(
        f"{BASE_URL}/sendMessage",
        json=data,
        timeout=30
    )

    print("Send message:", response.status_code, response.text)


def main_menu():
    return [
        [{"text": "📦 شروع شمارش موجودی"}],
        [{"text": "📋 موجودی‌های ثبت‌شده"}],
        [{"text": "👤 اطلاعات کاربر"}],
        [{"text": "❓ راهنما"}]
    ]


def find_user(chat_id):
    records = users_sheet.get_all_records()

    for row_number, user in enumerate(records, start=2):
        if str(user.get("Chat ID", "")).strip() == str(chat_id).strip():
            return row_number, user

    return None, None


def find_staff(personnel_code):
    code = str(personnel_code).strip()

    records = staff_sheet.get_all_records()

    for row_number, staff in enumerate(records, start=2):
        staff_code = str(
            staff.get("کد پرسنلی", "")
        ).strip()

        status = str(
            staff.get("وضعیت", "")
        ).strip()

        if staff_code == code and status == "فعال":
            return row_number, staff

    return None, None


def code_already_registered(personnel_code):
    code = str(personnel_code).strip()

    records = users_sheet.get_all_records()

    for user in records:
        registered_code = str(
            user.get("کد پرسنلی", "")
        ).strip()

        if registered_code == code:
            return True

    return False

def get_active_employees():
    records = employees_sheet.get_all_records()

    employees = []

    for employee in records:
        active = str(employee.get("Active", "")).strip().upper()

        if active in ("TRUE", "1", "YES", "فعال"):
            employees.append(employee)

    return employees


def get_available_products():
    records = products_sheet.get_all_records()

    products = []

    for product in records:
        active = str(product.get("Active", "")).strip().upper()

        if active in ("TRUE", "1", "YES", "فعال"):
            products.append(product)

    products.sort(
        key=lambda x: float(
            x.get("Selection_Score", 0) or 0
        ),
        reverse=True
    )

    return products


def assignment_exists(control_date):
    records = assigned_products_sheet.get_all_records()

    for row in records:
        existing_date = str(
            row.get("Control_Date", "")
        ).strip()

        if existing_date == str(control_date).strip():
            return True

    return False


def create_assignments(control_date):

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

        try:
            target = int(
                employee.get("Daily_Target", 50)
            )
        except (ValueError, TypeError):
            target = 50

        if target > 0:
            total_required += target

    if len(products) < total_required:

        print(
            f"Not enough products. "
            f"Required: {total_required}, "
            f"Available: {len(products)}"
        )

        return False

    rows = []
    product_index = 0

    for employee in employees:

        employee_id = str(
            employee.get("Employee_ID", "")
        ).strip()

        employee_name = str(
            employee.get("Employee_Name", "")
        ).strip()

        try:
            daily_target = int(
                employee.get("Daily_Target", 50)
            )
        except (ValueError, TypeError):
            daily_target = 50

        if daily_target <= 0:
            continue

        for sequence in range(1, daily_target + 1):

            product = products[product_index]
            product_index += 1

            product_id = str(
                product.get("Product_ID", "")
            ).strip()

            product_name = str(
                product.get("Product_Name", "")
            ).strip()

            assignment_id = (
                f"{control_date}-"
                f"{employee_id}-"
                f"{sequence}"
            )

            rows.append([
                assignment_id,
                control_date,
                employee_id,
                employee_name,
                product_id,
                product_name,
                sequence,
                "Pending",
                ""
            ])

    if rows:

        assigned_products_sheet.append_rows(
            rows,
            value_input_option="USER_ENTERED"
        )

    print(
        f"Created {len(rows)} assignments "
        f"for {control_date}"
    )

    return True

def test_create_assignments():

    control_date = time.strftime("%Y-%m-%d")

    print(
        f"Testing assignment creation for "
        f"{control_date}"
    )

    create_assignments(control_date)


def register_user(chat_id, personnel_code, staff, username):

    full_name = str(
        staff.get("نام و نام خانوادگی", "")
    ).strip()

    parts = full_name.split()

    first_name = parts[0] if parts else ""

    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    users_sheet.append_row([
        str(chat_id),
        str(personnel_code),
        first_name,
        last_name,
        username,
        "فعال"
    ])


def handle_message(message):

    chat = message.get("chat", {})

    chat_id = chat.get("id")

    text = str(
        message.get("text", "")
    ).strip()

    username = chat.get("username", "")

    if not chat_id:
        return


    # =========================
    # Personnel code registration
    # =========================

    if chat_id in waiting_for_code:

        _, staff = find_staff(text)

        if not staff:

            send_message(
                chat_id,
                "❌ کد پرسنلی صحیح نیست یا پرسنل غیرفعال است.\n\n"
                "لطفاً کد پرسنلی صحیح خود را وارد کنید."
            )

            return


        if code_already_registered(text):

            waiting_for_code.discard(chat_id)

            send_message(
                chat_id,
                "⚠️ این کد پرسنلی قبلاً ثبت شده است.\n\n"
                "اگر فکر می‌کنید اشتباهی رخ داده، "
                "با مسئول فروشگاه تماس بگیرید."
            )

            return


        register_user(
            chat_id,
            text,
            staff,
            username
        )

        waiting_for_code.discard(chat_id)

        full_name = str(
            staff.get("نام و نام خانوادگی", "")
        ).strip()

        send_message(
            chat_id,
            f"✅ ثبت‌نام با موفقیت انجام شد.\n\n"
            f"نام: {full_name}\n"
            f"کد پرسنلی: {text}\n\n"
            "حساب شما با موفقیت فعال شد.",
            main_menu()
        )

        return


    # =========================
    # Start
    # =========================

    if text == "/start":

        _, user = find_user(chat_id)

        if user:

            send_message(
                chat_id,
                "سلام 👋\n"
                "خوش آمدید.\n\n"
                "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
                main_menu()
            )

        else:

            waiting_for_code.add(chat_id)

            send_message(
                chat_id,
                "سلام 👋\n\n"
                "برای استفاده از ربات ابتدا باید ثبت‌نام کنید.\n\n"
                "🔐 لطفاً کد پرسنلی خود را وارد کنید:"
            )

        return


    # =========================
    # Start inventory
    # =========================

    if text == "📦 شروع شمارش موجودی":

        _, user = find_user(chat_id)

        if not user:

            waiting_for_code.add(chat_id)

            send_message(
                chat_id,
                "ابتدا باید ثبت‌نام کنید.\n\n"
                "🔐 لطفاً کد پرسنلی خود را وارد کنید."
            )

            return

        send_message(
            chat_id,
            "📦 بخش شمارش موجودی\n\n"
            "این بخش در مرحله بعد فعال می‌شود.",
            main_menu()
        )

        return


    # =========================
    # Registered inventories
    # =========================

    if text == "📋 موجودی‌های ثبت‌شده":

        send_message(
            chat_id,
            "📋 موجودی‌های ثبت‌شده\n\n"
            "در حال حاضر اطلاعاتی برای نمایش وجود ندارد.",
            main_menu()
        )

        return


    # =========================
    # User information
    # =========================

    if text == "👤 اطلاعات کاربر":

        _, user = find_user(chat_id)

        if not user:

            waiting_for_code.add(chat_id)

            send_message(
                chat_id,
                "شما هنوز ثبت‌نام نکرده‌اید.\n\n"
                "🔐 لطفاً کد پرسنلی خود را وارد کنید."
            )

            return

        full_name = (
            f"{user.get('نام', '')} "
            f"{user.get('نام خانوادگی', '')}"
        ).strip()

        send_message(
            chat_id,
            f"👤 اطلاعات کاربر\n\n"
            f"نام: {full_name}\n"
            f"کد پرسنلی: {user.get('کد پرسنلی', '')}\n"
            f"Username: {user.get('Username', '')}\n"
            f"وضعیت: {user.get('وضعیت', '')}",
            main_menu()
        )

        return


    # =========================
    # Help
    # =========================

    if text == "❓ راهنما":

        send_message(
            chat_id,
            "❓ راهنمای ربات\n\n"
            "برای شروع شمارش موجودی، گزینه "
            "«📦 شروع شمارش موجودی» را انتخاب کنید.\n\n"
            "در مراحل بعد محصولات اختصاص‌یافته "
            "به شما نمایش داده خواهد شد.",
            main_menu()
        )

        return


    # =========================
    # Unknown message
    # =========================

    send_message(
        chat_id,
        "لطفاً یکی از گزینه‌های منو را انتخاب کنید.",
        main_menu()
    )


def main():

    print("Inventory bot started...")

    offset = None

    while True:

        try:

            params = {
                "timeout": 30
            }

            if offset is not None:
                params["offset"] = offset

            response = requests.get(
                f"{BASE_URL}/getUpdates",
                params=params,
                timeout=40
            )

            data = response.json()

            print("Updates response:", data)

            if data.get("ok"):

                for update in data.get("result", []):

                    offset = update["update_id"] + 1

                    message = update.get("message")

                    if message:
                        handle_message(message)

        except Exception as error:

            print("Error:", error)

            time.sleep(5)


if __name__ == "__main__":
    main()
