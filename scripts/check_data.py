"""Check bundled Parquet data without modifying data or loading models."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "project" / "data"
TARGET = "tiempo_hasta_despegue"

def main():
    expected = [
        "join/all.parquet", "join/data.parquet", "join/data_cleaned.parquet",
        "join/data_sampled.parquet", "train/train_con_outliers.parquet",
        "train/train_sin_outliers.parquet", "test/test_con_outliers.parquet",
        "test/test_sin_outliers.parquet",
    ]
    tables = {}
    for name in expected:
        path = DATA / name
        if not path.is_file():
            raise FileNotFoundError(f"Missing bundled dataset: {path}")
        frame = pd.read_parquet(path)
        if frame.empty:
            raise ValueError(f"Empty dataset: {name}")
        tables[name] = frame
        print(f"{name}: {len(frame):,} rows x {len(frame.columns)} columns")
    for variant in ("con_outliers", "sin_outliers"):
        train = tables[f"train/train_{variant}.parquet"]
        test = tables[f"test/test_{variant}.parquet"]
        if TARGET not in train or TARGET not in test:
            raise ValueError(f"Missing target for {variant}: {TARGET}")
        if set(train.columns) != set(test.columns):
            raise ValueError(f"Train/test columns differ for {variant}")
    print("OK: all 8 datasets are readable; train/test columns are compatible.")

if __name__ == "__main__":
    main()
