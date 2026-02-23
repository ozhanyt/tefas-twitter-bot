# TEFAS Twitter Bot 📊

TEFAS (Türkiye Elektronik Fon Alım Satım Platformu) verilerini çekip görsel infografik üreten ve Twitter/X'e paylaşabileceğiniz bir Python aracı.

## Özellikler

- 📈 **Para Giriş / Çıkış Liderleri** — günlük, haftalık veya aylık en çok para giren/çıkan fonlar
- 👤 **Yatırımcı Hareketleri** — yeni katılan / ayrılan yatırımcılar
- 🏷️ **Kategori Bazlı Akışlar** — fon kategorilerine göre para giriş/çıkış özeti
- 🎯 **Takipteki Fonlar** — belirlediğiniz fonlar için fiyat, getiri, yatırımcı sayısı, büyüklük
- 🔮 **Tahmin Bölümü** — gün sonu tahmini gibi özel içerik kartı
- 🎨 **Dashboard UI** — `localhost:8080` üzerinden browser ile ayarlanabilir arayüz
- 🖼️ **Playwright ile PNG üretimi** — Twitter paylaşımına hazır yüksek çözünürlüklü görsel

## Kurulum

```bash
# Bağımlılıkları yükle
pip install borsapy pandas playwright

# Playwright browser'ı indir
playwright install chromium
```

## Kullanım

### Server (Dashboard) ile

```bash
python server.py
# Tarayıcıda http://localhost:8080 adresini aç
```

- Bölümleri seç / konumlandır
- Takip etmek istediğin fon kodlarını gir
- **Üret** butonuna bas → `infographic.png` oluşur

### Direkt üretim

```bash
python image_generator.py
```

`runtime_config.json` dosyasındaki ayarları kullanır.

## Dosya Yapısı

```
├── server.py              # Dashboard web sunucusu
├── image_generator.py     # Playwright ile PNG üretim motoru
├── data_fetcher.py        # borsapy ile TEFAS veri çekme
├── twitter_bot.py         # Twitter/X paylaşım entegrasyonu
├── template/
│   └── index.html         # İnfografik HTML/CSS şablonu
└── runtime_config.json    # Üretim konfigürasyonu (gitignore'd)
```

## Konfigürasyon

`dashboard_config.json` (dashboard'dan otomatik oluşur, gitignore'd):
- Bölüm seçimi ve grid konumları
- Font boyutları
- Canvas genişliği
- Arka plan görseli URL'si
- Tahmin verileri

## Gereksinimler

- Python 3.9+
- [borsapy](https://github.com/...) — TEFAS veri kütüphanesi
- playwright
- pandas
