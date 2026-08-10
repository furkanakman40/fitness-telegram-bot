import os

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler

TOKEN = os.environ["BOT_TOKEN"]

app = FastAPI()

telegram_app = (
    Application.builder()
    .token(TOKEN)
    .updater(None)
    .build()
)


async def start(update: Update, context):
    await update.message.reply_text(
        "Merhaba Furkan! 👋\n\n"
        "Kişisel fitness takip sistemin aktif.\n\n"
        "Yakında burada kilo, bel ölçüsü, "
        "kalori, protein, su, adım ve "
        "antrenman takibini yapabileceksin."
    )


async def help_command(update: Update, context):
    await update.message.reply_text(
        "Kullanabileceğin komutlar:\n\n"
        "/start - Sistemi başlat\n"
        "/help - Yardım"
    )


telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    CommandHandler("help", help_command)
)


@app.on_event("startup")
async def startup():
    await telegram_app.initialize()

    webhook_url = os.environ.get(
        "RENDER_EXTERNAL_URL"
    )

    if webhook_url:
        await telegram_app.bot.set_webhook(
            url=f"{webhook_url}/telegram"
        )


@app.on_event("shutdown")
async def shutdown():
    await telegram_app.shutdown()


@app.get("/")
async def home():
    return {
        "status": "online",
        "service": "Furkan Fitness Bot"
    }


@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()

    update = Update.de_json(
        data,
        telegram_app.bot
    )

    await telegram_app.process_update(update)

    return {"ok": True}
