# handlers/job_handlers.py

import logging
import sqlite3
from datetime import datetime
import time
from telegram.ext import Application
from services.crypto_service import get_crypto_price
from utils.time_utils import format_time_ago
from database.database import load_alerts
from config import COIN_MAP

from utils.price_utils import price_history, MAX_HISTORY_ITEMS, last_known_prices

async def hourly_check(app: Application, override_price=None, override_coin="bitcoin"):

    global last_check_time
    logging.info("Running scheduled price check...")

    alerts = load_alerts()
    triggered = []

    for user_id, targets in alerts.items():
        for alert in targets:
            coin_id = alert.get("coin_id", "bitcoin")
            symbol = next(k for k, v in COIN_MAP.items() if v == coin_id).upper()

            current_price = get_crypto_price(coin_id, symbol,force_price=override_price)

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
        else:
            msg = f"🔔 {coin_name} is in your target range: ${alert['low']:,.2f} - ${alert['high']:,.2f}"

        try: 
           await app.bot.send_message(chat_id=user_id, text=msg)
        except Exception as e:
            logging.error(f"Failed to send to {user_id}: {e}")

    last_check_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())


async def send_periodic_prices(app: Application):
    logging.info("Sending 30-min BTC/ETH/SOL/XRP price update...")

    from config import COIN_MAP
    from services.crypto_service import get_crypto_price

    prices = {}
    for symbol, coin_id in COIN_MAP.items():
        price = get_crypto_price(coin_id, symbol)
        if price:
            prices[coin_id] = price

    if not prices:
        logging.warning("Failed to fetch one or more prices. Skipping periodic update.")
        return

    # Get all subscribers
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers")
    subscriber_rows = cur.fetchall()
    conn.close()

    # Build message
    msg = "📊 30-Minute Market Update\n\n"
    msg += f"₿ Bitcoin (BTC): ${prices['bitcoin']:,.2f}\n"
    msg += f"🔷 Ethereum (ETH): ${prices['ethereum']:,.2f}\n"
    msg += f"🟣 Solana (SOL): ${prices['solana']:,.2f}\n"
    msg += f"🔵 XRP (XRP): ${prices['xrp']:,.2f}"

    # Send to all subscribers
    for row in subscriber_rows:
        user_id = row[0]
        try:
            await app.bot.send_message(chat_id=user_id, text=msg)
            logging.info(f"Sent market update to {user_id}")
        except Exception as e:
            logging.error(f"Failed to send to {user_id}: {e}")