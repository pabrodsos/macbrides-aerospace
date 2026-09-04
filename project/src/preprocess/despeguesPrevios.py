import os
import json
import pandas as pd
import pyModeS as pms
import multiprocessing as mp
from datetime import timedelta
from math import radians, cos, sin, asin, sqrt
import warnings

warnings.filterwarnings("ignore")

def get_num_despegues_previos(row, despegues, minutes):
    despegues = despegues[despegues["hora_despegue"] > (row["ts"] - timedelta(minutes=minutes))]
    despegues = despegues[despegues["hora_despegue"] < row["ts"]]
    diff = despegues["hora_despegue"].diff()
    return len(despegues), diff.mean()

def get_wake_vortex(msg_hex):
    try:
        return pms.bds.bds45.wv45(msg_hex)
    except:
        return None

def get_info_last_takeoff(row, despegues):
    despegues = despegues[despegues["hora_despegue"] < row["ts"]]
    if despegues.empty:
        return pd.Series([None, None, None])

    last_takeoff = despegues.iloc[-1]
    icao = last_takeoff["icao"]
    tiempo_desde_ultimo_despegue = (row["ts"] - last_takeoff["hora_despegue"]).total_seconds()
    tipo_ultimo_avion = get_wake_vortex(last_takeoff["msg_hex"])
    return tiempo_desde_ultimo_despegue, tipo_ultimo_avion, icao

def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r * 1000

def get_other_aircraft_info(row, df_global, runway_target):
    runway_centers = {}
    with open('../json/runway_takeoffs_centers.json', 'r') as f:
        runway_centers = json.load(f)
    center_coords = runway_centers[runway_target]
    
    current_ts = row['ts']
    current_icao = row['icao']

    nearby_traffic = df_global[
        (df_global['ts'] >= current_ts - timedelta(seconds=5)) &
        (df_global['ts'] <= current_ts + timedelta(seconds=2)) &
        (df_global['icao'] != current_icao)
    ].copy()

    holding_ocupado = False
    num_holding_aircrafts = 0
    tiempo_holding = None
    despegue_holdings = None
    icaos_holdings = None
    distancias_holdings = None

    pista_ocupada = False
    num_en_pista_aircrafts = 0
    icaos_en_pista = None
    distancia_en_pista = None

    en_camino_antes = False
    num_yendo_a_pista_aircrafts = 0
    icaos_yendo_a_pista = None
    distancia_yendo_a_pista = None

    # 2. Revisar Punto de Espera (Holding Point)
    holdings = nearby_traffic[
        (nearby_traffic['holding_point_id'].notna()) & 
        (nearby_traffic['runway'] == runway_target)
    ].drop_duplicates("icao")
    if not holdings.empty:
        holding_ocupado = True

        num_holding_aircrafts = len(holdings)
        tiempo_holding = [(current_ts - aircraft[1]["llegada_punto_espera"]) for aircraft in holdings.iterrows()]
        despegue_holdings = [aircraft[1]["hora_despegue"] for aircraft in holdings.iterrows()]
        icaos_holdings = [aircraft[1]["icao"] for aircraft in holdings.iterrows()]
        distancias_holdings = [haversine(aircraft[1]['lon_despegue'], aircraft[1]['lat_despegue'], center_coords['lon_despegue'], center_coords['lat_despegue']) for aircraft in holdings.iterrows()]

    # 3. Revisar Pista Ocupada
    on_runway = nearby_traffic[
        (nearby_traffic['esta_en_pista']) &
        (nearby_traffic['runway'] == runway_target)
    ].drop_duplicates("icao")
    if not on_runway.empty:
        pista_ocupada = True
        num_en_pista_aircrafts = len(on_runway)
        icaos_en_pista = [aircraft[1]["icao"] for aircraft in on_runway.iterrows()]
        distancia_en_pista = [haversine(aircraft[1]['lon_despegue'], aircraft[1]['lat_despegue'], center_coords['lon_despegue'], center_coords['lat_despegue']) for aircraft in on_runway.iterrows()]

    # 4. Revisar Avión en Camino (Antes que el actual)
    current_takeoff_time = row['hora_despegue']

    en_route = nearby_traffic[
        (nearby_traffic['runway'] == runway_target) &
        (~nearby_traffic['icao'].isin(holdings['icao'])) &
        (~nearby_traffic['icao'].isin(on_runway['icao'])) &
        (nearby_traffic['hora_despegue'] < current_takeoff_time)
    ].drop_duplicates("icao")
    en_route = en_route.sort_values('hora_despegue')

    if not en_route.empty:
        en_camino_antes = True
        num_yendo_a_pista_aircrafts = len(en_route)
        icaos_yendo_a_pista = [aircraft[1]["icao"] for aircraft in en_route.iterrows()]
        distancia_yendo_a_pista = [haversine(aircraft[1]['lon_despegue'], aircraft[1]['lat_despegue'], center_coords['lon_despegue'], center_coords['lat_despegue']) for aircraft in en_route.iterrows()]

    return pd.Series([holding_ocupado, num_holding_aircrafts,       icaos_holdings,      distancias_holdings,    tiempo_holding, despegue_holdings,
                      pista_ocupada,   num_en_pista_aircrafts,      icaos_en_pista,      distancia_en_pista,
                      en_camino_antes, num_yendo_a_pista_aircrafts, icaos_yendo_a_pista, distancia_yendo_a_pista])

def process_flight(flight):
    hora_despegue_programada = flight["hora_despegue"].iloc[0]
    rw = flight["runway"].iloc[0]    
    año = flight.iloc[0]["ts"].year
    mes = flight.iloc[0]["month"]
    dia = flight.iloc[0]["day"]
    if os.path.exists(f"D:/data//filtrado/despegues/{año}/{mes}/{dia}.parquet"):
        despegues_dia = pd.read_parquet(f"D:/data/filtrado/despegues/{año}/{mes}/{dia}.parquet")
        if despegues_dia["hora_despegue"].isnull().any():
                print(f"WARNING: 'hora_despegue_onground' contains null values in file: D:/data//filtrado/despegues/{año}/{mes}/{dia}.parquet", flush=True)
            

        filtered_previos = despegues_dia[
            (despegues_dia["hora_despegue"] < hora_despegue_programada) &
            (despegues_dia["hora_despegue"] > hora_despegue_programada - timedelta(minutes=90)) &
            (despegues_dia["runway"] == rw)
        ].sort_values("hora_despegue")

        list_despegues_previos = filtered_previos.drop_duplicates(subset=["hora_despegue"])   

        flight[["despegues_previos_1h", "media_diff_1h"]]   = flight.apply(lambda x: get_num_despegues_previos(x, list_despegues_previos, 60), axis=1, result_type='expand')
        flight[["despegues_previos_45m", "media_diff_45m"]] = flight.apply(lambda x: get_num_despegues_previos(x, list_despegues_previos, 45), axis=1, result_type='expand')
        flight[["despegues_previos_30m", "media_diff_30m"]] = flight.apply(lambda x: get_num_despegues_previos(x, list_despegues_previos, 30), axis=1, result_type='expand')
        flight[["despegues_previos_20m", "media_diff_20m"]] = flight.apply(lambda x: get_num_despegues_previos(x, list_despegues_previos, 20), axis=1, result_type='expand')
        flight[["despegues_previos_10m", "media_diff_10m"]] = flight.apply(lambda x: get_num_despegues_previos(x, list_despegues_previos, 10), axis=1, result_type='expand')
        flight[["despegues_previos_5m", "media_diff_5m"]]   = flight.apply(lambda x: get_num_despegues_previos(x, list_despegues_previos,  5), axis=1, result_type='expand')

        flight[["tiempo_desde_ultimo_despegue", "tipo_avion_ultimo_despegue", "icao_ultimo_despegue"]] = flight.apply(lambda x: get_info_last_takeoff(x, list_despegues_previos), axis=1, result_type='expand')
        wake_vortex_na_idx = flight[flight["tipo_avion_ultimo_despegue"].isna()].index
        for idx in wake_vortex_na_idx:
            icao_last = flight.at[idx, "icao_ultimo_despegue"]
            if pd.isna(icao_last):
                continue
            msg_list = despegues_dia.loc[despegues_dia["icao"] == icao_last, "msg_hex"].tolist()
            wake_value = None
            for msg in msg_list:
                try:
                    w = pms.bds.bds45.wv45(msg)
                except Exception:
                    w = None
                if w is not None:
                    wake_value = w
                    break
            if wake_value is not None:
                flight.at[idx, "tipo_avion_ultimo_despegue"] = wake_value
            flight.loc[wake_vortex_na_idx]
        
        flight[[
            "holding_ocupado", "num_holding_aircrafts",       "icaos_holdings",      "distancias_holdings",   "tiempo_holding", "despegue_holdings",
            "pista_ocupada",   "num_en_pista_aircrafts",      "icaos_en_pista",      "distancia_en_pista",
            "en_camino_antes", "num_yendo_a_pista_aircrafts", "icaos_yendo_a_pista", "distancia_yendo_a_pista"]] = flight.apply(lambda x: get_other_aircraft_info(x, filtered_previos, rw), axis=1, result_type='expand')
        return flight
    else:
        print(f"no existe", f"D:/data/filtrado/despegues/{año}/{mes}/{dia}.parquet")
        return pd.DataFrame()

def process_data(df):
    n_flights = df.groupby(["icao", "flight_id", "day"], observed=True).ngroups
    dfs = []
    i = 0
    print("Procesando ", n_flights, " vuelos", end="  -->  ", flush=True)
    for _, df_flight in df.groupby(["icao", "flight_id", "day"], observed=True):
            i+=1
            if i % 20 == 0 or i == n_flights:
                print(i, end=" - ", flush=True)
            aux = process_flight(df_flight)
            dfs.append(aux)
    print()
    return pd.concat(dfs, ignore_index=True)
    

def main():
    path_base = "D:/data/enEspera"
    out_dir_base = "D:/data/processed"
    for a in ["2024", "2025"]:
        path_año = os.path.join(path_base, a)
        for m in ["1", "11", "12"]:
            path_mes = os.path.join(path_año, m)
            if os.path.exists(path_mes):
                for (init, end) in [["1", "8"], ["8", "15"], ["15", "22"], ["22", "29"], ["29", "32"]]:
                    os.makedirs(os.path.join(out_dir_base, a, m), exist_ok=True)
                    path_semana = os.path.join(path_mes, f"{init}_{end}.parquet")
                    out_dir = os.path.join(out_dir_base, a, m, f"{init}_{end}.parquet")
                    if os.path.exists(path_semana):
                        df = pd.read_parquet(path_semana)
                        df = df.sort_values("ts")
                        result = process_data(df)
                        result.to_parquet(out_dir)
                    else:
                        print(path_semana, " no existe")
            else:
                print(path_mes, " no existe")

if __name__ == "__main__":
    main()