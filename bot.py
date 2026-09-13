import os
import time
import requests

BALE_TOKEN = os.environ["BALE_TOKEN"]

BASE_URL = f"https://tapi.bale.ai/bot{BALE_TOKEN}"


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


def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "").strip()

    if not chat_id:
        return

    if text == "/start":
        send_message(
            chat_id,
            "سلام 👋\n"
            "به ربات کنترل موجودی هایپرمارکت مارلیک ۵ خوش آمدید.\n\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            main_menu()
        )

    elif text == "📦 شروع شمارش موجودی":
        send_message(
            chat_id,
            "📦 بخش شمارش موجودی\n\n"
            "این بخش به‌زودی فعال می‌شود.\n"
            "در مرحله بعد، محصولات اختصاص‌یافته به شما نمایش داده خواهد شد.",
            main_menu()
        )

    elif text == "📋 موجودی‌های ثبت‌شده":
        send_message(
            chat_id,
            "📋 موجودی‌های ثبت‌شده\n\n"
            "هنوز اطلاعاتی برای نمایش ثبت نشده است.",
            main_menu()
        )

    elif text == "👤 اطلاعات کاربر":
        first_name = chat.get("first_name", "ثبت نشده")
        username = chat.get("username", "ثبت نشده")

        send_message(
            chat_id,
            f"👤 اطلاعات کاربر\n\n"
            f"نام: {first_name}\n"
            f"Username: {username}\n"
            f"Chat ID: {chat_id}",
            main_menu()
        )

    elif text == "❓ راهنما":
        send_message(
            chat_id,
            "❓ راهنمای ربات\n\n"
            "از گزینه «شروع شمارش موجودی» برای ثبت موجودی محصولات استفاده کنید.\n"
            "در مراحل بعد، موجودی واقعی و موجودی آنلاین از شما دریافت خواهد شد.",
            main_menu()
        )

    else:
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
