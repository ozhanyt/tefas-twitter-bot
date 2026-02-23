# TEFAS İnfografik — Standart Setup Rehberi

## 🔮 Tahmin Bölümü (Sadece Tahmin)

| Ayar | Değer |
|---|---|
| Tuval Genişliği | **1200 px** |
| Liste Font | **72 px** |
| Bölümler | Sadece `Tahmin` işaretli |
| Ana Sütun | — |
| Takip Izgarası | — |

---

## 🎯 Takipteki Fonlar

| Ayar | Değer |
|---|---|
| Tuval Genişliği | **1800 px** |
| Liste Font | **40 px** |
| Ana Sütun | **1** |
| Takip Izgarası | **3** |
| Bölümler | Sadece `Takipteki Fonlar` işaretli |

---

## 📊 Diğer Bölümler (Para Giriş/Çıkış, Kategori, Yatırımcı vb.)

| Ayar | Değer |
|---|---|
| Tuval Genişliği | **2100 px** |
| Liste Font | **40 px** |
| Ana Sütun | 2 (varsayılan) |
| Takip Izgarası | — |
| Bölümler | İstenen bölümler işaretli |

---

## 📌 Notlar

- **Etiket Font** genellikle **Liste Font ile aynı** değerde bırakılır.
- **Tahmin** checkbox'ı seçilmediği sürece infografikte görünmez (veri girilmiş olsa bile).
- `runtime_config.json` ve `dashboard_config.json` gitignore'da — her local kurulumda ayarlar sıfırdan yapılır.
- Üretim sonrası `infographic.png` proje klasöründe oluşur.
