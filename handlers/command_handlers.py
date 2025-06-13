# handlers/command_handlers.py

from telegram._update import Update
from telegram.ext import ContextTypes
import sqlite3  # Required for subscriptions
from config import COIN_MAP 
from services.crypto_service import get_crypto_price
from database.database import load_alerts
from utils.time_utils import format_time_ago
from utils.forcenow import forcenow
from config import last_known_prices


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Price Pilot Bot!\n\n"
                                    "Use /price <coin> to get current crypto price.\n"
                                    "Examples:\n"
                                    "  /price btc\n"
                                    "  /setalert eth 3500\n"
                                    "  /setrangalert sol 140 160\n\n"
                                    "Want regular updates?\n"
                                    "  /subscribe - BTC/ETH/SOL/XRP every 30 mins")


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
    cur.execute("DELETE FROM sol_subscribers WHERE user_id = ?", (user_id,))
    cur.execute("DELETE FROM xrp_subscribers WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text("❌ Unsubscribed from price updates")


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

    from handlers.job_handlers import hourly_check
    await hourly_check(context.application, override_price=fake_price, override_coin=COIN_MAP[coin_arg])
    await update.message.reply_text(f"Manual check done for {coin_arg.upper()} @ ${fake_price:,.2f}")


async def sendprices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.job_handlers import send_periodic_prices
    await send_periodic_prices(context.application.bot._application)
    await update.message.reply_text("✅ Sent market update to all subscribers!")


def register_commands(app):
    from telegram.ext import CommandHandler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("listalerts", listalerts))
    app.add_handler(CommandHandler("forcerun", forcerun))
    app.add_handler(CommandHandler("sendprices", sendprices))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("forcenow", forcenow))