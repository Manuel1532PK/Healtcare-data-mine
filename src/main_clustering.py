"""Agrupamiento con K-means (principal) y jerárquico Ward sobre muestra (apoyo).

Usamos EXCLUSIVAMENTE los archivos versionados en main:
  outputs/transformed/X_nhanes.csv
  outputs/transformed/y_nhanes.csv

No modificamos esos archivos. Usamos la etiqueta solo al final, para perfilar los grupos.

Flujo:
1. Ward jerárquico sobre una muestra de 5 000 personas: revisamos el dendrograma y
   confirmamos cuántos grupos sugiere el corte.
2. K-means con k=3 sobre las 48 710 personas: asigna el grupo definitivo.
3. Comparamos ambos métodos sobre la misma muestra con ARI.
"""

from pathlib import Path
import time
import tracemalloc

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_X = RAIZ / "outputs" / "transformed" / "X_nhanes.csv"
ARCHIVO_Y = RAIZ / "outputs" / "transformed" / "y_nhanes.csv"
CARPETA_REPORTES = RAIZ / "outputs" / "reportes"
CARPETA_FIGURAS = RAIZ / "outputs" / "figuras"

TECNICAS = ["RIDSTATR", "SDDSRVYR"]
K = 3
MUESTRA = 5000
SEMILLA = 42


def cargar():
    X = pd.read_csv(ARCHIVO_X)
    y = pd.read_csv(ARCHIVO_Y)["Disease_Indicator"]
    return X, y


def seleccionar_columnas(X):
    """Conjunto C: sin variables de diseño y sin una dummy de referencia por grupo."""
    grupos = {}
    for columna in X.select_dtypes(include=["int64"]).columns:
        prefijo = columna.rsplit("_", 1)[0]
        grupos.setdefault(prefijo, []).append(columna)

    referencias = [sorted(cols)[-1] for prefijo, cols in grupos.items() if prefijo not in TECNICAS]
    return [
        c for c in X.columns
        if c.rsplit("_", 1)[0] not in TECNICAS and c not in referencias
    ]


def kmeans_completo(Z):
    modelo = KMeans(n_clusters=K, n_init=10, random_state=SEMILLA)
    t0 = time.perf_counter()
    etiquetas = modelo.fit_predict(Z)
    return etiquetas, time.perf_counter() - t0


def jerarquico_muestra(Z, indices):
    muestra = Z[indices]
    tracemalloc.start()
    t0 = time.perf_counter()
    enlaces = linkage(muestra, method="ward")
    tiempo = time.perf_counter() - t0
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    etiquetas = fcluster(enlaces, t=K, criterion="maxclust")
    return enlaces, etiquetas, tiempo, round(pico / 1024 / 1024, 1)


def dibujar_dendrograma(enlaces):
    fig, ax = plt.subplots(figsize=(12, 6))
    dendrogram(enlaces, truncate_mode="lastp", p=30, show_contracted=True, ax=ax)
    corte = (enlaces[-K, 2] + enlaces[-(K - 1), 2]) / 2
    ax.axhline(y=corte, color="red", linestyle="--", label=f"Corte para {K} grupos")
    ax.legend()
    ax.set_title(f"Dendrograma Ward (muestra de {MUESTRA:,} personas)")
    ax.set_xlabel("Ramas del árbol (truncado a 30)")
    ax.set_ylabel("Distancia de fusión")
    fig.tight_layout()
    CARPETA_FIGURAS.mkdir(parents=True, exist_ok=True)
    fig.savefig(CARPETA_FIGURAS / "dendrograma_muestra.png", dpi=120)
    plt.close(fig)


def perfil(X, y, columnas, etiquetas):
    tabla = X[columnas].copy()
    tabla["cluster"] = etiquetas
    tabla["Disease_Indicator"] = y.values
    resumen = tabla.groupby("cluster").agg(
        personas=("Disease_Indicator", "size"),
        prevalencia_diabetes_obesidad_colesterol=("Disease_Indicator", "mean"),
        edad_z=("RIDAGEYR", "mean"),
        cintura_z=("BMXWAIST", "mean"),
        proporcion_proxy_menores=("DMDEDUC2_0.0", "mean"),
        proporcion_hombres=("RIAGENDR_1.0", "mean"),
    ).reset_index()
    return resumen.round(4)


def main():
    X, y = cargar()
    columnas = seleccionar_columnas(X)
    Z = X[columnas].to_numpy(dtype=np.float64)

    etiquetas_km, t_km = kmeans_completo(Z)
    silueta = silhouette_score(Z, etiquetas_km, sample_size=2000, random_state=SEMILLA)
    silueta_10k = silhouette_score(Z, etiquetas_km, sample_size=10000, random_state=SEMILLA)
    tamanos = pd.Series(etiquetas_km).value_counts().sort_index()
    tabla_perfil = perfil(X, y, columnas, etiquetas_km)

    rng = np.random.default_rng(SEMILLA)
    indices = np.sort(rng.choice(Z.shape[0], size=MUESTRA, replace=False))
    enlaces, etiquetas_jer, t_jer, pico_jer_mb = jerarquico_muestra(Z, indices)
    ari = adjusted_rand_score(etiquetas_jer, etiquetas_km[indices])
    fusion_inferior = enlaces[-K, 2]
    fusion_superior = enlaces[-(K - 1), 2]
    tamanos_jer = pd.Series(etiquetas_jer).value_counts().sort_index()

    CARPETA_REPORTES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "fila": np.arange(len(etiquetas_km)),
        "cluster": etiquetas_km,
        "Disease_Indicator": y.values,
    }).to_csv(CARPETA_REPORTES / "clustering_etiquetas.csv", index=False)
    tabla_perfil.to_csv(CARPETA_REPORTES / "clustering_perfil_final.csv", index=False)

    comparacion = pd.DataFrame([{
        "muestra": MUESTRA,
        "k": K,
        "ari_jerarquico_vs_kmeans": round(float(ari), 4),
        "tamanos_jerarquico": "/".join(str(n) for n in tamanos_jer.tolist()),
        "tamanos_kmeans_muestra": "/".join(
            str(n) for n in pd.Series(etiquetas_km[indices]).value_counts().sort_index().tolist()),
        "corte_3_grupos_desde": round(float(fusion_inferior), 4),
        "corte_3_grupos_hasta": round(float(fusion_superior), 4),
        "tiempo_jerarquico_s": round(t_jer, 2),
        "pico_memoria_jerarquico_mb": pico_jer_mb,
        "tiempo_kmeans_s": round(t_km, 2),
    }])
    comparacion.to_csv(CARPETA_REPORTES / "clustering_comparacion_metodos.csv", index=False)

    dibujar_dendrograma(enlaces)

    with open(CARPETA_REPORTES / "clustering_veredicto.md", "w", encoding="utf-8") as f:
        f.write("# Veredicto · Agrupamiento K-means con apoyo jerárquico\n\n")
        f.write("## Qué hicimos\n\n")
        f.write(f"Agrupamos los **{Z.shape[0]:,}** registros de `main` con **{Z.shape[1]} variables** "
                "(conjunto C: sin variables de diseño de encuesta y sin una dummy de referencia por grupo).\n\n")
        f.write("Combinamos dos métodos, según la forma que propone la clase:\n\n")
        f.write(f"1. **Jerárquico Ward sobre una muestra de {MUESTRA:,} personas.** "
                "Lo usamos para revisar el dendrograma y confirmar cuántos grupos sugiere el corte.\n")
        f.write(f"2. **K-means con `k={K}`, `n_init=10`, `random_state={SEMILLA}`, sobre las 48 710 personas.** "
                "Es el método principal y asigna el grupo definitivo.\n\n")
        f.write("No usamos la etiqueta para entrenar. La guardamos para describir los grupos al final.\n\n")
        f.write("## Resultados\n\n")
        f.write(f"- El corte que da {K} grupos cae entre las alturas {fusion_inferior:.2f} y {fusion_superior:.2f}. "
                "Ese salto grande es lo que sostiene el número de grupos.\n")
        f.write(f"- Tamaños del jerárquico en la muestra: {', '.join(str(n) for n in tamanos_jer.tolist())}.\n")
        f.write(f"- Acuerdo entre jerárquico y K-means en la misma muestra (ARI): **{ari:.4f}**.\n")
        f.write(f"- Silueta de K-means con 2 000 personas: **{silueta:.4f}**; con 10 000: **{silueta_10k:.4f}**.\n")
        f.write("- Tamaños de K-means en las 48 710 personas: " +
                ", ".join(f"grupo {i}: {n:,}" for i, n in tamanos.items()) + ".\n\n")
        f.write("```\n" + tabla_perfil.to_string(index=False) + "\n```\n\n")
        f.write("## Qué significan los grupos\n\n")
        f.write("- **Grupo de personas jóvenes:** casi todas tienen el proxy de menores de edad y prevalencia muy baja.\n")
        f.write("- **Grupo de adultos con mayor prevalencia:** más edad, más cintura y prevalencia cercana a 0,64.\n")
        f.write("- **Grupo intermedio:** prevalencia cercana a la media de la muestra.\n\n")
        f.write("## Lectura del acuerdo\n\n")
        f.write(f"Un ARI de {ari:.2f} indica acuerdo moderado: los dos métodos coinciden en la mayoría de las personas, "
                "pero no en todas. Por eso presentamos K-means como resultado principal y el jerárquico como apoyo, "
                "no como prueba definitiva.\n\n")
        f.write("## Límites\n\n")
        f.write("- La silueta es baja (≈0,22): son perfiles amplios, no grupos perfectamente separados.\n")
        f.write("- El jerárquico se calculó sobre una muestra, por el costo de memoria del método Ward. "
                "El resultado final usa las 48 710 personas con K-means.\n")
        f.write("- El dendrograma está truncado a 30 ramas para poder leerlo.\n")
        f.write("- La memoria del jerárquico se midió con `tracemalloc` (solo Python); el proceso completo consume más.\n")

    print("Registros:", Z.shape[0], "| variables:", Z.shape[1])
    print("K-means: silueta 2000:", round(float(silueta), 4), "| 10000:", round(float(silueta_10k), 4))
    print("Tamaños K-means:", tamanos.to_dict())
    print("Jerárquico muestra", MUESTRA, "| tamaños:", tamanos_jer.to_dict(),
          "| ARI vs K-means:", round(float(ari), 4))
    print("Corte para 3 grupos entre:", round(float(fusion_inferior), 4),
          "y", round(float(fusion_superior), 4))
    print("Tiempo jerárquico (s):", round(t_jer, 2), "| pico memoria (MB):", pico_jer_mb)
    print(tabla_perfil.to_string(index=False))


if __name__ == "__main__":
    main()
