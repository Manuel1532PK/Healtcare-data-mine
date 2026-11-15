import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

from repositorios.cargador import CargadorDataset
from servicios.transformacion import (
    DerivadorEtiqueta, SelectorVariables, CodificadorOneHot,
    DiscretizadorEdad, Escalador, AnalizadorPCA, ConstructorMatriz,
)
from utilidades.constantes import (
    ARCHIVO_NHANES_MASTER_CSV, CARPETA_OUTPUTS,
    COLUMNAS_CATEGORICAS,
)

CARPETA_TRANSFORMED = CARPETA_OUTPUTS / "transformed"
CARPETA_TRANSFORMED.mkdir(parents=True, exist_ok=True)
ARCHIVO_X = CARPETA_TRANSFORMED / "X_nhanes.csv"
ARCHIVO_Y = CARPETA_TRANSFORMED / "y_nhanes.csv"
ARCHIVO_DECISION = CARPETA_TRANSFORMED / "decision_escalador.csv"
ARCHIVO_VARIANZA = CARPETA_TRANSFORMED / "varianza_pca.csv"


class PipelineTransformacion:
    def ejecutar(self):
        print("=== Cargando maestro limpio ===")
        df = pd.read_csv(ARCHIVO_NHANES_MASTER_CSV)
        print("Forma:", df.shape)

        # 1. Derivar etiqueta objetivo
        print("\n=== Derivando Disease_Indicator ===")
        derivador = DerivadorEtiqueta()
        df = derivador.derivar(df)

        # 2. Seleccionar variables
        print("\n=== Seleccionando variables ===")
        numericasPredictoras = [
            "RIDAGEYR", "BMXWT", "BMXHT", "BMXBMI", "BMXWAIST",
            "LBXGLU", "LBXTC", "LBDLDL", "LBXTR",
            "DR1TKCAL", "DR1TSUGR", "DR1TPROT", "DR1TCARB", "DR1TFIBE", "DR1TTFAT",
        ]
        selector = SelectorVariables(numericasPredictoras, COLUMNAS_CATEGORICAS)
        numCols, catCols = selector.seleccionar(df)

        # 3. Discretizar edad (reporte)
        print("\n=== Discretizando edad (cuantiles) ===")
        disc = DiscretizadorEdad("RIDAGEYR", nBins=4)
        bins, bordes = disc.discretizar(df)

        # 4. Codificar categoricas (one-hot)
        print("\n=== Codificando categoricas (one-hot) ===")
        codificador = CodificadorOneHot(catCols)
        dummies = codificador.codificar(df)

        # 5. Escalar numericas (StandardScaler por defecto)
        print("\n=== Escalando numericas (StandardScaler) ===")
        escalador = Escalador()
        Xnum = escalador.ajustarTransformar(df, numCols)

        # 6. PCA (diagnostico de redundancia)
        print("\n=== PCA sobre numericas escaladas ===")
        pca = AnalizadorPCA()
        acum, para80, para90 = pca.analizar(Xnum)
        CARPETA_FIGURAS = CARPETA_OUTPUTS / "figuras"
        CARPETA_FIGURAS.mkdir(parents=True, exist_ok=True)
        pca.graficar(CARPETA_FIGURAS / "pca_scree_plot.png")

        # 7. Construir matriz final
        print("\n=== Construyendo matriz final ===")
        y = df["Disease_Indicator"]
        constructor = ConstructorMatriz()
        Xfinal = constructor.construir(Xnum, dummies, y)

        # 8. Guardar entregables
        CARPETA_TRANSFORMED.mkdir(parents=True, exist_ok=True)
        Xfinal.to_csv(ARCHIVO_X, index=False)
        y.to_frame(name="Disease_Indicator").to_csv(ARCHIVO_Y, index=False)
        print("\nGuardado:", ARCHIVO_X)
        print("Guardado:", ARCHIVO_Y)

        # 9. Tabla de decision de escalador
        decision = pd.DataFrame([
            {"variable": c, "scaler": "StandardScaler", "justificacion": "caso general (sin outliers graves tras limpieza)"}
            for c in numCols
        ])
        # labs con outliers reales -> RobustScaler opcional documentado
        labs = {"LBXGLU", "LBXTC", "LBDLDL", "LBXTR", "DR1TKCAL", "DR1TSUGR", "DR1TPROT", "DR1TCARB", "DR1TFIBE", "DR1TTFAT"}
        for i, row in decision.iterrows():
            if row["variable"] in labs:
                decision.loc[i, "justificacion"] = "StandardScaler por defecto; RobustScaler opcional si se conservan outliers reales"
        decision.to_csv(ARCHIVO_DECISION, index=False)
        print("Guardado:", ARCHIVO_DECISION)

        # 10. Varianza PCA
        varianza = pd.DataFrame({
            "componente": [f"PC{i+1}" for i in range(len(acum))],
            "varianza_acumulada": acum,
        })
        varianza.to_csv(ARCHIVO_VARIANZA, index=False)
        print("Guardado:", ARCHIVO_VARIANZA)

        print("\nResumen:")
        print("  X_final:", Xfinal.shape)
        print("  y:", y.shape)
        print("  Componentes para >=80%:", para80, "| >=90%:", para90)

        return Xfinal, y


if __name__ == "__main__":
    PipelineTransformacion().ejecutar()