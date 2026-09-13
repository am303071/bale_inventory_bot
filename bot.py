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

credentials, project = google.auth.default(scopes=SCOPES)
gc = gspread.authorize(credentials)

spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)

users_sheet = spreadsheet.worksheet("Users")
staff_sheet = spreadsheet.worksheet("Staff")

print("Google Sheets connected successfully.")

waiting_for_code = {}


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

    for index, user in enumerate(records, start=2):
        if str(user.get("Chat ID", "")).strip() == str(chat_id):
            return index, user

    return None, None


def find_staff(personnel_code):
    records = staff_sheet.get_all_records()

    for index, staff in enumerate(records, start=2):

        code = str(staff.get("کد پرسنلی", "")).strip()
        status = str(staff.get("وضعیت", "")).strip()

        if code == str(personnel_code).strip():

            if status == "فعال":
                return index, staff

            return None, None

    return None, None


def personnel_code_already_registered(personnel_code):
    records = users_sheet.get_all_records()

    for user in records:

        code = str(user.get("کد پرسنلی", "")).strip()

        if code == str(personnel_code).strip():
            return True

    return False


def register_user(chat_id, personnel_code, staff, username):

    full_name = str(
        staff.get("نام و نام خانوادگی", "")
    ).strip()

    parts = full_name.split()

    first_name = parts[0] if len(parts) >= 1 else ""
    last_name = " ".join(parts[1:]) if len(parts) >= 2 else ""

    users_sheet.append_row([
        str(chat_id),
        str(personnel_code),
        first_name,
        last_name,
        username,
        "فعال"
    ])

    print(
        f"New user registered: "
        f"{personnel_code} - {full_name} - {chat_id}"
    )


def handle_message(message):

    chat = message.get("chat", {})

    chat_id = chat.get("id")

    text = message.get("text", "").strip()

    username = chat.get("username", "")

    if not chat_id:
        return


    # =========================
    # Waiting for personnel code
    # =========================

    if chat_id in waiting_for_code:

        personnel_code = text

        row, staff = find_staff(personnel_code)

        if not staff:

            send_message(
                chat_id,
                "❌ کد پرسنلی صحیح نیست یا پرسنل غیرفعال است.\n\n"
                "لطفاً کد پرسنلی صحیح خود را وارد کنید."
            )

            return


        # جلوگیری از ثبت یک کد برای چند نفر

        if personnel_code_already_registered(personnel_code):

            send_message(
                chat_id,
                "⚠️ این کد پرسنلی قبلاً ثبت شده است.\n\n"
                "اگر فکر می‌کنید اشتباهی رخ داده، "
                "با مسئول فروشگاه تماس بگیرید."
            )

            del waiting_for_code[chat_id]

            return


        # ثبت کاربر

        register_user(
            chat_id,
            personnel_code,
            staff,
            username
        )

        del waiting_for_code[chat_id]

        full_name = staff.get(
            "نام و نام خانوادگی",
            ""
        )

        send_message(
            chat_id,
            f"✅ ثبت‌نام با موفقیت انجام شد.\n\n"
            f"نام: {full_name}\n"
            f"کد پرسنلی: {personnel_code}\n\n"
            f"حساب شما با موفقیت فعال شد.",
            main_menu()
        )

        return


    # =========================
    # /start
    # =========================

    if text == "/start":

        row, user = find_user(chat_id)

        if user:

            send_message(
                chat_id,
                "سلام 👋\n"
                "خوش آمدید.\n\n"
                "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
                main_menu()
            )

        else:

            waiting_for_code[chat_id] = True

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

        row, user = find_user(chat_id)

        if not user:

            waiting_for_code[chat_id] = True

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

        row, user = find_user(chat_id)

        if not user:

            waiting_for_code[chat_id] = True

            send_message(
                chat_id,
                "شما هنوز ثبت‌نام نکرده‌اید.\n\n"
                "🔐 لطفاً کد پرسنلی خود را وارد کنید."
            )

            return

        personnel_code = user.get(
            "کد پرسنلی",
            ""
        )

        first_name = user.get(
            "نام",
            ""
        )

        last_name = user.get(
            "نام خانوادگی",
            ""
        )

        username_saved = user.get(
            "Username",
            ""
        )

        status = user.get(
            "وضعیت",
            ""
        )

        send_message(
            chat_id,
            f"👤 اطلاعات کاربر\n\n"
            f"نام: {first_name} {last_name}\n"
            f"کد پرسنلی: {personnel_code}\n"
            f"Username: {username_saved
