# handlers/alert_handlers.py

from telegram._update import Update
from telegram.ext import ContextTypes
from services.crypto_service import get_crypto_price
from database.database import save_alert
from config import COIN_MAP

async def setalert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /setalert <coin> <target>")
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


def register_alert_handlers(app):
    from telegram.ext import CommandHandler
    app.add_handler(CommandHandler("setalert", setalert))
    app.add_handler(CommandHandler("setrangalert", setrangalert))