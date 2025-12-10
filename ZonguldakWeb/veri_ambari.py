import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import os
import time
from datetime import datetime
from functools import reduce
from concurrent.futures import ThreadPoolExecutor, as_completed

def veri_ambari_optimize():
    print("\n" + "="*60)
    print("🌍 ZONGULDAK VERİ TOPLAMA v6.1 (DÜZELTİLMİŞ)")
    print("   Kasım-Mart Kış Ayları - Paralel Hızlı")
    print("="*60 + "\n")

    # Cache ve Retry
    cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    url = "https://archive-api.open-meteo.com/v1/archive"
    
    baslangic_yili = 2015
    bitis_yili = datetime.now().year
    
    print(f"📆 Yıl Aralığı: {baslangic_yili} - {bitis_yili}")
    print(f"📅 Sezon: Kasım-Mart (Kış Ayları)\n")

    # 14 STRATEJİK NOKTA (Jet lokasyonları kaldırıldı - API desteklemiyor)
    lokasyonlar = [
        {"id": "Zonguldak",      "lat": 41.4564, "lon": 31.7987, "tip": "hedef"},
        {"id": "Istanbul",       "lat": 41.0082, "lon": 28.9784, "tip": "hedef"},
        {"id": "Moskova",        "lat": 55.7558, "lon": 37.6173, "tip": "sinoptik"}, 
        {"id": "Sibirya_Bati",   "lat": 60.00,   "lon": 60.00,   "tip": "sinoptik"},
        {"id": "Sibirya_Derin",  "lat": 60.00,   "lon": 90.00,   "tip": "sinoptik"},
        {"id": "Iskandinavya",   "lat": 62.00,   "lon": 15.00,   "tip": "sinoptik"},
        {"id": "Izlanda",        "lat": 64.14,   "lon": -21.94,  "tip": "sinoptik"},
        {"id": "Azor",           "lat": 38.72,   "lon": -27.22,  "tip": "sinoptik"},
        {"id": "Gronland",       "lat": 70.00,   "lon": -40.00,  "tip": "sinoptik"},
        {"id": "Ingiltere",      "lat": 51.50,   "lon": -0.12,   "tip": "sinoptik"},
        {"id": "Italya",         "lat": 41.90,   "lon": 12.49,   "tip": "sinoptik"},
        {"id": "Balkanlar",      "lat": 44.42,   "lon": 26.10,   "tip": "sinoptik"},
        {"id": "Kutup_Merkez",   "lat": 90.00,   "lon": 0.00,    "tip": "stratosfer"},
        {"id": "Aleut_YB",       "lat": 55.00,   "lon": -170.00, "tip": "sinoptik"}
    ]
    
    # Kış sezonlarını hazırla
    kis_sezonlari = []
    for yil in range(baslangic_yili, bitis_yili + 1):
        if yil > baslangic_yili:
            start = f"{yil-1}-11-01"
            end = f"{yil}-03-31"
        else:
            start = f"{yil}-01-01"
            end = f"{yil}-03-31"
        
        if datetime.strptime(start, '%Y-%m-%d') <= datetime.now():
            kis_sezonlari.append((start, end, yil))
    
    print(f"📊 Toplam: {len(kis_sezonlari)} sezon × {len(lokasyonlar)} lokasyon\n")
    print("="*60)
    
    # Paralel veri çekme
    def fetch_location_data(lok_index, lok):
        isim = lok["id"]
        
        # Parametre belirleme
        if lok["tip"] == "hedef": 
            daily_params = ["temperature_2m_mean", "pressure_msl_mean", 
                          "snowfall_sum", "rain_sum"]
        elif lok["tip"] == "stratosfer": 
            daily_params = ["pressure_msl_mean"]
        elif lok["tip"] == "jet": 
            daily_params = ["wind_speed_10m_mean", "wind_direction_10m_mean"]
        else:
            daily_params = ["temperature_2m_mean", "pressure_msl_mean", 
                          "wind_speed_10m_mean"]
        
        lokasyon_dfs = []
        basarili_sezon = 0
        
        for start_date, end_date, yil in kis_sezonlari:
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                try:
                    params = {
                        "latitude": lok["lat"], 
                        "longitude": lok["lon"],
                        "start_date": start_date, 
                        "end_date": end_date,
                        "daily": daily_params, 
                        "timezone": "auto"
                    }
                    
                    responses = openmeteo.weather_api(url, params=params)
                    response = responses[0]
                    daily = response.Daily()
                    
                    # Tarih aralığı
                    dates = pd.date_range(
                        start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                        end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                        freq=pd.Timedelta(seconds=daily.Interval()),
                        inclusive="left"
                    )
                    
                    temp_df = pd.DataFrame({"Date": dates})
                    
                    # Veri alma helper
                    def get_var(idx): 
                        try:
                            data = daily.Variables(idx).ValuesAsNumpy()
                            # NaN kontrolü
                            if data is None or len(data) == 0:
                                return None
                            return data
                        except Exception as e:
                            print(f"      ⚠️  {isim} {yil} var{idx}: {str(e)[:30]}")
                            return None
                    
                    # Verileri kolonlara aktar
                    if lok["tip"] == "hedef":
                        temp_df[f"{isim}_Temp2m"] = get_var(0)
                        temp_df[f"{isim}_Basinc"] = get_var(1)
                        temp_df[f"{isim}_Kar"] = get_var(2)
                        temp_df[f"{isim}_Yagmur"] = get_var(3)
                    elif lok["tip"] == "stratosfer":
                        temp_df[f"{isim}_Basinc"] = get_var(0)
                    elif lok["tip"] == "jet":
                        temp_df[f"{isim}_Ruzgar"] = get_var(0)
                        temp_df[f"{isim}_Yon"] = get_var(1)
                    else:
                        temp_df[f"{isim}_Temp2m"] = get_var(0)
                        temp_df[f"{isim}_Basinc"] = get_var(1)
                        temp_df[f"{isim}_Ruzgar"] = get_var(2)

                    # Eksik veri doldurma
                    temp_df = temp_df.ffill().bfill()
                    
                    # Veri kalite kontrolü
                    valid_rows = temp_df.notna().all(axis=1).sum()
                    if valid_rows > 0:
                        lokasyon_dfs.append(temp_df)
                        basarili_sezon += 1
                        break  # Başarılı, retry'dan çık
                    else:
                        print(f"      ⚠️  {isim} {yil}: Tüm veriler NaN")
                        retry_count += 1
                        time.sleep(0.5)
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"   ❌ {isim} {yil}: {str(e)[:50]}")
                    else:
                        time.sleep(0.5)
        
        # Lokasyon verilerini birleştir
        if lokasyon_dfs:
            lokasyon_df = pd.concat(lokasyon_dfs, ignore_index=True)
            # Kalite raporu
            total_rows = len(lokasyon_df)
            valid_rows = lokasyon_df.notna().all(axis=1).sum()
            quality = (valid_rows / total_rows * 100) if total_rows > 0 else 0
            
            return (lok_index, isim, lokasyon_df, basarili_sezon, quality)
        
        return None
    
    # PARALEL İŞLEM - 3 thread (daha stabil)
    print("🚀 Paralel indirme başlıyor (3 thread)...\n")
    
    dataframes = [None] * len(lokasyonlar)
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fetch_location_data, i, lok): (i, lok["id"]) 
            for i, lok in enumerate(lokasyonlar)
        }
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    lok_index, isim, df, sezon_sayisi, kalite = result
                    dataframes[lok_index] = df
                    print(f"✅ [{lok_index+1:2d}/{len(lokasyonlar)}] {isim:20s} | "
                          f"{len(df):,} gün | {sezon_sayisi} sezon | Kalite: %{kalite:.1f}")
                else:
                    lok_index, isim = futures[future]
                    print(f"❌ [{lok_index+1:2d}/{len(lokasyonlar)}] {isim:20s} | VERİ ALINAMADI")
                    
            except KeyboardInterrupt:
                print("\n⚠️  Kullanıcı tarafından durduruldu!")
                executor.shutdown(wait=False, cancel_futures=True)
                raise
            except Exception as e:
                lok_index, isim = futures[future]
                print(f"❌ [{lok_index+1:2d}/{len(lokasyonlar)}] {isim:20s} | {str(e)[:40]}")
    
    # None'ları filtrele
    dataframes = [df for df in dataframes if df is not None]

    # BİRLEŞTİRME
    print("\n" + "="*60)
    print("🔄 Veriler birleştiriliyor...")
    
    if not dataframes:
        print("❌ Hiç veri indirilemedi!")
        return
    
    # DEBUG: İlk birkaç dataframe'in tarihlerini kontrol et
    print("\n🔍 DEBUG - Tarih Kontrolü:")
    for i, df in enumerate(dataframes[:3]):
        if df is not None and len(df) > 0:
            print(f"   DF{i}: İlk tarih = {df['Date'].iloc[0]}, Son tarih = {df['Date'].iloc[-1]}, Tip = {type(df['Date'].iloc[0])}")
    
    # Tüm Date kolonlarını string'e çevir (merge öncesi)
    for i, df in enumerate(dataframes):
        if df is not None and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    
    ana_df = reduce(lambda left, right: pd.merge(left, right, on='Date', how='inner'), 
                    dataframes)
    
    print(f"   Merge sonrası satır sayısı: {len(ana_df)}")
    
    if len(ana_df) == 0:
        print("\n❌ MERGE SONRASI 0 SATIR!")
        print("   İlk iki dataframe'i kontrol edelim:")
        if len(dataframes) >= 2:
            print(f"\n   DF1 tarihleri (ilk 5): {dataframes[0]['Date'].head().tolist()}")
            print(f"   DF2 tarihleri (ilk 5): {dataframes[1]['Date'].head().tolist()}")
            print(f"\n   Ortak tarih sayısı: {len(set(dataframes[0]['Date']).intersection(set(dataframes[1]['Date'])))}")
        return
    
    ana_df = ana_df.sort_values(by="Date")
    
    # KAYIT
    base_dir = os.path.dirname(os.path.abspath(__file__))
    hedef_klasor = os.path.join(base_dir, "wwwroot")
    os.makedirs(hedef_klasor, exist_ok=True)
    
    kayit_yolu = os.path.join(hedef_klasor, "ultimate_veri_ambari.csv")
    ana_df.to_csv(kayit_yolu, index=False)
    
    print("\n" + "="*60)
    print("🎉 VERİ AMBARI GÜNCELLENDİ!")
    print(f"📂 Dosya: {kayit_yolu}")
    print(f"📊 Toplam Satır: {len(ana_df):,}")
    print(f"📈 Değişken Sayısı: {len(ana_df.columns)}")
    
    # KALİTE RAPORU
    print("\n🔍 VERİ KALİTE RAPORU:")
    
    kritik_kolonlar = [
        "Zonguldak_Temp2m", "Zonguldak_Basinc",
        "Istanbul_Temp2m", "Moskova_Temp2m"
    ]
    
    for col in kritik_kolonlar:
        if col in ana_df.columns:
            dolu = ana_df[col].notna().sum()
            oran = (dolu / len(ana_df) * 100) if len(ana_df) > 0 else 0
            durum = "✅" if oran > 80 else "⚠️" if oran > 50 else "❌"
            print(f"   {durum} {col:25s}: {dolu:,}/{len(ana_df):,} (%{oran:.1f})")
        else:
            print(f"   ❌ {col:25s}: KOLON YOK")
    
    # ARDIŞIK VERİ ANALİZİ
    if 'Zonguldak_Temp2m' in ana_df.columns:
        suitable = 0
        for idx in range(2, len(ana_df) - 2):
            has_all = all(
                pd.notna(ana_df.iloc[idx + offset]['Zonguldak_Temp2m'])
                for offset in [-2, -1, 0, 1, 2]
            )
            if has_all:
                suitable += 1
        
        print(f"\n🎯 ARDIŞIK VERİ (5 günlük trajectory):")
        print(f"   Uygun günler: {suitable:,} / {len(ana_df)-4:,}")
        if suitable > 0:
            print(f"   ✅ Trajectory analizi yapılabilir!")
        else:
            print(f"   ❌ Ardışık veri yok - L2 regresyonu devre dışı!")
    
    print("="*60)

if __name__ == "__main__":
    try:
        veri_ambari_optimize()
    except KeyboardInterrupt:
        print("\n\n⚠️  Program kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"\n❌ HATA: {str(e)}")
        import traceback
        traceback.print_exc()