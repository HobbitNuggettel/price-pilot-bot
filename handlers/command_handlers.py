# handlers/command_handlers.py

import logging
from telegram._update import Update
from telegram.ext import ContextTypes
import sqlite3  # Required for subscriptions
from config import COIN_MAP 
from handlers.alert_handlers import export_alerts, listalerts, setalert, setchangealert, setrangalert, setvolumealert
from handlers.graph_command import graph
from handlers.manual_handlers import forcerun, history, sendprices, subscribe, unsubscribe
from handlers.market_handlers import listcoinsgain, listcoinsloss, listcoinstop
from handlers.news_handlers import news
from handlers.portfolio_handlers import buy, portfolio, sell, viewportfolio
from handlers.price_handlers import price, price_btc, price_eth, price_sol, price_usdt, price_xrp
from utils.forcenow import forcenow
from config import last_known_prices
from utils.price_utils import price_history, MAX_HISTORY_ITEMS
from handlers.misc_handlers import start, help_command



def register_commands(app):
    from telegram.ext import CommandHandler

     # Misc

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Price commands

    app.add_handler(CommandHandler("price", price))
     # Single-command price shortcuts
    app.add_handler(CommandHandler("pricebtc", price_btc))
    app.add_handler(CommandHandler("priceeth", price_eth))
    app.add_handler(CommandHandler("pricesol", price_sol))
    app.add_handler(CommandHandler("pricexrp", price_xrp))
    app.add_handler(CommandHandler("priceusdt", price_usdt))

    # Alerts

    app.add_handler(CommandHandler("listalerts", listalerts))
    app.add_handler(CommandHandler("setalert", setalert))
    app.add_handler(CommandHandler("setrangalert", setrangalert))
    app.add_handler(CommandHandler("export_alerts", export_alerts))
    app.add_handler(CommandHandler("setchangealert", setchangealert))
    app.add_handler(CommandHandler("setvolumealert", setvolumealert))


     # Admin/manual commands

    app.add_handler(CommandHandler("forcerun", forcerun))
    app.add_handler(CommandHandler("sendprices", sendprices))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("forcenow", forcenow))
    app.add_handler(CommandHandler("history", history))

     # Market updates

    app.add_handler(CommandHandler("listcoinstop", listcoinstop))
    app.add_handler(CommandHandler("listcoinsgain", listcoinsgain))
    app.add_handler(CommandHandler("listcoinsloss", listcoinsloss))

     # Graph 

    app.add_handler(CommandHandler("graph", graph))

    # News

    app.add_handler(CommandHandler("news", news))

     # Portfolio

    app.add_handler(CommandHandler("portfolio", portfolio))
    app.add_handler(CommandHandler("viewportfolio", viewportfolio))
    app.add_handler(CommandHandler("sell", sell))
    app.add_handler(CommandHandler("buy", buy))
