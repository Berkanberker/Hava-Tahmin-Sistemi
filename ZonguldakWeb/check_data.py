import pandas as pd
df = pd.read_csv("wwwroot/ultimate_veri_ambari.csv")
print("Dolu kolonlar:")
for col in df.columns:
    dolu = df[col].notna().sum()
    if dolu > 0:
        print(f"  {col}: {dolu}/{len(df)}")