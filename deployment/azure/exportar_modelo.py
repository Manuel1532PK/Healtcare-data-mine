"""Prepara los artefactos que el backend leerá desde Azure (o en modo local).

Solo LEE los archivos del repositorio. Escribe únicamente en deployment/azure/artefactos/.
No modifica src/, outputs/ ni docs/.
"""

from pathlib import Path
import json
import shutil

import joblib
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RAIZ = Path(__file__).resolve().parents[2]
DESTINO = Path(__file__).resolve().parent / "artefactos"
TECNICAS = ["RIDSTATR", "SDDSRVYR"]
K = 3
MUESTRA = 5000
SEMILLA = 42

PARAMOS_LOG = []


def avisar(texto):
    PARAMOS_LOG.append(texto)
    print(texto)


def main():
    X = pd.read_csv(RAIZ / "outputs/transformed/X_nhanes.csv")
    y = pd.read_csv(RAIZ / "outputs/transformed/y_nhanes.csv")["Disease_Indicator"]
    numericas = X.select_dtypes(include=["float64"]).columns.tolist()
    dummies = X.select_dtypes(include=["int64"]).columns.tolist()

    grupos = {}
    for columna in dummies:
        prefijo = columna.rsplit("_", 1)[0]
        grupos.setdefault(prefijo, []).append(columna)

    referencias = [
        sorted(cols)[-1] for nombre, cols in grupos.items() if nombre not in TECNICAS
    ]
    columnas_c = [
        c for c in X.columns
        if c.rsplit("_", 1)[0] not in TECNICAS and c not in referencias
    ]

    (DESTINO / "modelos").mkdir(parents=True, exist_ok=True)
    (DESTINO / "reportes").mkdir(parents=True, exist_ok=True)
    (DESTINO / "figuras").mkdir(parents=True, exist_ok=True)

    # K-means final, con la misma configuración del resultado entregado.
    Z = X[columnas_c].to_numpy(dtype=np.float64)
    kmeans = KMeans(n_clusters=K, n_init=10, random_state=SEMILLA).fit(Z)
    joblib.dump(kmeans, DESTINO / "modelos/kmeans_model.joblib")

    # Enlaces del jerárquico sobre la muestra: permite cortes interactivos reales.
    rng = np.random.default_rng(SEMILLA)
    indices = np.sort(rng.choice(Z.shape[0], size=MUESTRA, replace=False))
    enlaces = linkage(Z[indices], method="ward")
    np.save(DESTINO / "modelos/linkage_muestra.npy", enlaces)

    # Clasificación: los mismos modelos y la misma partición.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=SEMILLA, stratify=y
    )
    nb = GaussianNB().fit(X_train, y_train)
    preparador = ColumnTransformer(
        transformers=[("num", StandardScaler(), numericas)],
        remainder="passthrough",
    )
    knn = Pipeline([
        ("prep", preparador),
        ("knn", KNeighborsClassifier(n_neighbors=51)),
    ]).fit(X_train, y_train)
    joblib.dump(nb, DESTINO / "modelos/nb_model.joblib")
    joblib.dump(knn, DESTINO / "modelos/knn51_model.joblib")

    # Detalle completo para cada vecindario del barrido. La interfaz necesita
    # números reales para cada opción del selector, no solo accuracy y F1.
    detalle = []
    for valor_k in [1, 5, 11, 21, 51]:
        modelo_k = Pipeline([
            ("prep", preparador),
            ("knn", KNeighborsClassifier(n_neighbors=valor_k)),
        ]).fit(X_train, y_train)
        predicciones = modelo_k.predict(X_test)
        tn, fp, fn, tp = confusion_matrix(y_test, predicciones).ravel()
        detalle.append({
            "k": valor_k,
            "accuracy_train": round(accuracy_score(y_train, modelo_k.predict(X_train)), 4),
            "accuracy_test": round(accuracy_score(y_test, predicciones), 4),
            "precision_test": round(precision_score(y_test, predicciones), 4),
            "recall_test": round(recall_score(y_test, predicciones), 4),
            "f1_test": round(f1_score(y_test, predicciones), 4),
            "TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp),
        })
    pd.DataFrame(detalle).to_csv(
        DESTINO / "reportes/clasificacion_detalle_k.csv", index=False
    )

    # Casos donde los dos modelos no coinciden: ejemplo interactivo.
    pred_nb = nb.predict(X_test)
    pred_knn = knn.predict(X_test)
    desacuerdo = pred_nb != pred_knn
    columnas_ejemplo = [
        "RIDAGEYR", "BMXWAIST", "DR1TKCAL", "DMDEDUC2_0.0", "RIAGENDR_1.0"
    ]
    tabla = X_test.loc[desacuerdo, columnas_ejemplo].head(100).copy()
    tabla["etiqueta_real"] = y_test.loc[desacuerdo].head(100).values
    tabla["predice_NB"] = pred_nb[desacuerdo][:100]
    tabla["predice_KNN51"] = pred_knn[desacuerdo][:100]
    tabla.to_csv(DESTINO / "reportes/desacuerdos.csv", index=False)

    # Copias de los reportes ya calculados. Los originales no se tocan.
    copias = {
        "clasificacion_metricas_modelos.csv": "reportes",
        "clasificacion_barrido_k.csv": "reportes",
        "clasificacion_matrices_confusion.csv": "reportes",
        "clustering_perfil_final.csv": "reportes",
        "clustering_comparacion_metodos.csv": "reportes",
        "clustering_etiquetas.csv": "reportes",
    }
    for nombre, carpeta in copias.items():
        shutil.copy2(RAIZ / "outputs/reportes" / nombre, DESTINO / carpeta / nombre)
    shutil.copy2(
        RAIZ / "outputs/figuras/dendrograma_muestra.png",
        DESTINO / "figuras/dendrograma_muestra.png",
    )

    metadata = {
        "columnas_todas": X.columns.tolist(),
        "columnas_c": columnas_c,
        "numericas": numericas,
        "tecnicas": TECNICAS,
        "referencias": referencias,
        "grupos_one_hot": grupos,
        "k": K,
        "semilla": SEMILLA,
        "muestra_jerarquico": MUESTRA,
    }
    with open(DESTINO / "modelos/columnas.json", "w", encoding="utf-8") as archivo:
        json.dump(metadata, archivo, ensure_ascii=False, indent=2)

    avisar(f"Filas: {len(X)} | columnas: {len(X.columns)} | columnas C: {len(columnas_c)}")
    avisar(f"Desacuerdos guardados: {len(tabla)}")
    avisar(f"Artefactos en: {DESTINO}")


if __name__ == "__main__":
    main()
