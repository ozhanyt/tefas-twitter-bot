import os
import sys
import json
from datetime import datetime

# ─── Tweepy optional import ──────────────────────────────────────────────────
try:
    import tweepy
    TWEEPY_OK = True
except ImportError:
    TWEEPY_OK = False
    print("⚠️  tweepy yüklü değil. Sadece önizleme modunda çalışıyor.")
    print("   Yüklemek için: pip install tweepy\n")

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR         = os.path.dirname(__file__)
INFOGRAPHIC_PATH = os.path.join(BASE_DIR, "infographic.png")
DATA_PATH        = os.path.join(BASE_DIR, "data.json")
CONFIG_PATH      = os.path.join(BASE_DIR, "runtime_config.json")

# ─── Twitter API Credentials ─────────────────────────────────────────────────
# Bunları .env dosyasına taşıyabilir veya direkt buraya yazabilirsiniz.
API_KEY      = os.environ.get("TW_API_KEY",      "YOUR_API_KEY")
API_SECRET   = os.environ.get("TW_API_SECRET",   "YOUR_API_SECRET")
ACCESS_TOKEN = os.environ.get("TW_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN")
ACCESS_SECRET= os.environ.get("TW_ACCESS_SECRET","YOUR_ACCESS_SECRET")
BEARER_TOKEN = os.environ.get("TW_BEARER_TOKEN", "YOUR_BEARER_TOKEN")

# ─── Formatting helpers ───────────────────────────────────────────────────────
PERIOD_TR = {"daily": "Düne Göre", "weekly": "Haftaya Göre", "monthly": "Aya Göre"}
PERIOD_LABEL = {"daily": "Günlük", "weekly": "Haftalık", "monthly": "Aylık"}

def fmt_money(val):
    """₺639.9M  veya  -₺456.7M"""
    sign = "-" if val < 0 else "+"
    abs_v = abs(val)
    if abs_v >= 1_000_000_000:
        return f"{sign}₺{abs_v/1_000_000_000:.1f}Mlr"
    elif abs_v >= 1_000_000:
        return f"{sign}₺{abs_v/1_000_000:.1f}M"
    elif abs_v >= 1_000:
        return f"{sign}₺{abs_v/1_000:.0f}K"
    return f"{sign}₺{abs_v:.0f}"

def fmt_pct(val, sign=True):
    prefix = ("+" if val >= 0 else "") if sign else ""
    return f"{prefix}{val:.2f}%".replace(".", ",")

def tr_date(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        months = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                  "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
        return f"{d.day} {months[d.month-1]} {d.year}"
    except:
        return date_str

# ─── Per-Section Tweet Templates ─────────────────────────────────────────────

def tweet_inflows_outflows(data, period):
    """Para Girişi + Para Çıkışı birlikte ise"""
    ins  = data.get("top_inflows",  [])[:3]
    outs = data.get("top_outflows", [])[:3]
    date = tr_date(data["date"])
    lbl  = PERIOD_LABEL.get(period, "Günlük")

    lines = [f"📊 TEFAS {lbl} Para Hareketleri — {date}\n"]

    if ins:
        lines.append("🟢 En Fazla Giriş")
        for i, f in enumerate(ins, 1):
            lines.append(f"  {i}. ${f['fund_code']}  {fmt_money(f['net_flow'])}  ({fmt_pct(f['flow_pct'])})")

    if outs:
        lines.append("\n🔴 En Fazla Çıkış")
        for i, f in enumerate(outs, 1):
            lines.append(f"  {i}. ${f['fund_code']}  {fmt_money(f['net_flow'])}  ({fmt_pct(f['flow_pct'])})")

    lines.append("\n📈 Detaylar görselde ↓")
    lines.append("#TEFAS #FonYatırımı #Borsa #Yatırım")
    return "\n".join(lines)


def tweet_inflows_only(data, period):
    ins  = data.get("top_inflows", [])[:5]
    date = tr_date(data["date"])
    lbl  = PERIOD_LABEL.get(period, "Günlük")

    lines = [f"🟢 TEFAS {lbl} Para Girişi Liderleri — {date}\n"]
    for i, f in enumerate(ins, 1):
        lines.append(f"  {i}. ${f['fund_code']}  {fmt_money(f['net_flow'])}  ({fmt_pct(f['flow_pct'])})")
    lines.append("\n#TEFAS #FonYatırımı #Borsa")
    return "\n".join(lines)


def tweet_outflows_only(data, period):
    outs = data.get("top_outflows", [])[:5]
    date = tr_date(data["date"])
    lbl  = PERIOD_LABEL.get(period, "Günlük")

    lines = [f"🔴 TEFAS {lbl} Para Çıkışı Liderleri — {date}\n"]
    for i, f in enumerate(outs, 1):
        lines.append(f"  {i}. ${f['fund_code']}  {fmt_money(f['net_flow'])}  ({fmt_pct(f['flow_pct'])})")
    lines.append("\n#TEFAS #FonYatırımı #Borsa")
    return "\n".join(lines)


def tweet_investors(data, period):
    inv_in  = data.get("top_inv_in",  [])[:3]
    inv_out = data.get("top_inv_out", [])[:3]
    date = tr_date(data["date"])
    lbl  = PERIOD_LABEL.get(period, "Günlük")

    lines = [f"👤 TEFAS {lbl} Yatırımcı Hareketleri — {date}\n"]

    if inv_in:
        lines.append("🟢 En Fazla Yeni Yatırımcı")
        for i, f in enumerate(inv_in, 1):
            pct = fmt_pct(f.get("inv_change_pct", 0))
            lines.append(f"  {i}. ${f['fund_code']}  {f['inv_change']:+d} kişi  ({pct})")

    if inv_out:
        lines.append("\n🔴 En Fazla Yatırımcı Kaybı")
        for i, f in enumerate(inv_out, 1):
            pct = fmt_pct(f.get("inv_change_pct", 0))
            lines.append(f"  {i}. ${f['fund_code']}  {f['inv_change']:+d} kişi  ({pct})")

    lines.append("\n📈 Detaylar görselde ↓")
    lines.append("#TEFAS #FonYatırımı #Yatırımcı")
    return "\n".join(lines)


def tweet_tracked(data, period):
    tracked = data.get("tracked_funds", {})
    date = tr_date(data["date"])
    lbl  = PERIOD_LABEL.get(period, "Günlük")

    lines = [f"🎯 Takipteki Fonlar — {lbl} Performans — {date}\n"]
    for code, f in tracked.items():
        ret  = fmt_pct(f.get("period_return_pct", 0))
        flow = fmt_money(f.get("period_flow", 0))
        inv  = f.get("period_investor_change", 0)
        lines.append(f"  #{code}  Getiri: {ret}  Giriş: {flow}  Yatırımcı: {inv:+d}")

    lines.append("\n📊 Detaylar ve fon büyüklükleri görselde ↓")
    lines.append("#TEFAS #FonYatırımı #TLY #PHE #DFI")
    return "\n".join(lines)


def tweet_predictions(data):
    preds = data.get("predictions", [])
    date  = tr_date(data["date"])
    title = data.get("pred_title", "Gün Sonu Tahmini")

    lines = [f"🔮 {title} — {date}\n"]
    for p in preds:
        code = p.get("code", "")
        val  = p.get("value", "")
        desc = p.get("description", "")
        entry = f"  #{code}  {val}"
        if desc:
            entry += f"  ({desc})"
        lines.append(entry)

    lines.append("\n#TEFAS #Borsa #GünSonuTahmini")
    return "\n".join(lines)


# ─── Main Tweet Builder ───────────────────────────────────────────────────────

def generate_tweet_text(data, sections):
    """
    Aktif section listesine göre en uygun tweet şablonunu seçer.
    sections: ['inflows', 'outflows', 'inv_in', 'inv_out', 'tracked', 'predictions', ...]
    """
    period = data.get("period_type", "daily")
    has = lambda s: s in sections

    # Kombinasyon bazlı şablon seçimi
    if has("predictions") and len(sections) == 1:
        return tweet_predictions(data)

    if has("tracked") and len(sections) == 1:
        return tweet_tracked(data, period)

    if has("inflows") and has("outflows") and not has("inv_in"):
        return tweet_inflows_outflows(data, period)

    if has("inflows") and not has("outflows"):
        return tweet_inflows_only(data, period)

    if has("outflows") and not has("inflows"):
        return tweet_outflows_only(data, period)

    if has("inv_in") or has("inv_out"):
        return tweet_investors(data, period)

    # Fallback: her şey varsa inflows+outflows özeti
    return tweet_inflows_outflows(data, period)


# ─── Twitter Post ─────────────────────────────────────────────────────────────

def post_to_twitter(tweet_text):
    if not TWEEPY_OK:
        print("❌ tweepy yüklü değil, gönderilemedi.")
        return False

    if "YOUR_API_KEY" in API_KEY:
        print("❌ API anahtarları ayarlanmamış.")
        print("   Ortam değişkenlerini set edin veya twitter_bot.py'yi düzenleyin.")
        return False

    try:
        # v1.1 — medya yükleme
        auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
        api  = tweepy.API(auth)
        print("🖼️  Resim yükleniyor...")
        media = api.media_upload(INFOGRAPHIC_PATH)
        print(f"✅ Resim yüklendi. Media ID: {media.media_id}")

        # v2 — tweet gönder
        client = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_SECRET
        )
        print("📤 Tweet gönderiliyor...")
        response = client.create_tweet(text=tweet_text, media_ids=[media.media_id])
        tweet_id = response.data['id']
        print(f"✅ Tweet paylaşıldı! https://x.com/i/web/status/{tweet_id}")
        return True

    except Exception as e:
        print(f"❌ Hata: {e}")
        return False


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    # 1. Dosya kontrolü
    for path, name in [(INFOGRAPHIC_PATH, "infographic.png"), (DATA_PATH, "data.json"), (CONFIG_PATH, "runtime_config.json")]:
        if not os.path.exists(path):
            print(f"❌ Dosya bulunamadı: {name}")
            sys.exit(1)

    # 2. Verileri yükle
    with open(DATA_PATH,   "r", encoding="utf-8") as f: data    = json.load(f)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f: config  = json.load(f)

    sections = config.get("sections", ["inflows", "outflows"])

    # 3. Tweet oluştur
    tweet_text = generate_tweet_text(data, sections)

    # 4. Önizleme
    print("=" * 60)
    print("📋 TWEET ÖNİZLEME")
    print("=" * 60)
    print(tweet_text)
    print(f"\n({len(tweet_text)} karakter / 280 max)")
    print("=" * 60)

    if len(tweet_text) > 280:
        print("⚠️  Tweet 280 karakteri aşıyor! Kısaltma yapılacak...")
        tweet_text = tweet_text[:277] + "..."

    # 5. Onay al
    answer = input("\nTweet gönderilsin mi? (e/h) → ").strip().lower()
    if answer != "e":
        print("İptal edildi.")
        return

    # 6. Gönder
    post_to_twitter(tweet_text)


if __name__ == "__main__":
    main()
