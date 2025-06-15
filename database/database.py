import sqlite3

def init_db():
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            coin_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            target_price REAL,
            low REAL,
            high REAL,
            triggered BOOLEAN DEFAULT 0
        )
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS subscribers (user_id TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS sol_subscribers (user_id TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS xrp_subscribers (user_id TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()


def load_alerts(include_triggered=False):
    query = "SELECT * FROM alerts WHERE triggered = 0"
    if include_triggered:
        query = "SELECT * FROM alerts"

    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()

    alerts = {}
    for row in rows:
        alert_id = row[0]
        user_id = row[1]
        coin_id = row[2]
        alert_type = row[3]

        if user_id not in alerts:
            alerts[user_id] = []

        if alert_type == "price":
            price = row[4]
            alerts[user_id].append({
                "id": alert_id,
                "coin_id": coin_id,
                "price": price,
                "triggered": bool(row[7])
            })
        elif alert_type == "range":
            low, high = row[5], row[6]
            alerts[user_id].append({
                "id": alert_id,
                "coin_id": coin_id,
                "low": low,
                "high": high,
                "triggered": bool(row[7])
            })

    conn.close()
    return alerts


def save_alert(user_id, coin_id, alert_type, price=None, low=None, high=None):
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    if alert_type == "price":
        cur.execute("INSERT INTO alerts (user_id, coin_id, alert_type, target_price) VALUES (?, ?, ?, ?)",
                    (user_id, coin_id, alert_type, price))
    elif alert_type == "range":
        cur.execute("INSERT INTO alerts (user_id, coin_id, alert_type, low, high) VALUES (?, ?, ?, ?, ?)",
                    (user_id, coin_id, alert_type, low, high))
    conn.commit()
    conn.close()

def save_change_alert(user_id, coin_id, change_percent):
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO alerts (user_id, coin_id, alert_type, target_price)
        VALUES (?, ?, "change", ?)
    """, (user_id, coin_id, change_percent))
    conn.commit()
    conn.close()

def save_volume_alert(user_id, coin_id, volume_percent):
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO alerts (user_id, coin_id, alert_type, target_price)
        VALUES (?, ?, "volume", ?)
    """, (user_id, coin_id, volume_percent))
    conn.commit()
    conn.close()    

# database/database.py


def init_db():
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    
    # Existing tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            coin_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            target_price REAL,
            low REAL,
            high REAL,
            triggered BOOLEAN DEFAULT 0
        )
    """)
    
    cur.execute("CREATE TABLE IF NOT EXISTS subscribers (user_id TEXT PRIMARY KEY)")
    
    # Portfolio table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            coin_id TEXT NOT NULL,
            amount REAL NOT NULL,
            bought_at REAL NOT NULL,
            FOREIGN KEY(coin_id) REFERENCES alerts(coin_id)
        )
    """)

    conn.commit()
    conn.close()


def save_portfolio_data(user_id, coin_id, amount, bought_at=None):
    if bought_at is None:
        from services.crypto_service import get_crypto_price
        current_price = get_crypto_price(coin_id, coin_id.upper())
        if current_price is None:
            raise ValueError(f"Failed to fetch current price for {coin_id}")
        bought_at = current_price

    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO portfolio (user_id, coin_id, amount, bought_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, coin_id, amount, bought_at))
    conn.commit()
    conn.close()


def load_portfolio(user_id):
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute("SELECT coin_id, amount, bought_at FROM portfolio WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows    