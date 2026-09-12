import telebot
import time
import os
import threading
import requests

from flask import Flask, request, jsonify

# =========================================================
# FLASK WEB SERVER
# =========================================================

app = Flask(__name__)

SECRET_KEY = "my_app_secret_123"

# =========================================================
# TELEGRAM BOT CONFIGURATION
# =========================================================

BOT_TOKEN = "8742181210:AAGYW3emIWSrli3yI0BS6IIYa5YGt2LdcKI"

ADMIN_ID = 8864523429

bot = telebot.TeleBot(BOT_TOKEN)

USER_FILE = "users.txt"


# =========================================================
# HOME
# =========================================================

@app.route('/')
def home():
    return "Bot is live and running 24/7!"


# =========================================================
# AUTOMATIC APP POST / VIDEO NOTIFICATION
# =========================================================
#
# আপনার App যখন নতুন Post অথবা Video Publish করবে,
# তখন এই URL-এ POST request পাঠাবে:
#
# /notify_upload
#
# =========================================================

@app.route('/notify_upload', methods=['POST'])
def notify_upload():

    data = request.get_json(silent=True) or {}

    # Secret check
    if data.get('secret') != SECRET_KEY:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 401

    # Post / Video information
    title = data.get(
        'title',
        'নতুন পোস্ট প্রকাশিত হয়েছে!'
    )

    app_url = data.get(
        'app_url',
        ''
    )

    content_type = data.get(
        'type',
        'post'
    )

    # =====================================================
    # VIDEO NOTIFICATION
    # =====================================================

    if content_type == "video":

        message_text = (
            "🎬 নতুন ভিডিও আপলোড হয়েছে!\n\n"
            f"📌 টাইটেল: {title}\n\n"
            "👇 এখনই দেখতে নিচের লিংকে ক্লিক করুন:\n"
            f"{app_url}"
        )

    # =====================================================
    # NORMAL POST NOTIFICATION
    # =====================================================

    else:

        message_text = (
            "🆕 নতুন পোস্ট প্রকাশিত হয়েছে!\n\n"
            f"📌 টাইটেল: {title}\n\n"
            "👇 এখনই দেখতে নিচের লিংকে ক্লিক করুন:\n"
            f"{app_url}"
        )

    # =====================================================
    # GET ALL USERS
    # =====================================================

    users = get_users()

    if not users:

        return jsonify({
            "status": "warning",
            "message": "No users found in database"
        }), 200

    # =====================================================
    # SEND NOTIFICATION TO ALL USERS
    # =====================================================

    def send_to_all():

        success = 0
        failed = 0

        for u_id in users:

            try:

                bot.send_message(
                    int(u_id),
                    message_text,
                    disable_web_page_preview=False
                )

                success += 1

                # Telegram rate limit এড়ানোর জন্য
                time.sleep(0.05)

            except Exception as e:

                failed += 1

                print(
                    f"Notification failed for {u_id}: {e}"
                )

        print(
            f"Notification finished | "
            f"Success: {success} | Failed: {failed}"
        )

    # Background thread
    threading.Thread(
        target=send_to_all,
        daemon=True
    ).start()

    return jsonify({
        "status": "success",
        "message": "Notification broadcast started",
        "total_users": len(users)
    }), 200


# =========================================================
# SAVE USER
# =========================================================

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


# =========================================================
# GET USERS
# =========================================================

def get_users():

    if os.path.exists(USER_FILE):

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

    return []


# =========================================================
# START COMMAND
# =========================================================

@bot.message_handler(
    commands=['start']
)
def start(message):

    save_user(
        message.chat.id
    )

    bot.reply_to(
        message,
        "👋 স্বাগতম!\n\n"
        "আপনি সফলভাবে যুক্ত হয়েছেন।\n\n"
        "নতুন পোস্ট অথবা ভিডিও প্রকাশিত হলে "
        "আপনার কাছে Telegram notification চলে যাবে।"
    )


# =========================================================
# USER COUNT
# ADMIN ONLY
# =========================================================

@bot.message_handler(
    func=lambda message:
        message.text in ['/u', 'u', 'U', '/U']
)
def show_user_count(message):

    if message.chat.id != ADMIN_ID:
        return

    users = get_users()

    total_users = len(users)

    bot.reply_to(
        message,
        f"📊 বর্তমানে মোট ইউজার সংখ্যা: "
        f"{total_users} জন"
    )


# =========================================================
# TEXT BROADCAST
# ADMIN ONLY
# =========================================================

@bot.message_handler(
    commands=['broadcast']
)
def broadcast_text(message):

    if message.chat.id != ADMIN_ID:
        return

    text_to_send = (
        message.text
        .replace('/broadcast', '', 1)
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

    for u_id in users:

        try:

            bot.send_message(
                int(u_id),
                text_to_send
            )

            success += 1

            time.sleep(0.05)

        except Exception:

            failed += 1

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


# =========================================================
# PHOTO BROADCAST
# ADMIN ONLY
# =========================================================

@bot.message_handler(
    content_types=['photo']
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
        .replace('/broadcast', '', 1)
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

    for u_id in users:

        try:

            bot.send_photo(
                int(u_id),
                photo_id,
                caption=clean_caption
            )

            success += 1

            time.sleep(0.05)

        except Exception:

            failed += 1

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


# =========================================================
# BOT POLLING
# =========================================================

def start_bot_polling():

    bot.remove_webhook()

    print(
        "Telegram bot polling started..."
    )

    bot.infinity_polling(
        skip_pending=True,
        timeout=30,
        long_polling_timeout=30
    )


threading.Thread(
    target=start_bot_polling,
    daemon=True
).start()


# =========================================================
# START FLASK SERVER
# =========================================================

if __name__ == '__main__':

    port = int(
        os.environ.get(
            'PORT',
            8080
        )
    )

    app.run(
        host='0.0.0.0',
        port=port
    )