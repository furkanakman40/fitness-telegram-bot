import random
from telegram.ext import MessageHandler, filters
import v4 as base

app = base.app
bot = base.core.telegram_app

# Remove older free-text handlers so only this coach answers normal messages.
for group, handlers in list(bot.handlers.items()):
    bot.handlers[group] = [h for h in handlers if not isinstance(h, MessageHandler)]

STRICT_MESSAGES = [
    "Kaldır kıçını. Düşünmeyi bırak, ayakkabını giy ve başla. Bugün keyfinin gelmesini beklemiyoruz; işi yapıyoruz. 🔥",
    "Hadi lan, pazarlık bitti. Hedefin varsa bugün ona uygun davranacaksın. Spor kıyafetini giy, suyu al ve çık. 💪",
    "Bahane üretmek kolay. Değişmek istiyorsan zor olanı yapacaksın. Kalk, hazırlan, ilk seti başlat. Gerisi gelir. ⚡",
    "Yorgunluk programı iptal etmiyor; sadece tempoyu ayarlıyor. Kalk kıçını ve başla. Bugün zinciri kırmak yok. 🔥",
    "Canın istemiyor diye hedef ortadan kaybolmadı. Ayağa kalk. Beş dakika hazırlan, sonra hareket et. Bugünün galibiyeti başlamak. 🏋️",
]


def norm(text):
    return (text.lower().replace("ı","i").replace("ş","s").replace("ğ","g")
            .replace("ü","u").replace("ö","o").replace("ç","c"))


def workout_text(offset):
    return base.workout_text(offset)


async def strict_coach(update, context):
    if not update.message or not update.message.text:
        return

    text = norm(update.message.text.strip())

    if any(x in text for x in ["yarinin program", "yarin program", "yarin ne var", "yarin ne yapacagim", "yarin antrenman"]):
        await update.message.reply_text(workout_text(1))
        return

    if any(x in text for x in ["bugunun program", "bugun program", "bugun ne var", "bugun ne yapacagim", "bugun antrenman", "programi at"]):
        await update.message.reply_text(workout_text(0))
        return

    if any(x in text for x in [
        "usendim", "yorgunum", "cok yorgunum", "gitmek istemiyorum", "spor yapasim yok",
        "antrenman yapasim yok", "motivasyonum yok", "yataktan kalkamiyorum", "bugun gitmesem",
        "yarin giderim", "gaz ver", "motive et", "beni zorla", "bahane", "canim istemiyor",
        "uykum var", "halim yok", "modum yok"
    ]):
        await update.message.reply_text(random.choice(STRICT_MESSAGES))
        return

    if any(x in text for x in ["ne yesem", "ne yiyim", "yemek oner", "acim"]):
        await update.message.reply_text(
            "Açsın diye plan çöpe gitmiyor. Önce proteinini koy: yağsız protein + ölçülü karbonhidrat + sebze. "
            "Rastgele atıştırma yok. Öğününü seç, ye, toplamı kaydet. 🥗"
        )
        return

    if "hedef" in text:
        uid = base.core.get_or_create_user(update.effective_user)
        g = base.core.get_goals(uid)
        await update.message.reply_text(
            f"🎯 Hedeflerin\n⚖️ {g.get('target_weight_kg','—')} kg\n🔥 {g.get('daily_calories','—')} kcal\n"
            f"🥩 {g.get('daily_protein_g','—')} g protein\n💧 {g.get('daily_water_l','—')} L su\n"
            f"🚶 {g.get('daily_steps','—')} adım\n\nŞimdi eksik olan ilk hedefi seç ve tamamla. Laf değil, kayıt görmek istiyorum. 🔥"
        )
        return

    # Default personality is now demanding, even when the sentence doesn't match a special trigger.
    await update.message.reply_text(
        random.choice([
            "Tamam, koç buradayım. Ama boş konuşmayalım: bugün neyi tamamlayacağız? Program, adım, protein veya antrenman — birini seç ve harekete geç. 🔥",
            "Mesajı aldım. Şimdi icraat: bugünkü programı mı istiyorsun, hedeflerini mi kontrol edeceğiz, yoksa seni salona mı kaldırayım? 💪",
            "Güzel. Ama sonuç mesajdan değil aksiyondan geliyor. Bana ne yapacağını söyle ya da ‘gaz ver’ yaz; seni rahat bırakmayacağım. ⚡",
        ])
    )

bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, strict_coach), group=0)
