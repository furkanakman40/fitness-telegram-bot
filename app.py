import os
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI
from telegram import Update
from telegram.ext import Application, CommandHandler
from supabase import create_client


# =========================================
# AYARLAR
# =========================================

TOKEN = os.environ["BOT_TOKEN"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

app = FastAPI()

telegram_app = (
    Application.builder()
    .token(TOKEN)
    .build()
)

TR_TIMEZONE = timezone(timedelta(hours=3))


# =========================================
# YARDIMCI FONKSİYONLAR
# =========================================

def today():
    return datetime.now(TR_TIMEZONE).date().isoformat()


def get_or_create_user(tg_user):
    result = (
        supabase
        .table("profiles")
        .select("id")
        .eq("telegram_user_id", tg_user.id)
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]["id"]

    new_user = {
        "telegram_user_id": tg_user.id,
        "telegram_username": tg_user.username,
        "first_name": tg_user.first_name,
        "last_name": tg_user.last_name,
    }

    result = (
        supabase
        .table("profiles")
        .insert(new_user)
        .execute()
    )

    return result.data[0]["id"]


# =========================================
# TELEGRAM KOMUTLARI
# =========================================

async def start(update: Update, context):
    try:
        get_or_create_user(update.effective_user)

        await update.message.reply_text(
            "🏋️ Furkan Fitness aktif!\n\n"
            "Telegram: ✅\n"
            "Render: ✅\n"
            "Supabase: ✅\n\n"
            "İlk kilo kaydını yapmak için:\n"
            "/kilo 124\n\n"
            "Bugünkü durumunu görmek için:\n"
            "/bugun"
        )

    except Exception as e:
        print("START ERROR:", e)

        await update.message.reply_text(
            "⚠️ Bot çalışıyor fakat veritabanına "
            "bağlanırken hata oluştu."
        )


async def help_command(update: Update, context):
    await update.message.reply_text(
        "📋 FITNESS KOMUTLARI\n\n"
        "/start - Sistemi başlat\n"
        "/test - Sistem testi\n"
        "/kilo 124 - Kilo kaydet\n"
        "/bugun - Bugünkü durum\n"
        "/help - Komutları göster"
    )


async def test_command(update: Update, context):
    try:
        user_id = get_or_create_user(
            update.effective_user
        )

        await update.message.reply_text(
            "🟢 SİSTEM ÇALIŞIYOR!\n\n"
            "Telegram: ✅\n"
            "Render: ✅\n"
            "Supabase: ✅\n"
            f"Profil ID: {str(user_id)[:8]}..."
        )

    except Exception as e:
        print("TEST ERROR:", e)

        await update.message.reply_text(
            "🔴 Supabase bağlantısı başarısız.\n\n"
            "Render loglarını kontrol etmemiz gerekiyor."
        )


async def kilo_command(update: Update, context):
    if not context.args:
        await update.message.reply_text(
            "⚖️ Kullanım:\n\n"
            "/kilo 124\n\n"
            "Ondalıklı değer de kullanabilirsin:\n"
            "/kilo 123.5"
        )
        return

    try:
        value = context.args[0].replace(",", ".")
        weight = float(value)

        if weight < 30 or weight > 350:
            await update.message.reply_text(
                "⚠️ Geçerli bir kilo değeri gir."
            )
            return

        user_id = get_or_create_user(
            update.effective_user
        )

        log_date = today()

        existing = (
            supabase
            .table("daily_logs")
            .select("id")
            .eq("user_id", user_id)
            .eq("log_date", log_date)
            .limit(1)
            .execute()
        )

        if existing.data:
            (
                supabase
                .table("daily_logs")
                .update({
                    "weight_kg": weight,
                    "updated_at": datetime.now(
                        timezone.utc
                    ).isoformat()
                })
                .eq(
                    "id",
                    existing.data[0]["id"]
                )
                .execute()
            )

        else:
            (
                supabase
                .table("daily_logs")
                .insert({
                    "user_id": user_id,
                    "log_date": log_date,
                    "weight_kg": weight
                })
                .execute()
            )

        await update.message.reply_text(
            f"✅ Kilon {weight:g} kg olarak kaydedildi.\n\n"
            "Bugünkü durum için:\n"
            "/bugun"
        )

    except ValueError:
        await update.message.reply_text(
            "⚠️ Kilo sayı olmalı.\n\n"
            "Örnek: /kilo 123.5"
        )

    except Exception as e:
        print("KILO ERROR:", e)

        await update.message.reply_text(
            "🔴 Kilo kaydedilirken bir hata oluştu."
        )


async def bugun_command(update: Update, context):
    try:
        user_id = get_or_create_user(
            update.effective_user
        )

        result = (
            supabase
            .table("daily_logs")
            .select(
                "weight_kg,"
                "calories,"
                "protein_g,"
                "water_l,"
                "steps"
            )
            .eq("user_id", user_id)
            .eq("log_date", today())
            .limit(1)
            .execute()
        )

        if not result.data:
            await update.message.reply_text(
                "📊 BUGÜN\n\n"
                "Henüz bugüne ait kayıt yok.\n\n"
                "İlk kaydını yap:\n"
                "/kilo 124"
            )
            return

        data = result.data[0]

        weight = (
            f'{data["weight_kg"]} kg'
            if data["weight_kg"] is not None
            else "—"
        )

        calories = (
            str(data["calories"])
            if data["calories"] is not None
            else "—"
        )

        protein = (
            f'{data["protein_g"]} g'
            if data["protein_g"] is not None
            else "—"
        )

        water = (
            f'{data["water_l"]} L'
            if data["water_l"] is not None
            else "—"
        )

        steps = (
            str(data["steps"])
            if data["steps"] is not None
            else "—"
        )

        await update.message.reply_text(
            "📊 BUGÜNKÜ DURUM\n\n"
            f"⚖️ Kilo: {weight}\n"
            f"🔥 Kalori: {calories}\n"
            f"🥩 Protein: {protein}\n"
            f"💧 Su: {water}\n"
            f"🚶 Adım: {steps}\n\n"
            "━━━━━━━━━━━━━━\n"
            "Takibe devam. 💪"
        )

    except Exception as e:
        print("BUGUN ERROR:", e)

        await update.message.reply_text(
            "🔴 Günlük bilgiler alınırken hata oluştu."
        )


# =========================================
# HANDLER'LAR
# =========================================

telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    CommandHandler("help", help_command)
)

telegram_app.add_handler(
    CommandHandler("test", test_command)
)

telegram_app.add_handler(
    CommandHandler("kilo", kilo_command)
)

telegram_app.add_handler(
    CommandHandler("bugun", bugun_command)
)


# =========================================
# BOT BAŞLATMA
# =========================================

@app.on_event("startup")
async def startup():
    await telegram_app.initialize()

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
        "service": "Furkan Fitness Bot",
        "database": "Supabase"
    }
