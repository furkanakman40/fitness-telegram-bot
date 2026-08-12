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

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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


def now_utc():
    return datetime.now(timezone.utc).isoformat()


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

    result = (
        supabase
        .table("profiles")
        .insert({
            "telegram_user_id": tg_user.id,
            "telegram_username": tg_user.username,
            "first_name": tg_user.first_name,
            "last_name": tg_user.last_name,
        })
        .execute()
    )

    return result.data[0]["id"]


def get_daily_log(user_id):
    return (
        supabase
        .table("daily_logs")
        .select("*")
        .eq("user_id", user_id)
        .eq("log_date", today())
        .limit(1)
        .execute()
    )


def update_daily_value(user_id, field, value):
    existing = get_daily_log(user_id)

    if existing.data:
        (
            supabase
            .table("daily_logs")
            .update({
                field: value,
                "updated_at": now_utc()
            })
            .eq("id", existing.data[0]["id"])
            .execute()
        )
    else:
        (
            supabase
            .table("daily_logs")
            .insert({
                "user_id": user_id,
                "log_date": today(),
                field: value
            })
            .execute()
        )


# =========================================
# TEMEL KOMUTLAR
# =========================================

async def start(update: Update, context):
    get_or_create_user(update.effective_user)

    await update.message.reply_text(
        "🏋️ Furkan AI Trainer aktif!\n\n"
        "Günlük takip komutların:\n\n"
        "⚖️ /kilo 124\n"
        "🔥 /kalori 2200\n"
        "🥩 /protein 180\n"
        "💧 /su 2.5\n"
        "🚶 /adim 7500\n"
        "📏 /bel 118\n"
        "🫁 /gogus 125\n"
        "🏋️ /antrenman Push 60\n"
        "📊 /bugun\n\n"
        "/help ile tüm komutları görebilirsin."
    )


async def help_command(update: Update, context):
    await update.message.reply_text(
        "📋 KOMUTLAR\n\n"
        "/kilo 124\n"
        "/kalori 2200\n"
        "/protein 180\n"
        "/su 2.5\n"
        "/adim 7500\n"
        "/bel 118\n"
        "/gogus 125\n"
        "/antrenman Push 60\n"
        "/bugun\n"
        "/test"
    )


async def test_command(update: Update, context):
    try:
        user_id = get_or_create_user(update.effective_user)

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
            "🔴 Sistem testinde hata oluştu."
        )


# =========================================
# GÜNLÜK VERİ KOMUTLARI
# =========================================

async def kilo_command(update: Update, context):
    if not context.args:
        await update.message.reply_text(
            "Kullanım: /kilo 123.5"
        )
        return

    try:
        weight = float(context.args[0].replace(",", "."))

        if not 30 <= weight <= 350:
            raise ValueError

        user_id = get_or_create_user(update.effective_user)
        update_daily_value(user_id, "weight_kg", weight)

        await update.message.reply_text(
            f"✅ Kilon {weight:g} kg olarak kaydedildi."
        )

    except ValueError:
        await update.message.reply_text(
            "⚠️ Örnek kullanım: /kilo 123.5"
        )


async def kalori_command(update: Update, context):
    if not context.args:
        await update.message.reply_text(
            "Kullanım: /kalori 2200"
        )
        return

    try:
        calories = int(context.args[0])

        if not 0 <= calories <= 10000:
            raise ValueError

        user_id = get_or_create_user(update.effective_user)
        update_daily_value(user_id, "calories", calories)

        await update.message.reply_text(
            f"✅ Kalori {calories} kcal olarak kaydedildi."
        )

    except ValueError:
        await update.message.reply_text(
            "⚠️ Örnek kullanım: /kalori 2200"
        )


async def protein_command(update: Update, context):
    if not context.args:
        await update.message.reply_text(
            "Kullanım: /protein 180"
        )
        return

    try:
        protein = float(context.args[0].replace(",", "."))

        if not 0 <= protein <= 500:
            raise ValueError

        user_id = get_or_create_user(update.effective_user)
        update_daily_value(user_id, "protein_g", protein)

        await update.message.reply_text(
            f"✅ Protein {protein:g} g olarak kaydedildi."
        )

    except ValueError:
        await update.message.reply_text(
            "⚠️ Örnek kullanım: /protein 180"
        )


async def su_command(update: Update, context):
    if not context.args:
        await update.message.reply_text(
            "Kullanım: /su 2.5"
        )
        return

    try:
        water = float(context.args[0].replace(",", "."))

        if not 0 <= water <= 15:
            raise ValueError

        user_id = get_or_create_user(update.effective_user)
        update_daily_value(user_id, "water_l", water)

        await update.message.reply_text(
            f"✅ Su {water:g} L olarak kaydedildi."
        )

    except ValueError:
        await update.message.reply_text(
            "⚠️ Örnek kullanım: /su 2.5"
        )


async def adim_command(update: Update, context):
    if not context.args:
        await update.message.reply_text(
            "Kullanım: /adim 7500"
        )
        return

    try:
        steps = int(context.args[0])

        if not 0 <= steps <= 100000:
            raise ValueError

        user_id = get_or_create_user(update.effective_user)
        update_daily_value(user_id, "steps", steps)

        await update.message.reply_text(
            f"✅ {steps} adım olarak kaydedildi."
        )

    except ValueError:
        await update.message.reply_text(
            "⚠️ Örnek kullanım: /adim 7500"
        )


# =========================================
# ÖLÇÜM KOMUTLARI
# =========================================

async def save_measurement(update, field, label):
    if not update.message:
        return

    context = update._bot_data_context if False else None


async def bel_command(update: Update, context):
    if not context.args:
        await update.message.reply_text(
            "Kullanım: /bel 118"
        )
        return

    try:
        value = float(context.args[0].replace(",", "."))

        if not 40 <= value <= 250:
            raise ValueError

        user_id = get_or_create_user(update.effective_user)

        (
            supabase
            .table("measurements")
            .insert({
                "user_id": user_id,
                "measurement_date": today(),
                "waist_cm": value
            })
            .execute()
        )

        await update.message.reply_text(
            f"✅ Bel çevresi {value:g} cm olarak kaydedildi."
        )

    except ValueError:
        await update.message.reply_text(
            "⚠️ Örnek kullanım: /bel 118"
        )


async def gogus_command(update: Update, context):
    if not context.args:
        await update.message.reply_text(
            "Kullanım: /gogus 125"
        )
        return

    try:
        value = float(context.args[0].replace(",", "."))

        if not 40 <= value <= 250:
            raise ValueError

        user_id = get_or_create_user(update.effective_user)

        (
            supabase
            .table("measurements")
            .insert({
                "user_id": user_id,
                "measurement_date": today(),
                "chest_cm": value
            })
            .execute()
        )

        await update.message.reply_text(
            f"✅ Göğüs çevresi {value:g} cm olarak kaydedildi."
        )

    except ValueError:
        await update.message.reply_text(
            "⚠️ Örnek kullanım: /gogus 125"
        )


# =========================================
# ANTRENMAN
# =========================================

async def antrenman_command(update: Update, context):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Kullanım:\n"
            "/antrenman Push 60\n\n"
            "İlk değer antrenman türü,\n"
            "ikinci değer dakika."
        )
        return

    try:
        workout_type = context.args[0]
        duration = int(context.args[1])

        if not 1 <= duration <= 600:
            raise ValueError

        user_id = get_or_create_user(update.effective_user)

        (
            supabase
            .table("workouts")
            .insert({
                "user_id": user_id,
                "workout_date": today(),
                "workout_type": workout_type,
                "duration_minutes": duration
            })
            .execute()
        )

        await update.message.reply_text(
            "✅ Antrenman kaydedildi.\n\n"
            f"🏋️ Tür: {workout_type}\n"
            f"⏱ Süre: {duration} dk"
        )

    except ValueError:
        await update.message.reply_text(
            "⚠️ Örnek kullanım: /antrenman Push 60"
        )


# =========================================
# BUGÜN ÖZETİ
# =========================================

async def bugun_command(update: Update, context):
    try:
        user_id = get_or_create_user(update.effective_user)

        daily = get_daily_log(user_id)

        if daily.data:
            data = daily.data[0]
        else:
            data = {}

        measurement = (
            supabase
            .table("measurements")
            .select("waist_cm,chest_cm")
            .eq("user_id", user_id)
            .order("measurement_date", desc=True)
            .limit(1)
            .execute()
        )

        m = measurement.data[0] if measurement.data else {}

        workouts = (
            supabase
            .table("workouts")
            .select("workout_type,duration_minutes")
            .eq("user_id", user_id)
            .eq("workout_date", today())
            .execute()
        )

        if workouts.data:
            workout_text = "\n".join(
                [
                    f"🏋️ {w['workout_type']} - "
                    f"{w['duration_minutes']} dk"
                    for w in workouts.data
                ]
            )
        else:
            workout_text = "🏋️ Antrenman: —"

        def show(value, suffix=""):
            if value is None:
                return "—"
            return f"{value}{suffix}"

        await update.message.reply_text(
            "📊 BUGÜNKÜ DURUM\n\n"
            f"⚖️ Kilo: {show(data.get('weight_kg'), ' kg')}\n"
            f"🔥 Kalori: {show(data.get('calories'), ' kcal')}\n"
            f"🥩 Protein: {show(data.get('protein_g'), ' g')}\n"
            f"💧 Su: {show(data.get('water_l'), ' L')}\n"
            f"🚶 Adım: {show(data.get('steps'))}\n\n"
            f"📏 Bel: {show(m.get('waist_cm'), ' cm')}\n"
            f"🫁 Göğüs: {show(m.get('chest_cm'), ' cm')}\n\n"
            f"{workout_text}\n\n"
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

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("test", test_command))

telegram_app.add_handler(CommandHandler("kilo", kilo_command))
telegram_app.add_handler(CommandHandler("kalori", kalori_command))
telegram_app.add_handler(CommandHandler("protein", protein_command))
telegram_app.add_handler(CommandHandler("su", su_command))
telegram_app.add_handler(CommandHandler("adim", adim_command))

telegram_app.add_handler(CommandHandler("bel", bel_command))
telegram_app.add_handler(CommandHandler("gogus", gogus_command))

telegram_app.add_handler(
    CommandHandler("antrenman", antrenman_command)
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
        "service": "Furkan AI Trainer",
        "database": "Supabase"
    }
