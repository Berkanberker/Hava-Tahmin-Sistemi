# 🌪️ Zonguldak Kış Sistemleri Avcısı (AI-Powered Weather Forecasting System)

Bu proje, **Yapay Zeka (Google Gemini)**, **İleri Veri Bilimi (Python/Pandas)** ve **Modern Web Teknolojilerini (.NET 8.0)** birleştirerek; Zonguldak ve çevresi için **Hiper-Lokal**, **Sinoptik** ve **Tarihsel Analog** tahminler üreten yeni nesil bir meteorolojik karar destek sistemidir.

---

## 🚀 Temel Özellikler

### 1. 🧠 Hibrit Analiz Motoru

Sistem, sadece sayısal model verilerini (NWP) okumakla kalmaz, bunları **44 yıllık iklim hafızasıyla** kıyaslar.

* **L0 Mevsimsel Filtre:** Lorenz Kaos Teorisi'ne uygun ±60 günlük pencereleme.

* **L1 Sinoptik Desen:** 500hPa ve MSLP haritalarını "Bilgisayarlı Görü" mantığıyla tarar.

* **L2 Trajectory Matching (Yörünge Analizi):** Hava kütlesinin son 72 saatlik hareket vektörünü analiz eder.

### 2. 🌍 Küresel Sensör Ağı (14 Nokta)

Sistem sadece Zonguldak'a bakmaz. "Kelebek Etkisi"ni yakalamak için tüm kuzey yarım küreyi tarar:

* **Stratosfer (10hPa/50hPa):** Polar Vorteks kararlılığı ve SSW takibi.

* **Jet Akımları (250hPa):** Rossby dalgalarının analizi. 

* **Telekoneksiyonlar:** Moskova (Depo), İzlanda (Vana), Azor (Blokaj), İtalya (Vakum).

### 3. 🛡️ Tank Modu (Hata Toleransı)

* **Anti-Ban:** API limitlerine takılmamak için akıllı bekleme ve User-Agent rotasyonu.

* **Failover:** ECMWF verisi eksikse otomatik olarak GFS veya ICON modellerine geçiş.

* **Data Sanitation:** Eksik veya hatalı verileri (NaN) matematiksel operasyonlara sokmadan temizleme.

### 4. 📊 Olasılıksal Tahmin (Ensemble)

Tek bir tahmin yerine, geçmişteki en benzer 50 senaryoyu (Analog) çalıştırarak istatistiksel risk analizi yapar:

* **P10 / P50 / P90** senaryoları.

* Kar yağışı için **Belirsizlik (Uncertainty)** hesaplaması.

---

## 🛠️ Teknoloji Yığını (Tech Stack)

| **Katman** | **Teknoloji** | **Açıklama** | 
| :--- | :--- | :--- |
| **Backend** | .NET 8.0 (C#) | MVC Mimarisi, Süreç Yönetimi, Asenkron Yapı | 
| **AI & Data** | Python 3.11 | Pandas, NumPy, Scikit-Learn (Opsiyonel), SciPy | 
| **LLM** | Google Gemini 1.5 | Doğal Dil İşleme ve Uzman Yorumlama | 
| **Frontend** | Bootstrap 5 + JS | Glassmorphism UI, ApexCharts İnteraktif Grafikler | 
| **Database** | SQLite + EF Core | Veri Kalıcılığı ve Arşivleme | 
| **API** | Open-Meteo | ERA5 Reanalysis (1980-2024) + Operasyonel Modeller | 

---

## ⚙️ Kurulum ve Çalıştırma

### 1. Gereksinimler

* .NET 8.0 SDK

* Python 3.10+

* `pip install pandas numpy requests google-generativeai urllib3 scipy scikit-learn`

### 2. Veri Ambarını Oluşturun (Tek Seferlik):

```bash
python veri_ambari.py
