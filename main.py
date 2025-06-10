import logging
import json
import requests
import threading
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from http.server import BaseHTTPRequestHandler, HTTPServer

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Load config
from config import TELEGRAM_BOT_TOKEN

# File to store user alerts
ALERTS_FILE = "data/alerts.json"

# Helper functions
def get_btc_price(coin="bitcoin"):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
    try:
        logging.info(f"Fetching price for {coin} from {url}")
        response = requests.get(url)
        
        if response.status_code != 200:
            logging.error(f"API request failed with status code {response.status_code}")
            return None

        data = response.json()
        price = data.get(coin, {}).get("usd", None)

        if price is None:
            logging.warning(f"No price found in API response for {coin}")
            return None

        logging.info(f"{coin.upper()} Price: ${price:,.2f}")
        return price

    except Exception as e:
        logging.error(f"Error fetching price for {coin}: {str(e)}", exc_info=True)
        return None


def load_alerts():
    try:
        with open(ALERTS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_alerts(alerts):
    with open(ALERTS_FILE, 'w') as f:
        json.dump(alerts, f, indent=2)


# Commands 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Price Pilot Bot!\n\n"
                                    "Use /price to get current BTC price.\n"
                                    "Use /setalert 70000 to set a price alert.\n"
                                    "Use /setrangalert 69500 70500 to set a price range alert.")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = get_btc_price()
    if price is not None:
        await update.message.reply_text(f"BTC Price: ${price:,.2f}")
    else:
        await update.message.reply_text("Failed to fetch BTC price. Please try again later.")


async def setalert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /setalert <target_price>")
        return

    try:
        target_price = float(context.args[0])
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return

    user_id = str(update.effective_user.id)
    alerts = load_alerts()

    if user_id not in alerts:
        alerts[user_id] = []

    alerts[user_id].append({"price": target_price, "triggered": False})
    save_alerts(alerts)

    await update.message.reply_text(f"Alert set at ${target_price:,.2f}")


async def setrangalert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /setrangalert <low_price> <high_price>")
        return

    try:
        low = float(context.args[0])
        high = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Please enter valid numbers.")
        return

    if low >= high:
        await update.message.reply_text("Low price must be less than high price.")
        return

    user_id = str(update.effective_user.id)
    alerts = load_alerts()

    if user_id not in alerts:
        alerts[user_id] = []

    alerts[user_id].append({"low": low, "high": high, "triggered": False})
    save_alerts(alerts)

    await update.message.reply_text(f"Range alert set: ${low:,.2f} - ${high:,.2f}")


async def listalerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    alerts = load_alerts().get(user_id, [])

    if not alerts:
        await update.message.reply_text("You have no active alerts.")
        return

    msg = "Your active alerts:\n"
    for i, alert in enumerate(alerts):
        if "price" in alert:
            msg += f"{i+1}. Target: ${alert['price']:,.2f}\n"
        elif "low" in alert and "high" in alert:
            msg += f"{i+1}. Range: ${alert['low']:,.2f} - ${alert['high']:,.2f}\n"

    await update.message.reply_text(msg)


# Scheduler job
async def hourly_check(context):
    logging.info("Running BTC price check...")
    app = context.job.context  # Get the app instance
    alerts = load_alerts()
    current_price = get_btc_price()

    if current_price is None:
        logging.error("BTC price is None. Skipping alert check.")
        return

    triggered = []
    for user_id, targets in alerts.items():
        for alert in targets:
            if "price" in alert:
                if not alert["triggered"] and current_price >= alert["price"]:
                    logging.info(f"Alert triggered for user {user_id}: ${alert['price']}")
                    alert["triggered"] = True
                    triggered.append((user_id, alert))
            elif "low" in alert and "high" in alert:
                if not alert["triggered"] and alert["low"] <= current_price <= alert["high"]:
                    logging.info(f"Range alert triggered for user {user_id}: ${alert['low']} - ${alert['high']}")
                    alert["triggered"] = True
                    triggered.append((user_id, alert))

    save_alerts(alerts)

    for user_id, alert in triggered:
        if "price" in alert:
            msg = f"🚨 BTC has reached your target price: ${alert['price']:,.2f}!"
        else:
            msg = f"🔔 BTC is in your target range: ${alert['low']:,.2f} - ${alert['high']:,.2f}"
        await app.bot.send_message(chat_id=user_id, text=msg)


# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(f"Update {update} caused error {context.error}", exc_info=True)


# Main function
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_error_handler(error_handler)

    # Only add handlers and start polling if DISABLE_POLLING is not set
    if os.getenv("DISABLE_POLLING") != "true":
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("price", price))
        app.add_handler(CommandHandler("setalert", setalert))
        app.add_handler(CommandHandler("setrangalert", setrangalert))
        app.add_handler(CommandHandler("listalerts", listalerts))

        scheduler = BackgroundScheduler()
        scheduler.add_job(hourly_check, 'interval', minutes=10, args=[app])
        scheduler.start()

        print("Bot started...")
        app.run_polling()
    else:
        logging.info("Polling disabled via DISABLE_POLLING")


if __name__ == "__main__":
    # Start dummy HTTP server on port 8080
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Hello from Render!")

        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()

        def log_message(self, format, *args):
            return  # Suppress logs

    server = HTTPServer(('0.0.0.0', 8080), Handler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    main()