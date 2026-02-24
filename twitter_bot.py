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
            lines.append(f"  {i}. #{f['fund_code']}  {fmt_money(f['net_flow'])}  ({fmt_pct(f['flow_pct'])})")

    if outs:
        lines.append("\n🔴 En Fazla Çıkış")
        for i, f in enumerate(outs, 1):
            lines.append(f"  {i}. #{f['fund_code']}  {fmt_money(f['net_flow'])}  ({fmt_pct(f['flow_pct'])})")

    lines.append("\n📈 Detaylar görselde ↓")
    lines.append("#TEFAS #FonYatırımı #Borsa #Yatırım")
    return "\n".join(lines)


def tweet_inflows_only(data, period):
    ins  = data.get("top_inflows", [])[:5]
    date = tr_date(data["date"])
    lbl  = PERIOD_LABEL.get(period, "Günlük")

    lines = [f"🟢 TEFAS {lbl} Para Girişi Liderleri — {date}\n"]
    for i, f in enumerate(ins, 1):
        lines.append(f"  {i}. #{f['fund_code']}  {fmt_money(f['net_flow'])}  ({fmt_pct(f['flow_pct'])})")
    lines.append("\n#TEFAS #FonYatırımı #Borsa")
    return "\n".join(lines)


def tweet_outflows_only(data, period):
    outs = data.get("top_outflows", [])[:5]
    date = tr_date(data["date"])
    lbl  = PERIOD_LABEL.get(period, "Günlük")

    lines = [f"🔴 TEFAS {lbl} Para Çıkışı Liderleri — {date}\n"]
    for i, f in enumerate(outs, 1):
        lines.append(f"  {i}. #{f['fund_code']}  {fmt_money(f['net_flow'])}  ({fmt_pct(f['flow_pct'])})")
    lines.append("\n#TEFAS #FonYatırımı #Borsa")
    return "\n".join(lines)


def tweet_categories(data, period):
    cat_in = data.get("top_cat_in", [])[:3]
    cat_out = data.get("top_cat_out", [])[:3]
    date = tr_date(data["date"])
    lbl  = PERIOD_LABEL.get(period, "Günlük")

    lines = [f"📊 TEFAS {lbl} Kategori Hareketleri — {date}\n"]

    if cat_in:
        lines.append("🟢 En Fazla Para Girişi")
        for i, c in enumerate(cat_in, 1):
            lines.append(f"  {i}. {c['fund_code']}  {fmt_money(c['net_flow'])}  ({fmt_pct(c['flow_pct'])})")

    if cat_out:
        lines.append("\n🔴 En Fazla Para Çıkışı")
        for i, c in enumerate(cat_out, 1):
            lines.append(f"  {i}. {c['fund_code']}  {fmt_money(c['net_flow'])}  ({fmt_pct(c['flow_pct'])})")

    lines.append("\n📈 Detaylar görselde ↓")
    lines.append("#TEFAS #FonYatırımı #Borsa #Yatırım")
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
            lines.append(f"  {i}. #{f['fund_code']}  {f['inv_change']:+d} kişi  ({pct})")

    if inv_out:
        lines.append("\n🔴 En Fazla Yatırımcı Kaybı")
        for i, f in enumerate(inv_out, 1):
            pct = fmt_pct(f.get("inv_change_pct", 0))
            lines.append(f"  {i}. #{f['fund_code']}  {f['inv_change']:+d} kişi  ({pct})")

    lines.append("\n📈 Detaylar görselde ↓")
    lines.append("#TEFAS #FonYatırımı #Yatırımcı")
    return "\n".join(lines)


def tweet_tracked(data, period):
    tracked = data.get("tracked", {})
    date = tr_date(data["date"])
    lbl  = PERIOD_LABEL.get(period, "Günlük")

    lines = [f"🎯 {lbl} Para Girişi ve Çıkışı — {date}\n"]
    
    tags = ["#TEFAS", "#FonYatırımı"]
    for code, f in tracked.items():
        flow_val = f.get("period_flow", 0)
        sign = "-" if flow_val < 0 else "+"
        formatted_flow = f"{sign}{abs(int(flow_val)):,}".replace(",", ".")
        lines.append(f"#{code.lower()} {formatted_flow}")
        tags.append(f"#{code.upper()}")

    lines.append("\n" + " ".join(tags))
    return "\n".join(lines)


def tweet_predictions(data, config):
    preds = config.get("predictions", [])
    date  = tr_date(data["date"])
    title = config.get("pred_title", "Gün Ortası Tahmini")

    lines = [f"🔮 {title} — {date}\n"]
    for p in preds:
        code = p.get("code", "")
        val  = p.get("val", "")
        desc = p.get("desc", "")
        entry = f"  #{code}  {val}"
        if desc:
            entry += f"  ({desc})"
        lines.append(entry)

    lines.append("\n#TEFAS #Borsa #GünSonuTahmini")
    return "\n".join(lines)


def tweet_allocation_diff(data, config):
    # Target the specific fund from config
    target_fund = config.get("portfolio_diff_fund", "PHE").upper()
    diffs = data.get("allocation_diffs", {})
    if not diffs:
        return "Portföy dağılım verisi bulunamadı."
        
    # Fallback to the first available if not found
    if target_fund not in diffs:
        target_fund = list(diffs.keys())[0] if diffs else None
        
    if not target_fund:
        return "Portföy dağılım verisi bulunamadı."

    fund_data = diffs[target_fund]
    
    date = tr_date(data["date"])
    lines = [f"🎯 #{target_fund} Portföy Dağılımı (Düne Göre Değişim) — {date}\n"]
    
    allocations = fund_data.get("allocations", [])
    for alloc in allocations:
        asset = alloc.get("asset", "")
        w = alloc.get("weight", 0)
        d = alloc.get("diff", 0)
        
        # Formatting difference
        if abs(d) < 0.01:
            diff_str = "(-)"
        else:
            sign = "+" if d > 0 else ""
            diff_str = f"({sign}%{d:.2f})".replace(".", ",")
            
        weight_str = f"%{w:.2f}".replace(".", ",")
        lines.append(f"{asset}: {weight_str} {diff_str}")
        
    lines.append(f"\n#TEFAS #FonYatırımı #{target_fund}")
    return "\n".join(lines)


# ─── Main Tweet Builder ───────────────────────────────────────────────────────

def generate_tweet_text(data, sections, config=None):
    """
    Aktif section listesine göre en uygun tweet şablonunu seçer.
    sections: ['inflows', 'outflows', 'inv_in', 'inv_out', 'tracked', 'predictions', 'portfolio_diff', ...]
    """
    if config is None: config = {}
    period = data.get("period_type", "daily")
    has = lambda s: s in sections

    # ==========================
    # Tekil Şablon Seçimleri
    # ==========================
    if has("portfolio_diff") and len(sections) == 1:
        return tweet_allocation_diff(data, config)

    if has("predictions") and len(sections) == 1:
        return tweet_predictions(data, config)

    if has("tracked") and len(sections) == 1:
        return tweet_tracked(data, period)

    if has("inflows") and not has("outflows") and len(sections) == 1:
        return tweet_inflows_only(data, period)

    if has("outflows") and not has("inflows") and len(sections) == 1:
        return tweet_outflows_only(data, period)

    if (has("cat_in") or has("cat_out")) and not has("inflows") and not has("outflows") and not has("inv_in"):
        return tweet_categories(data, period)

    if (has("inv_in") or has("inv_out")) and len(sections) <= 2:
        return tweet_investors(data, period)

    # ==========================
    # Kombine Şablon Seçimleri 
    # ==========================
    if has("portfolio_diff"):
        return tweet_allocation_diff(data, config)

    if has("cat_in") or has("cat_out"):
        return tweet_categories(data, period)

    if has("inv_in") or has("inv_out"):
        return tweet_investors(data, period)

    if has("inflows") and not has("outflows"):
        return tweet_inflows_only(data, period)

    if has("outflows") and not has("inflows"):
        return tweet_outflows_only(data, period)

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
    tweet_text = generate_tweet_text(data, sections, config)

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
