import pandas as pd
import numpy as np
import joblib
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OrdinalEncoder, RobustScaler, FunctionTransformer
from sklearn.compose import ColumnTransformer
import warnings

warnings.filterwarnings("ignore")

def get_ct_feature_names(ct: ColumnTransformer) -> list[str]:
    feature_names: list[str] = []
    for name, transformer, cols in ct.transformers_:
        if name == 'remainder' or transformer == 'drop':
            continue
        if transformer == 'passthrough':
            feature_names.extend(cols)
            continue
        if isinstance(transformer, Pipeline):
            last_step = transformer.steps[-1][1]
            if hasattr(last_step, 'get_feature_names_out'):
                names = last_step.get_feature_names_out(cols)
            else:
                names = cols
        elif hasattr(transformer, 'get_feature_names_out'):
            names = transformer.get_feature_names_out(cols)
        else:
            names = cols
        feature_names.extend(names)
    return feature_names

# Cargar datos
df = pd.read_parquet("../../data/join/data_sampled.parquet")
df = df.dropna(subset="wake_vortex")
df = df[df["tiempo_hasta_despegue"]>=0]

# Definir categorías de variables
inutiles = ["icao", "flight_id"]
metereologicas_numeric = ["wind_speed", "wind_dir", "temp"]
metereologicas_categoric = ["wind_shear"]
temporales = ["month", "day_of_week", "day", "hour"]
categoricas = ["runway", "holding_point_id", "wake_vortex", "tipo_avion_ultimo_despegue",
               "holding_ocupado", "pista_ocupada", "en_camino_antes"]
despegues_previos = ["despegues_previos_1h", "despegues_previos_45m", "despegues_previos_30m",
                     "despegues_previos_20m", "despegues_previos_10m", "despegues_previos_5m"]
media_diff = ["media_diff_1h", "media_diff_45m", "media_diff_30m",
              "media_diff_20m", "media_diff_10m", "media_diff_5m"]
recuento = ["num_holding_aircrafts", "num_en_pista_aircrafts", "num_yendo_a_pista_aircrafts"]
distancias = ["distancia", "distancias_holdings_0", "distancias_holdings_1", "distancias_holdings_2",
              "distancia_en_pista_0", "distancia_en_pista_1",
              "distancia_yendo_a_pista_0", "distancia_yendo_a_pista_1", "distancia_yendo_a_pista_2"]
tiempos = ["tiempo_en_espera", "tiempo_desde_ultimo_despegue",
           "tiempo_holding_0", "tiempo_holding_1", "tiempo_holding_2"]
target = ["tiempo_hasta_despegue"]

# Eliminar columnas inútiles
df = df.drop(columns=inutiles)

# Transformaciones cíclicas para variables temporales
for col, period in [("hour", 24), ("month", 12), ("day_of_week", 7)]:
    df[f"{col}_sin"] = np.sin(2 * np.pi * df[col] / period)
    df[f"{col}_cos"] = np.cos(2 * np.pi * df[col] / period)

# Tratar valores -1 como NaN
features_with_minus1 = media_diff + distancias[1:] + tiempos[1:]
df[features_with_minus1] = df[features_with_minus1].replace(-1, np.nan)

# Recortar outliers extremos (solo para algunos tipos de variables)
numeric_cols = metereologicas_numeric + despegues_previos + recuento + distancias + ["hour_sin", "hour_cos", "month_sin", "month_cos", "day_of_week_sin", "day_of_week_cos"]
for col in numeric_cols:
    low, high = df[col].quantile([0.01, 0.99])
    df[col] = df[col].clip(lower=low, upper=high)

# df = df[df["tiempo_hasta_despegue"]<600]

# Agrupar variables para diferentes transformaciones
log_transform_vars = ["tiempo_en_espera", "tiempo_desde_ultimo_despegue"] + media_diff + [col for col in tiempos if col.startswith("tiempo_holding_")]
robust_scale_vars = distancias + recuento
standard_scale_vars = metereologicas_numeric + despegues_previos + [f"{c}_{trig}" for c in ["hour", "month", "day_of_week"] for trig in ["sin","cos"]]

# Asegurarse de que no hay solapamiento entre las listas
for var in log_transform_vars:
    if var in robust_scale_vars:
        robust_scale_vars.remove(var)
    if var in standard_scale_vars:
        standard_scale_vars.remove(var)

# Crear transformadores para cada grupo de variables
log_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("log_transform", FunctionTransformer(np.log1p, validate=False)),
    ("scaler", StandardScaler())
])

robust_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", RobustScaler())  
])

standard_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

categorical_transformer = Pipeline([
    ("imputer",    SimpleImputer(strategy="most_frequent")),
    ("ordinal",    OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1))
])

# Crear el preprocesador con transformaciones específicas para cada grupo
preprocessor = ColumnTransformer(transformers=[
    ("log", log_transformer, log_transform_vars),
    ("robust", robust_transformer, robust_scale_vars),
    ("standard", standard_transformer, standard_scale_vars),
    ("cat", categorical_transformer, categoricas + metereologicas_categoric)
], remainder="drop")

aux = df.drop("ts", axis=1)
# Dividir en conjuntos de entrenamiento y prueba
train = aux[(aux["month"].isin([11, 12])) | (aux["day"] < 15)].drop(columns=["month", "day_of_week", "day", "hour"])
test = aux[~((aux["month"].isin([11, 12])) | (aux["day"] < 15))].drop(columns=["month", "day_of_week", "day", "hour"])

# Ajustar el preprocesador a los datos de entrenamiento
preprocessor.fit(train)
feature_names = get_ct_feature_names(preprocessor)

train_transformed = preprocessor.transform(train)
test_transformed = preprocessor.transform(test)

# 2) Reconstruir DataFrame, volver a añadir la columna objetivo
train_proc = pd.DataFrame(train_transformed, columns=feature_names, index=train.index)
test_proc = pd.DataFrame(test_transformed, columns=feature_names, index=test.index)
train_proc["ts"] = df.loc[train.index, "ts"]
test_proc["ts"] = df.loc[test.index, "ts"]
train_proc["tiempo_hasta_despegue"] = df.loc[train.index, "tiempo_hasta_despegue"]
test_proc["tiempo_hasta_despegue"] = df.loc[test.index, "tiempo_hasta_despegue"]

train_proc.to_parquet("../../data/train/train_con_outliers.parquet", index=False)
test_proc.to_parquet("../../data/test/test_con_outliers.parquet", index=False)