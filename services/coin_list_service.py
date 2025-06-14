# services/coin_list_service.py

import requests
from datetime import datetime, timedelta

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
    except Exception as e:
        print(f"Error fetching top {limit} coins: {e}")
        return []

def format_coin_data(coin_data):
    name = coin_data["name"]
    symbol = coin_data["symbol"].upper()
    price = coin_data["current_price"]
    change_24h = coin_data["price_change_percentage_24h"]
    sparkline = coin_data.get("sparkline_in_7d", {}).get("price") or []
    
    arrow = "🟢" if change_24h >= 0 else "🔴"
    sign = "+" if change_24h >= 0 else "-"
    
    # Get first and last sparkline value (last 7 days)
    if len(sparkline) > 1:
        first_price = sparkline[0]
        last_price = sparkline[-1]
        historical_msg = f" | 7D: ${first_price:,.2f} → ${last_price:,.2f}"
    else:
        historical_msg = ""

    return {
        "id": coin_data["id"],
        "name": name,
        "symbol": symbol,
        "price": price,
        "change_24h": change_24h,
        "change_str": f"{sign}{abs(change_24h):.2f}%",
        "full_str": f"{arrow} {name} ({symbol}) → ${price:,.2f} | 24h: {sign}{abs(change_24h):.2f}%{historical_msg}"
    }

def get_top_gainers(limit=10):
    return sorted(get_top_coins(limit*2), key=lambda x: x["price_change_percentage_24h"], reverse=True)[:limit]


def get_top_losers(limit=10):
    return sorted(get_top_coins(limit*2), key=lambda x: x["price_change_percentage_24h"])[:limit]