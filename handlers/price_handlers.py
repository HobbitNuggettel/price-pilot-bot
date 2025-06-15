
from telegram._update import Update
from telegram.ext import ContextTypes
from services.crypto_service import get_crypto_price
from config import COIN_MAP, last_known_prices
from utils.time_utils import format_time_ago




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


async def price_coin(update: Update, context: ContextTypes.DEFAULT_TYPE, coin_arg: str):
    from config import COIN_MAP
    from services.crypto_service import get_crypto_price
    from utils.time_utils import format_time_ago
    from config import last_known_prices

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

async def price_btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await price_coin(update, context, "btc")

async def price_eth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await price_coin(update, context, "eth")

async def price_sol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await price_coin(update, context, "sol")

async def price_xrp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await price_coin(update, context, "xrp")

async def price_usdt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await price_coin(update, context, "usdt")

