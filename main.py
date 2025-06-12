import logging
import os
import time
import asyncio
import nest_asyncio
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import requests
import sqlite3
from flask import Flask, render_template_string, request
import smtplib
from email.mime.text import MIMEText


# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Load config
from config import TELEGRAM_BOT_TOKEN

# Global cached prices dictionary
last_known_prices = {}  # {"bitcoin": (price, timestamp)}

# Global last check time
last_check_time = None

# Supported coin mapping
COIN_MAP = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "xrp": "xrp"
}

# Headers to mimic browser traffic
HEADERS = {
    "User-Agent": "PricePilotBot/1.0",
    "Accept": "application/json"
}

# Global app reference for jobs
app_instance = None

# Web dashboard app
dashboard_app = Flask(__name__)


# SQLite Setup
def init_db():
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()

    # Main alerts table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            coin_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            target_price REAL,
            low REAL,
            high REAL,
            triggered BOOLEAN DEFAULT 0
        )
    """)

    # Subscription tables
    cur.execute("CREATE TABLE IF NOT EXISTS subscribers (user_id TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS sol_subscribers (user_id TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS eth_subscribers (user_id TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS xrp_subscribers (user_id TEXT PRIMARY KEY)")

    conn.commit()
    conn.close()


def load_alerts(include_triggered=False):
    query = "SELECT * FROM alerts WHERE triggered = 0"
    if include_triggered:
        query = "SELECT * FROM alerts"

    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()

    alerts = {}
    for row in rows:
        alert_id = row[0]
        user_id = row[1]
        coin_id = row[2]
        alert_type = row[3]

        if user_id not in alerts:
            alerts[user_id] = []

        if alert_type == "price":
            price = row[4]
            alerts[user_id].append({
                "id": alert_id,
                "coin_id": coin_id,
                "price": price,
                "triggered": bool(row[7])
            })
        elif alert_type == "range":
            low = row[5]
            high = row[6]
            alerts[user_id].append({
                "id": alert_id,
                "coin_id": coin_id,
                "low": low,
                "high": high,
                "triggered": bool(row[7])
            })

    conn.close()
    return alerts


def save_alert(user_id, coin_id, alert_type, price=None, low=None, high=None):
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    if alert_type == "price":
        cur.execute("INSERT INTO alerts (user_id, coin_id, alert_type, target_price) VALUES (?, ?, ?, ?)",
                    (user_id, coin_id, alert_type, price))
    elif alert_type == "range":
        cur.execute("INSERT INTO alerts (user_id, coin_id, alert_type, low, high) VALUES (?, ?, ?, ?, ?)",
                    (user_id, coin_id, alert_type, low, high))
    conn.commit()
    conn.close()


def clear_all_alerts():
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM alerts")
    conn.commit()
    conn.close()


# Helper functions
def get_crypto_price(coin_id, symbol, max_retries=2, retry_delay=5, force_price=None):
    global last_known_prices

    coin_name = coin_id.capitalize()
    symbol_upper = symbol.upper()

    # Use forced price during testing
    if force_price is not None:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        last_known_prices[coin_id] = (force_price, timestamp)
        logging.info(f"[TEST] Forced price: ${force_price:,.2f} for {symbol_upper}")
        return force_price

    # List of free APIs to try in order
    apis = [
        {
            "name": "CoinGecko",
            "url": f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        },
        {
            "name": "CoinPaprika",
            "url": f"https://api.coinpaprika.com/v1/tickers/{symbol.lower()}-{coin_id}"
        }
    ]

    for api in apis:
        try:
            logging.info(f"Trying {api['name']} API for {symbol_upper}...")
            response = requests.get(api["url"], timeout=10, headers=HEADERS)

            if response.status_code == 200:
                data = response.json()

                if api["name"] == "CoinGecko":
                    price = data.get(coin_id, {}).get("usd")
                elif api["name"] == "CoinPaprika":
                    price = data.get("quotes", {}).get("USD", {}).get("price")

                if price:
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                    last_known_prices[coin_id] = (price, timestamp)
                    logging.info(f"{symbol_upper} Price: ${price:,.2f} | Updated at: {timestamp}")
                    return price
                else:
                    logging.warning(f"{api['name']} returned no usable price for {symbol_upper}")

        except Exception as e:
            logging.error(f"Error fetching from {api['name']} for {symbol_upper}: {str(e)}", exc_info=True)
        time.sleep(retry_delay)

    # Try CoinMarketCap (fallback, requires API key) 
    coinmarketcap_api_key = os.getenv("COINMARKETCAP_API_KEY")
    if coinmarketcap_api_key:
        try:
            logging.info(f"Trying CoinMarketCap for {symbol_upper} (fallback)...")
            url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest" 
            params = {"symbol": symbol_upper, "convert": "USD"}
            headers = {
                "X-CMC_PRO_API_KEY": coinmarketcap_api_key,
                "Accept": "application/json"
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                try:
                    price = data["data"][symbol_upper][0]["quote"]["USD"]["price"]
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                    last_known_prices[coin_id] = (price, timestamp)
                    logging.info(f"CoinMarketCap returned {symbol_upper} price: ${price:,.2f} | Updated at: {timestamp}")
                    return price
                except KeyError:
                    logging.error(f"Unexpected CoinMarketCap response structure: {data}")
                    return None
            else:
                logging.warning(f"CoinMarketCap failed with status code {response.status_code}")
        except Exception as e:
            logging.error(f"Error fetching from CoinMarketCap for {symbol_upper}: {str(e)}", exc_info=True)

    # Fallback to cached price
    if coin_id in last_known_prices:
        price, timestamp = last_known_prices[coin_id]
        logging.warning(f"Returning cached {symbol_upper} price: ${price:,.2f} | Last updated: {timestamp}")
        return price
    else:
        logging.critical(f"All APIs failed and no cached price available for {symbol_upper}.")
        return None


# Format relative time
def format_time_ago(timestamp_str):
    try:
        then = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        diff_seconds = (now - then).total_seconds()

        if diff_seconds < 60:
            return "just now"
        elif diff_seconds < 3600:
            return f"{int(diff_seconds // 60)} mins ago"
        else:
            hour = then.strftime("%I:%M %p")
            return f"at {hour}"
    except:
        return "N/A"


# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Price Pilot Bot!\n\n"
                                    "Use /price <coin> to get current crypto price.\n"
                                    "Examples:\n"
                                    "  /price btc\n"
                                    "  /setalert eth 3500\n"
                                    "  /setrangalert sol 140 160\n\n"
                                    "Want regular updates?\n"
                                    "  /subscribe - BTC/ETH/SOL/XRP every 30 mins\n"
                                    "  /subscribesol\n"
                                    "  /subscribexrp")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /price <coin> (e.g., /price btc)")
        return

    coin_arg = context.args[0].lower()
    if coin_arg not in COIN_MAP:
        await update.message.reply_text(f"Unsupported coin: {coin_arg}. Supported: btc, eth, sol, xrp")
        return

    coin_id = COIN_MAP[coin_arg]
    symbol = coin_arg.upper()
    current_price = get_crypto_price(coin_id, symbol)

    if current_price is not None:
        timestamp = last_known_prices.get(coin_id, (None, "N/A"))[1]
        time_msg = f" (Updated {format_time_ago(timestamp)}"
        await update.message.reply_text(f"{symbol} Price: ${current_price:,.2f}{time_msg}")
    else:
        await update.message.reply_text(f"Failed to fetch {symbol} price.")


async def setalert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /setalert <coin> <target_price>")
        return

    coin_arg = context.args[0].lower()
    target_price_str = context.args[1]

    if coin_arg not in COIN_MAP:
        await update.message.reply_text(f"Unsupported coin: {coin_arg}. Supported: btc, eth, sol, xrp")
        return

    try:
        target_price = float(target_price_str)
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return

    coin_id = COIN_MAP[coin_arg]
    user_id = str(update.effective_user.id)
    save_alert(user_id, coin_id, "price", price=target_price)
    await update.message.reply_text(f"{coin_id.capitalize()} alert set at ${target_price:,.2f}")


async def setrangalert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /setrangalert <coin> <low> <high>")
        return

    coin_arg = context.args[0].lower()
    low_str = context.args[1]
    high_str = context.args[2]

    if coin_arg not in COIN_MAP:
        await update.message.reply_text(f"Unsupported coin: {coin_arg}. Supported: btc, eth, sol, xrp")
        return

    try:
        low = float(low_str)
        high = float(high_str)
    except ValueError:
        await update.message.reply_text("Please enter valid numbers.")
        return

    if low >= high:
        await update.message.reply_text("Low must be less than high.")
        return

    coin_id = COIN_MAP[coin_arg]
    user_id = str(update.effective_user.id)
    save_alert(user_id, coin_id, "range", low=low, high=high)
    await update.message.reply_text(f"{coin_id.capitalize()} range alert set: ${low:,.2f} - ${high:,.2f}")


async def listalerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    alerts = load_alerts().get(user_id, [])

    if not alerts:
        await update.message.reply_text("You have no active alerts.")
        return

    msg = "Your active alerts:\n"
    for i, alert in enumerate(alerts):
        coin_name = alert.get("coin_id", "unknown").capitalize()
        if "price" in alert:
            msg += f"{i+1}. {coin_name} Target: ${alert['price']:,.2f}\n"
        elif "low" in alert and "high" in alert:
            msg += f"{i+1}. {coin_name} Range: ${alert['low']:,.2f} - ${alert['high']:,.2f}\n"

    await update.message.reply_text(msg)


async def forcerun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /forcerun <coin> <price>")
        return

    coin_arg = context.args[0].lower()
    if coin_arg not in COIN_MAP:
        await update.message.reply_text(f"Unsupported coin: {coin_arg}. Supported: btc, eth, sol, xrp")
        return

    try:
        fake_price = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Invalid price value.")
        return

    logging.info(f"[Manual Trigger] Simulating price: {coin_arg} @ ${fake_price:,.2f}")
    await hourly_check(app_instance, override_price=fake_price, override_coin=coin_arg)
    await update.message.reply_text(f"Manual price check triggered for {coin_arg} @ ${fake_price:,.2f}")


async def sendprices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Manually triggering 30-min price update...")
    if app_instance:
        await send_periodic_prices(app_instance)
        await update.message.reply_text("✅ Sent full market update to all subscribers.")
    else:
        await update.message.reply_text("❌ Bot not running in polling mode.")


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Subscribed to BTC/ETH/SOL/XRP price updates (every 30 mins)")


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text("❌ Unsubscribed from price updates")


async def subscribesol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO sol_subscribers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Subscribed to Solana price updates")


async def subscribexrp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO xrp_subscribers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Subscribed to XRP price updates")


async def uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I'm online and working!")


async def lastcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_check_time
    if last_check_time:
        await update.message.reply_text(f"Last price check: {format_time_ago(last_check_time)}")
    else:
        await update.message.reply_text("No price checks yet.")


# Scheduler job
async def hourly_check(app, override_price=None, override_coin="bitcoin"):
    global last_check_time
    logging.info("Running scheduled price check...")

    alerts = load_alerts()
    triggered = []

    for user_id, targets in alerts.items():
        for alert in targets:
            coin_id = alert.get("coin_id", "bitcoin")
            symbol = next(k for k, v in COIN_MAP.items() if v == coin_id).upper()

            current_price = get_crypto_price(coin_id, symbol, force_price=override_price)

            if current_price is None:
                continue

            if "price" in alert:
                if not alert["triggered"] and current_price >= alert["price"]:
                    logging.info(f"{coin_id} alert triggered for user {user_id}: ${alert['price']}")
                    alert["triggered"] = True
                    triggered.append((user_id, alert))
            elif "low" in alert and "high" in alert:
                if not alert["triggered"] and alert["low"] <= current_price <= alert["high"]:
                    logging.info(f"{coin_id} range alert triggered for user {user_id}: ${alert['low']} - ${alert['high']}")
                    alert["triggered"] = True
                    triggered.append((user_id, alert))

    # Mark alerts as triggered
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    for user_id, alert in triggered:
        cur.execute("UPDATE alerts SET triggered = 1 WHERE id = ?", (alert["id"],))
    conn.commit()
    conn.close()

    # Send messages
    for user_id, alert in triggered:
        coin_name = alert.get("coin_id", "BTC").capitalize()
        if "price" in alert:
            msg = f"🚨 {coin_name} has reached your target price: ${alert['price']:,.2f}!"
        elif "low" in alert and "high" in alert:
            msg = f"🔔 {coin_name} is in your target range: ${alert['low']:,.2f} - ${alert['high']:,.2f}"

        await app.bot.send_message(chat_id=user_id, text=msg)


# Periodic price message job
async def send_periodic_prices(app):
    logging.info("Sending 30-min price update...")

    # Get prices
    btc_price = get_crypto_price("bitcoin", "btc")
    eth_price = get_crypto_price("ethereum", "eth")
    sol_price = get_crypto_price("solana", "sol")
    xrp_price = get_crypto_price("xrp", "xrp")

    if any(p is None for p in [btc_price, eth_price, sol_price, xrp_price]):
        logging.warning("Failed to fetch one or more prices. Skipping periodic update.")
        return

    # Load all general subscribers
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers")
    subscriber_rows = cur.fetchall()
    conn.close()

    # Build message
    msg = "📊 30-Minute Market Update\n\n"
    msg += f"₿ Bitcoin (BTC): ${btc_price:,.2f}\n"
    msg += f"🔷 Ethereum (ETH): ${eth_price:,.2f}\n"
    msg += f"🟣 Solana (SOL): ${sol_price:,.2f}\n"
    msg += f"🔵 XRP (XRP): ${xrp_price:,.2f}"

    # Send to all subscribers
    for row in subscriber_rows:
        user_id = row[0]
        try:
            await app.bot.send_message(chat_id=user_id, text=msg)
            logging.info(f"Sent 30-min update to {user_id}")
        except Exception as e:
            logging.error(f"Failed to send to {user_id}: {e}")


# Web Dashboard Routes
@dashboard_app.route('/')
def dashboard():
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM alerts")
    alerts = cur.fetchall()
    conn.close()

    html = """
    <html>
    <body>
    <h2>All Alerts</h2>
    <table border="1" cellpadding="10">
      <tr><th>User</th><th>Coin</th><th>Type</th><th>Target</th><th>Triggered?</th></tr>
    {% for alert in alerts %}
      <tr>
        <td>{{ alert[1] }}</td>
        <td>{{ alert[2].upper() }}</td>
        <td>{{ alert[3] }}</td>
        <td>{{ alert[4] or alert[5] ~ "-" ~ alert[6] or '' }}</td>
        <td>{{ 'Yes' if alert[7] else 'No' }}</td>
      </tr>
    {% endfor %}
    </table>
    <br>
    <form action="/test">
      <input type="text" name="price" placeholder="Price" />
      <input type="text" name="coin" placeholder="Coin (e.g. btc)" />
      <button type="submit">Trigger Fake Alert</button>
    </form>
    </body>
    </html>
    """
    return render_template_string(html, alerts=alerts)


@dashboard_app.route('/test')
def test_alert_route():
    price = float(request.args.get('price', 70000))
    coin = request.args.get('coin', 'bitcoin').lower()
    asyncio.run(hourly_check(app_instance, override_price=price, override_coin=coin))
    return f"<h2>Fake alert triggered for {coin.upper()} @ ${price:,.2f}</h2>"


# Main function
async def main():
    global app_instance
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_error_handler(error_handler)
    app_instance = app

    disable_polling = os.getenv("DISABLE_POLLING", "false").lower() in ["true", "1", "yes"]

    if not disable_polling:
        logging.info("Starting Telegram bot with polling...")

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("price", price))
        app.add_handler(CommandHandler("setalert", setalert))
        app.add_handler(CommandHandler("setrangalert", setrangalert))
        app.add_handler(CommandHandler("listalerts", listalerts))
        app.add_handler(CommandHandler("forcerun", forcerun))
        app.add_handler(CommandHandler("sendprices", sendprices))
        app.add_handler(CommandHandler("subscribe", subscribe))
        app.add_handler(CommandHandler("unsubscribe", unsubscribe))
        app.add_handler(CommandHandler("subscribesol", subscribesol))
        app.add_handler(CommandHandler("subscribexrp", subscribexrp))
        app.add_handler(CommandHandler("uptime", uptime))
        app.add_handler(CommandHandler("lastcheck", lastcheck))

        # Start scheduler
        scheduler = AsyncIOScheduler()
        scheduler.add_job(hourly_check, 'interval', minutes=10, args=[app])
        scheduler.add_job(send_periodic_prices, 'interval', minutes=30, args=[app])
        scheduler.start()

        print("Bot started...")
        await app.run_polling(drop_pending_updates=True)
    else:
        logging.info("Polling disabled via DISABLE_POLLING")
        app_instance = None


# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(f"Update {update} caused error {context.error}", exc_info=True)


if __name__ == "__main__":
    # Initialize SQLite DB
    init_db()

    # Start dummy HTTP server on port 8080
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is active")

        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()

        def log_message(self, format, *args):
            return  # Suppress logs

    server = HTTPServer(('0.0.0.0', 8080), Handler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    # Start dashboard in separate thread
    if os.getenv("DISABLE_POLLING") != "true":
        dashboard_thread = threading.Thread(target=lambda: dashboard_app.run(port=5001))
        dashboard_thread.daemon = True
        dashboard_thread.start()

    # Run the bot
    nest_asyncio.apply()
    asyncio.run(main())