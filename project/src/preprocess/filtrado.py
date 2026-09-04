import os
import math
import json
import numpy as np
import pandas as pd
import pyModeS as pms
import geopandas as gpd
import multiprocessing as mp
from shapely.geometry import Point
import warnings

warnings.filterwarnings("ignore")

LAT, LON = 40.5100278, -3.5300000

def is_position_msg(tc):
    return (5 <= tc <= 8) or (9 <= tc <= 18)

def decode_cpr(row):
    me = row['msg_hex_even']
    mo = row['msg_hex_odd']
    t0 = row['ts_even']
    t1 = row['ts_odd']

    out = { "lat": np.nan, "lon": np.nan }

    if all([isinstance(me, str), isinstance(mo, str), pd.notna(t0), pd.notna(t1)]):
        try:
            out['lat'], out['lon'] = pms.adsb.position(me, mo, t0, t1, LAT, LON)
        except (RuntimeError, TypeError):
            pass

    return pd.Series(out)

def add_position(flight):
    flight_pos = flight[flight['tc'].apply(is_position_msg)]
    if len(flight_pos) == 0:
        return pd.DataFrame()
    
    even_msgs = flight_pos[flight_pos['oe_flag']==0].rename(columns={'ts': 'ts_even'})
    odd_msgs  = flight_pos[flight_pos['oe_flag']==1].rename(columns={'ts': 'ts_odd'})

    pairs = pd.merge_asof(even_msgs, odd_msgs,
        left_on='ts_even', right_on='ts_odd', tolerance=pd.Timedelta('10s'),
        direction='backward', suffixes=('_even','_odd')
    ).loc[:, ["msg_hex_even", "msg_hex_odd", "ts_even", "ts_odd"]]

    if pairs.empty:
        return pd.DataFrame()
    
    decoded = pairs.apply(decode_cpr, axis=1)

    pairs = pd.concat([pairs, decoded], axis=1).loc[:, ["ts_even", "lat", "lon"]]

    result = pd.merge_asof(
        flight, pairs.sort_values('ts_even'),
        left_on='ts', right_on='ts_even',
        direction='nearest', tolerance=pd.Timedelta('1s')
    ).drop(["ts_even"], axis=1)

    if len(result) == 0:
        return pd.DataFrame()
    
    return result

def adding_runways(df, geojson_path):
    runways_gdf = gpd.read_file(geojson_path)
    runways_gdf = runways_gdf.set_crs(epsg=4326, allow_override=True)
    runways_utm = runways_gdf.to_crs(epsg=32630)

    points_gdf = gpd.GeoDataFrame( df.copy(), geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326" )
    points_utm = points_gdf.to_crs(epsg=32630)

    joined = gpd.sjoin(points_utm, runways_utm[['RWY', 'geometry']], how='left', predicate='within')
    if not joined.index.is_unique:
        joined = joined[~joined.index.duplicated(keep='first')]
    
    runway_series = joined['RWY'].where(joined['RWY'].notna(), None)
    runway_series.index = df.index
    df = df.copy()
    df['runway'] = runway_series
    return df

def separate_flights(df_icao):
    aux = df_icao[df_icao["runway"].notna()].copy()
    aux["flight_id"] = (aux["ts"].diff().gt(pd.Timedelta(seconds=300)).cumsum()) + 1
    result = pd.merge_asof(df_icao, aux[["ts", "flight_id"]],
                            on="ts", direction='backward', tolerance=pd.Timedelta(seconds=120))
    full_bfill = result["flight_id"].bfill()
    next_valid_ts = result["ts"].where(result["flight_id"].notna()).bfill()
    delta = next_valid_ts - result["ts"]
    mask = delta <= pd.Timedelta(minutes=20)
    result["flight_id"] = np.where(mask, full_bfill, result["flight_id"])
    result = result.dropna(subset=["flight_id"])
    return result

def filter_takeoffs(flights):
    dfs_takeoffs = []
    dfs_landings = []
    dfs_raros = []
    for _, flight in flights.groupby("flight_id"):
        flight["altitude"] = flight["altitude"].ffill()        
        rw = flight["runway"].dropna().value_counts().idxmax()
        flight["esta_en_pista"] = flight["runway"].notna()
        flight["runway"] = flight["runway"].fillna(rw)
        desnivel = flight["altitude"].diff().sum()
        min_speed = flight["speed"].min()
        todo_nans_speed = flight["speed"].isna().sum() == len(flight)
        if desnivel > 1500 and (min_speed < 110 or todo_nans_speed):
            dfs_takeoffs.append(flight)
        elif desnivel < -500 and (min_speed < 100 or todo_nans_speed):
            dfs_landings.append(flight)
        else:
            dfs_raros.append(flight)
    takeoffs = pd.DataFrame()
    landings = pd.DataFrame()
    raros = pd.DataFrame()
    if dfs_takeoffs:
        takeoffs = pd.concat(dfs_takeoffs)
        takeoffs["runway"] = takeoffs["runway"].astype("category")
        takeoffs["flight_id"] = takeoffs["flight_id"].astype("uint8")
    if dfs_landings:
        landings = pd.concat(dfs_landings)
        landings["runway"] = landings["runway"].astype("category")
        landings["flight_id"] = landings["flight_id"].astype("uint8")
    if dfs_raros:
        raros = pd.concat(dfs_raros)
        raros["runway"] = raros["runway"].astype("category")
        raros["flight_id"] = raros["flight_id"].astype("uint8")
    
    return takeoffs, landings, raros

def haversine(lat1, lon1, lat2, lon2, R=6371):
    φ1, λ1 = math.radians(lat1), math.radians(lon1)
    φ2, λ2 = math.radians(lat2), math.radians(lon2)
    Δφ = φ2 - φ1
    Δλ = λ2 - λ1

    a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return (R * c) * 1000

def haversine_vectorized(lat1, lon1, lat2, lon2, R=6371):
    if lat2 is None or lon2 is None:
        return None
    φ1, λ1 = np.radians(lat1), np.radians(lon1)
    φ2, λ2 = np.radians(lat2), np.radians(lon2)
    Δφ = φ2 - φ1
    Δλ = λ2 - λ1

    a = np.sin(Δφ/2)**2 + np.cos(φ1)*np.cos(φ2)*np.sin(Δλ/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return (R * c) * 1000

def adding_holding_points(df, holding_points_geojson_path, buffer_radius=0.0002):
    holding_points = gpd.read_file(holding_points_geojson_path)

    if 'id' not in holding_points.columns:
        holding_points = holding_points.reset_index().rename(columns={'index': 'id'})

    holding_buffers = holding_points.copy()
    holding_buffers['buffered'] = holding_buffers.geometry.buffer(buffer_radius)
    holding_buffers.set_geometry('buffered', inplace=True)
    try:
        geom = [Point(xy) for xy in zip(df['lon'], df['lat'])]
    except:
        print(df.columns)
        print(df)
    aircraft_gdf = gpd.GeoDataFrame(df, geometry=geom, crs="EPSG:4326")

    joined = gpd.sjoin(
        aircraft_gdf,
        holding_buffers[['id', 'buffered']],
        how='left',
        predicate='within'
    )
    joined = joined.rename(columns={'id': 'holding_point_id'}).drop(columns=['index_right'])

    result_df = joined.drop(columns=['geometry']).reset_index(drop=True)
    return result_df.reset_index(drop=True)

def extend_takeoffs(takeoffs, icao):
    dfs = []
    for flight_id, flight in takeoffs.groupby("flight_id"):
        idx_llegada_holding_point = flight["holding_point_id"].first_valid_index()
        flight = flight.loc[idx_llegada_holding_point: ]

        idx_comienzo_despegue = flight[flight["altitude"] > 1000].first_valid_index()
        flight = flight.loc[:idx_comienzo_despegue]
        flight["momento_despegue"] = True if idx_comienzo_despegue is not None else False
        if idx_comienzo_despegue is None or not flight.iloc[-1]["esta_en_pista"]:
            flight["pos_recalculada"] = True
            with open('../json/runway_takeoffs_centers.json', 'r', encoding='utf-8') as f:
                runway_grids = json.load(f)
            rw = flight.iloc[0]["runway"]
            lat_despegue = runway_grids[rw]["lat_despegue_onground"]
            lon_despegue = runway_grids[rw]["lon_despegue_onground"]
            flight["lat_despegue"] = lat_despegue
            flight["lon_despegue"] = lon_despegue
            dists = np.sqrt((flight["lat"].to_numpy() - lat_despegue) ** 2 + (flight["lon"].to_numpy() - lon_despegue) ** 2)
            idx_nearest = np.argmin(dists)
            closest_point = flight.iloc[idx_nearest]
            flight["hora_despegue"] = closest_point["ts"]

            flight["hora_despegue_mala"] = flight.iloc[-1]["ts"]
            flight["lat_despegue_mala"] = flight.iloc[-1]["lat"]
            flight["lon_despegue_mala"] = flight.iloc[-1]["lon"]

        else:
            flight["hora_despegue"] = flight.iloc[-1]["ts"]
            lat_despegue = flight.iloc[-1]["lat"]
            lon_despegue = flight.iloc[-1]["lon"]
            flight["lat_despegue"] = lat_despegue
            flight["lon_despegue"] = lon_despegue

        if idx_llegada_holding_point is not None:
            flight["llegada_punto_espera"] = flight.iloc[0]["ts"]
            flight["lat_espera"] = flight.iloc[0]["lat"]
            flight["lon_espera"] = flight.iloc[0]["lon"]
            aux = flight[flight["holding_point_id"].notna()]
            aux = aux[aux["speed"] == 0]
            flight["para_en_espera"] = (len(aux)>0)
            flight["tiempo_en_espera"] = (flight["ts"] - flight["llegada_punto_espera"]).dt.total_seconds()
        else:
            flight["tiempo_en_espera"] = 0
        
        flight["tiempo_hasta_despegue"] = (flight["hora_despegue"] - flight["ts"]).dt.total_seconds()
        flight["distancia"] = flight.apply(
            lambda row: haversine_vectorized(row["lat"], row["lon"], lat_despegue, lon_despegue), axis=1
        )
        dfs.append(flight)
    return pd.concat(dfs)

def process_icao(df_icao, icao):
    if len(df_icao) < 500:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    if all(df_icao["altitude"] < 100):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    df_icao_pos = add_position(df_icao)
    if df_icao_pos.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    df_icao_pos = df_icao_pos.set_index('ts')
    df_icao_pos[['lat', 'lon']] = df_icao_pos[['lat', 'lon']].interpolate(method='time', limit_direction='both')
    df_icao_pos = df_icao_pos.reset_index()

    bbox = { 'lon_min': -3.70, 'lon_max': -3.40, 'lat_min': 40.35, 'lat_max': 40.65}
    df_filtered = df_icao_pos[
        (df_icao_pos['lon'] >= bbox['lon_min']) & (df_icao_pos['lon'] <= bbox['lon_max']) &
        (df_icao_pos['lat'] >= bbox['lat_min']) & (df_icao_pos['lat'] <= bbox['lat_max'])
    ] 
    
    if len(df_filtered) == 0:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    df_icao_runways = adding_runways(df_filtered, "../json/puntosespera/runways.geojson")
    if df_icao_runways["runway"].isna().sum() == len(df_icao_runways):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    flights = separate_flights(df_icao_runways)
        
    takeoffs, landings, raros =  filter_takeoffs(flights)
    
    if len(takeoffs) != 0:
        takeoffs_holdings = adding_holding_points(takeoffs, holding_points_geojson_path="../json/puntosespera/holding_points.geojson", buffer_radius=0.0002)  # ~20 metros)
        takeoffs_extended = extend_takeoffs(takeoffs_holdings, icao)
        return takeoffs_extended, landings, raros

    return takeoffs, landings, raros

def process_icao_parallel(icao_data_tuple):
    icao, df_icao = icao_data_tuple
    try:
        takeoffs, landings, raros = process_icao(df_icao, icao)
        return takeoffs, landings, raros
    except Exception as e:
        print(f"Error al procesar ICAO {icao}: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
def process_day_parallel(day):
    print("\nInicio del procesamiento paralelo...")
    
    day.sort_values("ts", inplace=True)

    print("Agrupando datos por ICAO...")
    icao_groups = [(icao, df_icao) for icao, df_icao in day.groupby("icao", observed=True)]
    print(f"Encontrados {len(icao_groups)} ICAOs para procesar.")

    num_cores = os.cpu_count()
    print(f"Usando {num_cores} núcleos para el procesamiento paralelo.")

    all_results = []
    processed_count = 0
    total_icaos = len(icao_groups)

    with mp.Pool(processes=num_cores) as pool:
        results_iterator = pool.imap_unordered(process_icao_parallel, icao_groups)
        print(f"Procesados {processed_count}/{total_icaos} ICAOs...", flush=True)
        for result_tuple in results_iterator:
            all_results.append(result_tuple)
            processed_count += 1
            if processed_count % 50 == 0 or processed_count == total_icaos:
                 print(f"{processed_count}", end=" - ", flush=True)
    print("\nTodos los ICAOs procesados.")

    dfs_takeoffs, dfs_landings, dfs_raros = [], [], []
    for takeoffs, landings, raros in all_results:
         if takeoffs is not None and not takeoffs.empty:
            dfs_takeoffs.append(takeoffs)
         if landings is not None and not landings.empty:
            dfs_landings.append(landings)
         if raros is not None and not raros.empty:
            dfs_raros.append(raros)

    print("Concatenando resultados...")

    final_takeoffs = pd.concat(dfs_takeoffs, ignore_index=True) if dfs_takeoffs else pd.DataFrame()
    final_landings = pd.concat(dfs_landings, ignore_index=True) if dfs_landings else pd.DataFrame()
    final_raros = pd.concat(dfs_raros, ignore_index=True) if dfs_raros else pd.DataFrame()

    if not final_takeoffs.empty:
        final_takeoffs = final_takeoffs.drop(["tc", "oe_flag"], axis=1, errors='ignore')
    if not final_landings.empty:
        final_landings = final_landings.drop(["tc", "oe_flag"], axis=1, errors='ignore')
    if not final_raros.empty:
        final_raros = final_raros.drop(["tc", "oe_flag"], axis=1, errors='ignore')


    print("Procesamiento paralelo del día completado.")
    return final_takeoffs, final_landings, final_raros

def process_data(input_dir, out_dir_despegues, out_dir_aterrizajes, out_dir_raros):
    print(f"\n🚀 Procesando {input_dir}")
    try:
        df = pd.read_parquet(input_dir)
        result = process_day_parallel(df)
        result[0].to_parquet(out_dir_despegues, engine="pyarrow", compression="snappy", index=False)
        result[1].to_parquet(out_dir_aterrizajes, engine="pyarrow", compression="snappy", index=False)
        result[2].to_parquet(out_dir_raros, engine="pyarrow", compression="snappy", index=False)
        print(f"💾 Guardado: {out_dir_despegues}")

    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {input_dir}")
    except Exception as e:
        print(f"⚠️ Error procesando {input_dir}: {e}")

def main():
    path_base = "D:/data/decodificado"
    out_dir_base_despegues = "D:/data/filtrado/despegues"
    out_dir_base_aterrizajes = "D:/data/filtrado/aterrizajes"
    out_dir_base_raros = "D:/data/filtrado/raros"
    for a in ["2024", "2025"]:
        path_año = os.path.join(path_base, a)
        for m in ["1", "11", "12"]:
            path_mes = os.path.join(path_año, m)
            if os.path.exists(path_mes):
                for (init, end) in [["1", "8"], ["8", "15"], ["15", "22"], ["22", "29"], ["29", "32"]]:
                    for day in range(int(init), int(end)):
                        path_dia = os.path.join(path_mes, f"{day}.parquet")
                        if os.path.exists(path_dia):
                            os.makedirs(os.path.join(out_dir_base_despegues, a, m), exist_ok=True)
                            os.makedirs(os.path.join(out_dir_base_aterrizajes, a, m), exist_ok=True)
                            os.makedirs(os.path.join(out_dir_base_raros, a, m), exist_ok=True)
                            out_dir_despegues = os.path.join(out_dir_base_despegues, a, m, f"{day}.parquet")
                            out_dir_aterrizajes = os.path.join(out_dir_base_aterrizajes, a, m, f"{day}.parquet")
                            out_dir_raros = os.path.join(out_dir_base_raros, a, m, f"{day}.parquet")
                            process_data(path_dia, out_dir_despegues, out_dir_aterrizajes, out_dir_raros)

if __name__ == '__main__':
    main()