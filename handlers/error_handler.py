# handlers/error_handler.py

import logging
from telegram._update import Update
from telegram.ext import ContextTypes

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a Telegram message to notify the developer."""
    logging.error(f"Update {update} caused error {context.error}", exc_info=True)