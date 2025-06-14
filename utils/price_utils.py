# utils/price_utils.py

from config import COIN_MAP
from datetime import datetime, timedelta
import time
import logging

# Global cached prices dictionary
last_known_prices = {}  # {"bitcoin": (price, timestamp)}
price_history = {coin_id: [] for coin_id in COIN_MAP.values()}
MAX_HISTORY_ITEMS = 20