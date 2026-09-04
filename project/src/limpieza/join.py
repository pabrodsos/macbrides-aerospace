import pandas as pd
import warnings
warnings.filterwarnings("ignore")

base = "../../data/processed"
dfs = []
for año in [2024, 2025]:
    for mes in [1, 11, 12]:
        for (init, end) in [[1, 8], [8, 15], [15, 22], [22, 29], [29, 32]]:
            try:
                path = f"{base}/{año}/{mes}/{init}_{end}.parquet"
                dfs.append(pd.read_parquet(path))
            except:
                pass
df = pd.concat(dfs)
df.to_parquet(f"../../data/join/all.parquet")