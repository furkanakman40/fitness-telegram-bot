import os
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI
from telegram import Update
from telegram.ext import Application, CommandHandler
from supabase import create_client

TOKEN = os.environ["BOT_TOKEN"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
telegram_app = Application.builder().token(TOKEN).build()

TR_TIMEZONE = timezone(timedelta(hours=3))


def today():
    return datetime.now(TR_TIMEZONE).date().isoformat()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def get_or_create_user(tg_user):
    result = (
        supabase.table("profiles")
        .select("id")
        .eq("telegram_user_id", tg_user.id)
        .limit(1)
        .execute()
    )

    if result.data:
        return result.data[0]["id"]

    result = (
        supabase.table("profiles")
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
        supabase.table("daily_logs")
        .select("*")
        .eq("user_id", user_id)
        .eq("log_date", today())
        .limit(1)
        .execute()
    )


def get_goals(user_id):
    result = (
        supabase.table("goals")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    return result.data[0] if result.data else {}


def update_daily_value(user_id, field, value):
    existing = get_daily_log(user_id)

    if existing.data:
        (
            supabase.table("daily_logs")
            .update({
                field: value,
                "updated_at": now_utc()
            })
            .eq("id", existing.data[0]["id"])
            .execute()
        )
    else:
        (
            supabase.table("daily_logs")
            .insert({
                "user_id": user_id,
                "log_date": today(),
                field: value
            })
            .execute()
        )


async def start(update: Update, context):
    get_or_create_user(update.effective_user)

    await update.message.reply_text(
        "🏋️ Furkan AI Trainer aktif!\n\n"
        "/kilo 124\n"
        "/kalori 2200\n"
        "/protein 180\n"
        "/su 2.5\n"
        "/adim 7500\n"
        "/bel 118\n"
        "/gogus 125\n"
        "/antrenman Push 60\n\n"
        "📊 /bugun\n"
        "🎯 /hedef\n"
        "📈 /hafta"
    )


async def help_command(update: Update, context):
    await start(update, context)


async def test_command(update: Update, context):
    try:
        user_id = get_or_create_user(update.effective_user)
        get_goals(user_id)

        await update.message.reply_text(
            "🟢 SİSTEM ÇALIŞIYOR!\n\n"
            "Telegram: ✅\n"
            "Render: ✅\n"
            "Supabase: ✅\n"
            "Hedef sistemi: ✅"
        )

    except Exception as e:
        print("TEST ERROR:", e)
        await update.message.reply_text("🔴 Sistem testinde hata oluştu.")


async def kilo_command(update: Update, context):
    try:
        value = float(context.args[0].replace(",", "."))
        if not 30 <= value <= 350:
            raise ValueError

        user_id = get_or_create_user(update.effective_user)
        update_daily_value(user_id, "weight_kg", value)

        await update.message.reply_text(
            f"✅ Kilo: {value:g} kg kaydedildi."
        )

    except (ValueError, IndexError):
        await update.message.reply_text("⚠️ Kullanım: /kilo 123.5")


async def kalori_command(update: Update, context):
    try:
        value = int(context.args[0])
        if not 0 <= value <= 10000:
            raise ValueError

        user_id = get_or_create_user(update.effective_user)
        update_daily_value(user_id, "calories", value)

        await update.message.reply_text(
            f"✅ Kalori: {value} kcal kaydedildi."
        )

    except (ValueError, IndexError):
        await update.message.reply_text("⚠️ Kullanım: /kalori 2200")


async def protein_command(update: Update, context):
    try:
        value = float(context.args[0].replace(",", "."))
        if not 0 <= value <= 500:
            raise ValueError

        user_id = get_or_create_user(update.effective_user)
        update_daily_value(user_id, "protein_g", value)

        await update.message.reply_text(
            f"✅ Protein: {value:g} g kaydedildi."
        )

    except (ValueError, IndexError):
        await update.message.reply_text("⚠️ Kullanım: /protein 190")


async def su_command(update: Update, context):
    try:
        value = float(context.args[0].replace(",", "."))
        if not 0 <= value <= 15:
            raise ValueError

        user_id = get_or_create_user(update.effective_user)
        update_daily_value(user_id, "water_l", value)

        await update.message.reply_text(
            f"✅ Su: {value:g} L kaydedildi."
        )

    except (ValueError, IndexError):
        await update.message.reply_text("⚠️ Kullanım: /su 3.5")


async def adim_command(update: Update, context):
    try:
        value = int(context.args[0])
        if not 0 <= value <= 100000:
            raise ValueError

        user_id = get_or_create_user(update.effective_user)
        update_daily_value(user_id, "steps", value)

        await update.message.reply_text(
            f"✅ Adım: {value} kaydedildi."
        )

    except (ValueError, IndexError):
        await update.message.reply_text("⚠️ Kullanım: /adim 8000")


async def bel_command(update: Update, context):
    try:
        value = float(context.args[0].replace(",", "."))
        user_id = get_or_create_user(update.effective_user)

        supabase.table("measurements").insert({
            "user_id": user_id,
            "measurement_date": today(),
            "waist_cm": value
        }).execute()

        await update.message.reply_text(
            f"✅ Bel: {value:g} cm kaydedildi."
        )

    except (ValueError, IndexError):
        await update.message.reply_text("⚠️ Kullanım: /bel 118")


async def gogus_command(update: Update, context):
    try:
        value = float(context.args[0].replace(",", "."))
        user_id = get_or_create_user(update.effective_user)

        supabase.table("measurements").insert({
            "user_id": user_id,
            "measurement_date": today(),
            "chest_cm": value
        }).execute()

        await update.message.reply_text(
            f"✅ Göğüs: {value:g} cm kaydedildi."
        )

    except (ValueError, IndexError):
        await update.message.reply_text("⚠️ Kullanım: /gogus 125")


async def antrenman_command(update: Update, context):
    try:
        workout_type = context.args[0]
        duration = int(context.args[1])

        user_id = get_or_create_user(update.effective_user)

        supabase.table("workouts").insert({
            "user_id": user_id,
            "workout_date": today(),
            "workout_type": workout_type,
            "duration_minutes": duration
        }).execute()

        await update.message.reply_text(
            f"✅ {workout_type} - {duration} dk kaydedildi."
        )

    except (ValueError, IndexError):
        await update.message.reply_text(
            "⚠️ Kullanım: /antrenman Push 60"
        )


async def hedef_command(update: Update, context):
    try:
        user_id = get_or_create_user(update.effective_user)
        g = get_goals(user_id)

        await update.message.reply_text(
            "🎯 GÜNLÜK HEDEFLER\n\n"
            f"⚖️ Hedef kilo: {g.get('target_weight_kg', '—')} kg\n"
            f"🔥 Kalori: {g.get('daily_calories', '—')} kcal\n"
            f"🥩 Protein: {g.get('daily_protein_g', '—')} g\n"
            f"💧 Su: {g.get('daily_water_l', '—')} L\n"
            f"🚶 Adım: {g.get('daily_steps', '—')}"
        )

    except Exception as e:
        print("HEDEF ERROR:", e)
        await update.message.reply_text("🔴 Hedefler okunamadı.")


async def bugun_command(update: Update, context):
    try:
        user_id = get_or_create_user(update.effective_user)

        daily = get_daily_log(user_id)
        data = daily.data[0] if daily.data else {}

        g = get_goals(user_id)

        workouts = (
            supabase.table("workouts")
            .select("workout_type,duration_minutes")
            .eq("user_id", user_id)
            .eq("workout_date", today())
            .execute()
        )

        workout_text = "—"

        if workouts.data:
            workout_text = ", ".join(
                f"{x['workout_type']} {x['duration_minutes']} dk"
                for x in workouts.data
            )

        await update.message.reply_text(
            "📊 BUGÜNKÜ DURUM\n\n"
            f"⚖️ Kilo: {data.get('weight_kg', '—')} kg\n"
            f"🔥 Kalori: {data.get('calories', '—')} / "
            f"{g.get('daily_calories', '—')} kcal\n"
            f"🥩 Protein: {data.get('protein_g', '—')} / "
            f"{g.get('daily_protein_g', '—')} g\n"
            f"💧 Su: {data.get('water_l', '—')} / "
            f"{g.get('daily_water_l', '—')} L\n"
            f"🚶 Adım: {data.get('steps', '—')} / "
            f"{g.get('daily_steps', '—')}\n"
            f"🏋️ Antrenman: {workout_text}\n\n"
            f"🎯 Hedef kilo: {g.get('target_weight_kg', '—')} kg"
        )

    except Exception as e:
        print("BUGUN ERROR:", e)
        await update.message.reply_text(
            "🔴 Günlük bilgiler alınırken hata oluştu."
        )


async def hafta_command(update: Update, context):
    try:
        user_id = get_or_create_user(update.effective_user)

        result = (
            supabase.table("daily_logs")
            .select("log_date,weight_kg")
            .eq("user_id", user_id)
            .not_.is_("weight_kg", "null")
            .order("log_date", desc=True)
            .limit(7)
            .execute()
        )

        if not result.data:
            await update.message.reply_text(
                "📈 Henüz yeterli kilo kaydı yok."
            )
            return

        rows = list(reversed(result.data))

        lines = [
            f"{x['log_date']} → {x['weight_kg']} kg"
            for x in rows
        ]

        difference = None

        if len(rows) >= 2:
            difference = float(rows[-1]["weight_kg"]) - float(
                rows[0]["weight_kg"]
            )

        text = "📈 SON KİLO KAYITLARI\n\n" + "\n".join(lines)

        if difference is not None:
            sign = "+" if difference > 0 else ""
            text += (
                f"\n\n⚖️ Değişim: {sign}{difference:.1f} kg"
            )

        await update.message.reply_text(text)

    except Exception as e:
        print("HAFTA ERROR:", e)
        await update.message.reply_text(
            "🔴 Haftalık rapor oluşturulamadı."
        )


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

telegram_app.add_handler(CommandHandler("hedef", hedef_command))
telegram_app.add_handler(CommandHandler("bugun", bugun_command))
telegram_app.add_handler(CommandHandler("hafta", hafta_command))


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
