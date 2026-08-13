import os
import json
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
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

PROGRAM = [
    ("Gün 1", "Push", [
        ("Machine Chest Press", "4×10"),
        ("Cable Crossover", "4×12"),
        ("Machine Shoulder Press", "4×10"),
        ("Lateral Raise", "4×10"),
        ("Triceps Pushdown", "4×12"),
    ]),
    ("Gün 2", "Pull", [
        ("Lat Pulldown", "4×10"),
        ("Seated Row", "4×12"),
        ("Reverse Fly", "4×12"),
        ("Dumbbell Curl", "4×10"),
    ]),
    ("Gün 3", "Legs", [
        ("Hack Squat", "4×10"),
        ("Leg Extension", "3×10"),
        ("Leg Curl", "3×10"),
        ("Calf Raise", "3×12"),
    ]),
    ("Gün 4", "Push", [
        ("Incline Dumbbell Press", "4×10"),
        ("Pec Deck", "4×12"),
        ("Machine Shoulder Press", "4×10"),
        ("Lateral Raise", "4×10"),
        ("Triceps Pushdown", "4×12"),
    ]),
    ("Gün 5", "Pull", [
        ("Lat Pulldown", "4×10"),
        ("Seated Row", "4×12"),
        ("Reverse Fly", "4×12"),
        ("Dumbbell Curl", "4×10"),
    ]),
]


def today():
    return datetime.now(TR_TIMEZONE).date().isoformat()


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok = secrets.compare_digest(credentials.username, DASHBOARD_USER) and secrets.compare_digest(credentials.password, DASHBOARD_PASSWORD)
    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})
    return credentials.username


def first_profile():
    r = supabase.table("profiles").select("id,first_name").limit(1).execute()
    return r.data[0] if r.data else None


def get_or_create_user(tg_user):
    r = supabase.table("profiles").select("id").eq("telegram_user_id", tg_user.id).limit(1).execute()
    if r.data:
        return r.data[0]["id"]
    r = supabase.table("profiles").insert({
        "telegram_user_id": tg_user.id,
        "telegram_username": tg_user.username,
        "first_name": tg_user.first_name,
        "last_name": tg_user.last_name,
    }).execute()
    return r.data[0]["id"]


def get_goals(uid):
    r = supabase.table("goals").select("*").eq("user_id", uid).limit(1).execute()
    return r.data[0] if r.data else {}


def get_daily(uid):
    r = supabase.table("daily_logs").select("*").eq("user_id", uid).eq("log_date", today()).limit(1).execute()
    return r.data[0] if r.data else {}


def save_daily(uid, field, value):
    r = supabase.table("daily_logs").select("id").eq("user_id", uid).eq("log_date", today()).limit(1).execute()
    if r.data:
        supabase.table("daily_logs").update({field: value, "updated_at": now_utc()}).eq("id", r.data[0]["id"]).execute()
    else:
        supabase.table("daily_logs").insert({"user_id": uid, "log_date": today(), field: value}).execute()


async def start(update: Update, context):
    get_or_create_user(update.effective_user)
    await update.message.reply_text("🏋️ Furkan AI Trainer aktif!\n\n/kilo 124\n/kalori 2200\n/protein 190\n/su 3.5\n/adim 8000\n/bugun\n/hedef\n/hafta")


async def test(update: Update, context):
    try:
        get_or_create_user(update.effective_user)
        await update.message.reply_text("🟢 SİSTEM ÇALIŞIYOR!\nTelegram ✅\nRender ✅\nSupabase ✅")
    except Exception as e:
        print(e)
        await update.message.reply_text("🔴 Sistem hatası")


async def value_cmd(update, context, field, label, suffix, integer=False):
    try:
        v = int(context.args[0]) if integer else float(context.args[0].replace(",", "."))
        uid = get_or_create_user(update.effective_user)
        save_daily(uid, field, v)
        await update.message.reply_text(f"✅ {label}: {v}{suffix}")
    except Exception:
        await update.message.reply_text(f"⚠️ {label} değeri gir.")


async def kilo(update, context): await value_cmd(update, context, "weight_kg", "Kilo", " kg")
async def kalori(update, context): await value_cmd(update, context, "calories", "Kalori", " kcal", True)
async def protein(update, context): await value_cmd(update, context, "protein_g", "Protein", " g")
async def su(update, context): await value_cmd(update, context, "water_l", "Su", " L")
async def adim(update, context): await value_cmd(update, context, "steps", "Adım", "", True)


async def hedef(update: Update, context):
    uid = get_or_create_user(update.effective_user)
    g = get_goals(uid)
    await update.message.reply_text(f"🎯 Hedefler\n⚖️ {g.get('target_weight_kg','—')} kg\n🔥 {g.get('daily_calories','—')} kcal\n🥩 {g.get('daily_protein_g','—')} g\n💧 {g.get('daily_water_l','—')} L\n🚶 {g.get('daily_steps','—')}")


async def bugun(update: Update, context):
    uid = get_or_create_user(update.effective_user)
    d, g = get_daily(uid), get_goals(uid)
    await update.message.reply_text(f"📊 BUGÜN\n⚖️ {d.get('weight_kg','—')} kg\n🔥 {d.get('calories','—')} / {g.get('daily_calories','—')}\n🥩 {d.get('protein_g','—')} / {g.get('daily_protein_g','—')} g\n💧 {d.get('water_l','—')} / {g.get('daily_water_l','—')} L\n🚶 {d.get('steps','—')} / {g.get('daily_steps','—')}")


async def hafta(update: Update, context):
    uid = get_or_create_user(update.effective_user)
    r = supabase.table("daily_logs").select("log_date,weight_kg").eq("user_id", uid).not_.is_("weight_kg", "null").order("log_date", desc=True).limit(7).execute()
    if not r.data:
        await update.message.reply_text("Henüz kilo kaydı yok.")
        return
    rows = list(reversed(r.data))
    await update.message.reply_text("📈 SON KAYITLAR\n" + "\n".join(f"{x['log_date']} → {x['weight_kg']} kg" for x in rows))


for c,h in [("start",start),("help",start),("test",test),("kilo",kilo),("kalori",kalori),("protein",protein),("su",su),("adim",adim),("hedef",hedef),("bugun",bugun),("hafta",hafta)]:
    telegram_app.add_handler(CommandHandler(c,h))


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


CSS = '''
:root{--bg:#071019;--panel:#0d1724;--panel2:#101d2d;--text:#f7fbff;--muted:#8ea0b5;--line:#203149;--green:#3ddc97;--blue:#68a9ff;--shadow:0 22px 70px rgba(0,0,0,.28);--input:#0a1420;--nav:#09131f;--glass:rgba(255,255,255,.04)}
[data-theme="light"]{--bg:#f4f7fb;--panel:#ffffff;--panel2:#f8fafc;--text:#0f172a;--muted:#64748b;--line:#e2e8f0;--green:#16a36a;--blue:#2563eb;--shadow:0 18px 55px rgba(15,23,42,.10);--input:#f8fafc;--nav:#ffffff;--glass:rgba(15,23,42,.035)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 80% 0%,rgba(59,130,246,.10),transparent 28%),radial-gradient(circle at 20% 10%,rgba(61,220,151,.08),transparent 28%),var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;transition:.25s ease}.layout{display:grid;grid-template-columns:250px 1fr;min-height:100vh}.side{background:color-mix(in srgb,var(--nav) 92%,transparent);border-right:1px solid var(--line);padding:24px 18px;position:sticky;top:0;height:100vh;backdrop-filter:blur(18px)}.brand{font-weight:950;font-size:22px;margin-bottom:28px;letter-spacing:-.04em}.brand b{color:var(--green)}.brand small{display:block;font-size:11px;color:var(--muted);font-weight:700;letter-spacing:.12em;margin-top:4px}.nav a{display:flex;gap:10px;align-items:center;color:var(--muted);text-decoration:none;padding:12px 14px;border-radius:14px;margin:7px 0;font-weight:800;transition:.2s}.nav a:hover,.nav a.on{background:linear-gradient(135deg,color-mix(in srgb,var(--green) 14%,transparent),color-mix(in srgb,var(--blue) 12%,transparent));color:var(--text);transform:translateX(2px)}.themebox{position:absolute;left:18px;right:18px;bottom:20px}.themebtn{width:100%;border:1px solid var(--line);background:var(--panel);color:var(--text);padding:11px 12px;border-radius:14px;font-weight:800;cursor:pointer}.main{padding:34px;max-width:1500px;width:100%;margin:auto}.hero{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:26px}.hero h1{font-size:42px;margin:4px 0 6px;letter-spacing:-.055em}.eyebrow{color:var(--green);font-size:12px;font-weight:950;letter-spacing:.14em}.muted{color:var(--muted)}.tag{background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:9px 12px;color:var(--muted);font-size:12px;font-weight:800}.premium-hero{display:grid;grid-template-columns:1.35fr .65fr;gap:16px;margin-bottom:16px}.hero-card{background:linear-gradient(145deg,color-mix(in srgb,var(--panel) 92%,transparent),var(--panel2));border:1px solid var(--line);border-radius:26px;padding:26px;box-shadow:var(--shadow);position:relative;overflow:hidden}.hero-card:after{content:'';position:absolute;width:280px;height:280px;border-radius:50%;background:radial-gradient(circle,color-mix(in srgb,var(--green) 22%,transparent),transparent 68%);right:-90px;top:-110px}.hero-title{font-size:14px;color:var(--muted);font-weight:900;letter-spacing:.06em}.hero-number{font-size:54px;font-weight:950;letter-spacing:-.06em;margin:12px 0 5px}.hero-sub{color:var(--muted);font-size:14px}.progress-ring{width:150px;height:150px;border-radius:50%;display:grid;place-items:center;margin:auto;position:relative;background:conic-gradient(var(--green) var(--p),var(--line) 0)}.progress-ring:before{content:'';position:absolute;width:118px;height:118px;border-radius:50%;background:var(--panel)}.progress-ring div{position:relative;text-align:center}.progress-ring strong{display:block;font-size:28px}.progress-ring span{font-size:11px;color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:15px}.card{background:linear-gradient(145deg,var(--panel),var(--panel2));border:1px solid var(--line);border-radius:22px;padding:20px;box-shadow:var(--shadow);transition:.2s}.card:hover{transform:translateY(-2px)}.label{font-size:12px;color:var(--muted);font-weight:900;letter-spacing:.05em}.num{font-size:31px;font-weight:950;margin-top:8px;letter-spacing:-.045em}.bar{height:9px;background:var(--line);border-radius:99px;overflow:hidden;margin-top:14px}.fill{height:100%;background:linear-gradient(90deg,var(--green),var(--blue));border-radius:99px}.section{margin-top:16px}.chart{height:340px}.split{display:grid;grid-template-columns:1.3fr .7fr;gap:16px}.mini-list{display:grid;gap:10px;margin-top:14px}.mini{display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid var(--line)}.mini:last-child{border-bottom:0}.mini b{font-size:13px}.mini span{font-size:12px;color:var(--muted)}.days{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}.day{position:relative;overflow:hidden}.day:before{content:'';height:4px;position:absolute;inset:0 0 auto;background:linear-gradient(90deg,var(--green),var(--blue))}.day h2{margin:8px 0 2px}.ex{padding:14px 0;border-bottom:1px solid var(--line)}.ex:last-child{border:0}.exhead{display:flex;justify-content:space-between;gap:15px}.track{display:grid;grid-template-columns:1fr 1fr auto;gap:8px;margin-top:10px}.track input{width:100%;background:var(--input);border:1px solid var(--line);color:var(--text);border-radius:11px;padding:10px}.track button{border:0;background:linear-gradient(135deg,var(--green),var(--blue));color:white;font-weight:950;border-radius:11px;padding:10px 13px;cursor:pointer}.pr{font-size:12px;color:#eab308;margin-top:7px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}.toast{position:fixed;right:20px;bottom:20px;background:var(--panel);border:1px solid var(--line);padding:13px 16px;border-radius:12px;display:none;box-shadow:var(--shadow)}.table{width:100%;border-collapse:collapse}.table th,.table td{text-align:left;padding:12px;border-bottom:1px solid var(--line);font-size:13px}.table th{color:var(--muted)}
@media(max-width:1000px){.premium-hero,.split{grid-template-columns:1fr}.grid{grid-template-columns:repeat(2,1fr)}.days{grid-template-columns:1fr}.stats{grid-template-columns:1fr}}
@media(max-width:850px){.layout{grid-template-columns:1fr}.side{position:static;height:auto;display:flex;align-items:center;gap:8px;overflow:auto}.brand{margin:0 12px 0 0;white-space:nowrap}.brand small{display:none}.nav{display:flex}.nav a{white-space:nowrap;margin:0}.themebox{position:static;margin-left:auto}.themebtn{white-space:nowrap}.main{padding:22px 14px}.hero h1{font-size:34px}}
@media(max-width:520px){.grid{grid-template-columns:1fr}.hero{align-items:start;flex-direction:column}.hero-number{font-size:44px}.track{grid-template-columns:1fr 1fr}.track button{grid-column:span 2}.brand{display:none}.themebox{margin-left:0}}
'''


def nav(active):
    items=[("dashboard","⌂ Genel","/dashboard"),("egzersiz","🏋 Egzersiz","/egzersiz"),("istatistik","◒ İstatistik","/istatistik")]
    return ''.join(f'<a class="{"on" if active==k else ""}" href="{u}">{n}</a>' for k,n,u in items)


def theme_script(extra=''):
    return f'''<script>
(function(){{const saved=localStorage.getItem('fitness-theme')||'dark';document.documentElement.setAttribute('data-theme',saved);updateThemeText();}})();
function toggleTheme(){{const cur=document.documentElement.getAttribute('data-theme')||'dark';const next=cur==='dark'?'light':'dark';document.documentElement.setAttribute('data-theme',next);localStorage.setItem('fitness-theme',next);updateThemeText();}}
function updateThemeText(){{const b=document.getElementById('themeBtn');if(!b)return;const t=document.documentElement.getAttribute('data-theme');b.innerText=t==='dark'?'☀️ Açık moda geç':'🌙 Koyu moda geç';}}
{extra}
</script>'''


def shell(title, sub, active, body, scripts=''):
    return f'''<!doctype html><html lang="tr" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark light"><title>{title}</title><style>{CSS}</style></head><body><div class="layout"><aside class="side"><div class="brand">Furkan <b>AI</b> Trainer<small>PERFORMANCE SYSTEM</small></div><div class="nav">{nav(active)}</div><div class="themebox"><button class="themebtn" id="themeBtn" onclick="toggleTheme()">Tema</button></div></aside><main class="main"><div class="hero"><div><div class="eyebrow">FURKAN AI TRAINER</div><h1>{title}</h1><div class="muted">{sub}</div></div><div class="tag">📅 {today()}</div></div>{body}</main></div><div class="toast" id="toast"></div>{scripts}{theme_script()}</body></html>'''


@app.get("/")
async def home():
    return {"status":"online","version":"v3-premium"}


def exercise_history(uid):
    rows=supabase.table("workouts").select("workout_date,workout_type,notes").eq("user_id",uid).order("workout_date",desc=True).limit(500).execute().data or []
    prs={}; today_done={}
    for r in rows:
        if not str(r.get("workout_type","")).startswith("EXERCISE:"):
            continue
        name=r["workout_type"][9:]
        try:data=json.loads(r.get("notes") or "{}")
        except:data={}
        w=float(data.get("weight") or 0)
        if w>prs.get(name,0):prs[name]=w
        if r.get("workout_date")==today() and name not in today_done:today_done[name]=data
    return prs,today_done


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(user=Depends(auth)):
    p=first_profile()
    if not p:return HTMLResponse("Profil yok",404)
    uid=p["id"]; d=get_daily(uid); g=get_goals(uid)
    wr=supabase.table("daily_logs").select("log_date,weight_kg,calories,protein_g,water_l,steps").eq("user_id",uid).order("log_date",desc=False).limit(30).execute().data or []
    labels=[x["log_date"] for x in wr if x.get("weight_kg") is not None]
    weights=[float(x["weight_kg"]) for x in wr if x.get("weight_kg") is not None]
    current=weights[-1] if weights else None
    start_w=weights[0] if weights else None
    target=float(g["target_weight_kg"]) if g.get("target_weight_kg") else None
    lost=(start_w-current) if start_w is not None and current is not None else 0
    total=(start_w-target) if start_w is not None and target is not None else 0
    progress=max(0,min(100,(lost/total*100))) if total and total>0 else 0
    remaining=max(0,current-target) if current is not None and target is not None else None
    def pct(a,b):
        try:return min(100,max(0,float(a or 0)/float(b)*100)) if b else 0
        except:return 0
    prs,done=exercise_history(uid)
    completed_today=len(done)
    weekday=datetime.now(TR_TIMEZONE).weekday()
    next_idx=min(weekday,4)
    next_day,next_title,next_ex=PROGRAM[next_idx]
    cards=[
        ("🔥 KALORİ",d.get('calories','—'),f"/ {g.get('daily_calories','—')} kcal",pct(d.get('calories'),g.get('daily_calories'))),
        ("🥩 PROTEİN",f"{d.get('protein_g','—')} g",f"/ {g.get('daily_protein_g','—')} g",pct(d.get('protein_g'),g.get('daily_protein_g'))),
        ("💧 SU",f"{d.get('water_l','—')} L",f"/ {g.get('daily_water_l','—')} L",pct(d.get('water_l'),g.get('daily_water_l'))),
        ("🚶 ADIM",d.get('steps','—'),f"/ {g.get('daily_steps','—')}",pct(d.get('steps'),g.get('daily_steps'))),
    ]
    card_html=''.join(f'<div class="card"><div class="label">{a}</div><div class="num">{b}</div><div class="muted">{c}</div><div class="bar"><div class="fill" style="width:{q}%"></div></div></div>' for a,b,c,q in cards)
    next_list=''.join(f'<div class="mini"><div><b>{n}</b><span>{s}</span></div><span>→</span></div>' for n,s in next_ex[:4])
    body=f'''<div class="premium-hero"><div class="hero-card"><div class="hero-title">MEVCUT KİLO</div><div class="hero-number">{current if current is not None else '—'} <span style="font-size:22px">kg</span></div><div class="hero-sub">Hedef {target if target is not None else '—'} kg · Kalan {round(remaining,1) if remaining is not None else '—'} kg · Toplam değişim {round(lost,1) if weights else '—'} kg</div></div><div class="hero-card"><div class="progress-ring" style="--p:{progress:.1f}%"><div><strong>%{progress:.0f}</strong><span>hedef ilerlemesi</span></div></div></div></div><div class="grid">{card_html}</div><div class="split section"><div class="card"><div class="label">📈 KİLO TRENDİ · SON 30 KAYIT</div><div class="chart"><canvas id="weightChart"></canvas></div></div><div class="card"><div class="label">🏋️ BUGÜNÜN ODAĞI</div><div class="num" style="font-size:24px">{next_day} · {next_title}</div><div class="muted">Bugün tamamlanan hareket: {completed_today}</div><div class="mini-list">{next_list}</div><a href="/egzersiz" style="display:inline-block;margin-top:14px;color:var(--green);font-weight:900;text-decoration:none">Egzersize git →</a></div></div>'''
    chart=f'''<script src="https://cdn.jsdelivr.net/npm/chart.js"></script><script>new Chart(document.getElementById('weightChart'),{{type:'line',data:{{labels:{json.dumps(labels)},datasets:[{{label:'Kilo (kg)',data:{json.dumps(weights)},borderColor:'#3ddc97',backgroundColor:'rgba(61,220,151,.12)',fill:true,tension:.35,pointRadius:4,pointBackgroundColor:'#3ddc97'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#8796a8'}}}}}},scales:{{x:{{ticks:{{color:'#8796a8'}},grid:{{color:'rgba(120,130,150,.12)'}}}},y:{{ticks:{{color:'#8796a8'}},grid:{{color:'rgba(120,130,150,.12)'}}}}}}}}}});</script>'''
    return HTMLResponse(shell("İlerleme Merkezi","Günün verileri, hedef ilerlemen ve antrenman odağın tek ekranda.","dashboard",body,chart))


@app.post("/api/exercise/log")
async def log_exercise(request:Request,user=Depends(auth)):
    p=first_profile()
    if not p:return JSONResponse({"ok":False},404)
    data=await request.json(); name=str(data.get("exercise","")).strip(); day=str(data.get("day","")).strip()
    try:weight=float(data.get("weight") or 0); reps=int(data.get("reps") or 0)
    except:return JSONResponse({"ok":False,"error":"Geçersiz değer"},400)
    if not name or reps<1 or weight<0:return JSONResponse({"ok":False,"error":"Eksik değer"},400)
    old_pr,_=exercise_history(p["id"]); is_pr=weight>old_pr.get(name,0)
    notes=json.dumps({"day":day,"weight":weight,"reps":reps,"completed":True,"pr":is_pr},ensure_ascii=False)
    supabase.table("workouts").insert({"user_id":p["id"],"workout_date":today(),"workout_type":"EXERCISE:"+name,"notes":notes}).execute()
    return {"ok":True,"pr":is_pr,"best":max(weight,old_pr.get(name,0))}


@app.get("/egzersiz",response_class=HTMLResponse)
async def egzersiz(user=Depends(auth)):
    p=first_profile(); uid=p["id"] if p else None
    prs,done=exercise_history(uid) if uid else ({},{})
    blocks=[]
    for day,title,exercises in PROGRAM:
        rows=[]
        for name,sets in exercises:
            d=done.get(name,{}); completed='✓ Bugün tamamlandı' if d else ''; pr=prs.get(name)
            rows.append(f'''<div class="ex"><div class="exhead"><div><b>{name}</b><div class="muted" style="font-size:12px;margin-top:3px;color:var(--green)">{completed}</div></div><span class="tag">{sets}</span></div><div class="track"><input id="w-{day}-{name}" type="number" step="0.5" placeholder="Kilo (kg)" value="{d.get('weight','') if d else ''}"><input id="r-{day}-{name}" type="number" placeholder="Tekrar" value="{d.get('reps','') if d else ''}"><button onclick='saveExercise({json.dumps(day)},{json.dumps(name)})'>Kaydet ✓</button></div><div class="pr">🏆 PR: {pr if pr is not None else 'Henüz yok'} kg</div></div>''')
        blocks.append(f'<div class="card day"><div class="label">{day}</div><h2>{title}</h2><div class="muted">Programındaki hareketler</div>{"".join(rows)}</div>')
    js='''<script>async function saveExercise(day,name){const w=document.getElementById('w-'+day+'-'+name).value;const r=document.getElementById('r-'+day+'-'+name).value;const res=await fetch('/api/exercise/log',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({day:day,exercise:name,weight:w,reps:r})});const j=await res.json();const t=document.getElementById('toast');t.style.display='block';t.innerText=j.ok?(j.pr?'🏆 Yeni PR! Kaydedildi.':'✅ Kaydedildi.'):'❌ '+(j.error||'Hata');setTimeout(()=>location.reload(),900)}</script>'''
    return HTMLResponse(shell("Egzersiz Planı","5 günlük programın · kilo, tekrar, tamamlandı ve PR takibi.","egzersiz",f'<div class="days">{"".join(blocks)}</div>',js))


@app.get("/istatistik",response_class=HTMLResponse)
async def istatistik(user=Depends(auth)):
    p=first_profile()
    if not p:return HTMLResponse("Profil yok",404)
    uid=p["id"]
    logs=supabase.table("daily_logs").select("log_date,weight_kg,calories,protein_g,water_l,steps").eq("user_id",uid).order("log_date",desc=False).limit(30).execute().data or []
    ex=supabase.table("workouts").select("workout_date,workout_type,notes").eq("user_id",uid).order("workout_date",desc=True).limit(500).execute().data or []
    weights=[float(x['weight_kg']) for x in logs if x.get('weight_kg') is not None]; labels=[x['log_date'] for x in logs if x.get('weight_kg') is not None]
    change=round(weights[-1]-weights[0],1) if len(weights)>1 else '—'
    cals=[float(x['calories']) for x in logs if x.get('calories') is not None]; prots=[float(x['protein_g']) for x in logs if x.get('protein_g') is not None]; steps=[float(x['steps']) for x in logs if x.get('steps') is not None]
    avg=lambda a:round(sum(a)/len(a),1) if a else '—'
    completed=sum(1 for x in ex if str(x.get('workout_type','')).startswith('EXERCISE:'))
    pr_count=0
    for x in ex:
        try:
            if json.loads(x.get('notes') or '{}').get('pr'):pr_count+=1
        except:pass
    cards=[("⚖️ Kilo değişimi",f"{change} kg"),("🔥 Ort. kalori",avg(cals)),("🥩 Ort. protein",f"{avg(prots)} g"),("🚶 Ort. adım",avg(steps)),("✅ Hareket kaydı",completed),("🏆 PR sayısı",pr_count)]
    top=''.join(f'<div class="card"><div class="label">{a}</div><div class="num">{b}</div></div>' for a,b in cards)
    rows=''.join(f'<tr><td>{x.get("log_date")}</td><td>{x.get("weight_kg") or "—"}</td><td>{x.get("calories") or "—"}</td><td>{x.get("protein_g") or "—"}</td><td>{x.get("steps") or "—"}</td></tr>' for x in reversed(logs[-7:]))
    body=f'<div class="stats">{top}</div><div class="card section"><div class="label">📈 KİLO ANALİZİ</div><div class="chart"><canvas id="s"></canvas></div></div><div class="card section"><table class="table"><thead><tr><th>Tarih</th><th>Kilo</th><th>Kalori</th><th>Protein</th><th>Adım</th></tr></thead><tbody>{rows}</tbody></table></div>'
    scripts=f'''<script src="https://cdn.jsdelivr.net/npm/chart.js"></script><script>new Chart(document.getElementById('s'),{{type:'line',data:{{labels:{json.dumps(labels)},datasets:[{{label:'Kilo',data:{json.dumps(weights)},borderColor:'#68a9ff',backgroundColor:'rgba(104,169,255,.12)',fill:true,tension:.35}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#8796a8'}}}}}},scales:{{x:{{ticks:{{color:'#8796a8'}},grid:{{color:'rgba(120,130,150,.12)'}}}},y:{{ticks:{{color:'#8796a8'}},grid:{{color:'rgba(120,130,150,.12)'}}}}}}}}}});</script>'''
    return HTMLResponse(shell("İstatistikler","Kilo, beslenme ve egzersiz performansın.","istatistik",body,scripts))
