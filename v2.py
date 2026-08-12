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
    text = "📈 SON KAYITLAR\n" + "\n".join(f"{x['log_date']} → {x['weight_kg']} kg" for x in rows)
    await update.message.reply_text(text)


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
*{box-sizing:border-box}body{margin:0;background:#060a12;color:#f8fafc;font-family:Inter,system-ui,sans-serif}.layout{display:grid;grid-template-columns:230px 1fr;min-height:100vh}.side{background:#0a101a;border-right:1px solid #1d2939;padding:24px 16px}.brand{font-weight:900;font-size:21px;margin-bottom:28px}.brand b{color:#22c55e}.nav a{display:block;color:#8e9aaf;text-decoration:none;padding:12px 14px;border-radius:12px;margin:5px 0;font-weight:700}.nav a:hover,.nav a.on{background:#162033;color:white}.main{padding:32px;max-width:1450px;width:100%;margin:auto}.hero{display:flex;justify-content:space-between;align-items:end;margin-bottom:24px}.hero h1{font-size:38px;margin:4px 0;letter-spacing:-.04em}.green{color:#22c55e}.muted{color:#8190a6}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:15px}.card{background:linear-gradient(145deg,#111a29,#0d1420);border:1px solid #202d42;border-radius:20px;padding:20px;box-shadow:0 18px 45px #0005}.label{font-size:12px;color:#8e9aaf;font-weight:800}.num{font-size:30px;font-weight:900;margin-top:8px}.bar{height:8px;background:#263246;border-radius:99px;overflow:hidden;margin-top:14px}.fill{height:100%;background:linear-gradient(90deg,#22c55e,#3b82f6)}.section{margin-top:16px}.chart{height:340px}.days{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}.day{position:relative;overflow:hidden}.day:before{content:'';height:4px;position:absolute;inset:0 0 auto;background:linear-gradient(90deg,#22c55e,#3b82f6)}.day h2{margin:8px 0 2px}.ex{padding:14px 0;border-bottom:1px solid #1d2939}.ex:last-child{border:0}.exhead{display:flex;justify-content:space-between;gap:15px}.tag{background:#172236;border:1px solid #2a3953;border-radius:999px;padding:5px 9px;font-size:12px;color:#bac4d3}.track{display:grid;grid-template-columns:1fr 1fr auto;gap:8px;margin-top:10px}.track input{width:100%;background:#0a111d;border:1px solid #2a3850;color:white;border-radius:10px;padding:9px}.track button{border:0;background:#22c55e;color:#041009;font-weight:900;border-radius:10px;padding:9px 12px;cursor:pointer}.pr{font-size:12px;color:#fbbf24;margin-top:7px}.done{color:#22c55e;font-weight:800}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}.toast{position:fixed;right:20px;bottom:20px;background:#162033;border:1px solid #2a3953;padding:13px 16px;border-radius:12px;display:none}.table{width:100%;border-collapse:collapse}.table th,.table td{text-align:left;padding:12px;border-bottom:1px solid #1d2939;font-size:13px}.table th{color:#7f8ca1}@media(max-width:850px){.layout{grid-template-columns:1fr}.side{display:flex;gap:8px;overflow:auto}.brand{margin:7px 10px 0 0;white-space:nowrap}.nav{display:flex}.nav a{white-space:nowrap}.main{padding:22px 14px}.grid{grid-template-columns:repeat(2,1fr)}.days{grid-template-columns:1fr}.stats{grid-template-columns:1fr}}@media(max-width:520px){.grid{grid-template-columns:1fr}.hero{align-items:start;flex-direction:column}.hero h1{font-size:30px}.track{grid-template-columns:1fr 1fr}.track button{grid-column:span 2}}
'''


def nav(active):
    items=[("dashboard","Genel","/dashboard"),("egzersiz","Egzersiz","/egzersiz"),("istatistik","İstatistik","/istatistik")]
    return ''.join(f'<a class="{"on" if active==k else ""}" href="{u}">{n}</a>' for k,n,u in items)


def shell(title, sub, active, body, scripts=''):
    return f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{CSS}</style></head><body><div class="layout"><aside class="side"><div class="brand">Furkan <b>AI</b> Trainer</div><div class="nav">{nav(active)}</div></aside><main class="main"><div class="hero"><div><div class="green" style="font-size:12px;font-weight:900;letter-spacing:.12em">FURKAN AI TRAINER</div><h1>{title}</h1><div class="muted">{sub}</div></div><div class="tag">📅 {today()}</div></div>{body}</main></div><div class="toast" id="toast"></div>{scripts}</body></html>'''


@app.get("/")
async def home():
    return {"status":"online","version":"v2"}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(user=Depends(auth)):
    p=first_profile()
    if not p:return HTMLResponse("Profil yok",404)
    uid=p["id"]; d=get_daily(uid); g=get_goals(uid)
    wr=supabase.table("daily_logs").select("log_date,weight_kg").eq("user_id",uid).not_.is_("weight_kg","null").order("log_date",desc=False).limit(30).execute().data or []
    labels=[x["log_date"] for x in wr]; weights=[float(x["weight_kg"]) for x in wr]
    current=weights[-1] if weights else None; target=float(g["target_weight_kg"]) if g.get("target_weight_kg") else None
    def pct(a,b):
        try:return min(100,max(0,float(a or 0)/float(b)*100)) if b else 0
        except:return 0
    cards=[("⚖️ Kilo",f"{current if current is not None else '—'} kg",f"Hedef {target if target else '—'} kg",0),("🔥 Kalori",d.get('calories','—'),f"/ {g.get('daily_calories','—')} kcal",pct(d.get('calories'),g.get('daily_calories'))),("🥩 Protein",f"{d.get('protein_g','—')} g",f"/ {g.get('daily_protein_g','—')} g",pct(d.get('protein_g'),g.get('daily_protein_g'))),("💧 Su",f"{d.get('water_l','—')} L",f"/ {g.get('daily_water_l','—')} L",pct(d.get('water_l'),g.get('daily_water_l'))),("🚶 Adım",d.get('steps','—'),f"/ {g.get('daily_steps','—')}",pct(d.get('steps'),g.get('daily_steps')))]
    html=''.join(f'<div class="card"><div class="label">{a}</div><div class="num">{b}</div><div class="muted">{c}</div>{f"<div class=bar><div class=fill style=width:{q}%></div></div>" if q else ""}</div>' for a,b,c,q in cards)
    body=f'<div class="grid">{html}</div><div class="card section"><div class="label">📈 KİLO TRENDİ</div><div class="chart"><canvas id="c"></canvas></div></div>'
    scripts=f'''<script src="https://cdn.jsdelivr.net/npm/chart.js"></script><script>new Chart(document.getElementById('c'),{{type:'line',data:{{labels:{json.dumps(labels)},datasets:[{{label:'Kilo',data:{json.dumps(weights)},borderColor:'#22c55e',backgroundColor:'rgba(34,197,94,.12)',fill:true,tension:.35}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#aaa'}}}}}},scales:{{x:{{ticks:{{color:'#777'}}}},y:{{ticks:{{color:'#777'}}}}}}}}}});</script>'''
    return HTMLResponse(shell("İlerleme Merkezi","Günlük hedeflerin ve kilo trendin.","dashboard",body,scripts))


def exercise_history(uid):
    rows=supabase.table("workouts").select("workout_date,workout_type,notes").eq("user_id",uid).order("workout_date",desc=True).limit(500).execute().data or []
    prs={}; today_done={}
    for r in rows:
        if not str(r.get("workout_type","")).startswith("EXERCISE:"):continue
        name=r["workout_type"][9:]
        try:data=json.loads(r.get("notes") or "{}")
        except:data={}
        w=float(data.get("weight") or 0); reps=int(data.get("reps") or 0)
        if w>prs.get(name,0):prs[name]=w
        if r.get("workout_date")==today() and name not in today_done:today_done[name]=data
    return prs,today_done


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
            rows.append(f'''<div class="ex"><div class="exhead"><div><b>{name}</b><div class="muted" style="font-size:12px;margin-top:3px">{completed}</div></div><span class="tag">{sets}</span></div><div class="track"><input id="w-{day}-{name}" type="number" step="0.5" placeholder="Kilo (kg)" value="{d.get('weight','') if d else ''}"><input id="r-{day}-{name}" type="number" placeholder="Tekrar" value="{d.get('reps','') if d else ''}"><button onclick='saveExercise({json.dumps(day)},{json.dumps(name)})'>Kaydet ✓</button></div><div class="pr">🏆 PR: {pr if pr is not None else 'Henüz yok'} kg</div></div>''')
        blocks.append(f'<div class="card day"><div class="label">{day}</div><h2>{title}</h2><div class="muted">Görseldeki programın</div>{"".join(rows)}</div>')
    js='''<script>async function saveExercise(day,name){const w=document.getElementById('w-'+day+'-'+name).value;const r=document.getElementById('r-'+day+'-'+name).value;const res=await fetch('/api/exercise/log',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({day:day,exercise:name,weight:w,reps:r})});const j=await res.json();const t=document.getElementById('toast');t.style.display='block';t.innerText=j.ok?(j.pr?'🏆 Yeni PR! Kaydedildi.':'✅ Kaydedildi.'):'❌ '+(j.error||'Hata');setTimeout(()=>location.reload(),900)}</script>'''
    return HTMLResponse(shell("Egzersiz Planı","Gönderdiğin 5 günlük program · kilo, tekrar ve PR takibi.","egzersiz",f'<div class="days">{"".join(blocks)}</div>',js))


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
    scripts=f'''<script src="https://cdn.jsdelivr.net/npm/chart.js"></script><script>new Chart(document.getElementById('s'),{{type:'line',data:{{labels:{json.dumps(labels)},datasets:[{{label:'Kilo',data:{json.dumps(weights)},borderColor:'#60a5fa',backgroundColor:'rgba(96,165,250,.12)',fill:true,tension:.35}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#aaa'}}}}}},scales:{{x:{{ticks:{{color:'#777'}}}},y:{{ticks:{{color:'#777'}}}}}}}}}});</script>'''
    return HTMLResponse(shell("İstatistikler","Kilo, beslenme ve egzersiz performansın.","istatistik",body,scripts))
