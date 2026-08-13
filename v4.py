import json
import v3 as core
from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = core.app

MEALS = [
    {
        "key": "kahvalti",
        "title": "Kahvaltı",
        "emoji": "🍳",
        "calories": 550,
        "protein": 45,
        "foods": ["3 tam yumurta", "80 g yulaf", "200 g yoğurt", "1 porsiyon meyve"],
        "alternative": "Yulaf yerine 2 dilim tam tahıllı ekmek; yoğurt yerine kefir kullanılabilir.",
    },
    {
        "key": "ogle",
        "title": "Öğle",
        "emoji": "🍗",
        "calories": 700,
        "protein": 60,
        "foods": ["200 g tavuk/hindi", "150 g pişmiş pirinç veya bulgur", "Bol salata", "1 yemek kaşığı zeytinyağı"],
        "alternative": "Tavuk yerine yağsız kırmızı et veya ton balığı; pirinç yerine patates kullanılabilir.",
    },
    {
        "key": "ara",
        "title": "Ara Öğün",
        "emoji": "🥣",
        "calories": 350,
        "protein": 30,
        "foods": ["250 g yüksek proteinli yoğurt", "1 muz", "20 g çiğ badem"],
        "alternative": "Yoğurt yerine lor peyniri + meyve tercih edilebilir.",
    },
    {
        "key": "aksam",
        "title": "Akşam",
        "emoji": "🥩",
        "calories": 800,
        "protein": 55,
        "foods": ["200–220 g yağsız et/tavuk/balık", "250–300 g patates veya 150 g pişmiş bulgur", "Sebze veya salata", "200 g yoğurt"],
        "alternative": "Karbonhidrat porsiyonunu günlük kalori durumuna göre azaltıp artırabilirsin.",
    },
]


def nutrition_nav(active):
    items = [
        ("dashboard", "⌂ Genel", "/dashboard"),
        ("egzersiz", "🏋 Egzersiz", "/egzersiz"),
        ("beslenme", "🥗 Beslenme", "/beslenme"),
        ("istatistik", "◒ İstatistik", "/istatistik"),
    ]
    return ''.join(f'<a class="{"on" if active == key else ""}" href="{url}">{label}</a>' for key, label, url in items)


core.nav = nutrition_nav
try:
    import v2
    v2.nav = nutrition_nav
except Exception:
    pass


def meal_history(uid):
    rows = (
        core.supabase.table("workouts")
        .select("workout_date,workout_type,notes")
        .eq("user_id", uid)
        .eq("workout_date", core.today())
        .execute().data or []
    )
    done = {}
    for row in rows:
        wt = str(row.get("workout_type", ""))
        if not wt.startswith("MEAL:"):
            continue
        key = wt[5:]
        try:
            done[key] = json.loads(row.get("notes") or "{}")
        except Exception:
            done[key] = {}
    return done


@app.post("/api/nutrition/toggle")
async def toggle_meal(request: Request, user=Depends(core.auth)):
    profile = core.first_profile()
    if not profile:
        return JSONResponse({"ok": False, "error": "Profil yok"}, 404)

    payload = await request.json()
    key = str(payload.get("key", "")).strip()
    meal = next((m for m in MEALS if m["key"] == key), None)
    if not meal:
        return JSONResponse({"ok": False, "error": "Öğün bulunamadı"}, 404)

    uid = profile["id"]
    existing = (
        core.supabase.table("workouts")
        .select("id")
        .eq("user_id", uid)
        .eq("workout_date", core.today())
        .eq("workout_type", "MEAL:" + key)
        .limit(1)
        .execute()
    )

    if existing.data:
        core.supabase.table("workouts").delete().eq("id", existing.data[0]["id"]).execute()
        return {"ok": True, "completed": False}

    notes = json.dumps({
        "title": meal["title"],
        "calories": meal["calories"],
        "protein": meal["protein"],
        "completed": True,
    }, ensure_ascii=False)

    core.supabase.table("workouts").insert({
        "user_id": uid,
        "workout_date": core.today(),
        "workout_type": "MEAL:" + key,
        "notes": notes,
    }).execute()

    return {"ok": True, "completed": True}


@app.get("/beslenme", response_class=HTMLResponse)
async def beslenme(user=Depends(core.auth)):
    profile = core.first_profile()
    if not profile:
        return HTMLResponse("Profil yok", 404)

    uid = profile["id"]
    goals = core.get_goals(uid)
    daily = core.get_daily(uid)
    done = meal_history(uid)

    target_cal = float(goals.get("daily_calories") or 2400)
    target_pro = float(goals.get("daily_protein_g") or 190)

    planned_cal = sum(m["calories"] for m in MEALS if m["key"] in done)
    planned_pro = sum(m["protein"] for m in MEALS if m["key"] in done)

    actual_cal = float(daily.get("calories") or 0)
    actual_pro = float(daily.get("protein_g") or 0)

    used_cal = actual_cal if actual_cal > 0 else planned_cal
    used_pro = actual_pro if actual_pro > 0 else planned_pro

    cal_left = max(0, target_cal - used_cal)
    pro_left = max(0, target_pro - used_pro)
    cal_pct = min(100, used_cal / target_cal * 100) if target_cal else 0
    pro_pct = min(100, used_pro / target_pro * 100) if target_pro else 0

    summary = f'''
    <div class="grid">
      <div class="card"><div class="label">🔥 KALORİ</div><div class="num">{used_cal:g}</div><div class="muted">/ {target_cal:g} kcal</div><div class="bar"><div class="fill" style="width:{cal_pct:.1f}%"></div></div></div>
      <div class="card"><div class="label">🥩 PROTEİN</div><div class="num">{used_pro:g} g</div><div class="muted">/ {target_pro:g} g</div><div class="bar"><div class="fill" style="width:{pro_pct:.1f}%"></div></div></div>
      <div class="card"><div class="label">🧮 KALAN KALORİ</div><div class="num">{cal_left:g}</div><div class="muted">kcal</div></div>
      <div class="card"><div class="label">🎯 KALAN PROTEİN</div><div class="num">{pro_left:g} g</div><div class="muted">bugünkü hedefe</div></div>
    </div>
    '''

    meal_cards = []
    for meal in MEALS:
        completed = meal["key"] in done
        status = "✓ Tamamlandı" if completed else "Tamamla"
        foods = ''.join(f'<div class="mini"><div><b>{food}</b></div><span>•</span></div>' for food in meal["foods"])
        meal_cards.append(f'''
        <div class="card day">
          <div class="label">{meal['emoji']} {meal['title'].upper()}</div>
          <div class="num" style="font-size:22px">{meal['calories']} kcal · {meal['protein']} g protein</div>
          <div class="mini-list">{foods}</div>
          <div class="muted" style="font-size:12px;margin-top:12px;line-height:1.6">Alternatif: {meal['alternative']}</div>
          <button onclick="toggleMeal('{meal['key']}')" style="margin-top:15px;width:100%;border:0;border-radius:12px;padding:11px 12px;font-weight:900;cursor:pointer;background:linear-gradient(135deg,var(--green),var(--blue));color:#06110d">{status}</button>
        </div>
        ''')

    note = '''
    <div class="card section">
      <div class="label">NASIL KULLANACAKSIN?</div>
      <div class="muted" style="line-height:1.75;margin-top:8px">
        Öğünü yediğinde “Tamamla” butonuna bas. Telegram'da /kalori ve /protein ile gerçek toplamı girdiğinde gerçek değerler öncelikli gösterilir. Plan yaklaşık bir çerçevedir; gramajları ilerleme hızına göre sonradan ayarlayacağız.
      </div>
    </div>
    '''

    body = summary + f'<div class="days section">{"".join(meal_cards)}</div>' + note
    js = '''
    <script>
    async function toggleMeal(key){
      const r=await fetch('/api/nutrition/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:key})});
      const j=await r.json();
      const t=document.getElementById('toast');
      t.style.display='block';
      t.innerText=j.ok?(j.completed?'✅ Öğün tamamlandı.':'↩️ İşaret kaldırıldı.'):'❌ '+(j.error||'Hata');
      setTimeout(()=>location.reload(),700);
    }
    </script>
    '''

    return HTMLResponse(core.shell("Beslenme Planı", "Kalori ve protein hedefini öğün öğün takip et.", "beslenme", body, js))
