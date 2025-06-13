# utils/forcenow.py

from telegram._update import Update
from telegram.ext import ContextTypes
from services.crypto_service import get_crypto_price
from handlers.job_handlers import send_periodic_prices


async def forcenow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from config import COIN_MAP
    from handlers.job_handlers import send_periodic_prices

    # Get latest prices
    prices = {}
    for symbol, coin_id in COIN_MAP.items():
        price = get_crypto_price(coin_id, symbol.upper())
        if price is not None:
            prices[coin_id] = price

    if not prices:
        await update.message.reply_text("❌ Failed to fetch prices. Try again later.")
        return

    # Build message
    msg = "📈 Real-Time Prices:\n\n"
    for coin_id, price in prices.items():
        msg += f"{coin_id.capitalize()}: ${price:,.2f}\n"

    await update.message.reply_text(msg)

    # Send to all subscribers
    from handlers.job_handlers import send_periodic_prices
    await send_periodic_prices(context.application)
    await update.message.reply_text("✅ Sent real-time prices to all subscribers!")