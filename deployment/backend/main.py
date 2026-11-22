"""API de solo lectura para el despliegue interactivo del proyecto NHANES.

Modo local (MODO_LOCAL=1): lee los CSV del repositorio y los artefactos de deployment/azure/artefactos.
Modo nube (MODO_LOCAL=0): descarga los mismos archivos desde Azure Blob Storage.

No escribe nada. No modifica los datos de entrada.
"""

from __future__ import annotations

import io
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from scipy.cluster.hierarchy import fcluster
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RAIZ = Path(__file__).resolve().parents[2]
ARTEFACTOS = RAIZ / "deployment" / "azure" / "artefactos"
TRANSFORMADOS = RAIZ / "outputs" / "transformed"

MODO_LOCAL = os.getenv("MODO_LOCAL", "1") == "1"
CONTENEDOR = os.getenv("AZURE_CONTAINER", "nhanes")
ORIGENES = [o.strip() for o in os.getenv("FRONTEND_URL", "*").split(",") if o.strip()]

app = FastAPI(title="NHANES · API interactiva", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

COLUMNAS_EJEMPLO = [
    "RIDAGEYR", "BMXWAIST", "DR1TKCAL", "DMDEDUC2_0.0", "RIAGENDR_1.0"
]


class Entrada(BaseModel):
    edad: float = 0.0
    cintura: float = 0.0
    calorias: float = 0.0
    sexo: int = 1
    k: int = 51


def _contenedor_blob():
    if MODO_LOCAL:
        return None
    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError as exc:
        raise HTTPException(503, "Instalamos azure-storage-blob en requirements.txt") from exc
    cadena = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not cadena:
        raise HTTPException(503, "Falta AZURE_STORAGE_CONNECTION_STRING")
    servicio = BlobServiceClient.from_connection_string(cadena)
    return servicio.get_container_client(CONTENEDOR)


def _ruta_local(nombre: str) -> Path:
    candidata = ARTEFACTOS / nombre
    if candidata.exists():
        return candidata
    if nombre.startswith("datos/"):
        alterna = TRANSFORMADOS / Path(nombre).name
        if alterna.exists():
            return alterna
    raise HTTPException(404, f"No encontramos el archivo {nombre}")


@lru_cache(maxsize=None)
def leer_bytes(nombre: str) -> bytes:
    if MODO_LOCAL:
        return _ruta_local(nombre).read_bytes()
    blob = _contenedor_blob()
    try:
        return blob.download_blob(nombre).readall()
    except Exception as exc:
        raise HTTPException(404, f"No encontramos {nombre} en Azure: {exc}") from exc


def leer_csv(nombre: str) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(leer_bytes(nombre)))


def leer_json(nombre: str) -> dict:
    return json.loads(leer_bytes(nombre).decode("utf-8"))


def leer_joblib(nombre: str):
    return joblib.load(io.BytesIO(leer_bytes(nombre)))


@lru_cache(maxsize=None)
def metadata() -> dict:
    return leer_json("modelos/columnas.json")


@lru_cache(maxsize=None)
def datos_x() -> pd.DataFrame:
    return leer_csv("datos/X_nhanes.csv")


@lru_cache(maxsize=None)
def datos_y() -> pd.Series:
    return leer_csv("datos/y_nhanes.csv")["Disease_Indicator"]


@lru_cache(maxsize=None)
def etiquetas() -> pd.DataFrame:
    return leer_csv("reportes/clustering_etiquetas.csv")


@lru_cache(maxsize=None)
def perfil() -> pd.DataFrame:
    return leer_csv("reportes/clustering_perfil_final.csv")


@lru_cache(maxsize=None)
def comparacion() -> dict:
    return leer_csv("reportes/clustering_comparacion_metodos.csv").iloc[0].to_dict()


@lru_cache(maxsize=None)
def barrido() -> pd.DataFrame:
    return leer_csv("reportes/clasificacion_barrido_k.csv")


@lru_cache(maxsize=None)
def metricas() -> pd.DataFrame:
    return leer_csv("reportes/clasificacion_metricas_modelos.csv")


@lru_cache(maxsize=None)
def matrices() -> pd.DataFrame:
    return leer_csv("reportes/clasificacion_matrices_confusion.csv")


@lru_cache(maxsize=None)
def detalle() -> pd.DataFrame:
    return leer_csv("reportes/clasificacion_detalle_k.csv")


@lru_cache(maxsize=None)
def particion():
    return train_test_split(
        datos_x(), datos_y(), test_size=0.25, random_state=42, stratify=datos_y()
    )


@lru_cache(maxsize=None)
def modelo_knn_k(k: int):
    X_train, _, y_train, _ = particion()
    numericas = metadata()["numericas"]
    preparador = ColumnTransformer(
        transformers=[("num", StandardScaler(), numericas)],
        remainder="passthrough",
    )
    return Pipeline([
        ("prep", preparador),
        ("knn", KNeighborsClassifier(n_neighbors=k)),
    ]).fit(X_train, y_train)


@lru_cache(maxsize=None)
def desacuerdos_k(k: int) -> pd.DataFrame:
    _, X_test, _, y_test = particion()
    _, nb, _, _ = modelos()
    pred_nb = nb.predict(X_test)
    pred_knn = modelo_knn_k(k).predict(X_test)
    mascara = pred_nb != pred_knn
    tabla = X_test.loc[mascara, COLUMNAS_EJEMPLO].head(100).copy()
    tabla["etiqueta_real"] = y_test.loc[mascara].head(100).values
    tabla["predice_NB"] = pred_nb[mascara][:100]
    tabla["predice_KNN"] = pred_knn[mascara][:100]
    return tabla


@lru_cache(maxsize=None)
def modelos():
    return (
        leer_joblib("modelos/kmeans_model.joblib"),
        leer_joblib("modelos/nb_model.joblib"),
        leer_joblib("modelos/knn51_model.joblib"),
        np.load(io.BytesIO(leer_bytes("modelos/linkage_muestra.npy"))),
    )


def fila_completa(entrada: Entrada, meta: dict) -> pd.DataFrame:
    """Contruye una fila con las 42 columnas, usando las categorías de referencia."""
    fila = {columna: 0.0 for columna in meta["columnas_todas"]}
    referencias = set(meta["referencias"])
    for prefijo, columnas in meta["grupos_one_hot"].items():
        referencia = next((c for c in columnas if c in referencias), None)
        if referencia:
            fila[referencia] = 1.0

    fila["RIDAGEYR"] = float(entrada.edad)
    fila["BMXWAIST"] = float(entrada.cintura)
    fila["DR1TKCAL"] = float(entrada.calorias)
    if "RIAGENDR_1.0" in fila and "RIAGENDR_2.0" in fila:
        sexo = int(entrada.sexo)
        fila["RIAGENDR_1.0"] = float(sexo)
        fila["RIAGENDR_2.0"] = float(1 - sexo)

    return pd.DataFrame([fila])[meta["columnas_todas"]]


@app.get("/health")
def health():
    return {"status": "ok", "modo": "local" if MODO_LOCAL else "azure"}


@app.get("/resumen")
def resumen():
    X = datos_x()
    y = datos_y()
    return {
        "filas": int(X.shape[0]),
        "columnas": int(X.shape[1]),
        "numericas": int(X.select_dtypes(include=["float64"]).shape[1]),
        "dummies": int(X.select_dtypes(include=["int64"]).shape[1]),
        "nulos": int(X.isna().sum().sum()),
        "infinitos": int(np.isinf(X.to_numpy(float)).sum()),
        "duplicados": int(X.duplicated().sum()),
        "constantes": int(sum(X[c].nunique() <= 1 for c in X.columns)),
        "prevalencia": round(float(y.mean()), 4),
    }


@app.get("/metricas")
def metricas_endpoint():
    tabla = metricas().copy()
    tabla["modelo"] = tabla["modelo"].astype(str)
    return {
        "modelos": tabla.round(4).to_dict("records"),
        "barrido": barrido().round(4).to_dict("records"),
        "matrices": matrices().to_dict("records"),
        "detalle": detalle().round(4).to_dict("records"),
    }


@app.get("/clasificacion/desacuerdos")
def desacuerdos_endpoint(
    k: int = Query(51, ge=1, le=51),
    limit: int = Query(20, ge=1, le=100),
):
    return desacuerdos_k(k).head(limit).round(3).to_dict("records")


@app.post("/clasificacion/predecir")
def clasificacion_predecir(entrada: Entrada):
    meta = metadata()
    fila = fila_completa(entrada, meta)
    _, nb, _, _ = modelos()
    knn = modelo_knn_k(entrada.k)
    pred_nb = int(nb.predict(fila)[0])
    pred_knn = int(knn.predict(fila)[0])
    prob_nb = float(nb.predict_proba(fila)[0, 1])
    prob_knn = float(knn.predict_proba(fila)[0, 1])
    return {
        "k": entrada.k,
        "predice_nb": pred_nb,
        "predice_knn": pred_knn,
        "prob_nb": round(prob_nb, 3),
        "prob_knn": round(prob_knn, 3),
        "coinciden": pred_nb == pred_knn,
        "frase": (
            "Ambos modelos coinciden en la respuesta."
            if pred_nb == pred_knn
            else "Los modelos no coinciden: por eso mostramos los dos."
        ),
    }


@app.get("/clustering/perfil")
def perfil_endpoint(grupo: Optional[int] = Query(None)):
    tabla = perfil().copy()
    if grupo is not None:
        tabla = tabla[tabla["cluster"] == grupo]
        if tabla.empty:
            raise HTTPException(404, "Ese grupo no existe")
    return tabla.round(4).to_dict("records")


def _tabla_filtrada(
    grupo: Optional[int],
    etiqueta: Optional[int],
    edad_min: Optional[float],
    edad_max: Optional[float],
    sexo: Optional[int],
) -> pd.DataFrame:
    X = datos_x()
    tabla = X[COLUMNAS_EJEMPLO].copy()
    tabla["grupo"] = etiquetas()["cluster"].values
    tabla["etiqueta"] = datos_y().values
    if grupo is not None:
        tabla = tabla[tabla["grupo"] == grupo]
    if etiqueta is not None:
        tabla = tabla[tabla["etiqueta"] == etiqueta]
    if edad_min is not None:
        tabla = tabla[tabla["RIDAGEYR"] >= edad_min]
    if edad_max is not None:
        tabla = tabla[tabla["RIDAGEYR"] <= edad_max]
    if sexo is not None:
        tabla = tabla[tabla["RIAGENDR_1.0"] == sexo]
    return tabla


@app.get("/clustering/muestra")
def muestra_endpoint(
    grupo: Optional[int] = Query(None),
    etiqueta: Optional[int] = Query(None),
    edad_min: Optional[float] = Query(None),
    edad_max: Optional[float] = Query(None),
    sexo: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=200),
):
    tabla = _tabla_filtrada(grupo, etiqueta, edad_min, edad_max, sexo)
    return tabla.head(limit).round(3).to_dict("records")


@app.get("/datos/conteo")
def conteo_endpoint(
    grupo: Optional[int] = Query(None),
    etiqueta: Optional[int] = Query(None),
    edad_min: Optional[float] = Query(None),
    edad_max: Optional[float] = Query(None),
    sexo: Optional[int] = Query(None),
):
    tabla = _tabla_filtrada(grupo, etiqueta, edad_min, edad_max, sexo)
    return {
        "personas": int(len(tabla)),
        "prevalencia": round(float(tabla["etiqueta"].mean()), 4) if len(tabla) else 0.0,
        "por_grupo": {str(k): int(v) for k, v in tabla["grupo"].value_counts().sort_index().items()},
    }


@app.post("/clustering/predecir")
def clustering_predecir(entrada: Entrada):
    meta = metadata()
    fila = fila_completa(entrada, meta)[meta["columnas_c"]].to_numpy(dtype=float)
    kmeans, _, _, _ = modelos()
    grupo = int(kmeans.predict(fila)[0])
    frases = {
        0: "Se parece al grupo intermedio: prevalencia cercana al promedio.",
        1: "Se parece al grupo de adultos con mayor prevalencia.",
        2: "Se parece al grupo de personas jóvenes, con prevalencia muy baja.",
    }
    return {"grupo": grupo, "frase": frases[grupo], "columnas_usadas": len(meta["columnas_c"])}


@app.get("/clustering/comparacion")
def comparacion_endpoint():
    return comparacion()


@app.get("/clustering/corte")
def corte_endpoint(altura: float = Query(100.0)):
    _, _, _, enlaces = modelos()
    asignaciones = fcluster(enlaces, t=float(altura), criterion="distance")
    conteo = pd.Series(asignaciones).value_counts().sort_index()
    return {
        "altura": round(float(altura), 2),
        "grupos": int(conteo.size),
        "tamanos": {str(k): int(v) for k, v in conteo.items()},
        "nota": "Calculado sobre la muestra de 5 000 personas.",
    }


@app.get("/figura/dendrograma")
def figura_dendrograma():
    return Response(
        content=leer_bytes("figuras/dendrograma_muestra.png"),
        media_type="image/png",
    )


@app.get("/datos/descarga")
def descarga(
    grupo: Optional[int] = Query(None),
    etiqueta: Optional[int] = Query(None),
    edad_min: Optional[float] = Query(None),
    edad_max: Optional[float] = Query(None),
    sexo: Optional[int] = Query(None),
):
    tabla = _tabla_filtrada(grupo, etiqueta, edad_min, edad_max, sexo)
    contenido = tabla.to_csv(index=False).encode("utf-8")
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="nhanes_filtrado.csv"'},
    )
