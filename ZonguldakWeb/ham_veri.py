import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import numpy as np
import sys
import io
import shutil
import os

# UTF-8 Ayarı
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_et():
    print("🔍 GERÇEK VERİ KONTROLÜ (CACHE TEMİZLİKLİ)...")
    
    # 1. Önce eski cache'i silelim ki taze veri gelsin
    if os.path.exists(".cache"):
        try:
            shutil.rmtree(".cache")
            print("🧹 Eski önbellek (.cache) temizlendi.")
        except:
            print("⚠️ Önbellek silinemedi, devam ediliyor.")

    url = "https://api.open-meteo.com/v1/forecast"
    
    # İngiltere (Londra) Basıncı
    params = {
        "latitude": 51.50, "longitude": -0.12,
        "hourly": "pressure_msl",
        "models": "gfs_seamless", # GFS deneyelim
        "forecast_days": 1
    }
    
    try:
        # Cache süresini 0 yapıyoruz (Hep taze çek)
        cache_session = requests_cache.CachedSession('.cache', expire_after = 0)
        retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
        openmeteo = openmeteo_requests.Client(session = retry_session)

        responses = openmeteo.weather_api(url, params=params)
        r = responses[0]
        
        # Ham veriyi al
        basinc_verileri = r.Hourly().Variables(0).ValuesAsNumpy()
        
        print(f"\n--- GFS MODELİ İLE İNGİLTERE BASINCI ---")
        print("(İlk 5 Saat)")
        
        for i in range(5):
            val = basinc_verileri[i]
            durum = "❌ BOŞ (nan)" if np.isnan(val) else f"{val} mb"
            print(f"Saat {i}: {durum}")
            
        # Analiz
        val = float(basinc_verileri[0])
        print(f"\n--- ANALİZ SONUCU ---")
        
        if np.isnan(val):
             print("❌ KRİTİK HATA: API hala 'nan' (boş) dönüyor.")
             print("   Sebep: Open-Meteo sunucularında GFS verisi anlık olarak eksik olabilir.")
             print("   Çözüm: Birkaç saat sonra tekrar denenmeli veya 'icon_seamless' modeli denenmeli.")
        elif val.is_integer():
             print(f"⚠️ UYARI: Veri tam sayı geldi: {val}")
             print("   Bilgi: Bu bir hata olmayabilir, model o an tam 1012.0 ölçmüş olabilir.")
        else:
             print(f"✅ BAŞARILI: Küsuratlı gerçek veri geldi: {val}")
             print("   (Örn: 1012.34 gibi hassas veri)")
             
    except Exception as e:
        print(f"❌ BAĞLANTI HATASI: {e}")

if __name__ == "__main__":
    test_et()