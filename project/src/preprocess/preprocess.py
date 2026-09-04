import decodificacion
import filtrado 
import puntosEspera
import despeguesPrevios

import time

if __name__ == "__main__":
    print("╔════════════════════════════════╗")
    print("║  INICIANDO PROCESO PRINCIPAL   ║")
    print("╚════════════════════════════════╝\n")
    tiempos = { 'decodificacion': 0, 'filtrado': 0, 'puntosEspera': 0, 'despeguesPrevios': 0, 'total': 0 }

    start_total = time.time()

    print("🔠 [1/4] Ejecutando módulo de DECODIFICACIÓN...")
    start = time.time()
    # decodificacion.main()
    tiempos['decodificacion'] = time.time() - start
    print(f"✅ Decodificación completada (Tiempo: {tiempos['decodificacion']:.2f}s)\n")

    print("🧹 [2/4] Ejecutando módulo de FILTRADO...")
    start = time.time()
    # filtrado.main()
    tiempos['filtrado'] = time.time() - start
    print(f"✅ Filtrado completado (Tiempo: {tiempos['filtrado']:.2f}s)\n")

    print("⏳ [3/4] Ejecutando módulo de PUNTOS DE ESPERA...")
    start = time.time()
    # puntosEspera.main()
    tiempos['puntosEspera'] = time.time() - start
    print(f"✅ Puntos de espera completados (Tiempo: {tiempos['puntosEspera']:.2f}s)\n")

    print("✈️ [4/4] Ejecutando módulo de DESPEGUES PREVIOS...")
    start = time.time()
    despeguesPrevios.main()
    tiempos['despeguesPrevios'] = time.time() - start
    print(f"✅ Despegues previos completados (Tiempo: {tiempos['despeguesPrevios']:.2f}s)\n")

    tiempos['total'] = time.time() - start_total

    print("\n📊 RESUMEN DE TIEMPOS:")
    print(f"1. Decodificación: {tiempos['decodificacion']:.2f}s")
    print(f"2. Filtrado:       {tiempos['filtrado']:.2f}s")
    print(f"3. Puntos espera:  {tiempos['puntosEspera']:.2f}s")
    print(f"4. Despegues:      {tiempos['despeguesPrevios']:.2f}s")
    print("────────────────────────────")
    print(f"   TOTAL:          {tiempos['total']:.2f}s\n")
    print("🏁 Proceso completado exitosamente!")
