<p align="center">
  <img src="docs/assets/banner.svg" alt="MacBrides Aerospace — Time-to-takeoff prediction · Madrid-Barajas" width="100%">
</p>

<p align="center">
  <strong>De mensajes ADS-B a modelos de predicción del tiempo hasta el despegue.</strong><br>
  Proyecto de ciencia de datos · Universidad Complutense de Madrid · 2024/25
</p>

<p align="center">
  <a href="project/PD2.pdf">Memoria del proyecto</a> ·
  <a href="project/src/train/">Notebooks de modelado</a> ·
  <a href="docs/reproducibility.md">Guía de ejecución</a> ·
  <a href="#mi-contribución">Mi contribución</a>
</p>

## El proyecto

¿Cuánto tiempo falta para que un avión despegue? **MacBrides Aerospace** explora esta pregunta en el aeropuerto Adolfo Suárez Madrid-Barajas mediante datos ADS-B, información geoespacial y modelos de machine learning.

El trabajo conecta el tratamiento de mensajes de vigilancia aérea con la reconstrucción de trayectorias, la caracterización del tráfico y la evaluación de modelos de regresión. Se desarrolló en equipo para la asignatura **Proyecto de Datos II**.

**Tecnologías:** Python, pandas, NumPy, scikit-learn, GeoPandas, Shapely, pyModeS, Matplotlib, Seaborn y Jupyter.

## Mi contribución

Soy **[Pablo Manuel Rodríguez Sosa](https://github.com/pabrodsos)**. Participé de forma transversal en las distintas etapas del proyecto: preparación y exploración de datos, modelado, evaluación y documentación, en colaboración con el resto del equipo.

Esta es mi edición de portfolio del trabajo conjunto. La organización y la documentación de esta copia facilitan su consulta; los experimentos y resultados proceden del proyecto universitario original. [Autoría y procedencia](AUTHORS.md).

## Del dato al modelo

```mermaid
flowchart LR
    A[Mensajes ADS-B] --> B[Decodificación y filtrado]
    B --> C[Trayectorias y puntos de espera]
    C --> D[Variables de tráfico y tiempo]
    D --> E[Limpieza y transformación]
    E --> F[Modelos de regresión]
    F --> G[Evaluación por pista y segmento]
```

| Etapa | Qué se trabaja | Explorar |
| --- | --- | --- |
| Preparación | Decodificación de mensajes, filtrado y tratamiento de trayectorias | [Preprocesamiento](project/src/preprocess/) |
| Contexto operativo | Puntos de espera, pistas y despegues previos | [Geometrías](project/src/json/) |
| Variables | Unión de datos, codificación temporal y transformaciones | [Limpieza](project/src/limpieza/) |
| Modelado | Random Forest, Gradient Boosting, SVR y KNN | [Experimentos](project/src/train/) |
| Evaluación | Error global y análisis por pista, punto de espera y rango temporal | [Notebook de referencia](project/src/train/train._models.ipynb) |

## Resultados del experimento de referencia

| Modelo | MAE | RMSE | R² | Observaciones de test |
| --- | ---: | ---: | ---: | ---: |
| Gradient Boosting | **67,64 s** | 104,08 s | 0,166 | 13.249 |

Valores extraídos de las salidas guardadas de [`train._models.ipynb`](project/src/train/train._models.ipynb). Son resultados históricos, no una nueva ejecución de esta edición. Las observaciones no equivalen necesariamente a vuelos únicos.

![Evaluación original de Gradient Boosting: valores reales frente a predichos, residuos y distribuciones](docs/assets/model-evaluation.png)

*Figura original del mismo notebook, extraída sin modificar.*

El error absoluto medio es de aproximadamente **un minuto y ocho segundos**. El análisis revela también un R² modesto y una tendencia a subestimar las esperas largas: el comportamiento del modelo cambia según la situación operativa. El proyecto ilustra tanto el proceso de modelado como la importancia de estudiar dónde falla una predicción.

Otros notebooks prueban variantes de variables, segmentación y tratamiento de valores atípicos. Sus resultados deben interpretarse con el conjunto de evaluación de cada experimento. [Detalles y limitaciones](docs/results.md).

## Explorar el repositorio

```text
macbrides-aerospace/
├── project/
│   ├── PD2.pdf              # Memoria académica
│   ├── data/                # Tablas Parquet del proyecto original
│   ├── models/              # Modelos históricos serializados
│   └── src/
│       ├── preprocess/     # Decodificación y preparación
│       ├── json/           # Geometrías y puntos de despegue
│       ├── limpieza/       # Limpieza y transformaciones
│       ├── train/          # Notebooks de entrenamiento
│       └── visualization/  # Exploración visual
├── archive/first-delivery/ # Primera entrega académica
├── docs/                   # Resultados y reproducibilidad
└── scripts/                # Comprobación de los datos incluidos
```

**Para una primera visita:** abre la [memoria](project/PD2.pdf), consulta los [resultados](docs/results.md) y revisa los [experimentos de entrenamiento](project/src/train/).

## Empezar

Para comprobar los datos incluidos sin entrenar modelos:

```bash
git clone https://github.com/pabrodsos/macbrides-aerospace.git
cd macbrides-aerospace
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/check_data.py
```

Para abrir los notebooks:

```bash
python -m pip install -r requirements-notebooks.txt
jupyter lab
```

Los notebooks conservan sus salidas originales. La reproducción completa de todos los experimentos requiere algunos datos adicionales y ajustes del entorno original; consulta la [guía de ejecución](docs/reproducibility.md) antes de entrenar.

## Equipo y origen

Proyecto realizado junto a **Carlos Mantilla, Héctor García, Diego Alonso, Telmo Aracama, Mario López e Ignacio Gutiérrez**.

Origen: [c123qw/PD2](https://github.com/c123qw/PD2). Esta copia personal reconoce la autoría colectiva y mantiene el código académico para su consulta. Más información en [AUTHORS.md](AUTHORS.md).
