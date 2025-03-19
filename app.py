from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import os
import asyncio

# Fetch bot token from environment variable
TOKEN = os.environ.get("TOKEN")  # Set this in Render's environment settings
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://insstagram-frontend.onrender.com/webhook")  # Change this after deployment

if not TOKEN:
    raise ValueError("Bot Token is missing! Set the TOKEN environment variable.")

app = Flask(__name__)

# Store user payment status
user_data = {}

# Initialize the Telegram Bot application
telegram_app = Application.builder().token(TOKEN).build()

async def start(update: Update, context: CallbackContext):
    """Sends the Chat ID and displays the main menu."""
    chat_id = update.effective_chat.id
    keyboard = [["/startbot", "/paynow", "/buypremium"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(f"Welcome! Your Chat ID is: {chat_id}\nChoose an option:", reply_markup=reply_markup)

async def startbot(update: Update, context: CallbackContext):
    """Shows payment options."""
    keyboard = [["/getqr", "/payusingupi"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("Choose a payment method:", reply_markup=reply_markup)

async def payusingupi(update: Update, context: CallbackContext):
    """Informs the user to pay via UPI and upload a screenshot."""
    await update.message.reply_text("Please pay using UPI and upload a screenshot.")

async def getqr(update: Update, context: CallbackContext):
    """Provides a QR code for payment."""
    await update.message.reply_text("Scan this QR to pay and upload a screenshot.")

async def upload_screenshot(update: Update, context: CallbackContext):
    """Verifies payment and provides the next steps."""
    user_id = update.message.chat_id
    user_data[user_id] = {"paid": True}  # Mark user as paid
    keyboard = [["/getlink", "/clearchat", "/closebot"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("Payment verified! Choose an option:", reply_markup=reply_markup)

async def getlink(update: Update, context: CallbackContext):
    """Generates and sends a unique link based on the user's Chat ID."""
    user_id = update.message.chat_id
    if user_id in user_data and user_data[user_id].get("paid"):
        unique_link = f"https://insstagram-4pwg.onrender.com/{user_id}"
        await update.message.reply_text(f"Here is your link: {unique_link}")
    else:
        await update.message.reply_text("Please complete the payment first.")

async def clearchat(update: Update, context: CallbackContext):
    """Clears the chat history and resets user data."""
    user_id = update.message.chat_id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text("Chat history cleared. You can restart by typing /start.")

async def closebot(update: Update, context: CallbackContext):
    """Closes the bot session for the user."""
    await update.message.reply_text("Bot closed. Type /start to restart anytime.")

# Register Telegram handlers
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

@app.route("/")
def home():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
async def webhook():
    """Handle incoming Telegram updates."""
    update = Update.de_json(request.get_json(), telegram_app.bot)
    await telegram_app.process_update(update)
    return "OK"

async def set_webhook():
    """Set webhook for Telegram bot."""
    await telegram_app.bot.set_webhook(WEBHOOK_URL)

if __name__ == "__main__":
    asyncio.run(set_webhook()) 
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
