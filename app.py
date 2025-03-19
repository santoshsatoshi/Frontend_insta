import os
import asyncio
import threading
import logging
import aiohttp
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

# Initialize Flask app (required for Gunicorn)
app = Flask(__name__)

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

# --- Bot Command Handlers (same as before) ---
async def start(update: Update, context: CallbackContext):
    # ... (keep original command handlers unchanged)
    # [Include all your original command handlers here]

# --- Flask Routes ---
@app.route("/")
def home():
    return "Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming Telegram updates."""
    update = Update.de_json(request.get_json(), telegram_app.bot)
    
    # Use a thread-safe method to process the update
    future = asyncio.run_coroutine_threadsafe(
        process_update(update),
        telegram_app._loop
    )
    future.result()
    return "OK"

async def process_update(update: Update):
    """Process update in the bot's event loop."""
    async with telegram_app:
        await telegram_app.process_update(update)

async def set_webhook():
    """Configure webhook for Telegram bot."""
    await telegram_app.bot.set_webhook(WEBHOOK_URL)

async def keep_alive():
    """Keep Render instance alive."""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await session.get(WEBHOOK_URL.replace("/webhook", ""))
                logger.info("Keep-alive request sent")
            except Exception as e:
                logger.error(f"Keep-alive failed: {e}")
            await asyncio.sleep(300)

def run_flask():
    """Run Flask in production mode."""
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), threaded=True)

async def main():
    """Main async setup."""
    await telegram_app.initialize()
    await set_webhook()
    asyncio.create_task(keep_alive())

    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Keep the event loop running
    await asyncio.Event().wait()

if __name__ == "__main__":
    # Start the async event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
