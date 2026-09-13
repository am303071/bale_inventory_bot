import os
import time
import requests
import gspread
import google.auth

# =========================
# Settings
# =========================

BALE_TOKEN = os.environ["BALE_TOKEN"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]

BASE_URL = f"https://tapi.bale.ai/bot{BALE_TOKEN}"

# =========================
# Google Sheets
# =========================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

credentials, project = google.auth.default(scopes=SCOPES)

gc = gspread.authorize(credentials)

spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)

users_sheet = spreadsheet.worksheet("Users")

print("Google Sheets connected successfully.")


# =========================
# Temporary user states
# =========================

waiting_for_name = {}


# =========================
# Bale functions
# =========================

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


# =========================
# Main menu
# =========================

def main_menu():

    return [
        [{"text": "📦 شروع شمارش موجودی"}],
        [{"text": "📋 موجودی‌های ثبت‌شده"}],
        [{"text": "👤 اطلاعات کاربر"}],
        [{"text": "❓ راهنما"}]
    ]


# =========================
# Find user
# =========================

def find_user(chat_id):

    records = users_sheet.get_all_records()

    for index, user in enumerate(records, start=2):

        if str(user.get("Chat ID", "")).strip() == str(chat_id):

            return index, user

    return None, None


# =========================
# Register user
# =========================

def register_user(chat_id, full_name, username):

    parts = full_name.strip().split()

    first_name = parts[0]

    if len(parts) > 1:
        last_name = " ".join(parts[1:])
    else:
        last_name = ""

    users_sheet.append_row([
        str(chat_id),
        first_name,
        last_name,
        username,
        "فعال"
    ])

    print(f"New user registered: {chat_id} - {full_name}")


# =========================
# Handle messages
# =========================

def handle_message(message):

    chat = message.get("chat", {})

    chat_id = chat.get("id")

    text = message.get("text", "").strip()

    username = chat.get("username", "")

    if not chat_id:
        return


    # -------------------------
    # Waiting for registration
    # -------------------------

    if chat_id in waiting_for_name:

        if not text:
            send_message(
                chat_id,
                "لطفاً نام و نام خانوادگی خود را وارد کنید."
            )
            return

        register_user(
            chat_id,
            text,
            username
        )

        del waiting_for_name[chat_id]

        send_message(
            chat_id,
            f"✅ ثبت‌نام شما با موفقیت انجام شد.\n\n"
            f"نام ثبت‌شده: {text}\n\n"
            f"حالا می‌توانید از منوی اصلی استفاده کنید.",
            main_menu()
        )

        return


    # -------------------------
    # /start
    # -------------------------

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

            waiting_for_name[chat_id] = True

            send_message(
                chat_id,
                "سلام 👋\n\n"
                "برای استفاده از ربات ابتدا باید ثبت‌نام کنید.\n\n"
                "لطفاً **نام و نام خانوادگی** خود را وارد کنید."
            )

        return


    # -------------------------
    # Start inventory
    # -------------------------

    if text == "📦 شروع شمارش موجودی":

        row, user = find_user(chat_id)

        if not user:

            waiting_for_name[chat_id] = True

            send_message(
                chat_id,
                "ابتدا باید ثبت‌نام کنید.\n\n"
                "لطفاً نام و نام خانوادگی خود را وارد کنید."
            )

            return

        send_message(
            chat_id,
            "📦 بخش شمارش موجودی\n\n"
            "این بخش در مرحله بعد فعال می‌شود.",
            main_menu()
        )

        return


    # -------------------------
    # Registered inventories
    # -------------------------

    if text == "📋 موجودی‌های ثبت‌شده":

        send_message(
            chat_id,
            "📋 موجودی‌های ثبت‌شده\n\n"
            "در حال حاضر اطلاعاتی برای نمایش وجود ندارد.",
            main_menu()
        )

        return


    # -------------------------
    # User information
    # -------------------------

    if text == "👤 اطلاعات کاربر":

        row, user = find_user(chat_id)

        if not user:

            waiting_for_name[chat_id] = True

            send_message(
                chat_id,
                "شما هنوز ثبت‌نام نکرده‌اید.\n\n"
                "لطفاً نام و نام خانوادگی خود را وارد کنید."
            )

            return

        first_name = user.get("نام", "")
        last_name = user.get("نام خانوادگی", "")
        username_saved = user.get("Username
