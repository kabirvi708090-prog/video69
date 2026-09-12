import telebot
import time
import os
import threading
from flask import Flask, request, jsonify

# ----------------- Flask Web Server -----------------
app = Flask(__name__)

SECRET_KEY = "my_app_secret_123"

@app.route('/')
def home():
    return "Bot is live and running 24/7!"

# ----------------- Webhook for App Notifications -----------------
@app.route('/notify_upload', methods=['POST'])
def notify_upload():
    data = request.get_json(silent=True) or {}
    
    if data.get('secret') != SECRET_KEY:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    video_title = data.get('title', 'নতুন ভিডিও পোস্ট করা হয়েছে!')
    app_url = data.get('app_url', 'https://t.me/FbHq11bot/deshimal')

    message_text = f"🎬 **নতুন ভিডিও আপলোড হয়েছে!**\n\n📌 **টাইটেল:** {video_title}\n\n👇 এখনই দেখতে নিচের লিংকে ক্লিক করুন:\n{app_url}"

    users = get_users()
    if not users:
        return jsonify({"status": "warning", "message": "No users found in database"}), 200

    def send_to_all():
        for u_id in users:
            try:
                bot.send_message(u_id, message_text, parse_mode="Markdown")
                time.sleep(0.04)
            except Exception:
                pass

    threading.Thread(target=send_to_all).start()
    return jsonify({"status": "success", "message": "Notification broadcast started"}), 200

# ----------------- তথ্য ও কনফিগারেশন -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8742181210:AAGYW3emIWSrli3yI0BS6IIYa5YGt2LdcKI")
ADMIN_ID = 8864523429               # আপনার numeric Telegram ID

bot = telebot.TeleBot(BOT_TOKEN)
USER_FILE = "users.txt"

def save_user(user_id):
    users = set()
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            users = set(f.read().splitlines())
    if str(user_id) not in users:
        with open(USER_FILE, "a") as f:
            f.write(f"{user_id}\n")

def get_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    return []

@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.chat.id)
    bot.reply_to(message, "👋 স্বাগতম! OPEN 🥵 বাটনে ক্লিক করে এক্স ভিডিও দেখুন 👇🏿👇🏿")

@bot.message_handler(func=lambda message: message.text in ['/u', 'u', 'U', '/U'])
def show_user_count(message):
    if message.chat.id != ADMIN_ID:
        return
    
    users = get_users()
    total_users = len(users)
    bot.reply_to(message, f"📊 **বর্তমানে মোট ইউজার সংখ্যা:** `{total_users}` জন", parse_mode="Markdown")

@bot.message_handler(commands=['broadcast'])
def broadcast_text(message):
    if message.chat.id != ADMIN_ID:
        return
    
    text_to_send = message.text.replace('/broadcast', '').strip()
    if not text_to_send:
        bot.reply_to(message, "⚠️ ব্রডকাস্টের জন্য টেক্সট লিখুন।\nউদাহরণ: `/broadcast সবাই কেমন আছেন?`", parse_mode="Markdown")
        return

    users = get_users()
    if not users:
        bot.reply_to(message, "❌ কোনো ইউজার ডাটাবেজে পাওয়া যায়নি।")
        return

    status_msg = bot.reply_to(message, f"⏳ ব্রডকাস্ট শুরু হচ্ছে... মোট ইউজার: {len(users)}")
    success, failed = 0, 0

    for u_id in users:
        try:
            bot.send_message(u_id, text_to_send)
            success += 1
            time.sleep(0.04)
        except Exception:
            failed += 1

    bot.edit_message_text(f"✅ **ব্রডকাস্ট সম্পন্ন!**\n\n সফল: {success}\n❌ ব্যর্থ/ব্লকড: {failed}", 
                          chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def broadcast_photo(message):
    if message.chat.id != ADMIN_ID:
        return
    
    caption = message.caption or ""
    if "/broadcast" in caption or caption == "":
        clean_caption = caption.replace('/broadcast', '').strip()
        photo_id = message.photo[-1].file_id

        users = get_users()
        if not users:
            bot.reply_to(message, "❌ কোনো ইউজার ডাটাবেজে পাওয়া যায়নি।")
            return

        status_msg = bot.reply_to(message, f"⏳ ছবি ব্রডকাস্ট শুরু হচ্ছে... মোট ইউজার: {len(users)}")
        success, failed = 0, 0

        for u_id in users:
            try:
                bot.send_photo(u_id, photo_id, caption=clean_caption)
                success += 1
                time.sleep(0.04)
            except Exception:
                failed += 1

        bot.edit_message_text(f"✅ **ছবি ব্রডকাস্ট সম্পন্ন!**\n\n সফল: {success}\n❌ ব্যর্থ/ব্লকড: {failed}", 
                              chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")

# ----------------- ব্যাকগ্রাউন্ডে বট পোলিং -----------------
def start_bot_polling():
    bot.remove_webhook()
    bot.infinity_polling()

threading.Thread(target=start_bot_polling, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
