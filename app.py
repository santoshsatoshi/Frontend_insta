import os
import asyncio
import threading
import logging
import requests
import time
import traceback
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

# Function to start the event loop
def start_event_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

# Define a simple coroutine to test the event loop
async def test_loop():
    logging.getLogger(__name__).info("Event loop is running.")

# Create and start the MAIN_LOOP if not already set.
if not app.config.get("MAIN_LOOP"):
    loop = asyncio.new_event_loop()
    app.config["MAIN_LOOP"] = loop
    threading.Thread(target=start_event_loop, args=(loop,), daemon=True).start()
    # Schedule our test coroutine
    asyncio.run_coroutine_threadsafe(test_loop(), loop)

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
    logger.info(f"Handling /start command for chat: {chat_id}")
    await update.message.reply_text(
        f"👋 Welcome! Your Chat ID is: {chat_id}\n\n"
        "Choose an option:\n"
        "➡️ /startbot - Start bot\n"
        "➡️ /paynow - Pay now\n"
        "➡️ /buypremium - Buy premium"
    )

async def startbot(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    logger.info(f"Handling /startbot command for chat: {chat_id}")
    await update.message.reply_text(
        "💰 Choose a payment method:\n"
        "📌 /getqr - Get QR Code\n"
        "📌 /payusingupi - Pay using UPI"
    )

async def payusingupi(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    logger.info(f"Handling /payusingupi command for chat: {chat_id}")
    await update.message.reply_text("💳 Please pay using UPI and upload a screenshot.")

async def getqr(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    logger.info(f"Handling /getqr command for chat: {chat_id}")
    await update.message.reply_text("📸 Scan this QR to pay and upload a screenshot.")

async def upload_screenshot(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    logger.info(f"Handling photo upload from chat: {chat_id}")
    user_data[chat_id] = {"paid": True}
    await update.message.reply_text(
        "✅ Payment verified!\n\nChoose an option:\n"
        "🔗 /getlink - Get your link\n"
        "🗑️ /clearchat - Clear chat\n"
        "❌ /closebot - Close bot"
    )

async def getlink(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    logger.info(f"Handling /getlink command for chat: {chat_id}")
    if chat_id in user_data and user_data[chat_id].get("paid"):
        unique_link = f"https://insstagram-4pwg.onrender.com/{chat_id}"
        await update.message.reply_text(f"🔗 Here is your link: {unique_link}")
    else:
        await update.message.reply_text("⚠️ Please complete the payment first.")

async def clearchat(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    logger.info(f"Handling /clearchat command for chat: {chat_id}")
    if chat_id in user_data:
        del user_data[chat_id]
    await update.message.reply_text("🧹 Chat history cleared. You can restart by typing /start.")

async def closebot(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    logger.info(f"Handling /closebot command for chat: {chat_id}")
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

# Synchronous webhook route with enhanced logging
@app.route("/webhook", methods=["POST"])
def webhook():
    logger.info("Webhook called.")
    try:
        loop = app.config['MAIN_LOOP']
    except KeyError:
        logger.error("MAIN_LOOP not found in Flask config.")
        return "Error", 500

    update_json = request.get_json()
    logger.info(f"Received update: {update_json}")
    update = Update.de_json(update_json, telegram_app.bot)

    # Schedule async processing on the main event loop without waiting for it to complete.
    asyncio.run_coroutine_threadsafe(process_update(update), loop)
    return "OK"

async def process_update(update: Update):
    logger.info("Entered process_update coroutine.")
    try:
        if not telegram_app._initialized:
            logger.info("Initializing telegram_app.")
            await telegram_app.initialize()
        logger.info("Before processing update via telegram_app.process_update.")
        await telegram_app.process_update(update)
        logger.info("After processing update via telegram_app.process_update.")
    except Exception as e:
        logger.error("Error processing update:")
        logger.error(traceback.format_exc())
        if update.effective_chat:
            try:
                await telegram_app.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ An error occurred. Please try again later."
                )
            except Exception as inner_e:
                logger.error("Failed to send error message:")
                logger.error(traceback.format_exc())

async def set_webhook():
    logger.info("Setting webhook...")
    await telegram_app.bot.set_webhook(WEBHOOK_URL)
    logger.info("Webhook set.")

def keep_alive():
    while True:
        try:
            requests.get(WEBHOOK_URL.replace("/webhook", ""))
            logger.info("✅ Keep-alive request sent.")
        except requests.exceptions.RequestException as e:
            logger.error(f"⚠️ Keep-alive request failed: {e}")
        time.sleep(60 * 5)  # every 5 minutes

# For local development, the __main__ block will be used.
if __name__ == "__main__":
    loop = app.config["MAIN_LOOP"]
    loop.run_until_complete(set_webhook())
    # Optionally, start the keep-alive thread
    threading.Thread(target=keep_alive, daemon=True).start()
    # For local testing, you can use waitress or similar instead of gunicorn.
    from waitress import serve
    serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
