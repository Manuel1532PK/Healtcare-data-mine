# Minería de Datos — NHANES (2005–2014) + Drugs_product

Proyecto de **Minería de Datos** (Corporación Universitaria Minuto de Dios, UNIMINUTO). Se limpia,
integra, transforma y analiza el dataset **NHANES** (5 ciclos, 2005–2014) junto con el catálogo
farmacológico **Drugs_product**, siguiendo las sesiones 2, 3, 4 y 5 del curso.

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
├── docs/                      # plan y notebooks de evidencia
├── outputs/
│   ├── cleaned/               # nhanes_master_cleaned.csv(.gz), nhanes_master_cruzado.csv
│   ├── transformed/           # X_nhanes.csv, y_nhanes.csv, decision_escalador.csv, varianza_pca.csv
│   ├── eda/                   # resumen_descriptivo.csv, outliers_iqr.csv, pares_correlacion.csv
│   ├── figuras/               # histogramas, boxplots, barras, scatter, heatmap, matriz de dispersión, PCA
│   └── reportes/              # cleaning_summary.csv, cleaning_report.md, informe_eda_nhanes.docx
├── src/
│   ├── main.py                # Fase 1: limpieza NHANES
│   ├── main_cruce.py          # Fase 1: validación de integración + catálogo Drugs
│   ├── main_transformacion.py # Fase 2: transformación y escalado (StandardScaler) + PCA
│   ├── main_eda.py            # Fase 3: EDA (estadística, figuras, correlación, informe)
│   ├── repositorios/          # cargador, nhanes (schema mapper + fusión)
│   ├── servicios/             # limpieza, calidad (IQR), cruce, transformación, eda
│   └── utilidades/            # constantes y rutas
└── README.md
```

## Orden de ejecución

```powershell
cd healtcare
python src/main.py                 # 1) Limpieza NHANES
python src/main_cruce.py           # 2) Validación de integración + CSV cruzado
python src/main_transformacion.py  # 3) Transformación y escalado (StandardScaler) + PCA
python src/main_eda.py             # 4) EDA (figuras + informe docx)
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

## Limitaciones conocidas (pendientes)
- No hay partición train/test: el escalador y el PCA se ajustan con todo el conjunto. Antes de modelar, ajustar solo con train.
- La población mezcla menores y adultos; los umbrales clínicos se aplican a todos.
- Los notebooks `docs/*.ipynb` no se han ejecutado con salida guardada.
- `Drugs_product` solo se resume (cruce con medicamentos no implementado).

## Ramas
- `main`: rama principal (default).

## Referencias
- Presentación del curso: `Presentacion/mineria_de_datos/sesion2..5`.
- Chapman, P. et al. (2000). *CRISP-DM 1.0*. SPSS.
- Han, J., Kamber, M. y Pei, J. (2012). *Data mining: Concepts and techniques* (3.ª ed.). Elsevier.
