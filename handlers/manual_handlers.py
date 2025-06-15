


import sqlite3
from telegram.ext import ContextTypes
from telegram import Update

from config import COIN_MAP


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


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /history <coin> (e.g., /history btc)")
        return

    coin_arg = context.args[0].lower()
    from config import COIN_MAP

    if coin_arg == "all":
        msg = "📈 Full Price History\n\n"
        from config import COIN_MAP
        from utils.price_utils import price_history
        for coin_id in COIN_MAP.values():
            if coin_id in price_history and price_history[coin_id]:
                last_price, ts = price_history[coin_id][-1]
                msg += f"{coin_id.capitalize()}: ${last_price:,.2f} (Last updated: {ts})\n"
        await update.message.reply_text(msg)
        return

    if coin_arg not in COIN_MAP:
        await update.message.reply_text(f"Unsupported coin: {coin_arg}. Supported: btc, eth, sol, xrp, all")
        return

    coin_id = COIN_MAP[coin_arg]
    from utils.price_utils import price_history

    if coin_id not in price_history or not price_history[coin_id]:
        await update.message.reply_text(f"No history available for {coin_id.capitalize()}")
        return

    msg = f"📈 {coin_id.capitalize()} Price History:\n\n"
    for price, ts in reversed(price_history[coin_id][-5:]):  # Last 5 entries
        msg += f"{ts} → ${price:,.2f}\n"

    await update.message.reply_text(msg)

