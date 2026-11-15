# Minería de Datos — NHANES (2005–2014) + Drugs_product

Proyecto de **Minería de Datos** (Corporación Universitaria Minuto de Dios, UNIMINUTO). Se limpia,
integra, transforma y analiza el dataset **NHANES** (5 ciclos, 2005–2014) junto con el catálogo
farmacológico **Drugs_product**, siguiendo las sesiones 2, 3, 4 y 5 del curso.

**Equipo (MIMETIC):** Manuel José Rivera Guzmán · Julián Andrés Correa Cuevas
**Asignatura:** Minería de Datos · Ibagué · 2026-2

## Dataset

- **NHANES** (National Health and Nutrition Examination Survey, CDC/NCHS): 5 ciclos
  (2005–2006, 2007–2008, 2009–2010, 2011–2012, 2013–2014); ~50 965 participantes;
  26 columnas comunes por intersección de esquemas.
- **Drugs_product** (FDA): ~117 365 productos farmacéuticos, 18 columnas (catálogo de referencia).

## Requisitos

- Python 3.12+
- `pandas`, `numpy`, `scikit-learn`, `matplotlib`, `python-docx`

```powershell
pip install pandas numpy scikit-learn matplotlib python-docx
```

## Estructura del proyecto

```
healtcare/
├── data/raw/                  # datos crudos (5 CSV NHANES + Drugs_product.csv)
├── docs/                      # plan, notebooks de evidencia
├── outputs/
│   ├── cleaned/               # nhanes_master_cleaned.csv(.gz), nhanes_master_cruzado.csv
│   ├── transformed/           # X_nhanes.csv, y_nhanes.csv, decision_escalador.csv, varianza_pca.csv
│   ├── eda/                   # resumen_descriptivo.csv, outliers_iqr.csv, pares_correlacion.csv
│   ├── figuras/               # histogramas, boxplots, barras, scatter, heatmap, matriz dispersion, PCA
│   └── reportes/              # cleaning_summary.csv, cleaning_report.md, informe_eda_nhanes.docx
├── src/
│   ├── main.py                # Fase 1: limpieza NHANES
│   ├── main_cruce.py          # Fase 1: validacion de integracion + catalogo Drugs
│   ├── main_transformacion.py # Fase 2: transformacion y escalado (StandardScaler) + PCA
│   ├── main_eda.py            # Fase 3: EDA (estadistica, figuras, correlacion, informe)
│   ├── repositorios/          # cargador, nhanes (schema mapper + fusion)
│   ├── servicios/             # limpieza, calidad (IQR), cruce, transformacion, eda
│   └── utilidades/            # constantes y rutas
└── README.md
```

## Orden de ejecución

```powershell
cd healtcare
python src/main.py                # 1) Limpieza NHANES
python src/main_cruce.py          # 2) Validacion de integracion + CSV cruzado
python src/main_transformacion.py  # 3) Transformacion y escalado (StandardScaler) + PCA
python src/main_eda.py            # 4) EDA (figuras + informe docx)
```

## Resultados por fase

### Fase 1 — Limpieza y cruce
- Integración de 5 ciclos por intersección de columnas (26 comunes), indexados por `SEQN` (0 duplicados).
- Nulos: 261 879 → 0 (imputación con mediana/moda).
- Outliers: regla IQR (k=1,5), modo `flag` (17 116 filas marcadas, 33,6 %; sin eliminar pacientes).
- Salidas: `nhanes_master_cleaned.csv(.gz)`, `nhanes_master_cruzado.csv`, bitácora.

### Fase 2 — Transformación y escalado
- Etiqueta `Disease_Indicator` derivada (diabetes OR obesidad OR colesterol alto): 30 942 clase 0 · 20 023 clase 1.
- Codificación one-hot de 7 categóricas → 29 dummies (sin orden falso).
- Escalado con **StandardScaler** por defecto (medias ≈ 0, desv. ≈ 1).
- PCA: 6 componentes para ≥80 %, 8 para ≥90 % de 15 variables.
- Salidas: `X_nhanes.csv` (50 965 × 44), `y_nhanes.csv`, `decision_escalador.csv`, `varianza_pca.csv`, `pca_scree_plot.png`.

### Fase 3 — EDA
- Estadística descriptiva (tendencia, dispersión, forma) + outliers cuantificados.
- Galería: histogramas, boxplots, barras, scatter, heatmap (con valor de r en cada celda), matriz de dispersión.
- Correlación de Pearson: 20 pares con |r| ≥ 0,5 (multicolinealidad en antropometría).
- Informe EDA de 6 secciones: `informe_eda_nhanes.docx`.

## Ramas
- `main`: rama principal (default).

## Referencias
- Presentación del curso: `Presentacion/mineria_de_datos/sesion2..5`.
- Chapman, P. et al. (2000). *CRISP-DM 1.0*. SPSS.
- Han, J., Kamber, M. y Pei, J. (2012). *Data mining: Concepts and techniques* (3.ª ed.). Elsevier.