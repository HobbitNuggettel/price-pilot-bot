# config.py

from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

# Telegram bot token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# CoinMarketCap API key (optional)
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")

# Supported coin mapping
COIN_MAP = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "xrp": "xrp"
}

# Headers for API requests
HEADERS = {
    "User-Agent": "PricePilotBot/1.0",
    "Accept": "application/json"
}


last_known_prices = {}