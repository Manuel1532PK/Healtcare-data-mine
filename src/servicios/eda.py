import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from utilidades.constantes import nombre_legible


class AnalizadorDescriptivo:
    """Tendencia central, dispersion, forma y outliers IQR por variable."""

    def __init__(self, columnasNumericas):
        self.columnasNumericas = columnasNumericas

    def resumen(self, df):
        cols = [c for c in self.columnasNumericas if c in df.columns]
        desc = df[cols].describe().T
        desc["skew"] = df[cols].skew()
        desc["kurtosis"] = df[cols].kurtosis()
        desc.index = [nombre_legible(c) for c in desc.index]
        return desc

    def outliersIQR(self, df, k=1.5):
        filas = []
        for col in self.columnasNumericas:
            if col not in df.columns:
                continue
            s = df[col].dropna()
            if s.empty:
                continue
            q1, q3 = s.quantile([0.25, 0.75])
            iqr = q3 - q1
            if iqr == 0 or pd.isna(iqr):
                filas.append({"variable": nombre_legible(col), "Q1": q1, "Q3": q3, "IQR": iqr, "outliers": 0, "nota": "IQR nulo"})
                continue
            li, ls = q1 - k * iqr, q3 + k * iqr
            fuera = int(((df[col] < li) | (df[col] > ls)).sum())
            filas.append({"variable": nombre_legible(col), "Q1": round(float(q1), 2), "Q3": round(float(q3), 2),
                          "IQR": round(float(iqr), 2), "lim_inf": round(float(li), 2),
                          "lim_sup": round(float(ls), 2), "outliers": fuera, "nota": ""})
        return pd.DataFrame(filas)


class Visualizador:
    """Galeria minima de matplotlib: hist, box, barras, scatter, heatmap, matriz dispersion."""

    def __init__(self, carpetaFiguras):
        self.carpeta = carpetaFiguras

    def _guardar(self, fig, nombre):
        ruta = self.carpeta / nombre
        fig.tight_layout()
        fig.savefig(ruta, dpi=100, bbox_inches="tight")
        plt.close(fig)
        print("Figura guardada:", ruta)
        return ruta

    def histograma(self, df, columna, bins=30):
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(df[columna].dropna(), bins=bins, color="#2563eb", edgecolor="white", alpha=0.85)
        media = df[columna].mean()
        mediana = df[columna].median()
        ax.axvline(media, color="red", linestyle="--", linewidth=1.2, label=f"Media {media:,.0f}")
        ax.axvline(mediana, color="green", linestyle=":", linewidth=1.2, label=f"Mediana {mediana:,.0f}")
        ax.set_title(f"Histograma de {nombre_legible(columna)}")
        ax.set_xlabel(nombre_legible(columna))
        ax.set_ylabel("Frecuencia")
        ax.legend(fontsize=8)
        return self._guardar(fig, f"fig_hist_{columna}.png")

    def boxplot(self, df, columna):
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.boxplot(df[columna].dropna(), vert=True, patch_artist=True,
                   boxprops=dict(facecolor="#93c5fd"))
        ax.set_title(f"Boxplot de {nombre_legible(columna)}")
        ax.set_ylabel(nombre_legible(columna))
        return self._guardar(fig, f"fig_box_{columna}.png")

    def barras(self, df, columna, top=10):
        vc = df[columna].value_counts().head(top)
        fig, ax = plt.subplots(figsize=(7, 4))
        vc.sort_values().plot(kind="barh", ax=ax, color="#2563eb")
        ax.set_title(f"Frecuencia por {nombre_legible(columna)}")
        ax.set_xlabel("Conteo")
        ax.set_ylabel(nombre_legible(columna))
        return self._guardar(fig, f"fig_barras_{columna}.png")

    def scatter(self, df, x, y, hue=None):
        fig, ax = plt.subplots(figsize=(7, 4))
        if hue is not None and hue in df.columns:
            for val in sorted(df[hue].dropna().unique()):
                sub = df[df[hue] == val]
                ax.scatter(sub[x], sub[y], s=12, alpha=0.5, label=str(val))
            ax.legend(fontsize=8, title=hue)
        else:
            ax.scatter(df[x], df[y], s=12, alpha=0.5, color="#2563eb")
        ax.set_title(f"{nombre_legible(x)} vs {nombre_legible(y)}")
        ax.set_xlabel(nombre_legible(x))
        ax.set_ylabel(nombre_legible(y))
        return self._guardar(fig, f"fig_scatter_{x}_{y}.png")

    def heatmap(self, df, columnasNumericas):
        cols = [c for c in columnasNumericas if c in df.columns]
        etiquetas = [nombre_legible(c) for c in cols]
        corr = df[cols].corr(method="pearson")
        fig, ax = plt.subplots(figsize=(11, 9))
        im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
        ax.set_xticks(range(len(cols)))
        ax.set_yticks(range(len(cols)))
        ax.set_xticklabels(etiquetas, rotation=90, fontsize=7)
        ax.set_yticklabels(etiquetas, fontsize=7)
        # anotar cada celda con el valor de r
        for i in range(len(cols)):
            for j in range(len(cols)):
                val = corr.values[i, j]
                color = "white" if abs(val) > 0.5 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=6, color=color)
        fig.colorbar(im, ax=ax, shrink=0.8)
        ax.set_title("Mapa de calor de correlaciones (Pearson)")
        return self._guardar(fig, "fig_heatmap_corr.png")

    def matrizDispersion(self, df, columnas, maxCols=6):
        cols = [c for c in columnas if c in df.columns][:maxCols]
        etiquetas = [nombre_legible(c) for c in cols]
        n = len(cols)
        fig, axes = plt.subplots(n, n, figsize=(2.2 * n, 2.2 * n))
        for i in range(n):
            for j in range(n):
                ax = axes[i, j]
                if i == j:
                    ax.hist(df[cols[i]].dropna(), bins=20, color="#2563eb", alpha=0.7)
                else:
                    ax.scatter(df[cols[j]], df[cols[i]], s=4, alpha=0.3, color="#2563eb")
                if i == n - 1:
                    ax.set_xlabel(etiquetas[j], fontsize=7)
                if j == 0:
                    ax.set_ylabel(etiquetas[i], fontsize=7)
                ax.tick_params(labelsize=6)
        fig.suptitle("Matriz de dispersion", fontsize=12)
        return self._guardar(fig, "fig_matriz_dispersion.png")


class AnalizadorCorrelacion:
    """Pearson + clasificacion de fuerza + pares destacados."""

    ESCALA = [(0.0, 0.1, "sin relacion lineal"), (0.1, 0.3, "debil"),
              (0.3, 0.5, "moderada"), (0.5, 0.7, "fuerte"), (0.7, 1.01, "muy fuerte")]

    def __init__(self, columnasNumericas):
        self.columnasNumericas = columnasNumericas

    def matriz(self, df):
        cols = [c for c in self.columnasNumericas if c in df.columns]
        return df[cols].corr(method="pearson")

    def fuerza(self, r):
        a = abs(r)
        for lo, hi, etiqueta in self.ESCALA:
            if lo <= a < hi:
                return etiqueta
        return "muy fuerte"

    def paresDestacados(self, df, umbral=0.5):
        corr = self.matriz(df)
        filas = []
        cols = list(corr.columns)
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                r = corr.iloc[i, j]
                if pd.isna(r):
                    continue
                if abs(r) >= umbral:
                    filas.append({"var1": cols[i], "var2": cols[j],
                                  "variable_1": nombre_legible(cols[i]),
                                  "variable_2": nombre_legible(cols[j]),
                                  "r": round(float(r), 3), "fuerza": self.fuerza(r)})
        return pd.DataFrame(filas).sort_values("r", key=lambda s: s.abs(), ascending=False)