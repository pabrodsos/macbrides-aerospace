# Estructura de la Entrega

Esta entrega está compuesta por los siguientes archivos, cada uno con un propósito específico relacionado con el análisis y procesamiento de datos ADS-B de aeronaves:

### 1. EJERCICIO 1/A/Ejercicio_1_a.ipynb
Este cuaderno realiza un análisis visual de los datos de tráfico aéreo y tiempos de espera. En particular, se genera la siguiente información:
- **Tráfico aéreo por horas**: Visualización que distingue entre los aviones en tierra y en el aire en función de las horas del día.
- **Distribución de los tiempos de espera**:
  - **Histograma**: Muestra cómo se distribuyen los tiempos de espera en general.
  - **Boxplot**: Permite identificar la mediana, los cuartiles y posibles valores atípicos en los tiempos de espera.
  - **Mapa de calor**: Visualiza las horas del día con mayor tiempo de espera, facilitando la identificación de patrones.

### 2. EJERCICIO 1/B/Ejercicio_1_b.ipynb
Este cuaderno complementa el ejercicio anterior proporcionando un análisis adicional de los datos de tiempos de espera, ayudando a entender mejor las dinámicas del tráfico aéreo en puntos de espera.

### 3. EJERCICIO 2/Ejercicio_2.ipynb
Este cuaderno tiene como objetivo visualizar la información en un mapa. Las tareas específicas incluyen:
- **Ubicación de las pistas**: Muestra las ubicaciones de las pistas de aterrizaje en el mapa.
- **Ubicación de los aviones**: Sitúa los aviones sobre el mapa, basándose en su posición y otros parámetros.
- **Estado de los aviones**: Indica si los aviones están en tierra o en el aire, lo cual es crucial para el análisis del tráfico aéreo.

### 4. preprocesamiento.ipynb
Este cuaderno realiza el procesamiento de los datos ADS-B desde un archivo comprimido. Los pasos son los siguientes:
- **Extracción de datos**: Se descomprime un archivo `.tar` que contiene datos en formato CSV.
- **Carga y preprocesamiento**: Se utilizan herramientas como `dask.dataframe` para manejar grandes volúmenes de datos y convertir los timestamps a un formato legible.
- **Extracción de información relevante**: Se extraen parámetros como ICAO (identificador único de la aeronave), velocidad, rumbo, tasa de ascenso/descenso, y capacidad del transpondedor.
- **Conversión y agrupación por fecha**: Los datos se segmentan por días y se almacenan en archivos CSV individuales, como `data_2024-12-01.csv`, `data_2024-12-02.csv`, etc.

---

## Importancia del Preprocesamiento para los Ejercicios

Los ejercicios de análisis de datos están diseñados para ser ejecutados con los archivos CSV segmentados por días, como se describe en el cuaderno de **preprocesamiento.ipynb**. Para poder ejecutar los ejercicios correctamente, es necesario contar con los siguientes archivos CSV, generados a partir de los datos preprocesados:

- `data_2024-12-01.csv`
- `data_2024-12-02.csv`
- `data_2024-12-03.csv`
- `data_2024-12-04.csv`
- `data_2024-12-05.csv`
- `data_2024-12-06.csv`
- `data_2024-12-07.csv`

Estos archivos contienen los datos segmentados por día, lo que permite realizar análisis detallados para cada fecha de manera eficiente. Por lo tanto, antes de ejecutar los ejercicios, es necesario realizar el paso de preprocesamiento para obtener estos archivos CSV segmentados.

Este flujo de trabajo asegura que los datos estén organizados y listos para ser analizados en los ejercicios de visualización y análisis de tráfico aéreo y tiempos de espera.

