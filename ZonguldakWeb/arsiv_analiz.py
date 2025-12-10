import pandas as pd
import numpy as np

arsiv = pd.read_csv("wwwroot/ultimate_veri_ambari.csv")

# Zonguldak_Temp2m kolonunu kontrol et
print("📊 ARŞİV ANALİZİ\n")
print(f"Toplam satır: {len(arsiv):,}")
print(f"\nKolon adları (ilk 20):")
print(list(arsiv.columns)[:20])

# Zonguldak ile ilgili kolonları bul
zong_cols = [col for col in arsiv.columns if 'Zonguldak' in col]
print(f"\n🎯 Zonguldak Kolonları ({len(zong_cols)} adet):")
for col in zong_cols[:10]:
    missing = arsiv[col].isna().sum()
    print(f"  {col:30s} - Eksik: {missing:,} (%{missing/len(arsiv)*100:.1f})")

# Ardışık veri kontrolü
if 'Zonguldak_Temp2m' in arsiv.columns:
    print(f"\n🔍 ARDIŞIK VERİ ANALİZİ (Zonguldak_Temp2m):")
    
    suitable = 0
    for idx in range(2, len(arsiv) - 2):
        has_all = True
        for offset in [-2, -1, 0, 1, 2]:
            val = arsiv.iloc[idx + offset]['Zonguldak_Temp2m']
            if pd.isna(val):
                has_all = False
                break
        if has_all:
            suitable += 1
    
    print(f"  5 günlük tam trajectory: {suitable:,} adet")
    print(f"  Uygunluk: %{suitable/(len(arsiv)-4)*100:.1f}")
    
    if suitable == 0:
        print(f"\n  ❌ HİÇ ARDIŞIK VERİ YOK!")
        print(f"  💡 ÇÖZÜMLERİ:")
        print(f"     1. Veri toplama scriptini çalıştırın")
        print(f"     2. 'Zonguldak_Temp2m' yerine başka kolon kullanın")
        print(f"     3. L2'yi devre dışı bırakın (şu anki durum)")