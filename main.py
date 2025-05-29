from datetime import datetime
import os
import finnhub
import httpx
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials


load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
finnhub_client = finnhub.Client(api_key=os.getenv("FINN_API_KEY"))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! 2 варинта: Киев или BTC.")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    log_to_sheet(text, update.effective_user.username or "Unknow")
    if text.isupper():
        stock_info = await get_stock_price(text)
        log_to_sheet(stock_info, update.effective_user.username or "Unknow")
        await update.message.reply_text(stock_info)
    else:
        weather = await get_weather_by_city(update.message.text)
        await update.message.reply_text(weather)


async def get_weather_by_city(city: str) -> str:
    WEATHER_URL = f"https://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city}&aqi=no"
    async with httpx.AsyncClient() as client:
        response = await client.get(WEATHER_URL)
        try:
            if response.status_code == 200:
                data = response.json()
                temperature = int(data["current"]["temp_c"])
                if temperature < 15:
                    weather_response = (
                        f"Сегодня температура {temperature} °C, холодно, одень куртку."
                    )
                else:
                    weather_response = f"Сегодня {temperature} °C, отличный день, можно бегать в футболке."
                return weather_response
            else:
                return f"Не удалось узнать данные по запрсоу {city}."
        except Exception as e:
            return f"Ошибка при полученни данных: {str(e)}"


async def get_stock_price(ticker: str) -> str:
    try:
        quote = finnhub_client.quote(ticker)
        current_price = quote["c"]
        if current_price:
            return f"Цена акции {ticker.upper()}: {current_price}$"
        else:
            return "Не удалось получить цену акции."
    except Exception as e:
        return f"Ошибка при полученни данных: {str(e)}"


def log_to_sheet(message: str, user: str):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_dict = {
        "type": "service_account",
        "project_id": "total-now-461220-q5",
        "private_key_id": os.getenv("PRIVATE_KEY_ID"),
        "private_key": os.getenv("PRIVATE_KEY").replace("\\n", "\n"),
        "client_email": "sheets-writer@total-now-461220-q5.iam.gserviceaccount.com",
        "client_id": "107179566616802042151",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/sheets-writer%40total-now-461220-q5.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com",
    }

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    sheet = client.open("bot_logs").sheet1

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([timestamp, user, message])


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

app.run_polling()


if __name__ == "__main__":
    app.run_polling()
