import os
import asyncio
import logging
import aiohttp
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://insstagram-frontend.onrender.com/webhook")

if not TOKEN:
    raise ValueError("Bot Token is missing! Set the BOT_TOKEN environment variable.")

# Store user payment status
user_data = {}

# Initialize Telegram bot
telegram_app = Application.builder().token(TOKEN).build()

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Define Bot Commands ---
async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    keyboard = [["/startbot", "/paynow", "/buypremium"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(f"Welcome! Your Chat ID is: {chat_id}\nChoose an option:", reply_markup=reply_markup)

async def startbot(update: Update, context: CallbackContext):
    keyboard = [["/getqr", "/payusingupi"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("Choose a payment method:", reply_markup=reply_markup)

async def payusingupi(update: Update, context: CallbackContext):
    await update.message.reply_text("Please pay using UPI and upload a screenshot.")

async def getqr(update: Update, context: CallbackContext):
    await update.message.reply_text("Scan this QR to pay and upload a screenshot.")

async def upload_screenshot(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    user_data[user_id] = {"paid": True}
    keyboard = [["/getlink", "/clearchat", "/closebot"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("Payment verified! Choose an option:", reply_markup=reply_markup)

async def getlink(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if user_id in user_data and user_data[user_id].get("paid"):
        unique_link = f"https://insstagram-4pwg.onrender.com/{user_id}"
        await update.message.reply_text(f"Here is your link: {unique_link}")
    else:
        await update.message.reply_text("Please complete the payment first.")

async def clearchat(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("Chat history cleared. You can restart by typing /start.")

async def closebot(update: Update, context: CallbackContext):
    await update.message.reply_text("Bot closed. Type /start to restart anytime.")

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

async def set_webhook():
    """Set the webhook for Telegram bot."""
    await telegram_app.bot.set_webhook(WEBHOOK_URL)

async def keep_alive():
    """Send periodic requests to keep the Render.com instance alive."""
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                url = WEBHOOK_URL.replace("/webhook", "")
                async with session.get(url) as response:
                    logger.info(f"Keep-alive request sent. Status: {response.status}")
        except Exception as e:
            logger.error(f"Keep-alive request failed: {e}")
        await asyncio.sleep(60 * 5)  # 5 minutes

async def main():
    await telegram_app.initialize()
    await set_webhook()
    
    # Get port from environment or use 5000
    port = int(os.environ.get("PORT", 5000))
    
    # Start webhook server
    await telegram_app.start_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=WEBHOOK_URL
    )
    
    # Start keep-alive task
    asyncio.create_task(keep_alive())
    
    # Run indefinitely
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
