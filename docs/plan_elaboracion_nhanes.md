# Plan de elaboración — Proyecto Minería de Datos con NHANES (2005–2014)

**Proyecto:** Minería de Datos — Corporación Universitaria Minuto de Dios (UNIMINUTO), Ibagué, 2026-2
**Equipo (MIMETIC):** Manuel José Rivera Guzmán · Julián Andrés Correa Cuevas
**Dataset principal:** NHANES (National Health and Nutrition Examination Survey), ciclos 2005–2006, 2007–2008, 2009–2010, 2011–2012, 2013–2014
**Temario de referencia (no se sale de él):** `Presentacion/mineria_de_datos/sesion2` … `sesion5` (`presentacion.html` + código de `sesionX/codigo/`)
**Ciclo de vida:** CRISP-DM / KDD (fases de Entendimiento y Preparación de datos)
**Alcance de este plan:** Avance 1 — limpieza + transformación/escalado + EDA sobre NHANES

> Nota: la Fase 0 (qué es NHANES y cómo leer sus columnas) se entrega por separado en la
> conversación; **no forma parte de este plan**, por decisión del equipo.

---

## 0. Fuentes de verdad usadas (para no inventar)

| Fuente | Qué aporta al plan |
|---|---|
| `Presentacion/mineria_de_datos/sesion2/presentacion.html` | Fuentes, formatos, tipos pandas, cargas defensivas, API REST/JSON |
| `Presentacion/mineria_de_datos/sesion3/presentacion.html` | Diagnóstico, MCAR/MAR/MNAR, imputación, duplicados, outliers IQR/z-score, pipeline |
| `Presentacion/mineria_de_datos/sesion4/presentacion.html` | Escalado (MinMax/Standard/Robust), one-hot, ordinal, discretización, PCA |
| `Presentacion/mineria_de_datos/sesion5/presentacion.html` | EDA: tendencia/dispersión/forma, gráficos matplotlib, Pearson, causalidad, informe |
| `proyecto/docs/DOCUMENTACION_FASE_1.md` | Limpieza real ejecutada sobre NHANES (cifras verificadas) |
| `proyecto/docs/PLAN_DE_DESARROLLO.md` | Arquitectura no monolítica, SOLID, regla IQR |
| `proyecto/outputs/reportes/cleaning_summary.csv` | Cifras verificadas de `nhanes_master` |

Cifras de NHANES **verificadas** (de `cleaning_summary.csv`): 5 archivos crudos, 50 965 filas
brutas, 34 columnas curadas, 0 duplicados de `SEQN`, 33 columnas con tipo convertido, memoria
13 537,7 KB → 11 099,2 KB (−18,0 %), nulos 391 851 → 43 289 (imputación con mediana),
18 columnas válidas para IQR, 45 267 valores atípicos por columna, 22 834 filas marcadas (44,8 %),
modo `flag` (no se eliminó ningún paciente).

---

## Fase 1 — Limpieza de datos y cruce de datos necesarios
**Temario:** Sesión 2 · Fuentes y Tipos de Datos  +  Sesión 3 · Limpieza de Datos

### 1.1 Fuentes y tipos (Sesión 2)

**Qué se hace y por qué (según la presentación):**
- Identificar las fuentes del proyecto: los 5 CSV de NHANES (`Nhanes_2005_2006.csv` …
  `Nhanes_2013_2014.csv`) y, como fuente secundaria opcional, `Drugs_product.csv`
  (farmacología). En el espectro de datos (estructurado/semiestructurado/no estructurado),
  ambos son **estructurados** (filas y columnas fijas, esquema rígido).
- Formato: CSV (texto plano separado por comas). Regla práctica del curso: prototipar en CSV.
- Carga defensiva con `pandas.read_csv`: verificar `sep`, `encoding`, `decimal`, `skiprows`.
  NHANES se lee bien en UTF-8 (todas las columnas son numéricas); `Drugs_product.csv` es
  latin-1 (contiene caracteres especiales). Se usa `read_csv_robust()` (intenta
  `utf-8 → cp1252 → latin-1` y registra la codificación usada).
- Diagnóstico de tipos que pandas infiere (`df.dtypes`, `df.shape`, `df.isna().sum()`,
  `df.describe()`): NHANES llega con **todas las columnas en `float64`** (412–465 por ciclo),
  porque los códigos NHANES son numéricos; por eso conviene convertir demografía a
  `category` para ahorrar memoria.
- Regla del curso: "que pandas cargue sin errores NO significa que cargue bien" — los dtypes
  inferidos son el primer examen de salud del dataset.

**Procedimiento concreto:**
1. Listar los 5 archivos en `data/raw/` y confirmar que existen (sin descomprimir ningún zip).
2. Cargar cada ciclo con `read_csv` y reportar `shape` + `dtypes` por ciclo.
3. Comparar las columnas entre ciclos: identificar las ~38 curadas y la intersección común
   (~34) que sobrevive a todos los años (algunas cambian de nombre entre años:
   `DMDBORN`, `DMDBORN2`, `DMDBORN4`).
4. Documentar formato, tamaño y posible variable objetivo (tarea independiente de la sesión 2).

**Entregable:** reporte de fuentes y dtypes por ciclo (`docs/` o notebook).

---

### 1.2 Cruce / integración de los datos necesarios (NhanesFusion)

**Qué se hace y por qué:**
- Integrar los 5 ciclos de NHANES en un solo `DataFrame` maestro, siguiendo el requisito de la
  propuesta técnica: "unificar NHANES 2005–2014 en un DataFrame maestro indexado por `SEQN`
  (Patient_ID)".
- `NhanesSchemaMapper`: resuelve el esquema por **intersección de columnas** (no unión), porque
  solo las columnas comunes a todos los años son comparables; las específicas de un ciclo se
  descartan para no crear nulos masivos.
- `NhanesFusion`: une los 5 archivos por las columnas comunes y los indexa por `SEQN`.
- Validar unicidad de la clave maestra (`SEQN`): 0 duplicados (verificado en
  `cleaning_summary.csv`).

**Procedimiento concreto:**
1. Seleccionar las ~38 columnas curadas (demografía, antropometría, laboratorio, nutrición,
   estado de salud) según `PLAN_DE_DESARROLLO.md` §2.1.
2. Calcular la intersección de columnas entre los 5 ciclos → ~34 columnas comunes.
3. Concatenar los 5 ciclos manteniendo solo la intersección.
4. Indexar por `SEQN` y verificar unicidad (`SEQN.duplicated().sum() == 0`).
5. Exportar `nhanes_master` (50 965 filas × 34 columnas) como punto de partida de la limpieza.

**Entregable:** `nhanes_master` (DataFrame maestro) + verificación de unicidad de `SEQN`.

---

### 1.3 Limpieza de datos (Sesión 3)

**Qué se hace y por qué (según la presentación y la documentación existente):**

**a) Diagnóstico (3 preguntas):** `isna().sum()`, `duplicated().sum()`, `describe()` sobre
las numéricas. Tres líneas que revelan la salud del dataset (sesión 3, diapositiva 6).

**b) Duplicados:** `drop_duplicates()` por clave maestra `SEQN` y por filas idénticas exactas.
En NHANES: 0 duplicados (verificado). Se hace **primero** para no sesgar medianas posteriores
(regla del curso: deduplicar → categorías → nulos → outliers).

**c) Tipos de datos (`TypeCleaner`):**
- 33 columnas convertidas: demografía/labs/nutrición a numérico; `RIAGENDR`, `RIDRETH1`,
  `DMDEDUC2`, `DMDMARTL`, `RIDSTATR`, `HUQ010`, `SDDSRVYR` a `category`.
- Memoria: 13 537,7 KB → 11 099,2 KB (−18,0 %), cumpliendo el requisito de optimización
  de RAM de la propuesta.
- Justificación (sesión 2): `object` es la "caja negra"; si una columna numérica cae ahí,
  hay basura adentro. Convertir a `category` ahorra memoria y evita confusiones.

**d) Categorías uniformes / códigos NHANES:**
- NHANES codifica variables como números con etiquetas (1 = Masculino, 2 = Femenino) y usa
  códigos especiales para no respuesta: 7 = "Refused", 9 = "Don't know". Estos **no son
  valores reales** y se tratan como `NaN` (documentar la decisión).
- Se normalizan los códigos categóricos y se verifica contra la lista oficial de categorías.

**e) Valores faltantes (MCAR/MAR/MNAR):**
- Clasificar los nulos por columna según su origen (sesión 3, diapositiva 7): ¿faltan al azar
  (MCAR), dependen de otra variable (MAR) o del propio valor (MNAR)?
- Estrategia: imputación con **mediana** (robusta a outliers) para numéricas; **moda** para
  categóricas. Justificación: mediana casi no se mueve ante extremos (sesión 3, código
  comentado: "Imputando edad = 49.0"). La media NO se usa porque convive con valores extremos.
- Resultado verificado: nulos 391 851 → 43 289.
- Regla de oro del curso: toda imputación queda documentada (columna, método y por qué).

**f) Outliers — regla IQR (única, obligatoria):**
- Fórmula (sesión 3, diapositiva 12): `Q1 = percentil 25`, `Q3 = percentil 75`,
  `IQR = Q3 − Q1`, límite inferior = `Q1 − 1,5·IQR`, límite superior = `Q3 + 1,5·IQR`.
  `k = 1,5` (moderado). Un valor es atípico si está fuera de `[inferior, superior]`.
- Aplicado **solo a columnas numéricas**, columna por columna, ignorando NaN.
- Columnas con IQR nulo (`Q1 == Q3`) se **omiten** (sin dispersión no hay outliers válidos)
  — caso visto en NHANES (`LBDLDL`, `LBXGLU`, etc.).
- Modo **`flag`**: se añade la columna `OUTLIER_IQR` (`True/False`), **sin eliminar pacientes**
  (decisión de negocio: no borrar registros de salud; se reserva para EDA).
- Resultado verificado: 18 columnas válidas, 45 267 valores atípicos por columna, 22 834 filas
  marcadas (44,8 %).

**g) Tratar vs conservar (sesión 3, diapositiva 14):** en NHANES los outliers de laboratorio
pueden ser valores clínicos reales (paciente diabético, hipercolesterolémico) → se **marcan**
(flag), no se eliminan. La decisión se valida con el negocio y se documenta.

**h) Validación y exportación:**
- Validar contra criterios explícitos: filas, nulos, rangos (rúbrica de código, funcionalidad 40%).
- Exportar `nhanes_master_cleaned.csv.gz` (gzip) con la columna `OUTLIER_IQR`.
- Bitácora: qué cambió, cuántos valores, con qué criterio (documentación 20%).

---

### 1.4 Cruce opcional con Drugs_product (farmacología)

**Qué se hace y por qué:**
- Normalizar `Drugs_product.csv` (117 365 filas → 115 678 tras dedup de 1 687 duplicados):
  `ACTIVE_NUMERATOR_STRENGTH` a numérico; `PHARM_CLASSES`, `LABELERNAME`, `ROUTENAME`,
  `DOSAGEFORMNAME`, etc. a `category`; `START/ENDMARKETINGDATE` a `datetime`.
- Enriquecer el dataset de salud con información farmacológica por condición médica
  (medicamento activo por `Medical Condition`).
- Los `NaN` de las columnas enriquecidas son **MNAR** (información no disponible en el
  catálogo, no error de captura) → **no se imputan** (sesión 3, MCAR/MAR/MNAR).

**Entregables de la Fase 1:**
- `data/raw/` verificado (5 CSV de NHANES + Drugs_product.csv).
- `nhanes_master` (50 965 × 34) y `nhanes_master_cleaned.csv.gz` (50 965 × 35 con
  `OUTLIER_IQR`).
- `cleaning_report.md` y `cleaning_summary.csv` (bitácora línea por línea).
- Notebook de evidencia con el pipeline ejecutado y validación verde.

---

## Fase 2 — Transformación y escalado
**Temario:** Sesión 4 · Transformación y Reducción de Datos

### 2.1 Selección de variables y exclusión

**Qué se hace y por qué (según la presentación, sección "matriz final"):**
- `X` (predictores) solo con variables numéricas/categóricas útiles; `y` (objetivo) aparte.
  Mezclarlas es filtrar el futuro (leakage).
- Excluir `SEQN` (identificador, no patrón), variables con IQR nulo, y columnas con
  porcentaje alto de nulos.
- Variables candidatas NHANES (de `PLAN_DE_DESARROLLO.md` §2.1):
  - Demografía: `RIAGENDR`, `RIDAGEYR`, `RIDRETH1`, `DMDEDUC2`, `INDFMIN2`/`INDHHIN2`.
  - Antropometría: `BMXWT`, `BMXHT`, `BMXBMI`, `BMXWAIST`.
  - Laboratorio: `LBXGLU`, `LBXIN`, `LBXTC`, `LBDLDL`, `LBXTR`.
  - Nutrición (día 1): `DR1TKCAL`, `DR1TSUGR`, `DR1TPROT`, `DR1TCARB`, `DR1TFIBE`,
    `DR1TTFAT`.
  - Estado de salud: `HUQ010`, `DIQ160`, `DIQ170`.
- Objetivo `y`: `Disease_Indicator` derivado de `DIQ010` (diabetes), `BMXBMI ≥ 30`
  (obesidad) y `LBXTC` (colesterol alto) — derivación por reglas clínicas documentadas
  (como en `derivar_etiquetas_clinicas.py` del proyecto healthcare, pero adaptado a NHANES).

---

### 2.2 Codificación de categóricas (Sesión 4, diapositivas 9–10)

**Qué se hace y por qué:**
- Variable **nominal** (sin orden real: `RIAGENDR`, `RIDRETH1`, `DMDEDUC2`) → **one-hot**
  (`pd.get_dummies`, `dtype=int`). No inventa orden: las categorías son "diferentes", no
  "menor/mayor".
- Variable **ordinal genuina** (jerarquía real, p. ej. nivel educativo primario < bachiller <
  universitario) → mapeo manual consciente y documentado. **Nunca** `LabelEncoder` sobre
  nominales (inventa Premium > Estandar > Basico).
- `drop="first"` en producción (evita multicolinealidad perfecta): si no es Basico ni
  Estandar, es Premium.

**Procedimiento concreto:**
1. Identificar categóricas nominales vs ordinales genuinas en NHANES.
2. Aplicar `get_dummies` a las nominales (`dtype=int`).
3. Aplicar mapeo manual a las ordinales (documentar cada mapeo).
4. Verificar: número de columnas = categorías; sin booleanos sueltos.

---

### 2.3 Discretización (Sesión 4, diapositiva 11)

**Qué se hace y por qué:**
- `KBinsDiscretizer` (`n_bins`, `encode="ordinal"`, `strategy="quantile"`) para traducir
  numéricas a segmentos de negocio (p. ej. `RIDAGEYR` → joven/adulto/mayor por cuartiles).
- Útil para segmentación comercial y reglas legibles; costo: se pierde detalle dentro del
  rango (decisión de negocio, no técnica).

---

### 2.4 Escalado (Sesión 4, diapositivas 6–8)

**Qué se hace y por qué:**
- Sin escalar, la columna de mayor escala secuestra la distancia (ejemplo del curso:
  facturación aporta el 99,9 % de la distancia). KNN y K-means quedarían ciegos.
- Tres escaladores (tabla de la sesión 4):
  - `MinMaxScaler`: `(x − mín)/(máx − mín)` → [0,1]. Para datos acotados sin outliers graves
    (redes neuronales, imagen).
  - `StandardScaler`: `(x − media)/desv.est.` → media ≈ 0, desv ≈ 1. Caso general; favorito
    para regresión, SVM, PCA.
  - `RobustScaler`: `(x − mediana)/IQR`. Para cuando hay outliers **reales** que el negocio
    pide conservar.
- Decisión para NHANES (argumentada): se adopta **StandardScaler como escalador por defecto
  para todas las variables numéricas** (caso general del curso: media ≈ 0, desv ≈ 1; favorito
  para regresión, SVM y PCA).
  - Justificación: la mayoría de las variables (antropometría, demografía, labs tras la
    limpieza) no presentan outliers graves; StandardScaler es el escalador recomendado por
    el curso para el caso general.
  - **RobustScaler queda como opción documentada** para una variable específica cuando se
    decida conservar outliers reales (p. ej. un lab con pacientes diabéticos) — decisión que
    se registra en la bitácora, no se aplica por defecto.
  - MinMax solo si se requiere rango [0,1] (p. ej. para redes neuronales).
- Advertencia del curso (fuga de datos): el escalador se ajusta (`fit`) **solo con los datos
  de entrenamiento**. Aplicarlo antes de separar train/test filtra información del futuro.
  Esto se formaliza en la fase de modelado (sesión 7).

**Procedimiento concreto:**
1. Definir `NUMERICAS` (lista de predictoras numéricas) y `CATEGORICAS`.
2. Calcular distancia entre dos pacientes sin escalar y con MinMax para evidenciar el efecto
   (como en `transformaciones.py` del temario: 42 550,3 → 0,829).
3. Aplicar cada escalador y verificar: MinMax min=0 max=1; Standard media≈0 desv≈1;
   Robust mediana≈0.
4. Escoger el escalador por variable según la tabla anterior y documentar la decisión.
5. No escalar las dummies (ya viven en [0,1]).

---

### 2.5 Reducción dimensional — PCA (Sesión 4, diapositivas 12–14)

**Qué se hace y por qué:**
- PCA = proyección que conserva la máxima varianza ("la sombra que conserva la forma").
- Requisitos inquebrantables: datos sin nulos y **escalados primero** (StandardScaler); si no,
  la variable grande domina la primera componente por pura escala.
- Criterio práctico: conservar componentes hasta 80–90 % de varianza acumulada.
- En NHANES, las variables antropométricas y de laboratorio suelen estar correlacionadas
  (multicolinealidad) → PCA puede comprimir. Pero si las variables son independientes (como
  en TelecomUNO del temario: ~17 % por componente, no comprime), PCA sirve como
  **diagnóstico de redundancia**, no como compresión.
- Trade-off: se pierde interpretabilidad (los componentes ya no tienen nombre físico).
- NO usar PCA cuando cada variable debe seguir siendo interpretable (regulación/auditoría) o
  con datos categóricos puros.

**Procedimiento concreto:**
1. Estandarizar las numéricas con `StandardScaler`.
2. `PCA()` completo; imprimir `explained_variance_ratio_.cumsum()`.
3. Calcular componentes para ≥80 % y ≥90 %.
4. Decidir si se aplica (y con cuántos componentes) y documentar la varianza retenida.

---

### 2.6 Matriz final (Sesión 4, diapositiva 16)

**Qué se hace y por qué:**
- `X_final = concat(numéricas escaladas, dummies)`; `y` aparte.
- Checklist de orden (memorizar): **Limpiar → Codificar → Escalar → (PCA si aplica) → Modelar**.
- Nunca incluir la variable objetivo en `X`.

**Procedimiento concreto:**
1. Concatenar numéricas escaladas + dummies.
2. Verificar forma `X` (n × k) y que `y` esté fuera.
3. Guardar `X_nhanes` y `y_nhanes` (CSV o `.npy`) para la fase de modelado.

**Entregables de la Fase 2:**
- `X_nhanes` y `y_nhanes` guardados.
- Tabla de decisión de escalador por variable.
- Tabla de varianza explicada de PCA y decisión.
- Notebook de evidencia.

---

## Fase 3 — Análisis Exploratorio de Datos (EDA)
**Temario:** Sesión 5 · Análisis Exploratorio de Datos (EDA)

### 3.1 Estadística descriptiva (Sesión 5, diapositiva 7)

**Qué se hace y por qué:**
- Tres familias de medidas, tres preguntas:
  - Tendencia central (media, mediana, moda): ¿dónde está el centro típico?
  - Dispersión (rango, IQR, desviación estándar): ¿qué tan extendidos están los datos?
  - Forma (asimetría/skew, curtosis): ¿es simétrica? ¿tiene colas pesadas?
- Con asimetría alta (cola larga), reportar **mediana** (la voz honesta del centro); la media
  se deja arrastrar por los extremos (ejemplo del curso: arriendo media 249 mil vs mediana
  238 mil, skew +2,56).
- Curtosis: colas pesadas → eventos raros pero muy alejados.

**Procedimiento concreto:**
1. `df.describe()` de las numéricas + `skew()` y `kurtosis()` de `facturacion`-equivalentes
   en NHANES (labs, nutrición).
2. Identificar las 2 asimetrías más marcadas.
3. Decidir media vs mediana por variable y documentar.

---

### 3.2 Visualización con matplotlib (Sesión 5, diapositivas 10–14)

**Qué se hace y por qué:**
- Galería mínima del curso: histograma, boxplot, barras, dispersión, heatmap y matriz de
  dispersión — todos con `matplotlib` puro.
- Histograma: la silueta de la variable; pocos bins ocultan picos, demasiados inventan ruido
  (30 es buen punto de partida).
- Boxplot: IQR (caja), mediana (línea), bigotes 1,5·IQR, puntos fuera = outliers visuales.
  Súper poder: comparar grupos lado a lado (p. ej. labs por sexo o por grupo de edad).
- Barras: contar categorías; ordenar siempre por frecuencia o por valor, jamás alfabético
  "porque sí" (el orden ya es información). Para precio/valor por grupo, mejor la mediana.
- Dispersión + recta de tendencia: cada punto un paciente; r y pendiente.
- Heatmap de correlaciones: toda la matriz de Pearson en un vistazo (rojo positivo, azul
  negativo). Detecta redundancia (multicolinealidad) y relaciones.
- Matriz de dispersión: todos los scatter cruzados + histogramas en diagonal (versión
  matplotlib del pairplot).

**Buenas prácticas (Sesión 5, diapositiva 15):**
- Ejes etiquetados con unidades; título que declara el **hallazgo**, no el tipo de gráfico;
  barras arrancan en cero; paleta accesible.
- Nunca: pastel 3D, truncar eje Y, doble eje Y disfrazando correlaciones, colormap arcoíris.

**Procedimiento concreto:**
1. Univariado: histograma + boxplot de las variables numéricas clave (labs, nutrición,
   antropometría); cuantificar outliers con IQR (no solo "se ven raros").
2. Barras de categorías (`RIAGENDR`, `RIDRETH1`, `DMDEDUC2`) + tabla de tasa del objetivo
   por segmento (`pd.crosstab(normalize="index")`).
3. Dispersión: antropometría/labs vs objetivo; heatmap de correlaciones numéricas.
4. Guardar cada figura en `docs/figuras/` (o carpeta equivalente) con nombre descriptivo.

---

### 3.3 Correlación de Pearson (Sesión 5, diapositiva 8)

**Qué se hace y por qué:**
- Pearson mide asociación **lineal**: fuerza (|r|) y dirección (signo).
- Guía práctica (no dogma): 0–0,1 sin relación; 0,1–0,3 débil; 0,3–0,5 moderada;
  0,5–0,7 fuerte; >0,7 muy fuerte.
- **Correlación NO es causalidad** (sesión 5): helado ↔ ahogamientos (confusora = verano);
  más bomberos ↔ más daños (la gravedad causa ambos). En NHANES: edad ↔ glucosa es
  asociación, no causalidad; las confusoras (dieta, actividad) deben controlarse.
- Variables redundantes (r alto) anticipan multicolinealidad en modelos lineales.

**Procedimiento concreto:**
1. `df[numéricas].corr()` y heatmap.
2. Reportar pares con |r| > 0,5 (fuerte) y discutir redundancia.
3. Redactar cada relación como "asociación", nunca como causalidad, salvo diseño que la
   soporte.

---

### 3.4 Informe EDA — estructura oficial (Sesión 5, diapositiva 20)

El instrumento del curso exige 6 secciones con pesos:

| Sección | Contenido mínimo | Peso |
|---|---|---|
| 1 · Portada y contexto | Integrantes, pregunta de negocio del proyecto, objetivos del análisis | 10 % |
| 2 · Calidad de datos | Nulos, duplicados, outliers encontrados y decisiones tomadas (herencia sesiones 3–4) | 15 % |
| 3 · Análisis univariado | Tablas descriptivas + mínimo 4 gráficos interpretados (no solo pegados) | 25 % |
| 4 · Análisis bivariado/multivariado | Correlaciones, cruces con la variable objetivo, heatmap | 25 % |
| 5 · Hallazgos y recomendaciones | Mínimo 3 hallazgos en formato evidencia-acción, redactados para no técnicos | 20 % |
| 6 · Anexos | Notebook reproducible con el código completo ejecutado | 5 % |

**Formato de hallazgo (sesión 5, ejercicio en clase, punto 5):**
"hallazgo + evidencia (cifra/gráfico) + acción sugerida para el negocio".

**Escalera de logro esperada:** tablas y gráficos básicos → interpretación de la mayoría →
informe completo con hallazgos accionables → (excepcional) nuevas variables/segmentos y
validación de hipótesis con datos.

**Entregables de la Fase 3:**
- Informe EDA de NHANES (docx/pdf) con las 6 secciones.
- Figuras: histogramas, boxplots, barras, scatter, heatmap, matriz de dispersión.
- Notebook reproducible (anexo).

---

## Cronograma y dependencias

```
Fase 1 (limpieza + cruce)  →  Fase 2 (transformación/escalado)  →  Fase 3 (EDA)
   produce nhanes_master_cleaned     produce X_nhanes, y_nhanes       produce informe EDA
   + bitácora                        + decisión de scaler/PCA         + figuras + hallazgos
```

Secuencial: cada fase consume los entregables de la anterior. La rúbrica de código del curso
(funcionalidad 40 %, justificación técnica 30 %, documentación 20 %, reproducibilidad 10 %)
aplica a todos los entregables programados.

---

## Riesgos y mitigaciones (tomados de `PLAN_DE_DESARROLLO.md` §7)

| Riesgo | Mitigación |
|---|---|
| NHANES: esquemas heterogéneos entre años | Mapper canónico por intersección de columnas (`NhanesSchemaMapper`) |
| Archivos grandes (412–465 cols, ~10 k filas/ciclo) | `dtype` optimizados, categóricas, carga por chunks si hace falta |
| Códigos especiales NHANES (7 = Refused, 9 = Don't know) | Tratar como `NaN` y documentar |
| Outliers en labs/nutrición distorsionan análisis | Regla IQR obligatoria, modo `flag` (no eliminar pacientes) |
| Multicolinealidad entre variables antropométricas | Detectar con heatmap de Pearson; PCA como diagnóstico |
| Fuga de datos (data leakage) | `fit` del scaler solo con train; `y` fuera de `X` |

---

## Restricciones respetadas

- **No se inventa nada:** cada método, fórmula, cifra y criterio proviene del temario
  (`Presentacion/mineria_de_datos/sesion2..5`) o de la documentación ya generada
  (`DOCUMENTACION_FASE_1.md`, `PLAN_DE_DESARROLLO.md`, `cleaning_summary.csv`).
- **Se dice qué hizo cada procedimiento:** la bitácora (`cleaning_report.md`) y los notebooks
  de evidencia registran, por paso, qué cambió, cuántos valores y con qué criterio.
- **No se sale del temario:** las fases mapean 1:1 a las sesiones 2, 3, 4 y 5 del curso.