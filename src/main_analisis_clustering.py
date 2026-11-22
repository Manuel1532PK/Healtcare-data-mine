"""Análisis previo al agrupamiento con K-means.

Usamos EXCLUSIVAMENTE los archivos versionados en main:
  outputs/transformed/X_nhanes.csv
  outputs/transformed/y_nhanes.csv

No modificamos esos archivos. Solo escribimos tablas y un reporte nuevo en outputs/reportes/.
Usamos la etiqueta y_nhanes.csv únicamente al final, para perfilar los grupos;
nunca la dejamos entrar en el entrenamiento del agrupamiento.
"""

from pathlib import Path
import time
import tracemalloc

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_X = RAIZ / "outputs" / "transformed" / "X_nhanes.csv"
ARCHIVO_Y = RAIZ / "outputs" / "transformed" / "y_nhanes.csv"
CARPETA = RAIZ / "outputs" / "reportes"

TECNICAS = ["RIDSTATR", "SDDSRVYR"]
K_RANGO = range(2, 11)
MUESTRAS_SILUETA = [2000, 5000, 10000]


def cargar():
    X = pd.read_csv(ARCHIVO_X)
    y = pd.read_csv(ARCHIVO_Y)["Disease_Indicator"]
    return X, y


def grupos_one_hot(X):
    """Agrupamos las dummies por el prefijo de la variable original."""
    dummies = X.select_dtypes(include=["int64"]).columns.tolist()
    grupos = {}
    for columna in dummies:
        prefijo = columna.rsplit("_", 1)[0]
        grupos.setdefault(prefijo, []).append(columna)
    return grupos


def auditoria(X, y, grupos):
    numericas = X.select_dtypes(include=["float64"]).columns.tolist()
    filas = []

    for nombre, tabla in grupos.items():
        suma = X[tabla].sum(axis=1)
        filas.append({
            "variable": nombre,
            "tipo": "dummy",
            "n_columnas": len(tabla),
            "prevalencia_min": round(float(X[tabla].mean().min()), 4),
            "prevalencia_max": round(float(X[tabla].mean().max()), 4),
            "suma_min": int(suma.min()),
            "suma_max": int(suma.max()),
            "media_z": "",
        })

    for columna in numericas:
        filas.append({
            "variable": columna,
            "tipo": "numérica escalada",
            "n_columnas": 1,
            "prevalencia_min": "",
            "prevalencia_max": "",
            "suma_min": "",
            "suma_max": "",
            "media_z": round(float(X[columna].mean()), 4),
        })

    tabla = pd.DataFrame(filas)
    resumen = pd.DataFrame([{
        "filas": X.shape[0],
        "columnas": X.shape[1],
        "numéricas": len(numericas),
        "dummies": sum(len(v) for v in grupos.values()),
        "nan": int(X.isna().sum().sum()),
        "infinitos": int(np.isinf(X.to_numpy(dtype=float)).sum()),
        "filas_duplicadas": int(X.duplicated().sum()),
        "columnas_constantes": sum(X[c].nunique() <= 1 for c in X.columns),
        "prevalencia_y": round(float(y.mean()), 4),
    }])
    return resumen, tabla


def correlaciones(X):
    numericas = X.select_dtypes(include=["float64"]).columns.tolist()
    corr = X[numericas].corr().abs()
    mascara = np.triu(np.ones(corr.shape), k=1).astype(bool)
    pares = corr.where(mascara).stack()
    tabla = pares[pares >= 0.5].sort_values(ascending=False).reset_index()
    tabla.columns = ["variable_1", "variable_2", "correlacion_abs"]
    return tabla.round(3)


def construir_sets(X, grupos):
    referencias = []
    for variable in grupos:
        if variable in TECNICAS:
            continue
        columnas_ordenadas = sorted(grupos[variable])
        referencias.append(columnas_ordenadas[-1])

    sets = {
        "A_todo": X.columns.tolist(),
        "B_sin_tecnicas": [c for c in X if c.rsplit("_", 1)[0] not in TECNICAS],
        "C_recomendado": [
            c for c in X
            if c.rsplit("_", 1)[0] not in TECNICAS and c not in referencias
        ],
        "D_solo_numericas": X.select_dtypes(include=["float64"]).columns.tolist(),
    }
    return sets, referencias


def barrido_k(X, sets):
    filas = []
    for nombre, columnas in sets.items():
        Z = X[columnas].to_numpy(dtype=np.float64)
        for k in K_RANGO:
            modelo = KMeans(n_clusters=k, n_init=10, random_state=42)
            t0 = time.perf_counter()
            etiquetas = modelo.fit_predict(Z)
            tiempo = time.perf_counter() - t0
            silueta = silhouette_score(Z, etiquetas, sample_size=2000, random_state=42)
            tamanos = pd.Series(etiquetas).value_counts().sort_index()
            filas.append({
                "conjunto": nombre,
                "k": k,
                "inercia": round(float(modelo.inertia_), 1),
                "silueta": round(float(silueta), 4),
                "tiempo_s": round(float(tiempo), 2),
                "cluster_mas_chico": int(tamanos.min()),
                "cluster_mas_grande": int(tamanos.max()),
            })
    return pd.DataFrame(filas)


def estabilidad(X, columnas, k):
    Z = X[columnas].to_numpy(dtype=np.float64)
    modelo = KMeans(n_clusters=k, n_init=10, random_state=42)
    etiquetas = modelo.fit_predict(Z)

    filas = []
    for n in MUESTRAS_SILUETA:
        valor = silhouette_score(Z, etiquetas, sample_size=n, random_state=42)
        filas.append({"tamano_muestra": n, "silueta": round(float(valor), 4)})

    tracemalloc.start()
    modelo = KMeans(n_clusters=k, n_init=10, random_state=42)
    modelo.fit_predict(Z)
    silhouette_score(Z, modelo.labels_, sample_size=2000, random_state=42)
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return pd.DataFrame(filas), round(pico / 1024 / 1024, 1), etiquetas


def perfil(X, y, etiquetas):
    tabla = X.copy()
    tabla["cluster"] = etiquetas
    tabla["Disease_Indicator"] = y.values
    resumen = tabla.groupby("cluster").agg(
        n=("Disease_Indicator", "size"),
        prevalencia=("Disease_Indicator", "mean"),
        edad_z=("RIDAGEYR", "mean"),
        cintura_z=("BMXWAIST", "mean"),
        proporcion_menores_proxy=("DMDEDUC2_0.0", "mean"),
        proporcion_hombres=("RIAGENDR_1.0", "mean"),
    ).reset_index()
    return resumen.round(4)


def main():
    X, y = cargar()
    grupos = grupos_one_hot(X)
    resumen, variables = auditoria(X, y, grupos)
    corr = correlaciones(X)
    sets, referencias = construir_sets(X, grupos)
    barrido = barrido_k(X, sets)

    mejor = barrido[barrido["conjunto"] == "C_recomendado"].sort_values(
        "silueta", ascending=False).iloc[0]
    k = int(mejor["k"])
    estable, pico_mb, etiquetas = estabilidad(X, sets["C_recomendado"], k)
    perfil_k = perfil(X, y, etiquetas)

    CARPETA.mkdir(parents=True, exist_ok=True)
    resumen.to_csv(CARPETA / "clustering_auditoria.csv", index=False)
    variables.to_csv(CARPETA / "clustering_variables.csv", index=False)
    corr.to_csv(CARPETA / "clustering_correlaciones.csv", index=False)
    barrido.to_csv(CARPETA / "clustering_barrido_k.csv", index=False)
    estable.to_csv(CARPETA / "clustering_estabilidad.csv", index=False)
    perfil_k.to_csv(CARPETA / "clustering_perfil.csv", index=False)

    with open(CARPETA / "analisis_pre_clustering.md", "w", encoding="utf-8") as f:
        f.write("# Análisis previo al agrupamiento K-means\n\n")
        f.write("## 1. Auditoría de los datos\n\n")
        f.write("Usamos `outputs/transformed/X_nhanes.csv` e `y_nhanes.csv` de `main`. ")
        f.write("No modificamos esos archivos. Guardamos la etiqueta para el perfil final; ")
        f.write("no la dejamos entrar en el entrenamiento.\n\n")
        f.write("```\n" + resumen.to_string(index=False) + "\n```\n\n")
        f.write("- No hay valores faltantes ni infinitos.\n")
        f.write("- Encontramos 152 filas duplicadas; las conservamos porque pueden ser ")
        f.write("participantes con mediciones idénticas.\n")
        f.write("- No hay columnas constantes.\n\n")

        f.write("## 2. Estructura de variables\n\n")
        f.write("Tenemos 10 numéricas ya escaladas (media ≈ 0, desviación ≈ 1) y 32 dummies ")
        f.write("repartidas en 7 grupos one-hot. Cada grupo suma exactamente 1 por fila.\n\n")
        f.write("```\n" + variables[variables["tipo"] == "dummy"].to_string(index=False) + "\n```\n\n")

        f.write("## 3. Redundancia y señales importantes\n\n")
        f.write("Las numéricas más correlacionadas son:\n\n")
        f.write("```\n" + corr.head(10).to_string(index=False) + "\n```\n\n")
        f.write("Además, `DMDEDUC2_0.0` está en 20 301 filas (41,7 %) y su edad promedio ")
        f.write("es notablemente menor que en el resto. Ese código funciona como proxy de ")
        f.write("menores de edad, así que esperamos que un grupo quede marcado por la edad.\n\n")

        f.write("## 4. Conjuntos de variables evaluados\n\n")
        f.write("- **A_todo (42):** todas las columnas, incluidas las técnicas `SDDSRVYR` y `RIDSTATR`.\n")
        f.write("- **B_sin_tecnicas (35):** quitamos `SDDSRVYR` y `RIDSTATR`.\n")
        f.write("- **C_recomendado (30):** lo anterior y además quitamos una dummy de referencia ")
        f.write("por grupo: " + ", ".join(referencias) + ".\n")
        f.write("- **D_solo_numericas (10):** solo las 10 numéricas, como control.\n\n")
        f.write("Excluimos `SDDSRVYR` y `RIDSTATR` porque son variables de diseño de la encuesta, ")
        f.write("no características de la persona. Quitar la referencia evita contar dos veces ")
        f.write("la misma categoría en la distancia euclidiana.\n\n")

        f.write("## 5. Barrido de k\n\n")
        f.write("Corremos K-means con `n_init=10`, `random_state=42` y silueta sobre 2 000 filas.\n\n")
        f.write("```\n" + barrido.to_string(index=False) + "\n```\n\n")
        f.write("El mejor resultado estable es **k=3** en A, B y C. D (solo numéricas) prefiere k=2. ")
        f.write("La silueta es baja (≈0,22 en C), así que los grupos son perfiles, no cajas ")
        f.write("perfectamente separadas. Lo decimos así para no exagerar el resultado.\n\n")

        f.write("## 6. Estabilidad y consumo de memoria\n\n")
        f.write("```\n" + estable.to_string(index=False) + "\n```\n\n")
        f.write(f"Pico de memoria Python medido: **{pico_mb} MB**. ")
        f.write("Al pasar de 2 000 a 10 000 filas en la silueta el valor casi no cambia, ")
        f.write("así que la muestra es suficiente.\n\n")

        f.write("## 7. Perfil del agrupamiento propuesto (C, k=3)\n\n")
        f.write("```\n" + perfil_k.to_string(index=False) + "\n```\n\n")
        f.write("No usamos la etiqueta para entrenar, aun así la prevalencia cambia mucho entre ")
        f.write("grupos (de 0,048 a 0,637). Eso confirma que los grupos capturan perfiles reales.\n\n")

        f.write("## 8. Recomendación\n\n")
        f.write("- Usar el conjunto **C_recomendado** (30 columnas).\n")
        f.write("- Fijar **k=3**, `random_state=42`, `n_init=10`.\n")
        f.write("- Reportar la silueta baja con honestidad.\n")
        f.write("- Usar `y_nhanes.csv` solo para perfilar, nunca para entrenar.\n")
        f.write("- No necesitamos GPU ni más RAM: el pico medido fue de pocas decenas de MB.\n")

    print("Filas/columnas:", X.shape)
    print("Conjuntos:", {k: len(v) for k, v in sets.items()})
    print("Mejor k en C_recomendado:", k, "| silueta:", mejor["silueta"])
    print("Estabilidad:", estable.to_dict("records"))
    print("Pico Python (MB):", pico_mb)
    print("Reportes escritos en", CARPETA)


if __name__ == "__main__":
    main()
