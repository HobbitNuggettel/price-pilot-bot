# services/crypto_service.py

import logging
import os
import time
import requests
from config import COIN_MAP, HEADERS, COINMARKETCAP_API_KEY
from datetime import datetime, timedelta
from utils.time_utils import format_time_ago
from utils.price_utils import last_known_prices, price_history, MAX_HISTORY_ITEMS

def get_crypto_price(coin_id, symbol, force_price=None):
    global last_known_prices, price_history

    if force_price is not None:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        last_known_prices[coin_id] = (force_price, timestamp)

        if coin_id not in price_history:
            price_history[coin_id] = []
        price_history[coin_id].append((force_price, timestamp))
        if len(price_history[coin_id]) > MAX_HISTORY_ITEMS:
            price_history[coin_id].pop(0)

        return force_price

    coin_name = coin_id.capitalize()
    symbol_upper = symbol.upper()

    # Try CoinGecko → CoinPaprika
    apis = [
        {
            "name": "CoinGecko",
            "url": f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        },
        {
            "name": "CoinPaprika",
            "url": f"https://api.coinpaprika.com/v1/tickers/{symbol.lower()}-{coin_id}"
        }
    ]

    for api in apis:
        try:
            logging.info(f"Trying {api['name']} API for {symbol_upper}...")
            response = requests.get(api["url"], timeout=10, headers=HEADERS)

            if response.status_code == 200:
                data = response.json()

                if api["name"] == "CoinGecko":
                    price = data.get(coin_id, {}).get("usd")
                elif api["name"] == "CoinPaprika":
                    price = data.get("quotes", {}).get("USD", {}).get("price")

                if price:
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                    last_known_prices[coin_id] = (price, timestamp)

                    # Update history 
                    if coin_id not in price_history:
                        price_history[coin_id] = []
                    price_history[coin_id].append((price, timestamp))
                    if len(price_history[coin_id]) > MAX_HISTORY_ITEMS:
                        price_history[coin_id].pop(0)

                    return price
                else:
                    logging.warning(f"{api['name']} returned no usable price for {symbol_upper}")
        except Exception as e:
            logging.error(f"Error fetching from {api['name']} for {symbol_upper}: {str(e)}", exc_info=True)
        time.sleep(5)

    # Fallback to CoinMarketCap (requires API key)
    if COINMARKETCAP_API_KEY:
        try:
            url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest" 
            params = {"symbol": symbol_upper, "convert": "USD"}
            headers = {"X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY}

            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                    # ✅ Safe handling of CMC response (list or single object)
            usd_data = data.get("data", {}).get(symbol_upper, {})

            if isinstance(usd_data, dict):
                        # If it's a dict (e.g., USDT), extract directly
                        price = usd_data.get("quote", {}).get("USD", {}).get("price")
            elif isinstance(usd_data, list) and len(usd_data) > 0:
                        # If it's a list, use index [0]
                        price = usd_data[0].get("quote", {}).get("USD", {}).get("price")
            else:
                        price = None

            if price:
                        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                        last_known_prices[coin_id] = (price, timestamp)

                        # Add to history
                        if coin_id not in price_history:
                            price_history[coin_id] = []
                        price_history[coin_id].append((price, timestamp))
                        if len(price_history[coin_id]) > MAX_HISTORY_ITEMS:
                            price_history[coin_id].pop(0)

                        return price
            else:
                        logging.warning(f"CMC returned no usable price for {symbol_upper}")
        except Exception as e:
            logging.error(f"Error from CMC for {symbol_upper}: {e}", exc_info=True)

    # Fallback to cached price
    if coin_id in last_known_prices:
        price, timestamp = last_known_prices[coin_id]
        logging.warning(f"Returning cached {symbol_upper} price: ${price:,.2f} | Last updated: {timestamp}")
        return price
    else:
        logging.critical(f"All APIs failed and no cached price available for {symbol_upper}.")
        return None
    

def get_historical_prices(coin_id, days=7):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart" 
    params = {
        "vs_currency": "usd",
        "days": days,
        "interval": "daily"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data["prices"]
    except Exception as e:
        logging.error(f"Error fetching historical data for {coin_id}: {e}")
        return []    