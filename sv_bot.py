import os
import json
import requests
import yfinance as yf
import schedule
import threading
import time
from datetime import datetime
from dotenv import load_dotenv
import telebot
from keep_alive import keep_alive  # For Render compatibility

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
bot = telebot.TeleBot(BOT_TOKEN)

# --- Helper Functions ---
def load_portfolio():
    try:
        with open("portfolio.json", "r") as f:
            return json.load(f)
    except:
        return {"stocks": [], "sip": []}

def save_portfolio(data):
    with open("portfolio.json", "w") as f:
        json.dump(data, f, indent=2)

ticker_map = {
    "Inox Wind": "INOXWIND.NS", "Suzlon Energy": "SUZLON.NS", "Ganga Forging": "GANGAFORGE.BO",
    "Groww MOM50": "MOM50.NS", "Groww Gold ETF": "GOLDBEES.NS", "ICICINXT50": "ICICINXT50.NS",
    "NIFTYBEES": "NIFTYBEES.NS", "Groww Silver ETF": "SILVERBEES.NS", "Nippon India ETF Gold BeES": "GOLDBEES.NS",
    "HOC": "HOC.NS", "Jaiprakash Power": "JPPOWER.NS", "Vikas Ecotech": "VIKASECO.NS", "MOM100": "MOM100.NS"
}

def get_live_price(symbol):
    try:
        return yf.Ticker(symbol).history(period="1d")["Close"].iloc[-1]
    except:
        return None

# --- Bot Commands ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Welcome to SV Portfolio Bot 💹\nType /help to know what I can do!")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, """📘 Commands:
/start - Welcome message
/help - Bot features
/portfolio - View your stock & SIP portfolio
/market - Real-time Nifty & Sensex data
/news - Live business news & reasons
/addstock name qty buyprice - Add a stock
/deletestock name - Delete a stock
/addsip name amount - Add a SIP
/deletesip name - Delete a SIP
""")

@bot.message_handler(commands=['market'])
def market(message):
    try:
        nifty = yf.Ticker("^NSEI").history(period="1d")["Close"].iloc[-1]
        sensex = yf.Ticker("^BSESN").history(period="1d")["Close"].iloc[-1]
        reply = f"📊 Live Market:\nNifty 50: {round(nifty)}\nSensex: {round(sensex)}"
        bot.reply_to(message, reply)
    except Exception as e:
        print("Market error:", e)
        bot.reply_to(message, "❌ Couldn't fetch live market data.")

@bot.message_handler(commands=['news'])
def market_news(message):
    try:
        url = 'https://newsapi.org/v2/top-headlines'
        params = {'category': 'business', 'country': 'in', 'apiKey': NEWS_API_KEY}
        response = requests.get(url, params=params)
        data = response.json()
        articles = data.get('articles', [])[:3]
        reply = "📰 Top Market News Today:\n\n"
        for i, article in enumerate(articles, 1):
            reply += f"{i}. {article['title']}\n"
        reply += "\n💡 Reason: Global cues, FIIs activity, inflation data, or profit booking."
        bot.reply_to(message, reply)
    except Exception as e:
        print("News error:", e)
        bot.reply_to(message, "❌ Failed to fetch news.")

@bot.message_handler(commands=['portfolio'])
def portfolio(message):
    try:
        data = load_portfolio()

        sip_text = "💰 SIPs:\n"
        for sip in data.get("sip", []):
            sip_text += f"- {sip['name']}: ₹{sip['amount']}\n"

        stock_text = "\n📈 Stocks:\n"
        total_invested = 0
        total_current = 0

        for stock in data.get("stocks", []):
            name = stock["name"]
            qty = stock["qty"]
            buy_price = stock["buy_price"]
            invested = qty * buy_price
            total_invested += invested

            symbol = ticker_map.get(name)
            if not symbol:
                stock_text += f"- {name}: {qty} @ ₹{buy_price} (⚠️ no data)\n"
                continue

            live_price = get_live_price(symbol)
            if live_price is None:
                stock_text += f"- {name}: {qty} @ ₹{buy_price} (⚠️ no price)\n"
                continue

            current = qty * live_price
            total_current += current
            gain = current - invested
            pct = (gain / invested) * 100
            emoji = "🔼" if gain >= 0 else "🔻"
            stock_text += f"- {name}: {qty} @ ₹{buy_price} → ₹{round(live_price,2)} {emoji} {round(pct,2)}%\n"

        net_gain = total_current - total_invested
        final_emoji = "🔼" if net_gain >= 0 else "🔻"
        summary = f"\n💼 Invested: ₹{round(total_invested)}\n📊 Current: ₹{round(total_current)}\n📈 Gain/Loss: {final_emoji} ₹{round(net_gain,2)} ({round((net_gain/total_invested)*100, 2)}%)"
        bot.reply_to(message, sip_text + stock_text + summary)
    except Exception as e:
        print("Portfolio Error:", e)
        bot.reply_to(message, "❌ Failed to load portfolio.")

# --- Add/Delete stock ---
@bot.message_handler(commands=['addstock'])
def add_stock(message):
    try:
        args = message.text.split()[1:]
        if len(args) != 3:
            bot.reply_to(message, "Usage: /addstock name qty buyprice")
            return
        name, qty, buy_price = args
        qty = int(qty)
        buy_price = float(buy_price)
        data = load_portfolio()
        data.setdefault("stocks", [])
        # Check if stock exists; update if yes
        for stock in data["stocks"]:
            if stock["name"].lower() == name.lower():
                stock["qty"] = qty
                stock["buy_price"] = buy_price
                break
        else:
            data["stocks"].append({"name": name, "qty": qty, "buy_price": buy_price})
        save_portfolio(data)
        bot.reply_to(message, f"✅ Added/Updated stock: {name}, Qty: {qty}, Buy Price: ₹{buy_price}")
    except Exception as e:
        print("AddStock Error:", e)
        bot.reply_to(message, "❌ Failed to add stock. Usage: /addstock name qty buyprice")

@bot.message_handler(commands=['deletestock'])
def delete_stock(message):
    try:
        args = message.text.split()[1:]
        if len(args) != 1:
            bot.reply_to(message, "Usage: /deletestock name")
            return
        name = args[0]
        data = load_portfolio()
        before = len(data.get("stocks", []))
        data["stocks"] = [s for s in data.get("stocks", []) if s["name"].lower() != name.lower()]
        after = len(data.get("stocks", []))
        if before == after:
            bot.reply_to(message, f"⚠️ Stock '{name}' not found.")
        else:
            save_portfolio(data)
            bot.reply_to(message, f"✅ Deleted stock '{name}'.")
    except Exception as e:
        print("DeleteStock Error:", e)
        bot.reply_to(message, "❌ Failed to delete stock. Usage: /deletestock name")

# --- Add/Delete SIP ---
@bot.message_handler(commands=['addsip'])
def add_sip(message):
    try:
        args = message.text.split()[1:]
        if len(args) != 2:
            bot.reply_to(message, "Usage: /addsip name amount")
            return
        name, amount = args
        amount = float(amount)
        data = load_portfolio()
        data.setdefault("sip", [])
        for sip in data["sip"]:
            if sip["name"].lower() == name.lower():
                sip["amount"] = amount
                break
        else:
            data["sip"].append({"name": name, "amount": amount})
        save_portfolio(data)
        bot.reply_to(message, f"✅ Added/Updated SIP: {name} – ₹{amount}")
    except Exception as e:
        print("AddSIP Error:", e)
        bot.reply_to(message, "❌ Failed to add SIP. Usage: /addsip name amount")

@bot.message_handler(commands=['deletesip'])
def delete_sip(message):
    try:
        args = message.text.split()[1:]
        if len(args) != 1:
            bot.reply_to(message, "Usage: /deletesip name")
            return
        name = args[0]
        data = load_portfolio()
        before = len(data.get("sip", []))
        data["sip"] = [s for s in data.get("sip", []) if s["name"].lower() != name.lower()]
        after = len(data.get("sip", []))
        if before == after:
            bot.reply_to(message, f"⚠️ SIP '{name}' not found.")
        else:
            save_portfolio(data)
            bot.reply_to(message, f"✅ Deleted SIP '{name}'.")
    except Exception as e:
        print("DeleteSIP Error:", e)
        bot.reply_to(message, "❌ Failed to delete SIP. Usage: /deletesip name")

# --- SIP Reminder ---
def send_sip_reminder(bot, chat_id, name, amount):
    bot.send_message(chat_id, f"🔔 SIP Reminder: {name} – ₹{amount}")

def schedule_sips(bot, chat_id):
    def job():
        today = datetime.now().day
        portfolio = load_portfolio()
        for sip in portfolio.get("sip", []):
            if (sip["name"].lower() == "icici corporate bond" and today == 11) or \
               (sip["name"].lower() == "nippon equity" and today == 18) or \
               (sip["name"].lower() == "goal sip" and today == 19):
                send_sip_reminder(bot, chat_id, sip["name"], sip["amount"])
    schedule.every().day.at("09:00").do(job)

    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(60)

    threading.Thread(target=run_schedule).start()

schedule_sips(bot, chat_id=5520822396)

# --- Keep alive for Render ---
keep_alive()

# --- Start Bot ---
print("Bot is running...")
bot.infinity_polling()
