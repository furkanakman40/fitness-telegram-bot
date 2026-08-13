import json
from datetime import datetime, timedelta

from fastapi import Depends
from fastapi.responses import HTMLResponse

from v2 import *

# Replace only the main dashboard. Exercise/statistics pages and Telegram bot remain from v2.
app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/dashboard"]

MOTIVATIONS = [
    "Bugün mükemmel olmak zorunda değilsin. Planı tamamlaman yeterli.",
    "Vücudun bir günde değişmez; ama verdiğin her doğru karar yönünü değiştirir.",
    "Motivasyon geçicidır. Seni hedefe götürecek şey tekrar tekrar yaptığın doğru seçimlerdir.",
    "Bugünkü antrenman gelecekteki haline verdiğin bir söz.",
    "Hız değil, devamlılık. Bugünü kazan ve yarını sonra düşün.",
    "Bir kötü öğün planı bozmaz. Bir kötü günü haftaya çevirmemek asıl başarıdır.",
    "Kendinle yarışıyorsun. Dünkü halinden biraz daha iyi olman yeterli.",
    "Zorlandığın günler sonuçların en çok inşa edildiği günlerdir.",
    "Disiplin, canın istemediğinde de hedefini hatırlamaktır.",
    "Her kaydettiğin kilo, her tamamladığın set ve her yürüyüş toplamda büyük fark yaratacak.",
    "Bugün yapacağın küçük iş, bir ay sonraki aynada büyük görünür.",
    "Hedef uzakta olabilir; bugünün görevi sadece bir sonraki doğru adım.",
    "Başlamak heyecan ister, devam etmek karakter. Bugün devam et.",
    "Tartı tek bir günün hükmü değil. Trend senin gerçek hikâyen.",
    "Güçlenirken hafifliyorsun. İkisini de sabırla inşa et.",
]


def moving_average(values, window=7):
    out = []
    for i in range(len(values)):
        chunk = values[max(0, i - window + 1):i + 1]
        out.append(round(sum(chunk) / len(chunk), 2))
    return out


def daily_score(d, g, completed_today):
    parts = []
    for field, goal_field in [
        ("calories", "daily_calories"),
        ("protein_g", "daily_protein_g"),
        ("water_l", "daily_water_l"),
        ("steps", "daily_steps"),
    ]:
        actual = d.get(field)
        goal = g.get(goal_field)
        if actual is None or not goal:
            parts.append(0)
            continue
        a, target = float(actual), float(goal)
        if field == "calories":
            # Full credit inside roughly ±10%, then taper down.
            ratio = a / target
            points = 100 if 0.90 <= ratio <= 1.10 else max(0, 100 - abs(1 - ratio) * 180)
        else:
            points = min(100, a / target * 100)
        parts.append(points)
    nutrition = sum(parts) / len(parts) if parts else 0
    workout = 100 if completed_today > 0 else 0
    # Daily fundamentals 80%, exercise completion 20%.
    return round(nutrition * 0.8 + workout * 0.2)


def calculate_streak(logs):
    active = set()
    for row in logs:
        if any(row.get(k) is not None for k in ["weight_kg", "calories", "protein_g", "water_l", "steps"]):
            active.add(row.get("log_date"))
    streak = 0
    cursor = datetime.now(TR_TIMEZONE).date()
    while cursor.isoformat() in active:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def motivation_for_day(score, completed_today, weight_delta):
    date_key = int(datetime.now(TR_TIMEZONE).strftime("%Y%m%d"))
    base = MOTIVATIONS[date_key % len(MOTIVATIONS)]
    if completed_today > 0 and score >= 80:
        lead = "Bugün işi ciddiye aldın. "
    elif score >= 70:
        lead = "İyi bir gün inşa ediyorsun. "
    elif weight_delta is not None and weight_delta < 0:
        lead = "Trend doğru yönde. "
    elif score < 35:
        lead = "Bugün hâlâ çevrilebilir. Bir hedef seç ve onu tamamla. "
    else:
        lead = "Planın senden kusursuzluk değil, devamlılık istiyor. "
    return lead + base


def coach_message(d, g, score, avg7, current, completed_today):
    notes = []
    protein = d.get("protein_g")
    pgoal = g.get("daily_protein_g")
    water = d.get("water_l")
    wgoal = g.get("daily_water_l")
    steps = d.get("steps")
    sgoal = g.get("daily_steps")
    calories = d.get("calories")
    cgoal = g.get("daily_calories")

    if protein is not None and pgoal and float(protein) < float(pgoal) * .8:
        notes.append("Protein hedefinin gerisindesin; kalan öğünlerde proteini öne al.")
    if water is not None and wgoal and float(water) < float(wgoal) * .65:
        notes.append("Su düşük gidiyor; günün kalanına yayarak tamamla.")
    if steps is not None and sgoal and float(steps) < float(sgoal) * .6:
        notes.append("Adım hedefin geride; kısa bir yürüyüş günü ciddi biçimde toparlar.")
    if calories is not None and cgoal and float(calories) > float(cgoal) * 1.15:
        notes.append("Kalori hedefini aşmışsın; telafi için aç kalma, sonraki öğünü normale döndür.")
    if completed_today > 0:
        notes.append("Antrenmanı kaydetmişsin; bugün toparlanma, protein ve uyku önemli.")
    if current is not None and avg7 is not None and current > avg7 + 1:
        notes.append("Bugünkü tartı 7 günlük ortalamanın üstünde; tek ölçüye değil trende bak.")
    if not notes:
        if score >= 80:
            notes.append("Bugünkü temel hedefler güçlü gidiyor. Sistemi değiştirme; aynı düzeni tekrarla.")
        else:
            notes.append("Bugün puanı yükseltmenin en kolay yolu eksik kalan su, protein veya adım hedeflerinden birini tamamlamak.")
    return " ".join(notes[:2])


@app.get("/dashboard", response_class=HTMLResponse)
async def smart_dashboard(user=Depends(auth)):
    p = first_profile()
    if not p:
        return HTMLResponse("Profil yok", 404)

    uid = p["id"]
    first_name = p.get("first_name") or "Furkan"
    d = get_daily(uid)
    g = get_goals(uid)

    logs = (
        supabase.table("daily_logs")
        .select("log_date,weight_kg,calories,protein_g,water_l,steps")
        .eq("user_id", uid)
        .order("log_date", desc=False)
        .limit(60)
        .execute().data or []
    )

    weight_rows = [x for x in logs if x.get("weight_kg") is not None]
    labels = [x["log_date"] for x in weight_rows]
    weights = [float(x["weight_kg"]) for x in weight_rows]
    avg7 = moving_average(weights, 7)

    current = weights[-1] if weights else None
    previous = weights[-2] if len(weights) > 1 else None
    weight_delta = current - previous if current is not None and previous is not None else None
    avg7_current = avg7[-1] if avg7 else None
    start_w = weights[0] if weights else None
    target = float(g["target_weight_kg"]) if g.get("target_weight_kg") else None
    lost = start_w - current if start_w is not None and current is not None else None
    total = start_w - target if start_w is not None and target is not None else None
    progress = max(0, min(100, lost / total * 100)) if total and total > 0 and lost is not None else 0
    remaining = max(0, current - target) if current is not None and target is not None else None

    prs, done = exercise_history(uid)
    completed_today = len(done)
    score = daily_score(d, g, completed_today)
    streak = calculate_streak(logs)
    motivation = motivation_for_day(score, completed_today, weight_delta)
    coach = coach_message(d, g, score, avg7_current, current, completed_today)

    weekday = datetime.now(TR_TIMEZONE).weekday()
    if weekday <= 4:
        plan_day, plan_title, plan_exercises = PROGRAM[weekday]
        plan_note = "Bugünkü plan"
    else:
        plan_day, plan_title, plan_exercises = ("Toparlanma", "Aktif Dinlenme", [("Yürüyüş", "30–45 dk"), ("Mobilite", "10 dk")])
        plan_note = "Hafta sonu odağı"

    def pct(a, b):
        try:
            return min(100, max(0, float(a or 0) / float(b) * 100)) if b else 0
        except Exception:
            return 0

    cards = [
        ("🔥 KALORİ", d.get("calories", "—"), f"/ {g.get('daily_calories','—')} kcal", pct(d.get("calories"), g.get("daily_calories"))),
        ("🥩 PROTEİN", f"{d.get('protein_g','—')} g", f"/ {g.get('daily_protein_g','—')} g", pct(d.get("protein_g"), g.get("daily_protein_g"))),
        ("💧 SU", f"{d.get('water_l','—')} L", f"/ {g.get('daily_water_l','—')} L", pct(d.get("water_l"), g.get("daily_water_l"))),
        ("🚶 ADIM", d.get("steps", "—"), f"/ {g.get('daily_steps','—')}", pct(d.get("steps"), g.get("daily_steps"))),
    ]
    card_html = ''.join(
        f'<div class="card"><div class="label">{a}</div><div class="num">{b}</div><div class="muted">{c}</div><div class="bar"><div class="fill" style="width:{q}%"></div></div></div>'
        for a, b, c, q in cards
    )
    focus = ''.join(f'<div class="mini"><div><b>{n}</b><span>{s}</span></div><span>→</span></div>' for n, s in plan_exercises[:5])

    body = f'''
    <div class="motivation-card">
      <div class="motivation-icon">✦</div>
      <div><div class="label">BUGÜNÜN MESAJI</div><div class="motivation-text">{motivation}</div></div>
    </div>

    <div class="smart-top section">
      <div class="hero-card score-card">
        <div class="hero-title">GÜNLÜK PERFORMANS</div>
        <div class="score-wrap">
          <div class="score-ring" style="--score:{score}%"><div><strong>{score}</strong><span>/100</span></div></div>
          <div><div class="score-label">Günün skoru</div><div class="hero-sub">Beslenme, su, adım ve antrenman kayıtlarından hesaplandı.</div></div>
        </div>
      </div>
      <div class="hero-card">
        <div class="hero-title">MEVCUT KİLO</div>
        <div class="hero-number">{current if current is not None else '—'} <span style="font-size:22px">kg</span></div>
        <div class="hero-sub">7 günlük ortalama: {avg7_current if avg7_current is not None else '—'} kg</div>
      </div>
      <div class="hero-card">
        <div class="hero-title">DEVAMLILIK</div>
        <div class="hero-number">🔥 {streak}</div>
        <div class="hero-sub">günlük kayıt serisi</div>
      </div>
    </div>

    <div class="premium-hero section">
      <div class="hero-card">
        <div class="hero-title">HEDEF YOLCULUĞU</div>
        <div class="hero-number">{round(remaining,1) if remaining is not None else '—'} <span style="font-size:22px">kg kaldı</span></div>
        <div class="hero-sub">Başlangıç {start_w if start_w is not None else '—'} kg · Hedef {target if target is not None else '—'} kg · Verilen {round(lost,1) if lost is not None else '—'} kg</div>
      </div>
      <div class="hero-card"><div class="progress-ring" style="--p:{progress:.1f}%"><div><strong>%{progress:.0f}</strong><span>hedef ilerlemesi</span></div></div></div>
    </div>

    <div class="grid">{card_html}</div>

    <div class="split section">
      <div class="card"><div class="label">📈 KİLO TRENDİ + 7 GÜNLÜK ORTALAMA</div><div class="chart"><canvas id="weightChart"></canvas></div></div>
      <div class="stack">
        <div class="card coach-card"><div class="label">🧠 KOÇ YORUMU</div><div class="coach-text">{coach}</div></div>
        <div class="card"><div class="label">🏋️ {plan_note.upper()}</div><div class="num" style="font-size:23px">{plan_day} · {plan_title}</div><div class="muted">Bugün kaydedilen hareket: {completed_today}</div><div class="mini-list">{focus}</div><a href="/egzersiz" class="go-link">Egzersize git →</a></div>
      </div>
    </div>
    '''

    extra_css = '''<style>
    .motivation-card{display:flex;gap:18px;align-items:center;padding:22px 24px;border:1px solid var(--line);border-radius:24px;background:linear-gradient(120deg,color-mix(in srgb,var(--green) 13%,var(--panel)),color-mix(in srgb,var(--blue) 10%,var(--panel)));box-shadow:var(--shadow)}
    .motivation-icon{width:52px;height:52px;border-radius:17px;display:grid;place-items:center;font-size:25px;background:linear-gradient(135deg,var(--green),var(--blue));color:#061018;font-weight:950;flex:0 0 auto}.motivation-text{font-size:20px;font-weight:850;line-height:1.4;margin-top:4px;letter-spacing:-.02em}.smart-top{display:grid;grid-template-columns:1.15fr 1fr .72fr;gap:16px}.score-wrap{display:flex;align-items:center;gap:22px;margin-top:10px}.score-ring{width:112px;height:112px;border-radius:50%;background:conic-gradient(var(--green) var(--score),var(--line) 0);display:grid;place-items:center;position:relative}.score-ring:before{content:'';position:absolute;width:86px;height:86px;background:var(--panel);border-radius:50%}.score-ring div{position:relative;text-align:center}.score-ring strong{font-size:31px}.score-ring span{font-size:11px;color:var(--muted)}.score-label{font-size:23px;font-weight:950;letter-spacing:-.03em}.stack{display:grid;gap:16px}.coach-card{background:linear-gradient(145deg,color-mix(in srgb,var(--blue) 8%,var(--panel)),var(--panel2))}.coach-text{font-size:17px;line-height:1.55;font-weight:750;margin-top:10px}.go-link{display:inline-block;margin-top:14px;color:var(--green);font-weight:900;text-decoration:none}@media(max-width:1050px){.smart-top{grid-template-columns:1fr 1fr}.score-card{grid-column:span 2}}@media(max-width:650px){.smart-top{grid-template-columns:1fr}.score-card{grid-column:span 1}.motivation-text{font-size:17px}.motivation-card{align-items:flex-start}}
    </style>'''

    chart = f'''<script src="https://cdn.jsdelivr.net/npm/chart.js"></script><script>
    new Chart(document.getElementById('weightChart'),{{type:'line',data:{{labels:{json.dumps(labels)},datasets:[
      {{label:'Günlük kilo',data:{json.dumps(weights)},borderColor:'#3ddc97',backgroundColor:'rgba(61,220,151,.08)',fill:false,tension:.25,pointRadius:3}},
      {{label:'7 günlük ortalama',data:{json.dumps(avg7)},borderColor:'#68a9ff',backgroundColor:'rgba(104,169,255,.10)',fill:true,tension:.4,pointRadius:0,borderWidth:3}}
    ]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#8796a8'}}}}}},scales:{{x:{{ticks:{{color:'#8796a8'}},grid:{{color:'rgba(120,130,150,.10)'}}}},y:{{ticks:{{color:'#8796a8'}},grid:{{color:'rgba(120,130,150,.10)'}}}}}}}}}});
    </script>'''

    return HTMLResponse(shell(f"{first_name}, bugün ne yapıyoruz?", "Skorun, trendin ve bugünkü koç planın burada.", "dashboard", extra_css + body, chart))
