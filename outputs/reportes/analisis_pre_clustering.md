# Análisis previo al agrupamiento K-means

## 1. Auditoría de los datos

Usamos `outputs/transformed/X_nhanes.csv` e `y_nhanes.csv` de `main`. No modificamos esos archivos. Guardamos la etiqueta para el perfil final; no la dejamos entrar en el entrenamiento.

```
 filas  columnas  numéricas  dummies  nan  infinitos  filas_duplicadas  columnas_constantes  prevalencia_y
 48710        42         10       32    0          0               152                    0         0.4111
```

- No hay valores faltantes ni infinitos.
- Encontramos 152 filas duplicadas; las conservamos porque pueden ser participantes con mediciones idénticas.
- No hay columnas constantes.

## 2. Estructura de variables

Tenemos 10 numéricas ya escaladas (media ≈ 0, desviación ≈ 1) y 32 dummies repartidas en 7 grupos one-hot. Cada grupo suma exactamente 1 por fila.

```
variable  tipo  n_columnas prevalencia_min prevalencia_max suma_min suma_max media_z
RIAGENDR dummy           2           0.495           0.505        1        1        
RIDRETH1 dummy           5          0.0924          0.3773        1        1        
DMDEDUC2 dummy           6          0.0659          0.4168        1        1        
DMDMARTL dummy           7          0.0194          0.4164        1        1        
RIDSTATR dummy           2          0.0363          0.9637        1        1        
  HUQ010 dummy           5          0.0299          0.3192        1        1        
SDDSRVYR dummy           5          0.1922          0.2074        1        1        
```

## 3. Redundancia y señales importantes

Las numéricas más correlacionadas son:

```
variable_1 variable_2  correlacion_abs
  DR1TKCAL   DR1TTFAT            0.888
  DR1TKCAL   DR1TCARB            0.887
     BMXWT   BMXWAIST            0.869
  DR1TSUGR   DR1TCARB            0.851
  DR1TKCAL   DR1TPROT            0.801
  DR1TPROT   DR1TTFAT            0.745
     BMXWT      BMXHT            0.736
     BMXHT   BMXWAIST            0.677
  DR1TKCAL   DR1TSUGR            0.673
  DR1TCARB   DR1TTFAT            0.653
```

Además, `DMDEDUC2_0.0` está en 20 301 filas (41,7 %) y su edad promedio es notablemente menor que en el resto. Ese código funciona como proxy de menores de edad, así que esperamos que un grupo quede marcado por la edad.

## 4. Conjuntos de variables evaluados

- **A_todo (42):** todas las columnas, incluidas las técnicas `SDDSRVYR` y `RIDSTATR`.
- **B_sin_tecnicas (35):** quitamos `SDDSRVYR` y `RIDSTATR`.
- **C_recomendado (30):** lo anterior y además quitamos una dummy de referencia por grupo: RIAGENDR_2.0, RIDRETH1_5.0, DMDEDUC2_5.0, DMDMARTL_6.0, HUQ010_5.0.
- **D_solo_numericas (10):** solo las 10 numéricas, como control.

Excluimos `SDDSRVYR` y `RIDSTATR` porque son variables de diseño de la encuesta, no características de la persona. Quitar la referencia evita contar dos veces la misma categoría en la distancia euclidiana.

## 5. Barrido de k

Corremos K-means con `n_init=10`, `random_state=42` y silueta sobre 2 000 filas.

```
        conjunto  k  inercia  silueta  tiempo_s  cluster_mas_chico  cluster_mas_grande
          A_todo  2 564841.1   0.1766      0.62              17766               30944
          A_todo  3 461419.9   0.1930      0.35               9174               23247
          A_todo  4 433771.0   0.1596      0.59               3435               18232
          A_todo  5 407908.5   0.1229      1.17               3292               16699
          A_todo  6 391622.1   0.1200      1.08               2613               16013
          A_todo  7 379510.3   0.1028      1.28               2184               11296
          A_todo  8 368387.3   0.1029      1.54               1499                9882
          A_todo  9 360096.0   0.1022      1.51               1055                9861
          A_todo 10 352925.4   0.1027      1.71                967                9398
  B_sin_tecnicas  2 522495.0   0.1899      0.27              17776               30934
  B_sin_tecnicas  3 419117.1   0.2089      0.31               9142               23280
  B_sin_tecnicas  4 391499.5   0.1742      0.51               3442               18237
  B_sin_tecnicas  5 365723.4   0.1363      0.75               3330               16687
  B_sin_tecnicas  6 349470.5   0.1340      1.15               2588               16071
  B_sin_tecnicas  7 337424.0   0.1155      1.02               2179               11438
  B_sin_tecnicas  8 326328.2   0.1160      1.09               1515               10005
  B_sin_tecnicas  9 318051.7   0.1150      1.41               1042               10009
  B_sin_tecnicas 10 310894.5   0.1160      1.56                994                9529
   C_recomendado  2 497729.1   0.1979      0.24              17757               30953
   C_recomendado  3 394926.4   0.2182      0.30               9130               23304
   C_recomendado  4 367448.2   0.1532      0.53               8027               20989
   C_recomendado  5 341749.5   0.1451      0.85               3090               16783
   C_recomendado  6 325659.7   0.1426      1.00               2552               16109
   C_recomendado  7 313769.0   0.1216      1.07               2181               11511
   C_recomendado  8 302852.9   0.1227      1.27               1517               10272
   C_recomendado  9 294591.3   0.1225      1.23               1057               10251
   C_recomendado 10 287443.2   0.1231      1.72                917                9718
D_solo_numericas  2 358619.6   0.2857      0.22              12850               35860
D_solo_numericas  3 271253.5   0.2673      0.21               9558               26033
D_solo_numericas  4 243004.4   0.2278      0.41               3263               20936
D_solo_numericas  5 219494.5   0.1999      0.40               2718               14728
D_solo_numericas  6 205102.4   0.1975      0.60               2499               13083
D_solo_numericas  7 194353.4   0.1885      0.64               1661               11927
D_solo_numericas  8 184272.8   0.1864      0.87               1406               10271
D_solo_numericas  9 176291.5   0.1849      1.11                985                9586
D_solo_numericas 10 168635.8   0.1716      0.94               1112                8484
```

El mejor resultado estable es **k=3** en A, B y C. D (solo numéricas) prefiere k=2. La silueta es baja (≈0,22 en C), así que los grupos son perfiles, no cajas perfectamente separadas. Lo decimos así para no exagerar el resultado.

## 6. Estabilidad y consumo de memoria

```
 tamano_muestra  silueta
           2000   0.2182
           5000   0.2212
          10000   0.2213
```

Pico de memoria Python medido: **61.9 MB**. Al pasar de 2 000 a 10 000 filas en la silueta el valor casi no cambia, así que la muestra es suficiente.

## 7. Perfil del agrupamiento propuesto (C, k=3)

```
 cluster     n  prevalencia  edad_z  cintura_z  proporcion_menores_proxy  proporcion_hombres
       0  9130       0.4807  0.0861     0.3138                    0.2789              0.7125
       1 23304       0.6371  0.6759     0.5262                    0.0689              0.4245
       2 16276       0.0484 -1.0161    -0.9294                    0.9922              0.4739
```

No usamos la etiqueta para entrenar, aun así la prevalencia cambia mucho entre grupos (de 0,048 a 0,637). Eso confirma que los grupos capturan perfiles reales.

## 8. Recomendación

- Usar el conjunto **C_recomendado** (30 columnas).
- Fijar **k=3**, `random_state=42`, `n_init=10`.
- Reportar la silueta baja con honestidad.
- Usar `y_nhanes.csv` solo para perfilar, nunca para entrenar.
- No necesitamos GPU ni más RAM: el pico medido fue de pocas decenas de MB.
