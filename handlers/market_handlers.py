
import logging
from telegram.ext import ContextTypes
from telegram import Update


async def listcoinstop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /listcoinstop <limit> (e.g., /listcoinstop 10)")
        return

    try:
        limit = int(context.args[0])
        if limit not in [5, 10, 20, 30]:
            await update.message.reply_text("Limit must be one of: 5, 10, 20, 30")
            return
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return

    from services.coin_list_service import get_top_coins, format_coin_data
    raw_data = get_top_coins(limit)

    if not raw_data:
        await update.message.reply_text("Failed to fetch top coins. Try again later.")
        return

    # Create headers
    markdown_msg = f"📈 *Top {limit} Cryptocurrencies*\n\n"
    markdown_msg += "| Symbol | Price \(USD\) | 24h Change   | 7D Range          |\n"
    markdown_msg += "|--------|---------------|--------------|-------------------|\n"
    
    plain_msg = f"📈 Top {limit} Cryptocurrencies\n\n"
    plain_msg += "| Symbol | Price (USD)   | 24h Change   | 7D Range          |\n"
    plain_msg += "|--------|---------------|--------------|-------------------|\n"

    # Add coin rows
    for coin in raw_data:
        formatted = format_coin_data(coin)
        markdown_msg += formatted["markdown_row"] + "\n"
        plain_msg += formatted["plain_row"] + "\n"

    try:
        await update.message.reply_markdown_v2(markdown_msg)
    except Exception as e:
        logging.error(f"MarkdownV2 failed: {e}")
        await update.message.reply_text(f"```\n{plain_msg}\n```", parse_mode="Markdown")

async def listcoinsgain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.coin_list_service import get_top_gainers, format_coin_data
    
    raw_data = get_top_gainers(10)
    if not raw_data:
        await update.message.reply_text("Failed to fetch gainers. Try again later.")
        return

    # Create headers
    markdown_msg = "📈 *Top 10 Gainers \(24h\)*\n\n"
    markdown_msg += "| Symbol | Price \(USD\) | 24h Change   | 7D Range          |\n"
    markdown_msg += "|--------|---------------|--------------|-------------------|\n"
    
    plain_msg = "📈 Top 10 Gainers (24h)\n\n"
    plain_msg += "| Symbol | Price (USD)   | 24h Change   | 7D Range          |\n"
    plain_msg += "|--------|---------------|--------------|-------------------|\n"

    # Add coin rows
    for coin in raw_data:
        formatted = format_coin_data(coin)
        markdown_msg += formatted["markdown_row"] + "\n"
        plain_msg += formatted["plain_row"] + "\n"

    try:
        await update.message.reply_markdown_v2(markdown_msg)
    except Exception as e:
        logging.error(f"MarkdownV2 failed: {e}")
        await update.message.reply_text(f"```\n{plain_msg}\n```", parse_mode="Markdown")

async def listcoinsloss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from services.coin_list_service import get_top_losers, format_coin_data
    
    raw_data = get_top_losers(10)
    if not raw_data:
        await update.message.reply_text("Failed to fetch losers. Try again later.")
        return

    # Create headers
    markdown_msg = "📉 *Top 10 Losers \(24h\)*\n\n"
    markdown_msg += "| Symbol | Price \(USD\) | 24h Change   | 7D Range          |\n"
    markdown_msg += "|--------|---------------|--------------|-------------------|\n"
    
    plain_msg = "📉 Top 10 Losers (24h)\n\n"
    plain_msg += "| Symbol | Price (USD)   | 24h Change   | 7D Range          |\n"
    plain_msg += "|--------|---------------|--------------|-------------------|\n"

    # Add coin rows
    for coin in raw_data:
        formatted = format_coin_data(coin)
        markdown_msg += formatted["markdown_row"] + "\n"
        plain_msg += formatted["plain_row"] + "\n"

    try:
        await update.message.reply_markdown_v2(markdown_msg)
    except Exception as e:
        logging.error(f"MarkdownV2 failed: {e}")
        await update.message.reply_text(f"```\n{plain_msg}\n```", parse_mode="Markdown")

