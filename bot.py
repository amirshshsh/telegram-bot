import re
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# -------------------- تنظیمات --------------------
BOT_TOKEN = "8526214876:AAHMFhpRwiVehBxvO44ESN7h2AeF_svM61k"
API_KEY = "220973:6911ba8db2337"
BASE_URL = "https://api.one-api.ir/instagram/v1"
CHANNEL_USERNAME = "@sarmaye_dollari"
USERS_FILE = "users.json"

# -------------------- مدیریت کاربران --------------------
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def register_user(user_id):
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = True
        save_users(users)

# -------------------- بررسی عضویت --------------------
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=update.effective_user.id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# -------------------- ارسال پیام عضویت --------------------
async def request_membership(update: Update):
    keyboard = [
        [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
        [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "❌ برای استفاده از ربات باید عضو کانال ما باشی.",
        reply_markup=reply_markup
    )

# -------------------- بررسی مجدد عضویت --------------------
async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    fake_update = Update(update.update_id, message=query.message)
    if await check_membership(fake_update, context):
        await query.message.edit_text("✅ عضویت شما تایید شد! حالا لینک اینستاگرام بفرست 🌐")
    else:
        await query.message.reply_text("⛔ هنوز عضو کانال نیستی.")

# -------------------- استخراج‌ها --------------------
def extract_username(url: str):
    match = re.search(r"instagram\.com/([^/?#]+)", url)
    return match.group(1) if match else None

def extract_shortcode(url: str):
    for part in ["/p/", "/reel/", "/tv/"]:
        if part in url:
            try:
                return url.split(part)[1].split("/")[0]
            except:
                return None
    return None

# -------------------- دستور /start --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 سلام! به ربات دانلودر اینستاگرام خوش اومدی.\n\n"
        "📸 لینک پست، ریلز یا پروفایل اینستاگرام رو بفرست تا برات دانلود کنم.\n\n"
        "⚠️ فقط اعضای کانال می‌تونن از ربات استفاده کنن."
    )

# -------------------- پردازش پیام --------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user.id)

    # بررسی عضویت
    if not await check_membership(update, context):
        await request_membership(update)
        return

    url = update.message.text.strip()
    shortcode = extract_shortcode(url)

    headers = {"one-api-token": API_KEY}

    # پست
    if shortcode:
        resp = requests.get(f"{BASE_URL}/post/", headers=headers, params={"shortcode": shortcode})
        data = resp.json()
        if data.get("status") != 200:
            await update.message.reply_text("⚠️ خطا در دریافت پست یا پست خصوصی است.")
            return
        caption = data["result"].get("caption", "")
        for media in data["result"].get("media", []):
            if media["type"] == "photo":
                await update.message.reply_photo(photo=media["url"], caption=caption)
            elif media["type"] == "video":
                await update.message.reply_video(video=media["url"], caption=caption)
        return

    # پروفایل
    username = extract_username(url)
    if not username:
        await update.message.reply_text("❌ لینک معتبر نیست.")
        return

    resp = requests.get(f"{BASE_URL}/user/", headers=headers, params={"username": username})
    data = resp.json()
    if data.get("status") != 200:
        await update.message.reply_text("⚠️ خطا در دریافت اطلاعات کاربر.")
        return

    user = data["result"]
    profile_msg = f"""📸 **{user['username']}**
👤 {user['full_name']}
📝 Bio: {user.get('bio', 'ندارد')}
👥 Followers: {user['followers']}
📦 Posts: {user['posts']}"""
    await update.message.reply_photo(user["profile_hd"], caption=profile_msg, parse_mode="Markdown")

# -------------------- ارسال پیام همگانی --------------------
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != 335571779:
        await update.message.reply_text("❌ فقط مدیر می‌تونه این دستور رو بزنه.")
        return
    if not context.args:
        await update.message.reply_text("❌ لطفاً متن پیام رو بعد از دستور بنویس.")
        return

    msg = " ".join(context.args)
    users = list(load_users().keys())
    count = 0
    for uid in users:
        try:
            await context.bot.send_message(int(uid), msg)
            count += 1
        except:
            pass
    await update.message.reply_text(f"✅ پیام برای {count} کاربر ارسال شد.")

# -------------------- اجرای ربات --------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(check_membership_callback, pattern="check_membership"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
