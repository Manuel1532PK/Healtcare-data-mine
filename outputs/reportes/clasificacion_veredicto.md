# Veredicto · Clasificación NB y KNN

**Datos:** versión del repositorio (`origin/main`). `X_nhanes.csv` 48 710 × 42,
`y_nhanes.csv` con prevalencia 41,1 %. Hicimos un split estratificado 75/25 con `random_state=42`.

## Decisión

Usamos **los dos en el tablero, pero recomendamos uno solo para operar**:

- **Modelo principal: KNN con k=51, pesos uniformes.**
  Accuracy test 0,825 · F1 0,792 · recall 0,782.
- **Línea base permanente: GaussianNB.**
  Accuracy test 0,762 · F1 0,754 · recall 0,889 · fit ~0,02 s.

## Por qué no uno solo de entrada

Al comparar necesitamos la misma partición y varias métricas. Con solo accuracy,
KNN parece ganar siempre; con F1 y recall vemos el matiz: NB detecta más positivos
(0,889 vs 0,782) pero genera muchos más falsos positivos (2 346 vs 1 208 en k=5).

## Exploración de k

| configuración | accuracy train | accuracy test | F1 test |
|---|---:|---:|---:|
| k=1 | 1,000 | 0,757 | 0,699 |
| k=5 | 0,860 | 0,799 | 0,755 |
| k=11 | 0,843 | 0,813 | 0,773 |
| k=21 | 0,837 | 0,818 | 0,782 |
| k=51 | 0,830 | 0,825 | 0,792 |
| k=51 `weights="distance"` | 1,000 | 0,826 | 0,793 |

El 1,000 en train con `weights="distance"` es un artefacto (cada punto se tiene a
sí mismo a distancia 0), no una ventaja real. Preferimos k=51 uniforme por
estabilidad y claridad.

## Limitaciones

La etiqueta del repositorio es `diabetes OR obesidad OR colesterol alto` e incluye
menores; no es diabetes sola. Las probabilidades de NB están mal calibradas.
KNN escala mal si aplicamos `StandardScaler` a las dummies raras.
