import telebot
import time
import os
import threading
from flask import Flask, request, jsonify

# ==============================
# Flask App
# ==============================

app = Flask(__name__)

SECRET_KEY = "my_app_secret_123"

# আপনার নতুন Telegram Bot Token এখানে বসান
BOT_TOKEN = "8742181210:AAFQWm__hBK1qNXtNy3EpfCg4bZSybn6So8"

ADMIN_ID = 8864523429

bot = telebot.TeleBot(BOT_TOKEN)

USER_FILE = "users.txt"

# একই content বারবার notification না পাঠানোর জন্য
sent_notifications = set()
notification_lock = threading.Lock()


# ==============================
# Home
# ==============================

@app.route("/")
def home():
    return "Bot is live and running 24/7!"


# ==============================
# Telegram Notification
# ==============================

@app.route("/notify_upload", methods=["POST"])
def notify_upload():

    data = request.get_json(silent=True) or {}

    # Secret check
    if data.get("secret") != SECRET_KEY:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    title = data.get(
        "title",
        "নতুন পোস্ট প্রকাশিত হয়েছে!"
    )

    app_url = data.get(
        "app_url",
        ""
    )

    content_type = data.get(
        "type",
        "post"
    )

    content_id = str(
        data.get(
            "content_id",
            app_url
        )
    )

    notification_key = f"{content_type}:{content_id}"

    # Duplicate notification আটকানো
    with notification_lock:

        if notification_key in sent_notifications:

            return jsonify({
                "status": "already_sent",
                "telegram_sent": True,
                "message": "Notification already sent"
            }), 200

    # ==============================
    # Message তৈরি
    # ==============================

    if content_type == "video":

        message_text = (
            "🎬 নতুন ভিডিও আপলোড হয়েছে!\n\n"
            f"📌 টাইটেল: {title}\n\n"
            "👇 এখনই দেখতে ক্লিক করুন:\n"
            f"{app_url}"
        )

    else:

        message_text = (
            "🆕 নতুন পোস্ট প্রকাশিত হয়েছে!\n\n"
            f"📌 টাইটেল: {title}\n\n"
            "👇 এখনই দেখতে ক্লিক করুন:\n"
            f"{app_url}"
        )

    # ==============================
    # Users নেওয়া
    # ==============================

    users = get_users()

    if not users:

        print("No Telegram users found.")

        return jsonify({
            "status": "warning",
            "telegram_sent": False,
            "total_users": 0,
            "successful_sends": 0,
            "failed_sends": 0,
            "message": "No users found"
        }), 200

    # ==============================
    # Telegram Send
    # ==============================

    successful_sends = 0
    failed_sends = 0
    errors = []

    for user_id in users:

        try:

            result = bot.send_message(
                int(user_id),
                message_text,
                disable_web_page_preview=False
            )

            if result:

                successful_sends += 1

                print(
                    f"Telegram SUCCESS -> user {user_id}"
                )

            time.sleep(0.05)

        except Exception as e:

            failed_sends += 1

            error_text = str(e)

            errors.append({
                "user_id": str(user_id),
                "error": error_text
            })

            print(
                f"Telegram FAILED -> user {user_id}: {error_text}"
            )

    # ==============================
    # Result
    # ==============================

    if successful_sends > 0:

        with notification_lock:
            sent_notifications.add(notification_key)

        print(
            f"Notification completed: "
            f"{successful_sends} successful, "
            f"{failed_sends} failed"
        )

        return jsonify({
            "status": "success",
            "telegram_sent": True,
            "total_users": len(users),
            "successful_sends": successful_sends,
            "failed_sends": failed_sends,
            "errors": errors
        }), 200

    # সব send ব্যর্থ হলে
    print(
        f"Notification FAILED: "
        f"{failed_sends} failed"
    )

    return jsonify({
        "status": "failed",
        "telegram_sent": False,
        "total_users": len(users),
        "successful_sends": successful_sends,
        "failed_sends": failed_sends,
        "errors": errors
    }), 500


# ==============================
# Save User
# ==============================

def save_user(user_id):

    users = set()

    if os.path.exists(USER_FILE):

        with open(
            USER_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            users = set(
                f.read().splitlines()
            )

    if str(user_id) not in users:

        with open(
            USER_FILE,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                f"{user_id}\n"
            )


# ==============================
# Get Users
# ==============================

def get_users():

    if not os.path.exists(USER_FILE):
        return []

    with open(
        USER_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return [
            line.strip()
            for line in f
            if line.strip()
        ]


# ==============================
# /start
# ==============================

@bot.message_handler(commands=["start"])
def start(message):

    save_user(message.chat.id)

    bot.reply_to(
        message,
        "👋 স্বাগতম!\n\n"
        "আপনি সফলভাবে যুক্ত হয়েছেন।\n\n"
        "নতুন পোস্ট অথবা ভিডিও প্রকাশিত হলে "
        "আপনার কাছে Telegram notification চলে যাবে।"
    )


# ==============================
# User Count
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text in ["/u", "u", "U", "/U"]
)
def show_user_count(message):

    if message.chat.id != ADMIN_ID:
        return

    users = get_users()

    bot.reply_to(
        message,
        f"📊 বর্তমানে মোট ইউজার সংখ্যা: "
        f"{len(users)} জন"
    )


# ==============================
# Text Broadcast
# ==============================

@bot.message_handler(commands=["broadcast"])
def broadcast_text(message):

    if message.chat.id != ADMIN_ID:
        return

    text_to_send = (
        message.text
        .replace("/broadcast", "", 1)
        .strip()
    )

    if not text_to_send:

        bot.reply_to(
            message,
            "⚠️ ব্রডকাস্টের জন্য টেক্সট লিখুন।\n\n"
            "উদাহরণ:\n"
            "/broadcast সবাই কেমন আছেন?"
        )

        return

    users = get_users()

    if not users:

        bot.reply_to(
            message,
            "❌ কোনো ইউজার পাওয়া যায়নি।"
        )

        return

    status_msg = bot.reply_to(
        message,
        f"⏳ ব্রডকাস্ট শুরু হচ্ছে...\n"
        f"মোট ইউজার: {len(users)}"
    )

    success = 0
    failed = 0

    for user_id in users:

        try:

            bot.send_message(
                int(user_id),
                text_to_send
            )

            success += 1

            time.sleep(0.05)

        except Exception as e:

            failed += 1

            print(
                f"Broadcast error {user_id}: {e}"
            )

    try:

        bot.edit_message_text(
            f"✅ ব্রডকাস্ট সম্পন্ন!\n\n"
            f"সফল: {success}\n"
            f"❌ ব্যর্থ/ব্লকড: {failed}",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )

    except Exception:
        pass


# ==============================
# Photo Broadcast
# ==============================

@bot.message_handler(
    content_types=["photo"]
)
def broadcast_photo(message):

    if message.chat.id != ADMIN_ID:
        return

    caption = message.caption or ""

    if (
        "/broadcast" not in caption
        and caption != ""
    ):
        return

    clean_caption = (
        caption
        .replace("/broadcast", "", 1)
        .strip()
    )

    photo_id = message.photo[-1].file_id

    users = get_users()

    if not users:

        bot.reply_to(
            message,
            "❌ কোনো ইউজার পাওয়া যায়নি।"
        )

        return

    status_msg = bot.reply_to(
        message,
        f"⏳ ছবি ব্রডকাস্ট শুরু হচ্ছে...\n"
        f"মোট ইউজার: {len(users)}"
    )

    success = 0
    failed = 0

    for user_id in users:

        try:

            bot.send_photo(
                int(user_id),
                photo_id,
                caption=clean_caption
            )

            success += 1

            time.sleep(0.05)

        except Exception as e:

            failed += 1

            print(
                f"Photo broadcast error "
                f"{user_id}: {e}"
            )

    try:

        bot.edit_message_text(
            f"✅ ছবি ব্রডকাস্ট সম্পন্ন!\n\n"
            f"সফল: {success}\n"
            f"❌ ব্যর্থ/ব্লকড: {failed}",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )

    except Exception:
        pass


# ==============================
# Telegram Polling
# ==============================

def start_bot_polling():

    try:

        bot.remove_webhook()

        print(
            "Telegram bot polling started..."
        )

        bot.infinity_polling(
            skip_pending=True,
            timeout=30,
            long_polling_timeout=30
        )

    except Exception as e:

        print(
            f"Bot polling error: {e}"
        )


# ==============================
# Start Telegram Bot
# ==============================

threading.Thread(
    target=start_bot_polling,
    daemon=True
).start()


# ==============================
# Start Flask
# ==============================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            8080
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )