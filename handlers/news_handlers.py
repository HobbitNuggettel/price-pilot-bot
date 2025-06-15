import logging
from telegram._update import Update
from telegram.ext import ContextTypes
from services.news_service import get_crypto_news




async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) > 1:
        await update.message.reply_text("Usage: /news [coin]")
        return

    coin_arg = context.args[0].lower() if context.args else None
    from config import COIN_MAP
    coin_id = COIN_MAP.get(coin_arg, coin_arg) if coin_arg else None

    from services.news_service import get_crypto_news
    news_data = get_crypto_news(coin_id)

    if not news_data:
        await update.message.reply_text("📰 No recent crypto news found at the moment.")
        return

    msg = f"📰 Top 3 Crypto News{' for ' + coin_arg.upper() if coin_arg else ''}\n\n"

    for item in news_data:
        title = item.get("title", "Untitled Article")
        summary = item.get("summary", "")
        url = item.get("url", "#")

        msg += f"🔹 *{title}*\n"
        if summary:
            msg += f"{summary[:150]}...\n"
        msg += f"[Read more]({url})\n\n"

    try:
        await update.message.reply_markdown_v2(msg)
    except Exception as e:
        logging.error(f"MarkdownV2 failed: {e}")
        plain_msg = ""
        for item in news_data:
            plain_msg += f"- {item['title']}\n  → {item.get('summary', '')[:100]}...\n\n"
        await update.message.reply_text(plain_msg or "No news found.")

# handlers/command_handlers.py

async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) > 1:
        await update.message.reply_text("Usage: /news [coin]")
        return

    coin_arg = context.args[0].lower() if context.args else None
    from config import COIN_MAP
    coin_id = COIN_MAP.get(coin_arg, coin_arg) if coin_arg else None

    from services.news_service import get_crypto_news
    news_data = get_crypto_news(coin_id)

    if not news_data:
        await update.message.reply_text("📰 No recent crypto news found at the moment.")
        return

    msg = f"📰 *Top 3 Crypto News{' for ' + coin_arg.upper() if coin_arg else ''}*\n\n"

    for i, item in enumerate(news_data):
        title = item.get("title", "Untitled Article")
        summary = item.get("summary", "")
        url = item.get("url", "#")

        # Proper Markdown escaping
        title_escaped = title.replace("-", "\\-").replace(".", "\\.").replace("(", "\\(")
        summary_escaped = summary.replace("-", "\\-").replace(".", "\\.").replace("(", "\\(")
        
        msg += f"*{i+1}\\. {title_escaped}*\n"
        if summary:
            msg += f"_{summary_escaped}_\n"
        msg += f"[Read more ↗]({url})\n\n"

    try:
        await update.message.reply_markdown_v2(msg, disable_web_page_preview=True)
    except Exception as e:
        logging.error(f"MarkdownV2 failed: {e}")
        plain_msg = "📰 Top 3 Crypto News:\n\n"
        for i, item in enumerate(news_data):
            plain_msg += f"{i+1}. {item['title']}\n"
            if item.get('summary'):
                plain_msg += f"   {item['summary']}\n"
            plain_msg += f"   {item['url']}\n\n"
        await update.message.reply_text(plain_msg)

