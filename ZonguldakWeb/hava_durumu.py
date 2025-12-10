import sys
import io
import os
import json
import datetime

# --- UTF-8 ZORLAMASI ---
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import google.generativeai as genai

# --- API ANAHTARI ---
API_KEY = "AIzaSyAA0r5kXRkOQ_uLBwuj77nY89-YhYJ8P9s"

def sistem_avcisi_hibrit():
    # --- YOL AYARLARI ---
    base_dir = os.path.dirname(os.path.abspath(__file__))
    wwwroot_dir = os.path.join(base_dir, "wwwroot")
    if not os.path.exists(wwwroot_dir): os.makedirs(wwwroot_dir)
        
    rapor_yolu = os.path.join(wwwroot_dir, "rapor.txt")
    json_yolu = os.path.join(wwwroot_dir, "grafik_verisi.json")
    resim_bilgi_yolu = os.path.join(wwwroot_dir, "son_resim.txt")
    
    # ARŞİV İÇİN BENZERSİZ İSİM
    zaman_damgasi = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dosya_ismi = f"zonguldak_analiz_{zaman_damgasi}.png"
    resim_yolu = os.path.join(wwwroot_dir, dosya_ismi)

    print("--- SISTEM AVCISI v16.0 (Hibrit Mod: JSON + PNG) ---")
    print("--- Hem Interaktif Veri Hem Arsiv Resmi Hazirlaniyor... ---")

    # 1. API ISTEGI
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 41.45, "longitude": 31.79,
        "hourly": "temperature_850hPa,temperature_2m,snowfall,rain,wind_speed_10m,wind_direction_10m",
        "timezone": "auto", "forecast_days": 7,
        "models": "ecmwf_ifs04,icon_seamless,gfs_seamless,gem_seamless" 
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"HATA: {e}")
        return

    # 2. VERI ISLEME
    hourly = data["hourly"]
    dates_raw = pd.to_datetime(hourly["time"])
    
    # Gun isimleri
    gunler_tr = ["Pazartesi", "Sali", "Carsamba", "Persembe", "Cuma", "Cumartesi", "Pazar"]
    dates_str = []
    for d in dates_raw:
        gun_ismi = gunler_tr[d.weekday()]
        dates_str.append(f"{d.strftime('%d %b')} {gun_ismi} {d.strftime('%H:00')}")

    df = pd.DataFrame({"Tarih": dates_raw})

    def get_data(key):
        val = hourly.get(key, [None]*len(df))
        return [None if x is None or np.isnan(x) else x for x in val]

    ecmwf = get_data("temperature_850hPa_ecmwf_ifs04")
    icon = get_data("temperature_850hPa_icon_seamless")
    gfs = get_data("temperature_850hPa_gfs_seamless")
    gem = get_data("temperature_850hPa_gem_seamless")
    
    yagmur = get_data("rain_gfs_seamless")
    kar = get_data("snowfall_gfs_seamless")
    ruzgar_hizi = get_data("wind_speed_10m_gfs_seamless")
    ruzgar_yonu = get_data("wind_direction_10m_gfs_seamless")

    # Konsensus
    temp_df = pd.DataFrame({"e": ecmwf, "i": icon, "g": gfs, "gm": gem})
    konsensus = temp_df.mean(axis=1).tolist()
    # Grafik icin NaN kontrolu
    konsensus_clean = [round(x, 1) if not np.isnan(x) else None for x in konsensus]

    # Yer Sicakligi
    temp_2m_raw = []
    for model in ["ecmwf_ifs04", "icon_seamless", "gfs_seamless", "gem_seamless"]:
        k = f"temperature_2m_{model}"
        if k in hourly: temp_2m_list = hourly[k]
        else: temp_2m_list = [None]*len(df)
        temp_2m_raw.append(temp_2m_list)
    
    yer_konsensus = pd.DataFrame(temp_2m_raw).T.mean(axis=1).tolist()
    yer_clean = [round(x, 1) if not np.isnan(x) else None for x in yer_konsensus]

    # 3. JSON KAYDET (ANA SAYFA İÇİN)
    grafik_paketi = {
        "categories": dates_str,
        "series": [
            {"name": "ECMWF", "data": ecmwf},
            {"name": "ICON", "data": icon},
            {"name": "GFS", "data": gfs},
            {"name": "GEM", "data": gem},
            {"name": "ORTALAMA", "data": konsensus_clean},
            {"name": "Yer Sicakligi (2m)", "data": yer_clean}
        ]
    }

    with open(json_yolu, "w", encoding="utf-8") as f:
        json.dump(grafik_paketi, f)
    print("JSON Paketi Hazir.")

    # 4. PNG RESİM KAYDET (ARŞİV İÇİN)
    print("Arsiv Resmi Ciziliyor...")
    try:
        # Pandas DataFrame'e geri yukleyelim cizim icin
        df["ECMWF"] = ecmwf
        df["ICON"] = icon
        df["GFS"] = gfs
        df["GEM"] = gem
        df["Konsensus"] = konsensus
        df["Yer"] = yer_konsensus

        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        # Baslik
        plt.title(f"Zonguldak Analiz Arsivi ({zaman_damgasi})", fontsize=12)
        
        # Sol Eksen
        ax1.set_ylabel("850hPa (C)", color="blue")
        ax1.plot(df["Tarih"], df["ECMWF"], color="cyan", alpha=0.4)
        ax1.plot(df["Tarih"], df["ICON"], color="orange", alpha=0.4)
        ax1.plot(df["Tarih"], df["GFS"], color="red", alpha=0.4)
        ax1.plot(df["Tarih"], df["GEM"], color="green", alpha=0.4)
        ax1.plot(df["Tarih"], df["Konsensus"], color="blue", linewidth=2, label="ORTALAMA")
        ax1.axhline(y=-6, color='purple', linestyle='-')

        # Sag Eksen
        ax2 = ax1.twinx()
        ax2.set_ylabel("Yer (2m)", color="gray")
        ax2.plot(df["Tarih"], df["Yer"], color="gray", linestyle="--", label="Yer")
        ax2.axhline(y=0, color='black', linestyle=':')

        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        plt.tight_layout()
        
        # Resmi Kaydet
        plt.savefig(resim_yolu)
        print(f"Resim Kaydedildi: {dosya_ismi}")
        
        # Resim ismini C#'a bildir
        with open(resim_bilgi_yolu, "w", encoding="utf-8") as f:
            f.write(f"/{dosya_ismi}")

    except Exception as e:
        print(f"Grafik Hatasi: {e}")

    # 5. RAPORLAMA
    idx_now = 0 
    valid_k = [x for x in konsensus if x is not None and not np.isnan(x)]
    min_val = min(valid_k) if valid_k else 0
    idx_future = konsensus.index(min_val)
    
    def fmt(x): return f"{x:.1f}" if x is not None and not np.isnan(x) else "?"
    
    # Ruzgar Yonu
    def get_yon(d):
        if d is None or np.isnan(d): return "?"
        dirs = ["Kuzey", "Kuzeydogu", "Dogu", "Guneydogu", "Guney", "Guneybati", "Bati", "Kuzeybati"]
        ix = round(d / 45) % 8
        return dirs[ix]

    modeller_text = "\n".join(filter(None, [
        f"- ECMWF: {fmt(ecmwf[idx_future])}" if ecmwf[idx_future] else "",
        f"- ICON: {fmt(icon[idx_future])}" if icon[idx_future] else "",
        f"- GFS: {fmt(gfs[idx_future])}" if gfs[idx_future] else "",
        f"- GEM: {fmt(gem[idx_future])}" if gem[idx_future] else ""
    ]))

    print("Yapay Zeka Raporluyor...")
    prompt = f"""
    Sen Zonguldak Meteoroloji Uzmanisin.
    
    BOLUM 1: BUGUN ({dates_str[idx_now]})
    - Gok (850hPa): {fmt(konsensus[idx_now])} C
    - Yer (2m): {fmt(yer_konsensus[idx_now])} C
    - Yagmur: {fmt(yagmur[idx_now])} mm
    - Ruzgar: {fmt(ruzgar_hizi[idx_now])} km/s ({get_yon(ruzgar_yonu[idx_now])})
    
    BOLUM 2: GELECEK ({dates_str[idx_future]})
    - Gok (850hPa): {fmt(konsensus[idx_future])} C
    - Yer (2m): {fmt(yer_konsensus[idx_future])} C
    
    MODELLER:
    {modeller_text}

    GÖREV:
    Bugunu anlat (ruzgar ve yagmur dahil).
    Gelecegi analiz et (-6 dereceye iniyor mu?).
    ECMWF yoksa bahsetme.
    """
    
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        with open(rapor_yolu, "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Rapor Yazildi.")
        
    except Exception as e:
        print(f"AI Hatasi: {e}")

if __name__ == "__main__":
    sistem_avcisi_hibrit()