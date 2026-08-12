import os

from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
)

TOKEN = os.environ["BOT_TOKEN"]

app = FastAPI()

telegram_app = (
    Application.builder()
    .token(TOKEN)
    .build()
)


async def start(update: Update, context):
    await update.message.reply_text(
        "Merhaba Furkan! 👋\n\n"
        "Kişisel fitness takip sistemin aktif.\n\n"
        "Bot bağlantısı başarılı! ✅\n\n"
        "Yakında kilo, bel ölçüsü, kalori, "
        "protein, su, adım ve antrenman "
        "takibini buradan yapabileceksin."
    )


async def help_command(update: Update, context):
    await update.message.reply_text(
        "📋 Komutlar\n\n"
        "/start - Sistemi başlat\n"
        "/help - Yardım\n"
        "/test - Bot bağlantısını test et"
    )


async def test_command(update: Update, context):
    await update.message.reply_text(
        "🟢 BOT ÇALIŞIYOR!\n\n"
        "Telegram bağlantısı: ✅\n"
        "Render bağlantısı: ✅\n"
        "Bot sistemi: ✅\n\n"
        "Bir sonraki aşamada veritabanını "
        "bağlayacağız."
    )


telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    CommandHandler("help", help_command)
)

telegram_app.add_handler(
    CommandHandler("test", test_command)
)


@app.on_event("startup")
async def startup():
    await telegram_app.initialize()

    # Daha önce oluşturulmuş webhook'u temizle.
    await telegram_app.bot.delete_webhook(
        drop_pending_updates=True
    )

    await telegram_app.start()

    await telegram_app.updater.start_polling(
        drop_pending_updates=True
    )


@app.on_event("shutdown")
async def shutdown():
    await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()


@app.get("/")
async def home():
    return {
        "status": "online",
        "service": "Furkan Fitness Bot"
    }
