from flask import Flask, render_template_string, request
import sqlite3
import asyncio
from handlers.job_handlers import hourly_check
from main import app_instance

dashboard_app = Flask(__name__)

@dashboard_app.route('/')
def dashboard():
    conn = sqlite3.connect("alerts.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM alerts")
    alerts = cur.fetchall()
    conn.close()

    html = """
    <html>
    <body>
    <h2>All Alerts</h2>
    <table border="1" cellpadding="10">
      <tr><th>User</th><th>Coin</th><th>Type</th><th>Target</th><th>Triggered?</th></tr>
    {% for alert in alerts %}
      <tr>
        <td>{{ alert[1] }}</td>
        <td>{{ alert[2].upper() }}</td>
        <td>{{ alert[3] }}</td>
        <td>{{ alert[4] or alert[5] ~ "-" ~ alert[6] or '' }}</td>
        <td>{{ 'Yes' if alert[7] else 'No' }}</td>
      </tr>
    {% endfor %}
    </table>
    <br>
    <form action="/test">
      <input type="text" name="price" placeholder="Price" />
      <input type="text" name="coin" placeholder="Coin (e.g. btc)" />
      <button type="submit">Trigger Fake Alert</button>
    </form>
    </body>
    </html>
    """
    return render_template_string(html, alerts=alerts)


@dashboard_app.route('/test')
def test_alert_route():
    price = float(request.args.get('price', 70000))
    coin = request.args.get('coin', 'bitcoin').lower()
    asyncio.run(hourly_check(app_instance, override_price=price, override_coin=coin))
    return f"<h2>Fake alert triggered for {coin.upper()} @ ${price:,.2f}</h2>"