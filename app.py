import os
import asyncio
import threading
import logging
import requests
import time
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://insstagram-frontend.onrender.com/webhook")

if not TOKEN:
    raise ValueError("Bot Token is missing! Set the BOT_TOKEN environment variable.")

# Initialize Flask app
app = Flask(__name__)

# Store user payment status
user_data = {}

# Initialize Telegram bot
telegram_app = Application.builder().token(TOKEN).build()

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Define Bot Commands ---
async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"👋 Welcome! Your Chat ID is: {chat_id}\n\n"
        "Choose an option:\n"
        "➡️ /startbot - Start bot\n"
        "➡️ /paynow - Pay now\n"
        "➡️ /buypremium - Buy premium"
    )

async def startbot(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "💰 Choose a payment method:\n"
        "📌 /getqr - Get QR Code\n"
        "📌 /payusingupi - Pay using UPI"
    )

async def payusingupi(update: Update, context: CallbackContext):
    await update.message.reply_text("💳 Please pay using UPI and upload a screenshot.")

async def getqr(update: Update, context: CallbackContext):
    await update.message.reply_text("📸 Scan this QR to pay and upload a screenshot.")

async def upload_screenshot(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    user_data[user_id] = {"paid": True}
    await update.message.reply_text(
        "✅ Payment verified!\n\nChoose an option:\n"
        "🔗 /getlink - Get your link\n"
        "🗑️ /clearchat - Clear chat\n"
        "❌ /closebot - Close bot"
    )

async def getlink(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if user_id in user_data and user_data[user_id].get("paid"):
        unique_link = f"https://insstagram-4pwg.onrender.com/{user_id}"
        await update.message.reply_text(f"🔗 Here is your link: {unique_link}")
    else:
        await update.message.reply_text("⚠️ Please complete the payment first.")

async def clearchat(update: Update, context: CallbackContext):
    user_id = update.message.chat_id

    # Delete the last 10 messages (adjust as needed)
    for i in range(10):  
        try:
            await context.bot.delete_message(chat_id=user_id, message_id=update.message.message_id - i)
        except Exception as e:
            logger.error(f"Failed to delete message {update.message.message_id - i}: {e}")

    # Clear user payment data
    if user_id in user_data:
        del user_data[user_id]

    # Notify the user
    await update.message.reply_text("🧹 Chat history cleared. You can restart by typing /start.")

async def closebot(update: Update, context: CallbackContext):
    await update.message.reply_text("🚪 Bot closed. Type /start to restart anytime.")

# --- Register Handlers ---
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("startbot", startbot))
telegram_app.add_handler(CommandHandler("paynow", startbot))
telegram_app.add_handler(CommandHandler("buypremium", startbot))
telegram_app.add_handler(CommandHandler("payusingupi", payusingupi))
telegram_app.add_handler(CommandHandler("getqr", getqr))
telegram_app.add_handler(MessageHandler(filters.PHOTO, upload_screenshot))
telegram_app.add_handler(CommandHandler("getlink", getlink))
telegram_app.add_handler(CommandHandler("clearchat", clearchat))
telegram_app.add_handler(CommandHandler("closebot", closebot))

# --- Flask Routes ---
@app.route("/")
def home():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
async def webhook():
    """Handle incoming Telegram updates asynchronously."""
    update = Update.de_json(request.get_json(), telegram_app.bot)

    if not telegram_app._initialized:
        await telegram_app.initialize()

    try:
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        if update.effective_chat:
            try:
                await telegram_app.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ An error occurred. Please try again later.")
            except Exception as inner_e:
                logger.error(f"Failed to send error message: {inner_e}")

    return "OK"

async def set_webhook():
    """Set the webhook for Telegram bot."""
    await telegram_app.bot.set_webhook(WEBHOOK_URL)

def run_flask():
    """Run Flask in a separate thread."""
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

def keep_alive():
    while True:
        try:
            requests.get(WEBHOOK_URL.replace("/webhook", ""))
            logger.info("✅ Keep-alive request sent.")
        except requests.exceptions.RequestException as e:
            logger.error(f"⚠️ Keep-alive request failed: {e}")
        time.sleep(60 * 5)  # Send request every 5 minutes

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(set_webhook())
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    keep_alive_thread = threading.Thread(target=keep_alive)
    keep_alive_thread.start()
