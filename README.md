# Limpieza del dataset NHANES (2005–2014)

Proyecto de **Minería de Datos** (Corporación Universitaria Minuto de Dios). Se limpia y se
integra el dataset NHANES (5 ciclos, 2005–2014) por capas (repositorios, servicios y
utilidades) para dejarlo listo para la siguiente etapa de transformación y EDA.

**Equipo (MIMETIC):** Manuel José Rivera Guzmán · Julián Andrés Correa Cuevas

## Dataset

- Fuente: NHANES (National Health and Nutrition Examination Survey), CDC/NCHS, ciclos
  2005–2006, 2007–2008, 2009–2010, 2011–2012, 2013–2014.
- Contenido: ~50 965 participantes, 26 columnas comunes (intersección entre ciclos).
- Problemas encontrados en el crudo: 261 879 nulos totales, códigos especiales de no
  respuesta (7, 9, …), outliers clínicos reales (marcados, no eliminados).

## Requisitos

- Python 3.12+
- `pandas`, `numpy`

## Estructura del proyecto

```
healtcare/
├── data/
│   ├── raw/                      # datos crudos de entrada (5 CSV de NHANES + Drugs_product)
│   └── (salidas en outputs/)
├── docs/                         # documentación, plan, notebook de evidencia
├── models/                       # modelos serializados (.pkl) (fases posteriores)
├── outputs/
│   ├── cleaned/                  # nhanes_master_cleaned.csv.gz
│   └── reportes/                 # cleaning_summary.csv, cleaning_report.md
├── src/
│   ├── main.py                   # orquestador de limpieza NHANES
│   ├── main_cruce.py             # validacion de integracion + catalogo Drugs
│   ├── repositorios/             # acceso a datos (cargador, nhanes)
│   ├── servicios/                # limpieza y calidad (IQR)
│   └── utilidades/               # constantes y rutas
└── README.md
```

## Cómo ejecutar el pipeline

```powershell
python src/main.py
```

El script carga los 5 ciclos, los integra por intersección de columnas, aplica la limpieza
en orden, valida y guarda `nhanes_master_cleaned.csv.gz`.

Validación de integración y catálogo de fármacos:

```powershell
python src/main_cruce.py
```

## Pipeline (orden y por qué)

1. Cargar los 5 CSV crudos de NHANES.
2. Integrar por intersección de columnas (`NhanesSchemaMapper` + `NhanesFusion`), indexar por `SEQN`.
3. Diagnosticar (duplicados, nulos, `describe()`).
4. Quitar duplicados (primero, para no sesgar las cuentas posteriores).
5. Normalizar códigos de no respuesta (7, 9, …) a `NaN`.
6. Convertir tipos (`category` en demografía; numérico en el resto).
7. Imputar nulos con mediana (numéricas) y moda (categóricas).
8. Marcar outliers con la regla IQR (k=1.5), modo `flag` (no se eliminan pacientes).
9. Validar y exportar el archivo limpio.

## Resultados

| Indicador | Crudo (5 ciclos) | Limpio |
|---|---|---|
| Filas | 50 965 | 50 965 |
| Columnas | 26 (comunes) | 27 (incluye `OUTLIER_IQR`) |
| Duplicados de `SEQN` | 0 | 0 |
| Nulos totales | 261 879 | 0 |
| Filas marcadas IQR | — | 17 116 (33,6 %) |
| Columnas válidas para IQR | — | 12 |

## Metodología

El proceso se documenta siguiendo **CRISP-DM** (fases 1 a 3): *Business Understanding*,
*Data Understanding* y *Data Preparation*. Plan de elaboración: `docs/plan_elaboracion_nhanes.md`.

## Cuaderno de evidencia

Abrir `docs/limpieza_datos_nhanes.ipynb` en Jupyter desde la raíz del proyecto (los imports
agregan `src` al `sys.path`).

## Referencias

- Presentación del curso: `Presentacion/mineria_de_datos/sesion2..5`.
- Chapman, P. et al. (2000). *CRISP-DM 1.0*. SPSS.
- Han, J., Kamber, M. y Pei, J. (2012). *Data mining: Concepts and techniques* (3.ª ed.). Elsevier.