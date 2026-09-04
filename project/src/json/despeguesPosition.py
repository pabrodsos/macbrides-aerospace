import pandas as pd
import json

dfs = []
for i in range(1, 8):
    temp = pd.read_parquet(f"../../data/filtrado/despegues/0{i}-12-2024.parquet")
    temp["day"] = i
    dfs.append(temp)
df = pd.concat(dfs).drop_duplicates(subset=["icao", "flight_id", "day"])
cols = [ 'lat_despegue', 'lon_despegue', 'lat_despegue_onground', 'lon_despegue_onground' ]
result = {}
for rw, g in df.groupby('runway'):
    stats = {}
    for col in cols:
        series = g[col].dropna()
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        stats[col] = series.median()
    result[rw] = stats
with open('runway_takeoffs_centers.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)