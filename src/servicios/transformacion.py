import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, KBinsDiscretizer
from sklearn.decomposition import PCA

from utilidades.constantes import COLUMNAS_CATEGORICAS


class DerivadorEtiqueta:
    """Deriva Disease_Indicator (target) desde DIQ010, BMXBMI y LBXTC."""

    def __init__(self, colDiabetes="DIQ010", colBmi="BMXBMI", colColesterol="LBXTC",
                 umbralBmi=30.0, umbralColesterol=200.0):
        self.colDiabetes = colDiabetes
        self.colBmi = colBmi
        self.colColesterol = colColesterol
        self.umbralBmi = umbralBmi
        self.umbralColesterol = umbralColesterol

    def derivar(self, df):
        df = df.copy()
        diabetes = (df[self.colDiabetes] == 1) if self.colDiabetes in df.columns else pd.Series(False, index=df.index)
        obesidad = (df[self.colBmi] >= self.umbralBmi) if self.colBmi in df.columns else pd.Series(False, index=df.index)
        colAlto = (df[self.colColesterol] >= self.umbralColesterol) if self.colColesterol in df.columns else pd.Series(False, index=df.index)
        df["Disease_Indicator"] = (diabetes | obesidad | colAlto).astype(int)
        print("Disease_Indicator:")
        print(df["Disease_Indicator"].value_counts().to_string())
        return df


class SelectorVariables:
    """Selecciona predictores X y excluye id, target y flags."""

    def __init__(self, columnasNumericas=None, columnasCategoricas=None):
        self.columnasNumericas = columnasNumericas
        self.columnasCategoricas = columnasCategoricas or [c for c in COLUMNAS_CATEGORICAS]

    def seleccionar(self, df):
        excluir = {"SEQN", "Disease_Indicator", "OUTLIER_IQR", "DIQ010", "DIQ160", "DIQ170"}
        num = [c for c in (self.columnasNumericas or []) if c in df.columns and c not in excluir]
        cat = [c for c in self.columnasCategoricas if c in df.columns and c not in excluir]
        print("Numericas seleccionadas:", len(num))
        print("Categoricas seleccionadas:", len(cat))
        return num, cat


class CodificadorOneHot:
    """One-hot para variables nominales (dtype=int)."""

    def __init__(self, columnas):
        self.columnas = columnas

    def codificar(self, df):
        if not self.columnas:
            return df, []
        dummies = pd.get_dummies(df[self.columnas].astype("category"), prefix=self.columnas, dtype=int)
        print("Dummies generadas:", list(dummies.columns))
        return dummies


class DiscretizadorEdad:
    """Discretiza RIDAGEYR en segmentos de negocio por cuantiles."""

    def __init__(self, columna="RIDAGEYR", nBins=4):
        self.columna = columna
        self.nBins = nBins
        self.discretizador = KBinsDiscretizer(n_bins=nBins, encode="ordinal", strategy="quantile")

    def discretizar(self, df):
        if self.columna not in df.columns:
            return None
        bins = self.discretizador.fit_transform(df[[self.columna]]).ravel()
        bordes = self.discretizador.bin_edges_[0].round(0)
        print("Bordes de edad:", [float(x) for x in bordes])
        return bins, bordes


class Escalador:
    """StandardScaler por defecto para las numericas."""

    def __init__(self):
        self.scaler = StandardScaler()
        self.columnas = None

    def ajustarTransformar(self, df, columnas):
        self.columnas = columnas
        X = df[columnas].copy()
        Xesc = self.scaler.fit_transform(X)
        Xesc = pd.DataFrame(Xesc, columns=columnas, index=df.index)
        print("Medias tras escalar (aprox 0):", np.round(Xesc.mean().values, 3).tolist())
        print("Desv. tras escalar (aprox 1):", np.round(Xesc.std().values, 3).tolist())
        return Xesc

    def getScaler(self):
        return self.scaler


class AnalizadorPCA:
    """PCA sobre numericas escaladas; reporta varianza explicada acumulada."""

    def __init__(self):
        self.pca = PCA()

    def analizar(self, Xesc):
        comps = self.pca.fit_transform(Xesc)
        acum = self.pca.explained_variance_ratio_.cumsum()
        print("Varianza acumulada:", np.round(acum, 3).tolist())
        para80 = int((acum < 0.80).sum()) + 1
        para90 = int((acum < 0.90).sum()) + 1
        print("Componentes para >=80%:", para80, "| para >=90%:", para90, "de", len(acum))
        return acum, para80, para90

    def graficar(self, ruta=None):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        var = self.pca.explained_variance_ratio_
        acum = var.cumsum()
        fig, ax1 = plt.subplots(figsize=(8, 5))
        ax1.bar(range(1, len(var) + 1), var, alpha=0.7, label="Varianza por componente")
        ax1.set_xlabel("Componente principal")
        ax1.set_ylabel("Varianza explicada")
        ax2 = ax1.twinx()
        ax2.plot(range(1, len(var) + 1), acum, color="red", marker="o", label="Varianza acumulada")
        ax2.set_ylabel("Varianza acumulada")
        ax2.axhline(0.80, color="gray", linestyle="--", linewidth=0.8)
        ax2.axhline(0.90, color="gray", linestyle=":", linewidth=0.8)
        ax1.set_title("PCA - Scree plot (varianza explicada)")
        fig.tight_layout()
        if ruta is not None:
            fig.savefig(ruta, dpi=100, bbox_inches="tight")
            print("Figura guardada:", ruta)
        if matplotlib.get_backend().lower() != "agg":
            plt.show()
        return fig


class ConstructorMatriz:
    """Concatena numericas escaladas + dummies; y aparte."""

    def __init__(self):
        pass

    def construir(self, Xnum, Xcat, y=None):
        if Xcat is not None and len(Xcat.columns) > 0:
            Xfinal = pd.concat([Xnum, Xcat], axis=1)
        else:
            Xfinal = Xnum.copy()
        print("Forma X_final:", Xfinal.shape)
        if y is not None:
            print("Forma y:", y.shape)
        return Xfinal