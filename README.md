# Minería de Datos — NHANES (2005–2014) + Drugs_product

Proyecto de **Minería de Datos** (Corporación Universitaria Minuto de Dios, UNIMINUTO). Se limpia,
integra, transforma y analiza el dataset **NHANES** (5 ciclos, 2005–2014) junto con el catálogo
farmacológico **Drugs_product**.

**Equipo (MIMETIC):** Manuel José Rivera Guzmán · Julián Andrés Correa Cuevas
**Asignatura:** Minería de Datos · Ibagué · 2026-2

## Dataset

- **NHANES** (National Health and Nutrition Examination Survey, CDC/NCHS): 5 ciclos
  (2005–2006, 2007–2008, 2009–2010, 2011–2012, 2013–2014); 50 965 participantes;
  26 columnas comunes por intersección de esquemas.
- **Drugs_product** (FDA): 117 365 productos farmacéuticos, 18 columnas (catálogo de referencia).

## Requisitos

- Python 3.12+

```powershell
pip install -r requirements.txt
```

## Estructura del proyecto

```
healtcare/
├── data/raw/                  # 5 CSV NHANES + Drugs_product.csv
├── docs/                      # plan, notebooks de evidencia, clasificación y análisis de agrupamiento
├── outputs/
│   ├── cleaned/               # nhanes_master_cleaned.csv(.gz), nhanes_master_cruzado.csv
│   ├── transformed/           # X_nhanes.csv, y_nhanes.csv, decision_escalador.csv, varianza_pca.csv
│   ├── eda/                   # resumen_descriptivo.csv, outliers_iqr.csv, pares_correlacion.csv
│   ├── figuras/               # histogramas, boxplots, barras, scatter, heatmap, matriz de dispersión, PCA
│   └── reportes/              # cleaning_*, informe_eda_nhanes.docx, clasificación_* y clustering_*
├── src/
│   ├── main.py                # Fase 1: limpieza NHANES
│   ├── main_cruce.py          # Fase 1: validación de integración + catálogo Drugs
│   ├── main_transformacion.py # Fase 2: transformación y escalado (StandardScaler) + PCA
│   ├── main_eda.py            # Fase 3: EDA (estadística, figuras, correlación, informe)
│   ├── main_clasificacion.py  # Naive Bayes y KNN (split, métricas, k)
│   ├── main_analisis_clustering.py  # auditoría y diagnóstico previo a K-means
│   ├── repositorios/          # cargador, nhanes (schema mapper + fusión)
│   ├── servicios/             # limpieza, calidad (IQR), cruce, transformación, eda
│   └── utilidades/            # constantes y rutas
├── deployment/                # demostración interactiva
│   ├── azure/                 # exportar_modelo.py y subir_datos.ps1
│   ├── backend/               # FastAPI de solo lectura
│   └── frontend/              # HTML, CSS y JS de la página
└── README.md
```

## Orden de ejecución

```powershell
cd healtcare
python src/main.py                 # 1) Limpieza NHANES
python src/main_cruce.py           # 2) Validación de integración + CSV cruzado
python src/main_transformacion.py  # 3) Transformación y escalado (StandardScaler) + PCA
python src/main_eda.py             # 4) EDA (figuras + informe docx)
python src/main_clasificacion.py   # 5) NB y KNN (métricas y veredicto)
python src/main_analisis_clustering.py  # 6) auditoría y diagnóstico previo a K-means
python src/main_clustering.py           # 7) agrupamiento final con K-means
```

## Resultados por fase

### Fase 1 — Limpieza y cruce
- Integración de 5 ciclos por intersección de columnas (26 comunes), indexados por `SEQN` (0 duplicados).
- Códigos de no respuesta (7, 9, …) aplicados **solo a categóricas**, por columna.
- Menores de 20 años: educación y estado civil = 'No aplica (menor)' (22 504 casos).
- No se imputan labs de ayuno (`LBXGLU`, `LBDLDL`, `LBXTR`) ni respuestas de diabetes (`DIQ010`, `DIQ160`, `DIQ170`).
- Nulos: 261 879 → 145 822 (resto de no imputables). El resto se imputa con mediana/moda.
- Outliers: regla IQR (k=1,5), modo `flag`: 18 310 filas marcadas (35,9 %); no se eliminan pacientes.

### Fase 2 — Transformación y escalado
- `Disease_Indicator` = diabetes OR obesidad (IMC ≥ 30) OR colesterol total alto (≥ 200).
  - 28 687 clase 0 · 20 023 clase 1.
  - 2 255 filas sin respuesta de diabetes y sin otro criterio positivo quedan **sin etiqueta** y se excluyen.
- `BMXBMI` y `LBXTC` excluidos de `X` (definen la etiqueta → evitar leakage).
- Labs de ayuno excluidos de `X` (nulos estructurales).
- One-hot de 7 categóricas → 32 dummies (sin orden falso).
- Escalado con **StandardScaler** por defecto (medias ≈ 0, desv. ≈ 1).
- PCA: 3 componentes para ≥ 80 %, 5 para ≥ 90 % de 10 variables.
- Salidas: `X_nhanes.csv` (48 710 × 42), `y_nhanes.csv`, `decision_escalador.csv`, `varianza_pca.csv`, `pca_scree_plot.png`.

### Fase 3 — EDA
- Estadística descriptiva (tendencia, dispersión, forma) y outliers cuantificados por IQR.
- Galería: histogramas, boxplots, barras, scatter, heatmap (valor de r en cada celda), matriz de dispersión.
- Correlación de Pearson: 20 pares con |r| ≥ 0,5.
- Informe de 6 secciones: `informe_eda_nhanes.docx`. Los hallazgos se calculan a partir de los datos.

### Fase 4 — Clasificación NB y KNN
- Creamos una partición train/test estratificada 75/25 (`random_state=42`) sobre `X_nhanes.csv` (48 710 × 42).
- Comparamos GaussianNB y KNN con `ColumnTransformer` (solo numéricas escaladas).
- Probamos `k = 1, 5, 11, 21, 51` y también `weights="distance"`.
- Obtuvimos en test: KNN k=51 accuracy 0,825 / F1 0,792; GaussianNB accuracy 0,762 / F1 0,754 / recall 0,889.
- Recomendamos KNN k=51 como modelo principal y GaussianNB como línea base.
- Dejamos la evidencia en `docs/clasificacion_nb_knn.ipynb` y en los reportes de clasificación de `outputs/reportes/`.

### Fase 5 — Análisis previo al agrupamiento K-means
- Auditamos `X_nhanes.csv`: 48 710 × 42, sin nulos ni infinitos, 152 filas duplicadas, 10 numéricas escaladas y 32 dummies en 7 grupos one-hot.
- Comparamos cuatro listas de variables: todas (42), sin variables de encuesta (35), sin esas y sin una referencia por grupo (30) y solo numéricas (10).
- Descartamos `SDDSRVYR` y `RIDSTATR` porque son de diseño de encuesta, y quitamos una dummy de referencia por grupo para no duplicar categorías.
- Corremos K-means para `k = 2..10`. La mejor opción estable es el conjunto de 30 columnas con **k=3** (silueta 0,218 con muestra de 2 000).
- Verificamos la silueta con 2 000, 5 000 y 10 000 filas: 0,2182 / 0,2212 / 0,2213. El pico de memoria medido fue de **61,9 MB**.
- Perfilamos los grupos sin usar la etiqueta para entrenar: las prevalencias van de 0,048 a 0,637, así que los perfiles capturan señales reales.
- Reportamos la silueta baja con honestidad: son perfiles amplios, no grupos perfectamente separados.
- Evidencia: `docs/analisis_clustering.ipynb`, `outputs/reportes/analisis_pre_clustering.md` y `outputs/reportes/clustering_*`.

### Fase 6 — Agrupamiento final con K-means
- Agrupamos las 48 710 personas con las 30 columnas del conjunto C y `KMeans(n_clusters=3, n_init=10, random_state=42)`.
- Silueta: 0,2182 con 2 000 personas y 0,2213 con 10 000.
- Grupos: 9 130 / 23 304 / 16 276 personas. Prevalencia de la etiqueta por grupo: 0,048 / 0,481 / 0,637; la etiqueta no entró al entrenamiento.
- Combinamos métodos: un dendrograma Ward sobre una muestra de 5 000 personas confirma el corte en 3 grupos (salto entre las alturas 78,8 y 135,6). Su acuerdo con K-means en esa muestra es ARI 0,59 (moderado).
- Resultados: `outputs/reportes/clustering_etiquetas.csv`, `clustering_perfil_final.csv`, `clustering_comparacion_metodos.csv`, `clustering_veredicto.md` y `outputs/figuras/dendrograma_muestra.png`.
- Ejecución: `python src/main_clustering.py`.

## Demostración interactiva

La página pública está en **https://nhanes-demo.netlify.app** y la API que la alimenta en
**https://healtcare-data-mine.onrender.com** (`/health` responde `modo: azure`).

- **Azure Blob Storage:** copias de los CSV, reportes, modelos y figuras en el contenedor `nhanes`.
- **Render:** FastAPI de solo lectura, con `MODO_LOCAL=0` para leer desde Azure.
- **Netlify:** página con filtros en vivo, selector de parecidos del KNN, corte del árbol,
  formularios de prueba y descarga del CSV filtrado.
- **Local:** con `MODO_LOCAL=1` la API lee los archivos del repositorio. Detalles en `deployment/GUIA.md`.
- Los artefactos se generan con `python deployment/azure/exportar_modelo.py` y se suben con
  `deployment/azure/subir_datos.ps1`.

## Limitaciones conocidas (pendientes)
- Ajustamos el escalado y el PCA con todo el conjunto en las fases anteriores; en esta fase creamos la partición train/test y re-escalamos solo las numéricas dentro del Pipeline, sin rehacer esas fases.
- La población mezcla menores y adultos; los umbrales clínicos se aplican a todos.
- Los notebooks originales de limpieza, transformación y EDA no tienen salida guardada; el de clasificación sí.
- `Drugs_product` solo se resume (cruce con medicamentos no implementado).

## Ramas
- `main`: rama principal (default).

## Referencias
- Chapman, P. et al. (2000). *CRISP-DM 1.0*. SPSS.
- Han, J., Kamber, M. y Pei, J. (2012). *Data mining: Concepts and techniques* (3.ª ed.). Elsevier.
