# handlers/alert_handlers.py

from io import BytesIO
from telegram._update import Update
from telegram.ext import ContextTypes
from services.crypto_service import get_crypto_price
from database.database import load_alerts, save_alert
from config import COIN_MAP
import sqlite3


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

def register_alert_handlers(app):
    from telegram.ext import CommandHandler
    app.add_handler(CommandHandler("setalert", setalert))

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

async def export_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    from database.database import load_alerts
    alerts = load_alerts().get(user_id, [])
    
    if not alerts:
        await update.message.reply_text("No alerts to export.")
        return

    csv_lines = ["Coin,Alert Type,Target,Triggered"]
    for alert in alerts:
        if "price" in alert:
            csv_lines.append(f"{alert['coin_id']},Price Alert,{alert['price']},{alert['triggered']}")
        elif "low" in alert and "high" in alert:
            csv_lines.append(f"{alert['coin_id']},Range Alert,{alert['low']} - {alert['high']},{alert['triggered']}")

    csv_content = "\n".join(csv_lines)
    bio = BytesIO(csv_content.encode())
    bio.name = f"{user_id}_alerts.csv"

    await update.message.reply_document(document=bio, filename=bio.name, caption="📊 Your alerts exported as CSV")


async def setchangealert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /setchangealert <coin> <percent>")
        return

    coin_arg = context.args[0].lower()
    percent_str = context.args[1]

    if coin_arg not in COIN_MAP:
        await update.message.reply_text(f"Unsupported coin: {coin_arg}. Supported: btc, eth, sol, xrp")
        return

    try:
        target_percent = float(percent_str.strip("%"))
    except ValueError:
        await update.message.reply_text("Please enter a valid percentage.")
        return

    coin_id = COIN_MAP[coin_arg]
    user_id = str(update.effective_user.id)

    from database.database import save_change_alert
    save_change_alert(user_id, coin_id, target_percent)
    await update.message.reply_text(f"🔔 Set alert for {coin_id.capitalize()} if price changes by ≥{target_percent:.2f}% in 24h")




async def setvolumealert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /setvolumealert <coin> <percent>")
        return

    coin_arg = context.args[0].lower()
    percent_str = context.args[1]

    if coin_arg not in COIN_MAP:
        await update.message.reply_text(f"Unsupported coin: {coin_arg}. Supported: btc, eth, sol, xrp")
        return

    try:
        volume_percent = float(percent_str.strip("%"))
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return

    coin_id = COIN_MAP[coin_arg]
    user_id = str(update.effective_user.id)

    from database.database import save_volume_alert
    save_volume_alert(user_id, coin_id, volume_percent)
    await update.message.reply_text(f"📈 Set alert for {coin_id.capitalize()} if trading volume increases by ≥{volume_percent:.2f}% in 24h")



async def listalerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    alerts = load_alerts().get(user_id, [])

    if not alerts:
        await update.message.reply_text("You have no active alerts.")
        return

    msg = "Your active alerts:\n"
    for i, alert in enumerate(alerts):
        coin_name = alert.get("coin_id", "unknown").capitalize()
        if "price" in alert:
            msg += f"{i+1}. {coin_name} Target: ${alert['price']:,.2f}\n"
        elif "low" in alert and "high" in alert:
            msg += f"{i+1}. {coin_name} Range: ${alert['low']:,.2f} - ${alert['high']:,.2f}\n"

    await update.message.reply_text(msg)


