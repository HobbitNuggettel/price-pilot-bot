# services/coin_list_service.py

import re
import requests
from datetime import datetime


def escape_markdown(text):
    """Escape all MarkdownV2 reserved characters"""
    if not isinstance(text, str):
        text = str(text)
    
    reserved_chars = '_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in reserved_chars else char for char in text)


def get_top_coins(limit=10):
    url = "https://api.coingecko.com/api/v3/coins/markets" 
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": "true"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed fetching top {limit} coins: Status code {response.status_code}")
            print("Response:", response.text[:200])
            return []
    except Exception as e:
        print(f"Connection error fetching top coins: {e}")
        return []


# services/coin_list_service.py

def format_coin_data(coin_data):
    symbol = coin_data["symbol"].upper()
    price = coin_data["current_price"]
    change_24h = coin_data["price_change_percentage_24h"]
    sparkline = coin_data.get("sparkline_in_7d", {}).get("price") or []

    # Format change with color indicator
    if change_24h >= 0:
        change_str = f"🟢 +{abs(change_24h):.2f}%"
    else:
        change_str = f"🔴 -{abs(change_24h):.2f}%"

    # Format price range
    if len(sparkline) > 1:
        first_price = sparkline[0]
        last_price = sparkline[-1]
        range_str = f"{first_price:,.2f} → {last_price:,.2f}"
    else:
        range_str = "N/A"

    # Escape all fields for MarkdownV2
    symbol_escaped = escape_markdown(symbol)
    price_escaped = escape_markdown(f"{price:,.2f}")
    range_escaped = escape_markdown(range_str)
    change_escaped = escape_markdown(change_str)

    return {
        "markdown_row": f" | {symbol_escaped} | ${price_escaped} | {change_escaped} | {range_escaped} |",
        "plain_row": f" | {symbol:<6} | ${price:>11,.2f} | {change_str:<12} | {range_str:<20} |",
        "change_24h": change_24h
    }


def get_top_gainers(limit=10):
    raw = get_top_coins(limit * 2)
    if not raw:
        return []
    sorted_data = sorted(raw, key=lambda x: x["price_change_percentage_24h"], reverse=True)
    return sorted_data[:limit]


def get_top_losers(limit=10):
    raw = get_top_coins(limit * 2)
    if not raw:
        return []
    sorted_data = sorted(raw, key=lambda x: x["price_change_percentage_24h"])
    return sorted_data[:limit]