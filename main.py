import logging
import os
import time
import asyncio
import nest_asyncio
from datetime import datetime
import signal

from telegram._update import Update
from telegram.ext import ContextTypes, ApplicationBuilder
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# Load config
from config import TELEGRAM_BOT_TOKEN, COIN_MAP, HEADERS, last_known_prices

# Load handlers
from handlers.alert_handlers import register_alert_handlers
from handlers.command_handlers import register_commands
from handlers.job_handlers import hourly_check, send_periodic_prices
from handlers.error_handler import error_handler  # ✅ Now properly imported

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Global app reference
app_instance = None


async def main():
    global app_instance

    # Initialize bot
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_error_handler(error_handler)  # ✅ Now works!
    app_instance = app

    # Register all command handlers
    register_commands(app)
    register_alert_handlers(app)

    # Start scheduler inside async context
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(hourly_check, 'interval', minutes=10, args=[app])
    scheduler.add_job(send_periodic_prices, 'interval', minutes=30, args=[app])
    scheduler.start()

    print("Bot started...")

    # Run the bot
    await app.run_polling(drop_pending_updates=True,poll_interval=30)


if __name__ == "__main__":
    # Initialize SQLite DB
    from database.database import init_db
    init_db()

    # Start dummy HTTP server (for Render.com)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is active")

        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()

        def log_message(self, format, *args):
            return  # Suppress logs

    server = HTTPServer(('0.0.0.0', 8080), Handler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    # Start dashboard in separate thread
    try:
        from dashboard.app import dashboard_app
        dashboard_thread = threading.Thread(target=lambda: dashboard_app.run(port=5001))
        dashboard_thread.daemon = True
        dashboard_thread.start()
    except Exception as e:
        logging.warning(f"Dashboard failed to start: {e}")

    # Apply macOS async fix
    nest_asyncio.apply()

 # Graceful shutdown handler
    def handle_exit():
        print("Shutting down gracefully...")
        server.shutdown()
        exit(0)

    # Set up Ctrl+C handling
    loop = asyncio.get_event_loop()
    for sig in [signal.SIGINT, signal.SIGTERM]:
        loop.add_signal_handler(sig, handle_exit)

    try:
        asyncio.run(main())  # Runs the bot
    except KeyboardInterrupt:
        handle_exit()