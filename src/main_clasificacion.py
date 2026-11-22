"""Clasificacion: Naive Bayes y KNN.

Usamos EXCLUSIVAMENTE los archivos versionados en el repositorio:
  outputs/transformed/X_nhanes.csv
  outputs/transformed/y_nhanes.csv

No modificamos ningun dato de entrada. Solo escribimos nuevas tablas en outputs/reportes/.
"""

from pathlib import Path
import time

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_X = RAIZ / "outputs" / "transformed" / "X_nhanes.csv"
ARCHIVO_Y = RAIZ / "outputs" / "transformed" / "y_nhanes.csv"
CARPETA_REPORTES = RAIZ / "outputs" / "reportes"

# Las 10 predictoras numericas del repositorio (main_transformacion.py:47-50).
NUMERICAS = [
    "RIDAGEYR", "BMXWT", "BMXHT", "BMXWAIST",
    "DR1TKCAL", "DR1TSUGR", "DR1TPROT", "DR1TCARB", "DR1TFIBE", "DR1TTFAT",
]


def cargar():
    X = pd.read_csv(ARCHIVO_X)
    y = pd.read_csv(ARCHIVO_Y)["Disease_Indicator"]
    return X, y


def partir(X, y):
    """Aplicamos una partición estratificada, con semilla fija y proporción 75/25."""
    return train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )


def preparador():
    """Escalamos SOLO las numericas; dejamos las 32 dummies en 0/1.

    Las numericas ya vienen escaladas del repositorio; al re-escalarlas dentro
    del Pipeline no las danamos y evitamos que las dummies raras se inflen como
    ocurriria si aplicaramos StandardScaler sobre todo el dataframe.
    """
    return ColumnTransformer(
        transformers=[("num", StandardScaler(), NUMERICAS)],
        remainder="passthrough",
    )


def medir(modelo, X_train, y_train, X_test, y_test):
    t0 = time.perf_counter()
    modelo.fit(X_train, y_train)
    tiempo = time.perf_counter() - t0
    filas = {}

    for nombre, Xm, ym in (("train", X_train, y_train), ("test", X_test, y_test)):
        pred = modelo.predict(Xm)
        prob = modelo.predict_proba(Xm)[:, 1]
        filas[f"accuracy_{nombre}"] = accuracy_score(ym, pred)
        filas[f"precision_{nombre}"] = precision_score(ym, pred, zero_division=0)
        filas[f"recall_{nombre}"] = recall_score(ym, pred, zero_division=0)
        filas[f"f1_{nombre}"] = f1_score(ym, pred, zero_division=0)
        filas[f"roc_auc_{nombre}"] = roc_auc_score(ym, prob)

    filas["tiempo_fit_s"] = tiempo
    return filas, modelo


def ejecutar():
    X, y = cargar()
    X_train, X_test, y_train, y_test = partir(X, y)

    print("X repositorio:", X.shape, "| y:", y.shape)
    print("Train:", X_train.shape, "| Test:", X_test.shape)
    print("Prevalencia train:", round(float(y_train.mean()), 4),
          "| test:", round(float(y_test.mean()), 4))

    modelos = {
        "GaussianNB": GaussianNB(),
        "KNN k=5": Pipeline([
            ("prep", preparador()),
            ("knn", KNeighborsClassifier(n_neighbors=5)),
        ]),
    }

    resultados = []
    ajustados = {}
    for nombre, modelo in modelos.items():
        filas, ajustado = medir(modelo, X_train, y_train, X_test, y_test)
        filas["modelo"] = nombre
        resultados.append(filas)
        ajustados[nombre] = ajustado
        print(f"\n{nombre}: accuracy test={filas['accuracy_test']:.3f} "
              f"F1 test={filas['f1_test']:.3f} "
              f"recall test={filas['recall_test']:.3f}")

    tabla = pd.DataFrame(resultados).set_index("modelo")
    CARPETA_REPORTES.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(CARPETA_REPORTES / "clasificacion_metricas_modelos.csv")

    # Probamos k impar y ademas pesos por distancia.
    barrido = []
    for k in [1, 5, 11, 21, 51]:
        knn = Pipeline([
            ("prep", preparador()),
            ("knn", KNeighborsClassifier(n_neighbors=k)),
        ])
        filas, _ = medir(knn, X_train, y_train, X_test, y_test)
        barrido.append({"k": k, "weights": "uniform",
                        "accuracy_train": filas["accuracy_train"],
                        "accuracy_test": filas["accuracy_test"],
                        "f1_train": filas["f1_train"],
                        "f1_test": filas["f1_test"]})

    mejor_k = int(max(barrido, key=lambda r: r["f1_test"])["k"])
    knn_dist = Pipeline([
        ("prep", preparador()),
        ("knn", KNeighborsClassifier(n_neighbors=mejor_k, weights="distance")),
    ])
    filas, _ = medir(knn_dist, X_train, y_train, X_test, y_test)
    barrido.append({"k": mejor_k, "weights": "distance",
                    "accuracy_train": filas["accuracy_train"],
                    "accuracy_test": filas["accuracy_test"],
                    "f1_train": filas["f1_train"],
                    "f1_test": filas["f1_test"]})

    tabla_k = pd.DataFrame(barrido)
    tabla_k.to_csv(CARPETA_REPORTES / "clasificacion_barrido_k.csv", index=False)

    # Calculamos la matriz de confusion de los dos finalistas.
    matrices = []
    for nombre, modelo in ajustados.items():
        pred = modelo.predict(X_test)
        tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
        matrices.append({"modelo": nombre, "TN": tn, "FP": fp,
                         "FN": fn, "TP": tp})
    pd.DataFrame(matrices).to_csv(
        CARPETA_REPORTES / "clasificacion_matrices_confusion.csv", index=False)

    print("\nBarrido de k:")
    print(tabla_k.to_string(index=False))
    return X, y, X_train, X_test, y_train, y_test, tabla, tabla_k, ajustados


if __name__ == "__main__":
    ejecutar()
