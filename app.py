import os
import json
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from telegram import Update
from telegram.ext import Application, CommandHandler
from supabase import create_client

TOKEN = os.environ["BOT_TOKEN"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
DASHBOARD_USER = os.environ["DASHBOARD_USER"]
DASHBOARD_PASSWORD = os.environ["DASHBOARD_PASSWORD"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()
telegram_app = Application.builder().token(TOKEN).build()
security = HTTPBasic()
TR_TIMEZONE = timezone(timedelta(hours=3))


def today():
    return datetime.now(TR_TIMEZONE).date().isoformat()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def dashboard_auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username, DASHBOARD_USER)
    ok_pass = secrets.compare_digest(credentials.password, DASHBOARD_PASSWORD)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yetkisiz erişim",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def get_or_create_user(tg_user):
    result = supabase.table("profiles").select("id").eq("telegram_user_id", tg_user.id).limit(1).execute()
    if result.data:
        return result.data[0]["id"]
    result = supabase.table("profiles").insert({
        "telegram_user_id": tg_user.id,
        "telegram_username": tg_user.username,
        "first_name": tg_user.first_name,
        "last_name": tg_user.last_name,
    }).execute()
    return result.data[0]["id"]


def get_daily_log(user_id):
    return supabase.table("daily_logs").select("*").eq("user_id", user_id).eq("log_date", today()).limit(1).execute()


def get_goals(user_id):
    result = supabase.table("goals").select("*").eq("user_id", user_id).limit(1).execute()
    return result.data[0] if result.data else {}


def update_daily_value(user_id, field, value):
    existing = get_daily_log(user_id)
    if existing.data:
        supabase.table("daily_logs").update({field: value, "updated_at": now_utc()}).eq("id", existing.data[0]["id"]).execute()
    else:
        supabase.table("daily_logs").insert({"user_id": user_id, "log_date": today(), field: value}).execute()


async def start(update: Update, context):
    get_or_create_user(update.effective_user)
    await update.message.reply_text(
        "🏋️ Furkan AI Trainer aktif!\n\n"
        "/kilo 124\n/kalori 2200\n/protein 180\n/su 2.5\n/adim 7500\n"
        "/bel 118\n/gogus 125\n/antrenman Push 60\n\n"
        "📊 /bugun\n🎯 /hedef\n📈 /hafta"
    )


async def help_command(update: Update, context):
    await start(update, context)


async def test_command(update: Update, context):
    try:
        user_id = get_or_create_user(update.effective_user)
        get_goals(user_id)
        await update.message.reply_text("🟢 SİSTEM ÇALIŞIYOR!\n\nTelegram: ✅\nRender: ✅\nSupabase: ✅\nHedef sistemi: ✅")
    except Exception as e:
        print("TEST ERROR:", e)
        await update.message.reply_text("🔴 Sistem testinde hata oluştu.")


async def save_daily(update, context, field, label, suffix, min_v, max_v, integer=False):
    try:
        raw = context.args[0].replace(",", ".")
        value = int(raw) if integer else float(raw)
        if not min_v <= value <= max_v:
            raise ValueError
        user_id = get_or_create_user(update.effective_user)
        update_daily_value(user_id, field, value)
        shown = str(value) if integer else f"{value:g}"
        await update.message.reply_text(f"✅ {label}: {shown}{suffix} kaydedildi.")
    except (ValueError, IndexError):
        await update.message.reply_text(f"⚠️ Geçerli bir {label.lower()} değeri gir.")


async def kilo_command(update, context): await save_daily(update, context, "weight_kg", "Kilo", " kg", 30, 350)
async def kalori_command(update, context): await save_daily(update, context, "calories", "Kalori", " kcal", 0, 10000, True)
async def protein_command(update, context): await save_daily(update, context, "protein_g", "Protein", " g", 0, 500)
async def su_command(update, context): await save_daily(update, context, "water_l", "Su", " L", 0, 15)
async def adim_command(update, context): await save_daily(update, context, "steps", "Adım", "", 0, 100000, True)


async def measurement_command(update, context, field, label):
    try:
        value = float(context.args[0].replace(",", "."))
        user_id = get_or_create_user(update.effective_user)
        supabase.table("measurements").insert({"user_id": user_id, "measurement_date": today(), field: value}).execute()
        await update.message.reply_text(f"✅ {label}: {value:g} cm kaydedildi.")
    except (ValueError, IndexError):
        await update.message.reply_text(f"⚠️ Geçerli bir {label.lower()} ölçüsü gir.")


async def bel_command(update, context): await measurement_command(update, context, "waist_cm", "Bel")
async def gogus_command(update, context): await measurement_command(update, context, "chest_cm", "Göğüs")


async def antrenman_command(update: Update, context):
    try:
        workout_type = context.args[0]
        duration = int(context.args[1])
        if not 1 <= duration <= 600:
            raise ValueError
        user_id = get_or_create_user(update.effective_user)
        supabase.table("workouts").insert({
            "user_id": user_id, "workout_date": today(),
            "workout_type": workout_type, "duration_minutes": duration
        }).execute()
        await update.message.reply_text(f"✅ {workout_type} - {duration} dk kaydedildi.")
    except (ValueError, IndexError):
        await update.message.reply_text("⚠️ Kullanım: /antrenman Push 60")


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
        d = daily.data[0] if daily.data else {}
        g = get_goals(user_id)
        workouts = supabase.table("workouts").select("workout_type,duration_minutes").eq("user_id", user_id).eq("workout_date", today()).execute()
        workout_text = ", ".join(f"{x['workout_type']} {x['duration_minutes']} dk" for x in workouts.data) if workouts.data else "—"
        await update.message.reply_text(
            "📊 BUGÜNKÜ DURUM\n\n"
            f"⚖️ Kilo: {d.get('weight_kg', '—')} kg\n"
            f"🔥 Kalori: {d.get('calories', '—')} / {g.get('daily_calories', '—')} kcal\n"
            f"🥩 Protein: {d.get('protein_g', '—')} / {g.get('daily_protein_g', '—')} g\n"
            f"💧 Su: {d.get('water_l', '—')} / {g.get('daily_water_l', '—')} L\n"
            f"🚶 Adım: {d.get('steps', '—')} / {g.get('daily_steps', '—')}\n"
            f"🏋️ Antrenman: {workout_text}\n\n🎯 Hedef kilo: {g.get('target_weight_kg', '—')} kg"
        )
    except Exception as e:
        print("BUGUN ERROR:", e)
        await update.message.reply_text("🔴 Günlük bilgiler alınırken hata oluştu.")


async def hafta_command(update: Update, context):
    try:
        user_id = get_or_create_user(update.effective_user)
        result = supabase.table("daily_logs").select("log_date,weight_kg").eq("user_id", user_id).not_.is_("weight_kg", "null").order("log_date", desc=True).limit(7).execute()
        if not result.data:
            await update.message.reply_text("📈 Henüz yeterli kilo kaydı yok.")
            return
        rows = list(reversed(result.data))
        text = "📈 SON KİLO KAYITLARI\n\n" + "\n".join(f"{x['log_date']} → {x['weight_kg']} kg" for x in rows)
        if len(rows) >= 2:
            diff = float(rows[-1]["weight_kg"]) - float(rows[0]["weight_kg"])
            text += f"\n\n⚖️ Değişim: {'+' if diff > 0 else ''}{diff:.1f} kg"
        await update.message.reply_text(text)
    except Exception as e:
        print("HAFTA ERROR:", e)
        await update.message.reply_text("🔴 Haftalık rapor oluşturulamadı.")


for command, handler in [
    ("start", start), ("help", help_command), ("test", test_command),
    ("kilo", kilo_command), ("kalori", kalori_command), ("protein", protein_command),
    ("su", su_command), ("adim", adim_command), ("bel", bel_command),
    ("gogus", gogus_command), ("antrenman", antrenman_command),
    ("hedef", hedef_command), ("bugun", bugun_command), ("hafta", hafta_command),
]:
    telegram_app.add_handler(CommandHandler(command, handler))


@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.bot.delete_webhook(drop_pending_updates=True)
    await telegram_app.start()
    await telegram_app.updater.start_polling(drop_pending_updates=True)


@app.on_event("shutdown")
async def shutdown():
    await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()


@app.get("/")
async def home():
    return {"status": "online", "service": "Furkan AI Trainer", "database": "Supabase"}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(username: str = Depends(dashboard_auth)):
    try:
        profile_result = supabase.table("profiles").select("id,first_name").limit(1).execute()
        if not profile_result.data:
            return HTMLResponse("<h2>Profil bulunamadı.</h2>", status_code=404)
        profile = profile_result.data[0]
        user_id = profile["id"]
        first_name = profile.get("first_name") or "Furkan"
        goals = get_goals(user_id)
        daily_result = get_daily_log(user_id)
        daily = daily_result.data[0] if daily_result.data else {}
        weight_result = supabase.table("daily_logs").select("log_date,weight_kg").eq("user_id", user_id).not_.is_("weight_kg", "null").order("log_date", desc=False).limit(30).execute()
        weight_rows = weight_result.data or []
        labels = [r["log_date"] for r in weight_rows]
        weights = [float(r["weight_kg"]) for r in weight_rows]
        current_weight = weights[-1] if weights else None
        start_weight = weights[0] if weights else None
        target_weight = float(goals["target_weight_kg"]) if goals.get("target_weight_kg") is not None else None
        remaining = max(0, current_weight - target_weight) if current_weight is not None and target_weight is not None else None
        lost = start_weight - current_weight if current_weight is not None and start_weight is not None else None
        total_goal = start_weight - target_weight if start_weight is not None and target_weight is not None else None
        weight_progress = max(0, min(100, (lost / total_goal * 100))) if total_goal and total_goal > 0 and lost is not None else 0
        workouts = supabase.table("workouts").select("workout_type,duration_minutes").eq("user_id", user_id).eq("workout_date", today()).execute().data or []
        workout_text = " · ".join(f"{w['workout_type']} {w['duration_minutes']} dk" for w in workouts) if workouts else "Bugün henüz antrenman kaydı yok"

        def val(v, default="—"):
            return default if v is None else v

        def pct(actual, goal):
            try:
                return max(0, min(100, float(actual or 0) / float(goal) * 100)) if goal else 0
            except Exception:
                return 0

        cal_p = pct(daily.get("calories"), goals.get("daily_calories"))
        pro_p = pct(daily.get("protein_g"), goals.get("daily_protein_g"))
        water_p = pct(daily.get("water_l"), goals.get("daily_water_l"))
        step_p = pct(daily.get("steps"), goals.get("daily_steps"))

        html = f'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{first_name} AI Trainer</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#080d18;color:#f8fafc;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}}.wrap{{max-width:1240px;margin:auto;padding:34px 22px 60px}}.hero{{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:26px}}.eyebrow{{color:#22c55e;font-weight:800;letter-spacing:.12em;font-size:12px}}h1{{font-size:38px;margin:7px 0 4px;letter-spacing:-.04em}}.muted{{color:#8793a8}}.date{{background:#111827;border:1px solid #263246;padding:11px 15px;border-radius:14px;color:#aab4c5}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:15px}}.card{{background:linear-gradient(145deg,#121b2b,#0f1725);border:1px solid #233047;border-radius:20px;padding:20px;box-shadow:0 14px 40px #0004}}.card.big{{grid-column:span 2}}.label{{font-size:13px;color:#93a0b5;font-weight:650}}.num{{font-size:30px;font-weight:850;margin:9px 0 5px;letter-spacing:-.04em}}.sub{{font-size:13px;color:#77849a}}.bar{{height:8px;background:#263246;border-radius:99px;overflow:hidden;margin-top:15px}}.fill{{height:100%;background:linear-gradient(90deg,#22c55e,#60a5fa);border-radius:99px}}.section{{margin-top:17px}}.chart{{height:330px}}.goalbox{{display:flex;align-items:center;gap:18px}}.ring{{width:86px;height:86px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(#22c55e {weight_progress:.1f}%,#263246 0);position:relative}}.ring:after{{content:'';position:absolute;width:68px;height:68px;background:#111a29;border-radius:50%}}.ring b{{z-index:1;font-size:17px}}.workout{{font-size:20px;font-weight:750;margin-top:10px}}.foot{{text-align:center;color:#56647a;font-size:12px;margin-top:25px}}@media(max-width:850px){{.grid{{grid-template-columns:repeat(2,1fr)}}.card.big{{grid-column:span 2}}}}@media(max-width:520px){{.wrap{{padding:22px 14px}}.hero{{align-items:start;flex-direction:column}}h1{{font-size:30px}}.grid{{grid-template-columns:1fr}}.card.big{{grid-column:span 1}}.chart{{height:260px}}}}
</style></head><body><main class="wrap">
<div class="hero"><div><div class="eyebrow">FURKAN AI TRAINER</div><h1>İlerleme Merkezi</h1><div class="muted">Bugünkü verilerin ve kilo yolculuğun tek ekranda.</div></div><div class="date">📅 {today()}</div></div>
<div class="grid">
<div class="card big"><div class="label">⚖️ KİLO HEDEFİ</div><div class="goalbox"><div class="ring"><b>%{weight_progress:.0f}</b></div><div><div class="num">{val(current_weight)} kg</div><div class="sub">Hedef {val(target_weight)} kg · Kalan {round(remaining,1) if remaining is not None else '—'} kg</div></div></div></div>
<div class="card"><div class="label">📉 TOPLAM DEĞİŞİM</div><div class="num">{round(lost,1) if lost is not None else '—'} kg</div><div class="sub">İlk kayıt → bugün</div></div>
<div class="card"><div class="label">🏋️ BUGÜN</div><div class="workout">{workout_text}</div></div>
<div class="card"><div class="label">🔥 KALORİ</div><div class="num">{val(daily.get('calories'))}</div><div class="sub">/ {val(goals.get('daily_calories'))} kcal</div><div class="bar"><div class="fill" style="width:{cal_p}%"></div></div></div>
<div class="card"><div class="label">🥩 PROTEİN</div><div class="num">{val(daily.get('protein_g'))} g</div><div class="sub">/ {val(goals.get('daily_protein_g'))} g</div><div class="bar"><div class="fill" style="width:{pro_p}%"></div></div></div>
<div class="card"><div class="label">💧 SU</div><div class="num">{val(daily.get('water_l'))} L</div><div class="sub">/ {val(goals.get('daily_water_l'))} L</div><div class="bar"><div class="fill" style="width:{water_p}%"></div></div></div>
<div class="card"><div class="label">🚶 ADIM</div><div class="num">{val(daily.get('steps'))}</div><div class="sub">/ {val(goals.get('daily_steps'))}</div><div class="bar"><div class="fill" style="width:{step_p}%"></div></div></div>
</div>
<div class="section card"><div class="label">📈 SON 30 KİLO KAYDI</div><div class="chart"><canvas id="weightChart"></canvas></div></div>
<div class="foot">Telegram kayıtları Supabase üzerinden otomatik güncellenir.</div></main>
<script>new Chart(document.getElementById('weightChart'),{{type:'line',data:{{labels:{json.dumps(labels)},datasets:[{{label:'Kilo (kg)',data:{json.dumps(weights)},borderColor:'#22c55e',backgroundColor:'rgba(34,197,94,.10)',fill:true,tension:.35,pointRadius:4,pointBackgroundColor:'#22c55e'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#aab4c5'}}}}}},scales:{{x:{{ticks:{{color:'#738198'}},grid:{{color:'#1e293b'}}}},y:{{ticks:{{color:'#738198'}},grid:{{color:'#1e293b'}}}}}}}}}});</script></body></html>'''
        return HTMLResponse(html)
    except Exception as e:
        print("DASHBOARD ERROR:", e)
        return HTMLResponse("<h2>Dashboard yüklenirken hata oluştu.</h2>", status_code=500)
