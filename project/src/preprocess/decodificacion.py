import os
import base64
import numpy as np
import pandas as pd
import pyModeS as pms
from pathlib import Path
import multiprocessing as mp

def decode_base64_to_hex(b64_msg):
    return base64.b64decode(b64_msg).hex().upper()

def get_altitude(msg_hex):
    try:
        return pms.adsb.altitude(msg_hex)
    except:
        return np.nan
    
def get_velocity(msg_hex):
    try:
        velocity = pms.adsb.velocity(msg_hex)
        return { "speed": velocity[0], "angle": velocity[1], "vertical_rate": velocity[2] }
    except:
        return { "speed": np.nan, "angle": np.nan, "vertical_rate": np.nan }

def process_chunk(chunk):
    chunk['msg_hex'] = chunk['message'].apply(decode_base64_to_hex)
    valid_msg_mask = (chunk['msg_hex'].apply(pms.crc, encode=False) == 0) & (chunk['msg_hex'].apply(pms.typecode) != -1)
    
    processed_chunk = chunk[valid_msg_mask].copy()

    processed_chunk['tc'] = processed_chunk['msg_hex'].apply(pms.typecode)
    processed_chunk['oe_flag'] = processed_chunk['msg_hex'].apply(pms.adsb.oe_flag)
    processed_chunk['icao'] = processed_chunk['msg_hex'].apply(pms.icao)
    processed_chunk['altitude'] = processed_chunk['msg_hex'].apply(get_altitude)
    velocity_results = processed_chunk['msg_hex'].apply(get_velocity)
    processed_chunk['speed'] = velocity_results.apply(lambda x: x['speed'])
    processed_chunk['angle'] = velocity_results.apply(lambda x: x['angle'])
    processed_chunk['vertical_rate'] = velocity_results.apply(lambda x: x['vertical_rate'])

    processed_chunk = processed_chunk.rename(columns={'ts_kafka': 'ts'})[['ts', 'msg_hex', 'tc', 'oe_flag', 'icao', 'altitude', 'speed', 'angle', 'vertical_rate']]

    return processed_chunk

def change_types(df):
    df = df.copy()
    df['ts']        = pd.to_datetime(df['ts'], unit='ms')
    print(df["ts"].iloc[0])
    
    df['msg_hex']   = df["msg_hex"].astype("string")
    
    df['tc']        = df['tc'].astype('category')
    df['icao']      = df['icao'].astype('category')
    
    df['oe_flag']   = df['oe_flag'].astype('boolean')

    df['altitude']      = pd.to_numeric(df['altitude'], downcast='unsigned')
    df['speed']         = pd.to_numeric(df['speed'],    downcast='unsigned')
    df['angle']         = pd.to_numeric(df['angle'],    downcast='unsigned')
    df['vertical_rate'] = pd.to_numeric(df['vertical_rate'], downcast='integer')

    return df

def process_file_as_chunk(csv_path):
    try:
        df = pd.read_csv(csv_path, usecols=["ts_kafka", "message"], sep=";")
    except:
        return pd.DataFrame()
    return process_chunk(df)

def process_chunks_parallel(file_path):
    print("\nInicio del procesamiento paralelo...")
    
    csv_paths = []
    file_path = Path(file_path)
    for hour_dir in sorted(file_path.iterdir()):
        if hour_dir.is_dir():
            csv_paths.extend(hour_dir.glob("*.csv"))
    
    num_cores = os.cpu_count()
    print(f"\n📂 {file_path.name}: procesando {len(csv_paths)} archivos en paralelo con {num_cores} núcleos…")

    all_results = []
    processed_count = 0

    with mp.Pool(processes=num_cores) as pool:
        results_iterator = pool.imap_unordered(process_file_as_chunk, csv_paths)
        print(f"Procesados ", flush=True, end=" - ")
        for result in results_iterator:
            all_results.append(result)
            processed_count += 1
            if processed_count % 1000 == 0 or processed_count == len(csv_paths):
                print(processed_count, end=" - ", flush=True)
    print("\nTodos los chunks.")

    print("Concatenando resultados...")

    results = change_types(pd.concat(all_results, ignore_index=True))

    print("Decodificacion paralela del día completado.")
    
    return results

def process_data(raw_dir, out_dir):
    print(f"\n🚀 Procesando {raw_dir}")
    try:
        result = process_chunks_parallel(raw_dir)
        result.to_parquet(out_dir, engine="pyarrow", compression="snappy", index=False)
        print(f"💾 Guardado: {out_dir}")
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {raw_dir}")
    except Exception as e:
        print(f"⚠️ Error procesando {raw_dir}: {e}")

def main():
    path_base = "D:/"
    out_dir_base = "D:/data/decodificado/"
    for a in ["2024", "2025"]:
        path_año = os.path.join(path_base, a)
        for m in ["1", "11", "12"]:
            path_mes = os.path.join(path_año, f"{int(m):02d}")
            print(path_mes)
            if os.path.exists(path_mes):
                for (init, end) in [["1", "8"], ["8", "15"], ["15", "22"], ["22", "29"], ["29", "32"]]:
                    for day in range(int(init), int(end)):
                        path_dia = os.path.join(path_mes, f"{day:02d}")
                        if os.path.exists(path_dia):
                            os.makedirs(os.path.join(out_dir_base, a, m), exist_ok=True)
                            out_dir = os.path.join(out_dir_base, a, m, f"{day}.parquet")
                            process_data(path_dia, out_dir)

if __name__ == "__main__":
    main()
