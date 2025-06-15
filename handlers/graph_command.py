# handlers/graph_command.py
import matplotlib.pyplot as plt
from io import BytesIO
from telegram import Update
from telegram.ext import ContextTypes
from utils.price_utils import price_history

async def graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /graph <coin> (e.g., /graph eth)")
        return

    coin_arg = context.args[0].lower()
    from config import COIN_MAP
    if coin_arg not in COIN_MAP:
        await update.message.reply_text(f"Unsupported coin: {coin_arg}")
        return

    coin_id = COIN_MAP[coin_arg]
    history_data = price_history.get(coin_id, [])

    if not history_data:
        await update.message.reply_text(f"No historical data for {coin_id.capitalize()}")
        return

    prices = [p for p, _ in history_data]
    timestamps = [t for _, t in history_data]

    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, prices, marker='o', linestyle='-', label=coin_id.capitalize())
    plt.title(f"{coin_id.capitalize()} Price Over Time")
    plt.xlabel("Time")
    plt.ylabel("Price (USD)")
    plt.xticks(rotation=45)
    plt.tight_layout()

    bio = BytesIO()
    plt.savefig(bio, format="png")
    bio.seek(0)
    plt.close()

    await update.message.reply_photo(photo=bio, caption=f"📈 {coin_id.capitalize()} Price Graph")