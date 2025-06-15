from telegram._update import Update
from telegram.ext import ContextTypes
import sqlite3
from collections import defaultdict
from config import COIN_MAP
from services.crypto_service import get_crypto_price
from database.database import save_portfolio_data, load_portfolio




async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /portfolio <coin> <amount> [bought_at]\n"
            "Example:\n"
            "  /portfolio sol 100 140   → Adds 100 SOL bought at $140\n"
            "  /portfolio eth 2.5       → Uses current ETH price as default bought_at"
        )
        return

    coin_arg = context.args[0].lower()
    if coin_arg not in COIN_MAP:
        await update.message.reply_text(f"Unsupported coin: {coin_arg}. Supported: btc, eth, sol, xrp")
        return

    try:
        amount = float(context.args[1])
        bought_at = float(context.args[2]) if len(context.args) == 3 else None
    except ValueError:
        await update.message.reply_text("Please enter valid numbers for amount and bought_at.")
        return

    from database.database import save_portfolio_data
    coin_id = COIN_MAP[coin_arg]
    save_portfolio_data(user_id, coin_id, amount, bought_at)

    msg = f"✅ Added {amount} {coin_arg.upper()} to your portfolio."
    if bought_at:
        msg += f" Bought at ${bought_at:,.2f}"
    else:
        from services.crypto_service import get_crypto_price
        current_price = get_crypto_price(coin_id, coin_arg.upper())
        if current_price:
            msg += f" (Current Price: ${current_price:,.2f})"
    await update.message.reply_text(msg)


async def viewportfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    from database.database import load_portfolio
    portfolio_items = load_portfolio(user_id)

    if not portfolio_items:
        await update.message.reply_text("Your portfolio is empty. Use `/buy <coin> <amount>` to add coins.")
        return

    from collections import defaultdict
    from services.crypto_service import get_crypto_price
    from config import COIN_MAP

    # Group by coin_id
    grouped = defaultdict(lambda: {"total_amount": 0, "avg_cost": 0})
    total_value = 0

    for item in portfolio_items:
        coin_id, amount, bought_at = item
        symbol = next(k for k, v in COIN_MAP.items() if v == coin_id).upper()
        current_price = get_crypto_price(coin_id, symbol)

        if current_price is None:
            await update.message.reply_text(f"Failed to fetch current price for {symbol}. Try again later.")
            return

        # Grouped stats
        grouped[coin_id]["total_amount"] += amount
        grouped[coin_id]["avg_cost"] = (
            grouped[coin_id]["avg_cost"] * (grouped[coin_id]["total_amount"] - amount) + bought_at * amount
        ) / grouped[coin_id]["total_amount"]
        total_value += amount * current_price

    msg = "💼 Your Crypto Portfolio\n\n"

    for coin_id, data in grouped.items():
        symbol = next(k for k, v in COIN_MAP.items() if v == coin_id).upper()
        amount = data["total_amount"]
        avg_cost = data["avg_cost"]
        current_price = get_crypto_price(coin_id, symbol)
        value = amount * current_price

        gain_loss_msg = ""
        profit = value - (avg_cost * amount)
        if avg_cost != 0:
            change_percent = (profit / (avg_cost * amount)) * 100
            arrow = "🟢" if change_percent >= 0 else "🔴"
            sign = "+" if change_percent >= 0 else "-"
            gain_loss_msg = f"{arrow} {sign}{abs(change_percent):.2f}% ({'Profit' if profit > 0 else 'Loss'}: ${abs(profit):,.2f})"

        msg += f"{symbol}: {amount:.2f}\n"
        msg += f"Price: ${current_price:,.2f} | Value: ${value:,.2f}\n"
        if avg_cost != 0:
            msg += f"Gain/Loss: {gain_loss_msg}\n"
        msg += "\n"

    msg += f"💰 Total Portfolio Value: ${total_value:,.2f}"

    await update.message.reply_text(msg)

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /buy <coin> <amount> [bought_at]\n"
            "Example:\n"
            "  /buy sol 100 140   → Adds 100 SOL bought at $140\n"
            "  /buy eth 2.5       → Uses current ETH price as default bought_at"
        )
        return

    coin_arg = context.args[0].lower()
    if coin_arg not in COIN_MAP:
        await update.message.reply_text(f"Unsupported coin: {coin_arg}. Supported: btc, eth, sol, xrp")
        return

    try:
        amount = float(context.args[1])
        bought_at = float(context.args[2]) if len(context.args) == 3 else None
    except ValueError:
        await update.message.reply_text("Please enter valid numbers for amount and bought_at.")
        return

    from database.database import save_portfolio_data
    coin_id = COIN_MAP[coin_arg]
    save_portfolio_data(user_id, coin_id, amount, bought_at)

    msg = f"✅ Added {amount} {coin_arg.upper()} to your portfolio."
    if bought_at:
        msg += f" Bought at ${bought_at:,.2f}"
    else:
        from services.crypto_service import get_crypto_price
        current_price = get_crypto_price(coin_id, coin_arg.upper())
        if current_price:
            msg += f" (Current Price: ${current_price:,.2f})"
    await update.message.reply_text(msg)

async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /sell <coin> <amount>\n"
            "Example:\n"
            "  /sell sol 100   → Sells 100 SOL from your portfolio"
        )
        return

    coin_arg = context.args[0].lower()
    if coin_arg not in COIN_MAP:
        await update.message.reply_text(f"Unsupported coin: {coin_arg}. Supported: btc, eth, sol, xrp")
        return

    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Please enter a valid number for amount.")
        return

    from database.database import load_portfolio, update_portfolio
    coin_id = COIN_MAP[coin_arg]

    # Load current portfolio
    portfolio_items = load_portfolio(user_id)

    # Find matching coin entries
    total_amount = 0
    total_cost = 0
    for item in portfolio_items:
        if item[0] == coin_id:
            total_amount += item[1]
            total_cost += item[1] * item[2]

    if total_amount < amount:
        await update.message.reply_text(f"You don't have enough {coin_arg.upper()} in your portfolio.")
        return

    # Update portfolio
    update_portfolio(user_id, coin_id, -amount)

    # Calculate sold value
    avg_cost = total_cost / total_amount
    sold_value = amount * avg_cost

    await update.message.reply_text(
        f"✅ Sold {amount} {coin_arg.upper()}.\n"
        f"Sold at average cost: ${avg_cost:,.2f}\n"
        f"Total sold value: ${sold_value:,.2f}"
    )


