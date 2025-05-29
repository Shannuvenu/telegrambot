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
from keep_alive import keep_alive  # for Replit hosting

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

# /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome to SV Portfolio Bot 💹! Type /help to know what I can do.")

# /help
@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "Commands:\n/start - Welcome message\n/portfolio - Show your portfolio\n/market - Live Market Info\n/news - Market movement reason")

# /market
@bot.message_handler(commands=['market'])
def market(message):
    bot.reply_to(message, "📊 Market Now:\nNifty: 22,500 🔺\nSensex: 74,200 🔺")

# /news
@bot.message_handler(commands=['news'])
def market_news(message):
    try:
        url = 'https://newsapi.org/v2/top-headlines'
        params = {'category': 'business', 'country': 'in', 'apiKey': NEWS_API_KEY}
        response = requests.get(url, params=params)
        data = response.json()
        headlines = [article['title'] for article in data.get('articles', [])[:3]]

        reply = "📰 Market News Today:\n\n"
        for i, title in enumerate(headlines, 1):
            reply += f"{i}. {title}\n"
        reply += "\n🧠 Reason: Market movement due to global cues, profit booking, or FIIs activity."

        bot.reply_to(message, reply)
    except Exception as e:
        print("Error fetching news:", e)
        bot.reply_to(message, "❌ Failed to fetch news. Please try again later.")

# /portfolio
@bot.message_handler(commands=['portfolio'])
def portfolio(message):
    try:
        with open("portfolio.json", "r") as f:
            data = json.load(f)

        sip_text = "💰 SIPs:\n"
        for sip in data["sip"]:
            sip_text += f"- {sip['name']}: ₹{sip['amount']}\n"

        stock_text = "\n📈 Stocks:\n"
        total_invested = 0
        total_current = 0

        ticker_map = {
            "Inox Wind": "INOXWIND.NS",
            "Suzlon Energy": "SUZLON.NS",
            "Ganga Forging": "GANGAFORGE.BO",
            "Groww MOM50": "MOM50.NS",
            "Groww Gold ETF": "GOLDBEES.NS",
            "ICICINXT50": "ICICINXT50.NS",
            "NIFTYBEES": "NIFTYBEES.NS",
            "Groww Silver ETF": "SILVERBEES.NS",
            "Nippon India ETF Gold BeES": "GOLDBEES.NS",
            "HOC": "HOC.NS",
            "Jaiprakash Power": "JPPOWER.NS",
            "Vikas Ecotech": "VIKASECO.NS",
            "MOM100": "MOM100.NS"
        }

        for stock in data["stocks"]:
            name = stock["name"]
            qty = stock["qty"]
            buy_price = stock["buy_price"]
            invested = qty * buy_price
            total_invested += invested

            symbol = ticker_map.get(name)
            if not symbol:
                stock_text += f"- {name}: {qty} @ ₹{buy_price} (⚠️ no data)\n"
                continue

            try:
                ticker = yf.Ticker(symbol)
                live_price = ticker.history(period="1d")["Close"].iloc[-1]
            except Exception as e:
                print(f"❌ Error fetching {symbol}:", e)
                stock_text += f"- {name}: {qty} @ ₹{buy_price} (⚠️ no price)\n"
                continue

            current_value = qty * live_price
            total_current += current_value
            gain = current_value - invested
            percent = (gain / invested) * 100
            emoji = "🔼" if gain >= 0 else "🔻"
            stock_text += f"- {name}: {qty} @ ₹{buy_price} → ₹{round(live_price,2)} {emoji} {round(percent,2)}%\n"

        total_gain = total_current - total_invested
        gain_symbol = "🔼" if total_gain >= 0 else "🔻"
        summary = f"\n💼 Total Invested: ₹{round(total_invested)}\n" \
                  f"📊 Current Value: ₹{round(total_current)}\n" \
                  f"📈 Gain/Loss: {gain_symbol} ₹{round(total_gain, 2)} ({round((total_gain/total_invested)*100, 2)}%)"

        reply = sip_text + stock_text + summary
        bot.reply_to(message, reply)

    except Exception as e:
        print("Portfolio Error:", e)
        bot.reply_to(message, "❌ Failed to load portfolio.")

# 🔔 SIP Reminder Setup
def send_sip_reminder(bot, chat_id, name, amount):
    bot.send_message(chat_id, f"🔔 SIP Reminder: {name} – ₹{amount}")

def schedule_sips(bot, chat_id):
    def job():
        today = datetime.now().day
        if today == 11:
            send_sip_reminder(bot, chat_id, "ICICI Corporate Bond", 100)
        elif today == 18:
            send_sip_reminder(bot, chat_id, "Nippon Equity", 500)
        elif today == 19:
            send_sip_reminder(bot, chat_id, "Goal SIP", 600)

    schedule.every().day.at("09:00").do(job)

    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(60)

    threading.Thread(target=run_schedule).start()

# 🧠 Start scheduled SIP reminders
schedule_sips(bot, chat_id=5520822396)

# ✅ For Replit Hosting
keep_alive()

# 🚀 Start the bot
print("Bot is running...")
bot.infinity_polling()
