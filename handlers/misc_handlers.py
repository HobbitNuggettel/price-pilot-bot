# handlers/misc_handlers.py

from telegram._update import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to Price Pilot Bot!\n\n"
                                    "Use /price <coin> to get current crypto price.\n"
                                    "Examples:\n"
                                    "  /price btc\n"
                                    "  /setalert eth 3500\n"
                                    "  /setrangalert sol 140 160\n\n"
                                    "Want regular updates?\n"
                                    "  /subscribe - BTC/ETH/SOL/XRP every 30 mins")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "*Available Commands*\n\n"
    msg += "/start - Start the bot\n"
    msg += "/price <coin> - Get current price\n"
    msg += "/setalert <coin> <price> - Set price alert\n"
    msg += "/setrangalert <coin> <low> <high> - Set range alert\n"
    msg += "/listalerts - View active alerts\n"
    msg += "/forcerun <coin> <price> - Manual check\n"
    msg += "/sendprices - Send market update to subscribers\n"
    msg += "/subscribe - Get price updates\n"
    msg += "/history <coin> - Price history\n"
    msg += "/viewportfolio - View your holdings\n"
    msg += "/graph <coin> - Show price chart\n"
    msg += "/news [coin] - Latest crypto news\n"
    msg += "/buy <coin> <amount> [price] - Add to portfolio\n"
    msg += "/sell <coin> <amount> - Remove from portfolio"

    await update.message.reply_text(msg, parse_mode="MarkdownV2")