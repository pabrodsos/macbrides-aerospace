import os
import pandas as pd
import pyModeS as pms
import warnings

warnings.filterwarnings("ignore")

def get_info_extra(msg_hex):
    info_extra = { 'wind_speed': None, 'wind_dir': None, 'wake_vortex': None, 'temp': None, 'wind_shear': None }
    functions = { 'wake_vortex': pms.bds.bds45.wv45, 'temp': pms.bds.bds45.temp45, 'wind_shear': pms.bds.bds45.ws45 }
    try:
        wind_speed, wind_dir = pms.bds.bds44.wind44(msg_hex)
        info_extra.update({'wind_speed': wind_speed, 'wind_dir': wind_dir})
    except Exception:
        pass

    for key, func in functions.items():
        try:
            info_extra[key] = func(msg_hex)
        except Exception:
            pass
    return info_extra

def transform_df(df):
    df['ts'] = pd.to_datetime(df['ts'])
    
    df['month']       = df['ts'].dt.month.astype("category")
    df['day_of_week'] = df['ts'].dt.dayofweek.astype('category')
    df['day']         = df['ts'].dt.day.astype("uint8")
    df['hour']         = (df['ts'].dt.hour + (df['ts'].dt.minute / 60)).astype("float16")
    
    df['icao']             = df['icao'].astype('category')
    df['flight_id']        = df['flight_id'].astype('uint8')
    df['holding_point_id'] = df['holding_point_id'].astype('category')
    df['runway']           = df['runway'].astype('category')
    df['wake_vortex']      = df['wake_vortex'].astype('category')
    df['wind_shear']       = df['wind_shear'].astype('category')
    
    float32_cols = [ 'lat', 'lon', 'lat_despegue',  'lon_despegue', 'lat_espera', 'lon_espera', 'speed', 'angle', 'altitude', 'vertical_rate', 'tiempo_hasta_despegue', 'tiempo_en_espera', 'distancia', "wind_speed", 'wind_dir', 'temp' ]
    for col in float32_cols:
        if col in df.columns:
            df[col] = df[col].astype('float32')
    return df.reset_index(drop=True)

def process_day(day):
    filtered_day = day[day["holding_point_id"].notna() & (day["speed"] == 0)].copy()
    if filtered_day.empty:
        return pd.DataFrame()
    info_extra_results = filtered_day["msg_hex"].apply(get_info_extra)
    for col in ['wind_speed', 'wind_dir', 'wake_vortex', 'temp', 'wind_shear']:
        filtered_day[col] = info_extra_results.apply(lambda x: x[col])
    return filtered_day

def process_data(raw_dir, out_dir, init, end):
    dfs = []
    for day in range(init, end):
        file_path = os.path.join(raw_dir, str(f"{day}.parquet"))
        if os.path.exists(file_path):
            print(f"\n🚀 Procesando {file_path}")
            df = pd.read_parquet(file_path)
            dfs.append(process_day(df))
    if dfs:
        result = pd.concat(dfs)
        result = transform_df(result)
        result.to_parquet(os.path.join(out_dir, f"{init}_{end}.parquet"))
    else:
        print("vacio")

def main():
    path_base = "D:/data/filtrado/despegues"
    out_dir_base = "D:/data/enEspera"
    for a in ["2024", "2025"]:
        path_año = os.path.join(path_base, a)
        for m in ["1", "11", "12"]:
            path_mes = os.path.join(path_año, m)
            print(path_mes, end=" -- ")
            if os.path.exists(path_mes):
                for (init, end) in [["1", "8"], ["8", "15"], ["15", "22"], ["22", "29"], ["29", "32"]]:
                    os.makedirs(os.path.join(out_dir_base, a, m), exist_ok=True)
                    out_dir = os.path.join(out_dir_base, a, m)
                    process_data(path_mes, out_dir, int(init), int(end))

if __name__ == "__main__":
    main()