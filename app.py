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


def first_profile():
    result = supabase.table("profiles").select("id,first_name").limit(1).execute()
    return result.data[0] if result.data else None


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


def nav(active):
    items = [("dashboard", "⌂ Genel", "/dashboard"), ("egzersiz", "🏋 Egzersiz", "/egzersiz"), ("istatistik", "◒ İstatistik", "/istatistik")]
    return ''.join(f'<a class="navitem {"active" if active == key else ""}" href="{url}">{label}</a>' for key, label, url in items)


def base_css():
    return '''
*{box-sizing:border-box}body{margin:0;background:#070b14;color:#f8fafc;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}.layout{min-height:100vh;display:grid;grid-template-columns:230px 1fr}.sidebar{padding:28px 18px;border-right:1px solid #1f2937;background:#0a101c;position:sticky;top:0;height:100vh}.brand{font-size:20px;font-weight:900;letter-spacing:-.03em;margin-bottom:28px}.brand span{color:#22c55e}.navitem{display:block;text-decoration:none;color:#8d99ad;padding:12px 14px;border-radius:12px;margin:6px 0;font-weight:700}.navitem:hover,.navitem.active{background:#162033;color:#fff}.main{padding:34px;max-width:1450px;width:100%;margin:auto}.eyebrow{font-size:12px;color:#22c55e;font-weight:900;letter-spacing:.13em}.hero{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:25px}h1{font-size:38px;margin:6px 0 5px;letter-spacing:-.045em}.muted{color:#8390a4}.pill{padding:10px 14px;background:#111827;border:1px solid #263246;border-radius:999px;color:#aab4c5}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:15px}.card{background:linear-gradient(145deg,#121a29,#0d1420);border:1px solid #202d42;border-radius:20px;padding:20px;box-shadow:0 18px 45px #0004}.big{grid-column:span 2}.label{font-size:12px;color:#8f9bae;font-weight:800;letter-spacing:.04em}.num{font-size:31px;font-weight:900;margin:9px 0 4px;letter-spacing:-.045em}.sub{font-size:13px;color:#6f7d92}.bar{height:8px;background:#263246;border-radius:99px;overflow:hidden;margin-top:15px}.fill{height:100%;background:linear-gradient(90deg,#22c55e,#3b82f6);border-radius:99px}.section{margin-top:16px}.chart{height:340px}.ring{width:88px;height:88px;border-radius:50%;display:grid;place-items:center;position:relative}.ring:after{content:'';position:absolute;width:69px;height:69px;background:#111827;border-radius:50%}.ring b{z-index:1}.goalbox{display:flex;align-items:center;gap:18px}.exercise-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}.day{position:relative;overflow:hidden}.day:before{content:'';position:absolute;inset:0 0 auto 0;height:4px;background:linear-gradient(90deg,#22c55e,#3b82f6)}.dayhead{display:flex;justify-content:space-between;align-items:center;margin-bottom:17px}.badge{font-size:12px;background:#172236;border:1px solid #2b3a55;padding:6px 9px;border-radius:999px;color:#a9b4c5}.exercise{display:grid;grid-template-columns:42px 1fr auto;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid #1d293b}.exercise:last-child{border-bottom:0}.icon{width:42px;height:42px;border-radius:12px;background:#162033;display:grid;place-items:center;font-size:20px}.exercise b{font-size:14px}.exercise small{display:block;color:#728097;margin-top:3px}.sets{font-size:12px;color:#d5dbe5;background:#101827;border:1px solid #243149;border-radius:10px;padding:7px 9px}.stat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}.table{width:100%;border-collapse:collapse}.table th,.table td{text-align:left;padding:12px;border-bottom:1px solid #1d293b;font-size:13px}.table th{color:#7f8ca1}.positive{color:#22c55e}.warning{color:#f59e0b}.foot{text-align:center;color:#536176;font-size:12px;margin:26px 0 10px}@media(max-width:900px){.layout{grid-template-columns:1fr}.sidebar{position:static;height:auto;border-right:0;border-bottom:1px solid #1f2937;display:flex;align-items:center;gap:8px;padding:14px;overflow:auto}.brand{margin:0 10px 0 0;white-space:nowrap}.navitem{display:inline-block;white-space:nowrap;margin:0}.main{padding:24px 16px}.grid{grid-template-columns:repeat(2,1fr)}.exercise-grid{grid-template-columns:1fr}.stat-grid{grid-template-columns:1fr}.big{grid-column:span 2}}@media(max-width:520px){h1{font-size:30px}.hero{align-items:start;flex-direction:column}.grid{grid-template-columns:1fr}.big{grid-column:span 1}.chart{height:260px}.brand{display:none}}
'''


def shell(title, subtitle, active, content, scripts=""):
    return f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · Furkan AI Trainer</title><style>{base_css()}</style></head><body><div class="layout"><aside class="sidebar"><div class="brand">Furkan <span>AI</span> Trainer</div><nav>{nav(active)}</nav></aside><main class="main"><div class="hero"><div><div class="eyebrow">FURKAN AI TRAINER</div><h1>{title}</h1><div class="muted">{subtitle}</div></div><div class="pill">📅 {today()}</div></div>{content}<div class="foot">Telegram kayıtların Supabase ile senkronize edilir.</div></main></div>{scripts}</body></html>'''


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(username: str = Depends(dashboard_auth)):
    try:
        profile = first_profile()
        if not profile:
            return HTMLResponse("<h2>Profil bulunamadı.</h2>", status_code=404)
        user_id = profile["id"]
        goals = get_goals(user_id)
        daily_result = get_daily_log(user_id)
        daily = daily_result.data[0] if daily_result.data else {}
        weight_rows = supabase.table("daily_logs").select("log_date,weight_kg").eq("user_id", user_id).not_.is_("weight_kg", "null").order("log_date", desc=False).limit(30).execute().data or []
        labels = [r["log_date"] for r in weight_rows]
        weights = [float(r["weight_kg"]) for r in weight_rows]
        current = weights[-1] if weights else None
        start = weights[0] if weights else None
        target = float(goals["target_weight_kg"]) if goals.get("target_weight_kg") is not None else None
        remaining = max(0, current-target) if current is not None and target is not None else None
        lost = start-current if current is not None and start is not None else None
        total_goal = start-target if start is not None and target is not None else None
        wp = max(0,min(100,lost/total_goal*100)) if total_goal and lost is not None else 0
        workouts = supabase.table("workouts").select("workout_type,duration_minutes").eq("user_id", user_id).eq("workout_date", today()).execute().data or []
        workout_text = " · ".join(f"{w['workout_type']} {w['duration_minutes']} dk" for w in workouts) if workouts else "Henüz kayıt yok"
        def val(v): return "—" if v is None else v
        def pct(a,g):
            try:return max(0,min(100,float(a or 0)/float(g)*100)) if g else 0
            except:return 0
        content=f'''<div class="grid"><div class="card big"><div class="label">⚖️ KİLO HEDEFİ</div><div class="goalbox"><div class="ring" style="background:conic-gradient(#22c55e {wp:.1f}%,#263246 0)"><b>%{wp:.0f}</b></div><div><div class="num">{val(current)} kg</div><div class="sub">Hedef {val(target)} kg · Kalan {round(remaining,1) if remaining is not None else '—'} kg</div></div></div></div><div class="card"><div class="label">📉 TOPLAM DEĞİŞİM</div><div class="num">{round(lost,1) if lost is not None else '—'} kg</div><div class="sub">İlk kayıttan bugüne</div></div><div class="card"><div class="label">🏋️ BUGÜNKÜ ANTRENMAN</div><div class="num" style="font-size:20px">{workout_text}</div></div><div class="card"><div class="label">🔥 KALORİ</div><div class="num">{val(daily.get('calories'))}</div><div class="sub">/ {val(goals.get('daily_calories'))} kcal</div><div class="bar"><div class="fill" style="width:{pct(daily.get('calories'),goals.get('daily_calories'))}%"></div></div></div><div class="card"><div class="label">🥩 PROTEİN</div><div class="num">{val(daily.get('protein_g'))} g</div><div class="sub">/ {val(goals.get('daily_protein_g'))} g</div><div class="bar"><div class="fill" style="width:{pct(daily.get('protein_g'),goals.get('daily_protein_g'))}%"></div></div></div><div class="card"><div class="label">💧 SU</div><div class="num">{val(daily.get('water_l'))} L</div><div class="sub">/ {val(goals.get('daily_water_l'))} L</div><div class="bar"><div class="fill" style="width:{pct(daily.get('water_l'),goals.get('daily_water_l'))}%"></div></div></div><div class="card"><div class="label">🚶 ADIM</div><div class="num">{val(daily.get('steps'))}</div><div class="sub">/ {val(goals.get('daily_steps'))}</div><div class="bar"><div class="fill" style="width:{pct(daily.get('steps'),goals.get('daily_steps'))}%"></div></div></div></div><div class="section card"><div class="label">📈 KİLO TRENDİ · SON 30 KAYIT</div><div class="chart"><canvas id="weightChart"></canvas></div></div>'''
        scripts=f'''<script src="https://cdn.jsdelivr.net/npm/chart.js"></script><script>new Chart(document.getElementById('weightChart'),{{type:'line',data:{{labels:{json.dumps(labels)},datasets:[{{label:'Kilo (kg)',data:{json.dumps(weights)},borderColor:'#22c55e',backgroundColor:'rgba(34,197,94,.10)',fill:true,tension:.35,pointRadius:4,pointBackgroundColor:'#22c55e'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#aab4c5'}}}}}},scales:{{x:{{ticks:{{color:'#738198'}},grid:{{color:'#1e293b'}}}},y:{{ticks:{{color:'#738198'}},grid:{{color:'#1e293b'}}}}}}}}}});</script>'''
        return HTMLResponse(shell("İlerleme Merkezi","Bugünkü performansın ve hedeflerin tek ekranda.","dashboard",content,scripts))
    except Exception as e:
        print("DASHBOARD ERROR:",e)
        return HTMLResponse("<h2>Dashboard yüklenirken hata oluştu.</h2>",status_code=500)


@app.get("/egzersiz", response_class=HTMLResponse)
async def egzersiz(username: str = Depends(dashboard_auth)):
    days=[
        ("Gün 1","Üst Vücut A","Göğüs · Sırt · Omuz",[("🏋️","Machine Chest Press","Kontrollü tempo","3 × 8–12"),("⬇️","Lat Pulldown","Göğse doğru çek","3 × 8–12"),("↔️","Seated Cable Row","Kürek kemiklerini sık","3 × 10–12"),("⬆️","Machine Shoulder Press","Belini sabit tut","2 × 8–12"),("🪽","Lateral Raise","Hafif ve kontrollü","2 × 12–15"),("💪","Triceps Pushdown","Dirsekler sabit","2 × 10–15"),("💪","Dumbbell Curl","Sallanmadan","2 × 10–15")]),
        ("Gün 2","Alt Vücut A","Bacak · Kalça · Core",[("🦵","Leg Press","Dizleri kilitleme","3 × 10–12"),("🏋️","Romanian Deadlift","Kalçadan menteşe","3 × 8–12"),("🦵","Leg Curl","Yavaş negatif","3 × 10–15"),("🦵","Leg Extension","Kontrollü sıkıştır","2 × 12–15"),("🦶","Calf Raise","Tam hareket açıklığı","3 × 12–15"),("🧱","Plank","Karın sıkı","3 × 30–45 sn")]),
        ("Gün 3","Üst Vücut B","Göğüs · Sırt · Kollar",[("🏋️","Incline Chest Press","Üst göğüs odak","3 × 8–12"),("⬇️","Neutral Grip Pulldown","Dirsekleri aşağı sür","3 × 8–12"),("↔️","Chest Supported Row","Göğüs sabit","3 × 10–12"),("🪽","Cable Lateral Raise","Omuz hizasına kadar","2 × 12–15"),("🔙","Face Pull","Arka omuz odak","2 × 12–15"),("💪","Rope Pushdown","Tam açılma","2 × 10–15"),("💪","Hammer Curl","Nötr tutuş","2 × 10–15")]),
        ("Gün 4","Alt Vücut B","Bacak · Kalça · Kondisyon",[("🦵","Hack Squat / Leg Press","Rahat derinlik","3 × 8–12"),("🍑","Hip Thrust","Üstte sık","3 × 10–12"),("🦵","Leg Curl","Hamstring odak","3 × 10–15"),("🦵","Leg Extension","Son sette kontrollü","2 × 12–15"),("🦶","Calf Raise","Tepe noktada bekle","3 × 12–15"),("🚶","Incline Walk","Konuşabileceğin tempo","15–25 dk")])
    ]
    blocks=[]
    for badge,title,focus,exs in days:
        rows=''.join(f'<div class="exercise"><div class="icon">{ic}</div><div><b>{name}</b><small>{note}</small></div><div class="sets">{sets}</div></div>' for ic,name,note,sets in exs)
        blocks.append(f'<div class="card day"><div class="dayhead"><div><div class="label">{badge}</div><div class="num" style="font-size:23px">{title}</div><div class="sub">{focus}</div></div><span class="badge">60–75 dk</span></div>{rows}</div>')
    content=f'''<div class="card" style="margin-bottom:16px"><div class="label">PROGRAM NOTU</div><div class="num" style="font-size:20px">4 gün ağırlık · kontrollü progresyon</div><div class="sub">Setlerde form bozulmadan hedef tekrar aralığının üstüne çıktığında ağırlığı küçük miktarda artır. İlk 2 hafta failure'a gitme; 2–3 tekrar cepte bırak.</div></div><div class="exercise-grid">{''.join(blocks)}</div>'''
    return HTMLResponse(shell("Egzersiz Planı","Kas koruyup güçlenirken yağ kaybını destekleyen başlangıç düzeni.","egzersiz",content))


@app.get("/istatistik", response_class=HTMLResponse)
async def istatistik(username: str = Depends(dashboard_auth)):
    try:
        profile=first_profile()
        if not profile:return HTMLResponse("<h2>Profil bulunamadı.</h2>",status_code=404)
        uid=profile["id"]
        logs=supabase.table("daily_logs").select("log_date,weight_kg,calories,protein_g,water_l,steps").eq("user_id",uid).order("log_date",desc=False).limit(30).execute().data or []
        workouts=supabase.table("workouts").select("workout_date,duration_minutes").eq("user_id",uid).order("workout_date",desc=False).limit(60).execute().data or []
        weights=[float(x["weight_kg"]) for x in logs if x.get("weight_kg") is not None]
        labels=[x["log_date"] for x in logs if x.get("weight_kg") is not None]
        change=(weights[-1]-weights[0]) if len(weights)>=2 else None
        cals=[float(x["calories"]) for x in logs if x.get("calories") is not None]
        prots=[float(x["protein_g"]) for x in logs if x.get("protein_g") is not None]
        steps=[float(x["steps"]) for x in logs if x.get("steps") is not None]
        avg=lambda arr: round(sum(arr)/len(arr),1) if arr else "—"
        total_minutes=sum(int(x.get("duration_minutes") or 0) for x in workouts)
        rows=''.join(f'<tr><td>{x.get("log_date")}</td><td>{x.get("weight_kg") or "—"}</td><td>{x.get("calories") or "—"}</td><td>{x.get("protein_g") or "—"}</td><td>{x.get("steps") or "—"}</td></tr>' for x in list(reversed(logs[-7:])))
        content=f'''<div class="stat-grid"><div class="card"><div class="label">⚖️ 30 GÜNLÜK KİLO DEĞİŞİMİ</div><div class="num {"positive" if change is not None and change<0 else "warning"}">{round(change,1) if change is not None else '—'} kg</div></div><div class="card"><div class="label">🏋️ ANTRENMAN SAYISI</div><div class="num">{len(workouts)}</div><div class="sub">Toplam {total_minutes} dk</div></div><div class="card"><div class="label">🚶 ORTALAMA ADIM</div><div class="num">{avg(steps)}</div></div><div class="card"><div class="label">🔥 ORTALAMA KALORİ</div><div class="num">{avg(cals)}</div><div class="sub">kcal / kayıtlı gün</div></div><div class="card"><div class="label">🥩 ORTALAMA PROTEİN</div><div class="num">{avg(prots)} g</div></div><div class="card"><div class="label">📅 VERİ GÜNÜ</div><div class="num">{len(logs)}</div><div class="sub">Son 30 kayıt</div></div></div><div class="section card"><div class="label">📈 KİLO ANALİZİ</div><div class="chart"><canvas id="statsChart"></canvas></div></div><div class="section card"><div class="label" style="margin-bottom:8px">SON 7 KAYIT</div><div style="overflow:auto"><table class="table"><thead><tr><th>Tarih</th><th>Kilo</th><th>Kalori</th><th>Protein</th><th>Adım</th></tr></thead><tbody>{rows}</tbody></table></div></div>'''
        scripts=f'''<script src="https://cdn.jsdelivr.net/npm/chart.js"></script><script>new Chart(document.getElementById('statsChart'),{{type:'line',data:{{labels:{json.dumps(labels)},datasets:[{{label:'Kilo (kg)',data:{json.dumps(weights)},borderColor:'#60a5fa',backgroundColor:'rgba(96,165,250,.10)',fill:true,tension:.35,pointRadius:4}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#aab4c5'}}}}}},scales:{{x:{{ticks:{{color:'#738198'}},grid:{{color:'#1e293b'}}}},y:{{ticks:{{color:'#738198'}},grid:{{color:'#1e293b'}}}}}}}}}});</script>'''
        return HTMLResponse(shell("İstatistikler","Son kayıtlarından oluşturulan performans özeti.","istatistik",content,scripts))
    except Exception as e:
        print("STAT ERROR:",e)
        return HTMLResponse("<h2>İstatistikler yüklenirken hata oluştu.</h2>",status_code=500)
