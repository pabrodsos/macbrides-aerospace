# Guía de ejecución

## Qué incluye la copia

Se incluyen los ocho ficheros Parquet y los cuatro modelos `.joblib` presentes en la entrega final original. Se conservan las salidas de los notebooks para que puedan consultarse en GitHub sin ejecutar código.

## Comprobación de datos

Desde la raíz del repositorio, con Python 3.14 (versión utilizada en la comprobación de esta edición):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/check_data.py
```

En PowerShell, activa el entorno con `.venv\Scripts\Activate.ps1`. El script lee las tablas Parquet, informa de sus dimensiones y comprueba que las particiones de entrenamiento y test tienen la columna objetivo y esquemas compatibles. No entrena modelos ni sobrescribe archivos. Es una comprobación estructural, no una validación de la metodología.

## Notebooks

```bash
python -m pip install -r requirements-notebooks.txt
jupyter lab
```

Abre los notebooks desde su carpeta original dentro de `project/src/`. Sus rutas `../../data/` presuponen ese directorio de trabajo.

| Notebook | Datos esperados | Estado |
| --- | --- | --- |
| `train_models2.ipynb` | `train_con_outliers.parquet` y `test_con_outliers.parquet` | Datos incluidos; entrenamiento completo no verificado en esta edición |
| `train_segmented*` | Particiones con/sin outliers | Datos incluidos; entrenamiento completo no verificado en esta edición |
| `train._models.ipynb` | `train_ordinal.parquet` y `test_ordinal.parquet` | Datos ausentes; consultar resultados guardados |
| `visualization_transformed.ipynb` | `final_ordinal.parquet` | Dato ausente; consultar resultados guardados |

La guía no sustituye los datos ordinales por tablas con nombres distintos: podrían representar otro procesamiento y producir resultados no comparables.

`requirements.txt` fija el entorno de la comprobación de datos. `requirements-notebooks.txt` recoge dependencias de los notebooks, pero no constituye una reconstrucción validada del entorno académico. El notebook de referencia registra un error de XGBoost con `callbacks`; para repetir ese experimento será necesario adaptar su API o recuperar la versión original.

## Preprocesamiento y modelos históricos

Los scripts de preprocesamiento y la primera entrega dependen de entradas ADS-B y rutas del entorno académico que no se distribuyen como un pipeline listo para ejecutar. Antes de usarlos, revisa sus rutas de entrada y salida. La limpieza puede sobrescribir tablas existentes.

Los `.joblib` se conservan como artefactos originales. Sus versiones de entrenamiento no están fijadas, por lo que su carga en otro entorno puede requerir compatibilidad de versiones.

## Alcance de la limpieza

Esta edición organiza y documenta el trabajo. No modifica las celdas de entrenamiento ni recalcula resultados históricos. Los modelos no se han reentrenado durante la preparación del portfolio.
