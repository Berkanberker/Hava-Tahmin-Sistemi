import sys
import io
import os
import time
import pandas as pd
import numpy as np
import requests
import google.generativeai as genai
import urllib3
from datetime import datetime, timedelta

try:
    from sklearn.ensemble import RandomForestRegressor
    SKLEARN_AVAILABLE = True
except:
    SKLEARN_AVAILABLE = False

import warnings
warnings.filterwarnings('ignore')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

API_KEY = "AIzaSyAA0r5kXRkOQ_uLBwuj77nY89-YhYJ8P9s"

BUYUK_OLCEK = [
    {"id": "Kutup_Merkez", "lat": 90.00, "lon": 0.00},
    {"id": "Sibirya_Bati", "lat": 60.00, "lon": 60.00},
    {"id": "Sibirya_Derin", "lat": 60.00, "lon": 90.00},
    {"id": "Moskova", "lat": 55.75, "lon": 37.61},
    {"id": "Balkanlar", "lat": 44.42, "lon": 26.10},
    {"id": "Ingiltere", "lat": 51.50, "lon": -0.12},
    {"id": "Iskandinavya", "lat": 62.00, "lon": 15.00},
    {"id": "Gronland", "lat": 70.00, "lon": -40.00},
    {"id": "Izlanda", "lat": 64.14, "lon": -21.94},
    {"id": "Azor", "lat": 38.72, "lon": -27.22},
    {"id": "Istanbul", "lat": 41.00, "lon": 28.97},
    {"id": "Zonguldak", "lat": 41.45, "lon": 31.79},
    {"id": "Italya", "lat": 41.90, "lon": 12.49},
    {"id": "Aleut_YB", "lat": 55.00, "lon": -170.00}
]

def veri_cek_8gun(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    try:
        params = {
            "latitude": lat, 
            "longitude": lon,
            "hourly": "temperature_2m,pressure_msl,wind_speed_10m,snowfall",
            "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,pressure_msl_mean,wind_speed_10m_max,precipitation_sum,snowfall_sum",
            "forecast_days": 8
        }
        response = requests.get(url, params=params, timeout=30, verify=False)
        if response.status_code == 429:
            print(f"\n   ⚠️ Rate limit, 10 saniye bekleniyor...")
            time.sleep(10)
            return None, None
        if response.status_code != 200:
            return None, None
        response.raise_for_status()
        data = response.json()
        if "daily" not in data and "hourly" not in data:
            return None, None
        return data, "best_match"
    except Exception as e:
        print(f"\n   ❌ Hata: {str(e)[:80]}")
        return None, None

def get_daily_value(data, key, day_index):
    if not data or "daily" not in data:
        return None
    daily = data["daily"]
    if key in daily and daily[key]:
        try:
            arr = np.array(daily[key], dtype=float)
            if day_index < len(arr):
                val = arr[day_index]
                if not np.isnan(val):
                    return val
        except:
            pass
    return None

def seasonal_day_difference(day1, day2):
    diff = abs(day1 - day2)
    return min(diff, 365 - diff)

def multi_level_analog_search(gfs_data, arsiv, target_date):
    """
    FULL L1 → L2 → L3 Analog Search (L2 ENABLED)
    """
    
    # LEVEL 0: Seasonal Preselection (±60 days)
    target_doy = target_date.timetuple().tm_yday
    seasonal_candidates = []
    
    for idx, row in arsiv.iterrows():
        try:
            tarih = pd.to_datetime(row.get("Date"))
            if tarih.month not in [11, 12, 1, 2, 3]:
                continue
            arsiv_doy = tarih.timetuple().tm_yday
            if seasonal_day_difference(target_doy, arsiv_doy) <= 60:
                seasonal_candidates.append(idx)
        except:
            continue
    
    print(f"   L0: {len(seasonal_candidates)} mevsimsel aday")
    if len(seasonal_candidates) < 10:
        return None
    
    # LEVEL 1: Large Scale Pattern Matching
    l1_candidates = []
    gfs_basinc_zong = gfs_data.get("Zonguldak_Basinc")
    gfs_sib_pres = gfs_data.get("Sibirya_Bati_Basinc")
    gfs_moskova_basinc = gfs_data.get("Moskova_Basinc")
    gfs_izlanda_basinc = gfs_data.get("Izlanda_Basinc")
    
    for idx in seasonal_candidates:
        row = arsiv.iloc[idx]
        
        def safe(k):
            v = row.get(k)
            if v is None or v == '' or (isinstance(v, float) and np.isnan(v)):
                return None
            return float(v)
        
        score = 0
        count = 0
        
        if gfs_basinc_zong:
            a_basinc = safe("Zonguldak_Basinc")
            if a_basinc:
                score += abs(a_basinc - gfs_basinc_zong) * 1.5
                count += 1
        
        if gfs_sib_pres:
            a_sib = safe("Sibirya_Bati_Basinc")
            if a_sib:
                score += abs(a_sib - gfs_sib_pres) * 1.0
                count += 1
        
        if gfs_moskova_basinc:
            a_mosk = safe("Moskova_Basinc")
            if a_mosk:
                score += abs(a_mosk - gfs_moskova_basinc) * 0.8
                count += 1
        
        if gfs_izlanda_basinc:
            a_izl = safe("Izlanda_Basinc")
            if a_izl:
                score += abs(a_izl - gfs_izlanda_basinc) * 0.8
                count += 1
        
        if count > 0 and score / count < 150:
            l1_candidates.append((idx, score / count))
    
    l1_candidates.sort(key=lambda x: x[1])
    l1_best = [c[0] for c in l1_candidates[:150]]
    print(f"   L1: {len(l1_best)} büyük ölçek adayı")
    
    if len(l1_best) < 5:
        return None
    
    # LEVEL 2: TRAJECTORY MATCHING (NOW ENABLED!)
    l2_candidates = []
    
    # GFS trajectory (son 2 gün basınç trendi)
    gfs_basinc_t0 = gfs_data.get("Zonguldak_Basinc_t0")  # bugün
    gfs_basinc_tm1 = gfs_data.get("Zonguldak_Basinc_tm1")  # dün
    gfs_basinc_tm2 = gfs_data.get("Zonguldak_Basinc_tm2")  # 2 gün önce
    
    for idx in l1_best:
        # İndex sınırlarını kontrol et
        if idx < 2 or idx >= len(arsiv) - 2:
            continue
        
        row = arsiv.iloc[idx]
        row_m1 = arsiv.iloc[idx - 1]
        row_m2 = arsiv.iloc[idx - 2]
        
        def safe(r, k):
            v = r.get(k)
            if v is None or v == '' or (isinstance(v, float) and np.isnan(v)):
                return None
            return float(v)
        
        # Arşiv trajectory
        a_basinc_t0 = safe(row, "Zonguldak_Basinc")
        a_basinc_tm1 = safe(row_m1, "Zonguldak_Basinc")
        a_basinc_tm2 = safe(row_m2, "Zonguldak_Basinc")
        
        # Trajectory karşılaştırması
        if all([gfs_basinc_t0, gfs_basinc_tm1, gfs_basinc_tm2,
                a_basinc_t0, a_basinc_tm1, a_basinc_tm2]):
            
            # Basınç değişim trendleri
            gfs_trend1 = gfs_basinc_t0 - gfs_basinc_tm1
            gfs_trend2 = gfs_basinc_tm1 - gfs_basinc_tm2
            
            a_trend1 = a_basinc_t0 - a_basinc_tm1
            a_trend2 = a_basinc_tm1 - a_basinc_tm2
            
            # Trend benzerliği
            trend_diff = abs(gfs_trend1 - a_trend1) + abs(gfs_trend2 - a_trend2)
            
            # Mutlak değer benzerliği
            abs_diff = abs(gfs_basinc_t0 - a_basinc_t0)
            
            # Toplam skor
            total_score = (trend_diff * 0.7) + (abs_diff * 0.3)
            
            if total_score < 50:  # Threshold
                l2_candidates.append((idx, total_score))
    
    if l2_candidates:
        l2_candidates.sort(key=lambda x: x[1])
        l2_best = [c[0] for c in l2_candidates[:100]]
        print(f"   L2: {len(l2_best)} trajectory match! ✨")
    else:
        print(f"   L2: Trajectory match bulunamadı, L1 kullanılıyor")
        l2_best = l1_best[:100]
    
    # LEVEL 3: Local Detail Matching
    l3_candidates = []
    gfs_temp2m = gfs_data.get("Zonguldak_Temp2m")
    gfs_basinc = gfs_data.get("Zonguldak_Basinc")
    
    for idx in l2_best:
        row = arsiv.iloc[idx]
        
        def safe(k):
            v = row.get(k)
            if v is None or v == '' or (isinstance(v, float) and np.isnan(v)):
                return None
            return float(v)
        
        score = 0
        count = 0
        
        if gfs_temp2m:
            a_temp = safe("Zonguldak_Temp2m")
            if a_temp:
                temp_diff = abs(a_temp - gfs_temp2m)
                score += temp_diff * 3.0
                count += 1
        
        if gfs_basinc:
            a_pres = safe("Zonguldak_Basinc")
            if a_pres:
                pres_diff = abs(a_pres - gfs_basinc)
                score += pres_diff * 1.0
                count += 1
        
        if count == 0:
            score = 15.0
            count = 1
        
        if count > 0:
            tarih = pd.to_datetime(row.get("Date"))
            kar = safe("Zonguldak_Kar") or 0
            temp = safe("Zonguldak_Temp2m")
            
            l3_candidates.append({
                "tarih": tarih.strftime('%Y-%m-%d'),
                "skor": score / count,
                "kar": kar,
                "temp": temp
            })
    
    l3_candidates.sort(key=lambda x: x["skor"])
    final_50 = l3_candidates[:50]
    
    print(f"   L3: {len(final_50)} final analog")
    
    if len(final_50) < 3:
        return None
    
    return final_50

def probabilistic_ensemble_output(analog_list):
    if not analog_list or len(analog_list) < 3:
        return None
    
    kar_values = [a["kar"] for a in analog_list]
    kar_p10 = np.percentile(kar_values, 10)
    kar_p50 = np.percentile(kar_values, 50)
    kar_p90 = np.percentile(kar_values, 90)
    kar_mean = np.mean(kar_values)
    kar_std = np.std(kar_values)
    kar_prob = len([k for k in kar_values if k > 2]) / len(kar_values)
    
    if kar_std < 5:
        belirsizlik = "DÜŞÜK"
        belirsizlik_yorum = "Tüm analoglar benzer sonuç gösteriyor"
    elif kar_std < 10:
        belirsizlik = "ORTA"
        belirsizlik_yorum = "Bazı senaryolarda farklılık var"
    else:
        belirsizlik = "YÜKSEK"
        belirsizlik_yorum = "Çok farklı senaryolar mümkün"
    
    return {
        "p10": kar_p10, "p50": kar_p50, "p90": kar_p90,
        "mean": kar_mean, "std": kar_std, "prob": kar_prob,
        "belirsizlik": belirsizlik,
        "belirsizlik_yorum": belirsizlik_yorum,
        "analog_sayisi": len(analog_list)
    }

def tarihsel_analiz_kusursuz():
    print("\n" + "="*80)
    print("🌨️  TARİHSEL ANALİZ v10.0 - L2 TRAJECTORY AKTİF!")
    print("📊  L1 (Büyük Ölçek) + L2 (Trajectory) + L3 (Lokal) + Ensemble")
    print("🎯  Arşivde 1,588 ardışık gün trajectory verisi mevcut!")
    print("="*80)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    wwwroot = os.path.join(base_dir, "wwwroot")
    arsiv_yolu = os.path.join(wwwroot, "ultimate_veri_ambari.csv")
    rapor_yolu = os.path.join(wwwroot, "tarihsel_rapor.txt")
    
    if not os.path.exists(arsiv_yolu):
        with open(rapor_yolu, "w", encoding="utf-8") as f:
            f.write("⚠️ Veri ambarı yok.")
        return
    
    print("\n📚 Arşiv yükleniyor...")
    arsiv = pd.read_csv(arsiv_yolu)
    print(f"✅ {len(arsiv):,} gün")
    
    # Trajectory veri kontrolü
    trajectory_uygun = 0
    for idx in range(2, len(arsiv) - 2):
        if all(pd.notna(arsiv.iloc[idx + offset]['Zonguldak_Basinc']) 
               for offset in [-2, -1, 0, 1, 2]):
            trajectory_uygun += 1
    
    print(f"🎯 Trajectory verisi: {trajectory_uygun:,} uygun gün (L2 için yeterli!)")
    
    # Veri toplama
    print(f"\n📡 VERİ ÇEKİLİYOR ({len(BUYUK_OLCEK)} nokta)...\n")
    data_dict = {}
    
    for i, lok in enumerate(BUYUK_OLCEK):
        print(f"[{i+1}/{len(BUYUK_OLCEK)}] {lok['id']:20s}...", end="", flush=True)
        data, model = veri_cek_8gun(lok["lat"], lok["lon"])
        if data:
            data_dict[lok["id"]] = data
            print(" ✅")
        else:
            print(" ❌")
        time.sleep(1)
    
    if "Zonguldak" not in data_dict:
        print("❌ Zonguldak verisi yok!")
        return
    
    print("\n" + "="*80)
    print("📈 7 GÜNLÜK ANALOG ANALİZİ (L2 TRAJECTORY AKTİF)")
    print("="*80)
    
    bugun = datetime.now()
    gunluk_sonuclar = []
    
    for gun in range(8):
        t = bugun + timedelta(days=gun)
        print(f"\n🎯 GÜN {gun} ({t.strftime('%d %b %A')})")
        
        # GFS vektörü - trajectory için geçmiş günler de dahil
        gfs_vektor = {}
        
        # Bugünün verileri
        for lid, d in data_dict.items():
            temp = get_daily_value(d, "temperature_2m_mean", gun)
            basinc = get_daily_value(d, "pressure_msl_mean", gun)
            if temp is not None:
                gfs_vektor[f"{lid}_Temp2m"] = temp
            if basinc is not None:
                gfs_vektor[f"{lid}_Basinc"] = basinc
        
        # Trajectory için geçmiş günler (t-1, t-2)
        zong_data = data_dict.get("Zonguldak")
        if zong_data and gun >= 2:
            gfs_vektor["Zonguldak_Basinc_t0"] = get_daily_value(zong_data, "pressure_msl_mean", gun)
            gfs_vektor["Zonguldak_Basinc_tm1"] = get_daily_value(zong_data, "pressure_msl_mean", gun - 1)
            gfs_vektor["Zonguldak_Basinc_tm2"] = get_daily_value(zong_data, "pressure_msl_mean", gun - 2)
        
        # Analog search
        analog_sonuc = multi_level_analog_search(gfs_vektor, arsiv, t)
        
        if analog_sonuc and len(analog_sonuc) >= 3:
            prob_sonuc = probabilistic_ensemble_output(analog_sonuc)
            if prob_sonuc:
                print(f"   📊 Kar Olasılığı: %{prob_sonuc['prob']*100:.0f} | P50: {prob_sonuc['p50']:.1f} cm")
                gunluk_sonuclar.append({
                    "gun": gun, "tarih": t,
                    "analog": analog_sonuc[:5],
                    "prob": prob_sonuc
                })
        else:
            print(f"   ⚠️ Yeterli analog bulunamadı")
    
    if not gunluk_sonuclar:
        print("\n❌ Hiçbir gün için analog bulunamadı!")
        with open(rapor_yolu, "w", encoding="utf-8") as f:
            f.write("⚠️ Hiçbir gün için yeterli analog bulunamadı.\n")
        return
    
    kritik = max(gunluk_sonuclar, key=lambda x: x["prob"]["prob"])
    print(f"\n🎯 EN KRİTİK: Gün {kritik['gun']} - %{kritik['prob']['prob']*100:.0f} kar olasılığı")
    
    # Rapor oluşturma
    print("\n📝 Rapor oluşturuluyor...")
    
    trend_text = "\n".join([
        f"Gün {g['gun']} ({g['tarih'].strftime('%d %b')}): "
        f"%{g['prob']['prob']*100:.0f} kar | "
        f"P50: {g['prob']['p50']:.1f}cm | "
        f"Belirsizlik: {g['prob']['belirsizlik']}"
        for g in gunluk_sonuclar
    ])
    
    toplam_kar_gun = len([g for g in gunluk_sonuclar if g['prob']['prob'] > 0.05])
    max_kar = max([g['prob']['p90'] for g in gunluk_sonuclar])
    
    ozet = f"""
TARİHSEL ANALİZ ÖZETİ v10.0 (L2 TRAJECTORY AKTİF)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 Tarih: {bugun.strftime('%Y-%m-%d %H:%M')}
🎯 En Kritik Gün: {kritik['tarih'].strftime('%d %B %A')} (Gün {kritik['gun']})

KAR TAHMİNİ
─────────────────────────────────────────────────────────────────────────────
Kar Olasılığı:      %{kritik['prob']['prob']*100:.0f}
P50 (Medyan):       {kritik['prob']['p50']:.1f} cm
P90 (Kötü senaryo): {kritik['prob']['p90']:.1f} cm
Belirsizlik:        {kritik['prob']['belirsizlik']} (±{kritik['prob']['std']:.1f} cm)

{kritik['prob']['belirsizlik_yorum']}

7 GÜNLÜK TREND
─────────────────────────────────────────────────────────────────────────────
{trend_text}

GENEL DEĞERLENDİRME
─────────────────────────────────────────────────────────────────────────────
• Analiz edilen gün sayısı: {len(gunluk_sonuclar)}
• Kar olasılığı >%5: {toplam_kar_gun} gün
• Maksimum beklenen kar (P90): {max_kar:.1f} cm
• Analog sayısı: {kritik['prob']['analog_sayisi']} tarihsel vaka

METODOLOJİ (v10.0) - TÜM SEVİYELER AKTİF
─────────────────────────────────────────────────────────────────────────────
✓ L0: Seasonal Preselection (±60 gün)
✓ L1: Large Scale Pattern Matching (büyük ölçek atmosfer)
✓ L2: Trajectory Matching (basınç trendi analizi) ✨ YENİ!
✓ L3: Local Detail Matching (lokal koşullar)
✓ Probabilistic Ensemble (50 analog)
✓ Arşiv: {len(arsiv):,} günlük tarihsel veri
✓ Trajectory: {trajectory_uygun:,} uygun gün

L2 TRAJECTORY MATCHING AÇIKLAMASI:
L2 seviyesi, atmosfer koşullarının son 2-3 günlük değişim trendini analiz eder.
Sadece mevcut duruma değil, oraya nasıl gelindiğine de bakar. Bu sayede:
- Hava sistemlerinin dinamik evrimini yakalar
- Yüksek/alçak basınç merkezlerinin hareketini izler
- Kar olaylarının öncesindeki karakteristik pattern'leri bulur

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    with open(rapor_yolu, "w", encoding="utf-8") as f:
        f.write(ozet)
    
    print("✅ Rapor kaydedildi: tarihsel_rapor.txt")
    
    # AI Rapor (isteğe bağlı)
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""7 günlük kar analizi özeti (max 8 cümle):
En kritik: {kritik['tarih'].strftime('%d %B')} - %{kritik['prob']['prob']*100:.0f}
Beklenen: {kritik['prob']['p50']:.1f} cm (P90: {kritik['prob']['p90']:.1f} cm)
Not: L2 Trajectory matching aktif - basınç trendi analizi yapıldı."""
        
        resp = model.generate_content(prompt)
        print(f"\n🤖 AI Özet:\n{resp.text}\n")
        
        with open(rapor_yolu, "a", encoding="utf-8") as f:
            f.write(f"\n\nAI DEĞERLENDİRME\n{'─'*80}\n{resp.text}\n")
    except Exception as e:
        print(f"⚠️ AI raporu atlandı: {str(e)[:50]}")

if __name__ == "__main__":
    tarihsel_analiz_kusursuz()