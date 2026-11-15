import pandas as pd


class Diagnosticador:
    def __init__(self, columnasNumericas=None):
        self.columnasNumericas = columnasNumericas

    def diagnosticar(self, df, etiqueta):
        print(f"=== {etiqueta} ===")
        print("Filas:", len(df))
        print("Columnas:", len(df.columns))
        print("Duplicados:", int(df.duplicated().sum()))
        print("Nulos totales:", int(df.isna().sum().sum()))
        if self.columnasNumericas:
            cols = [c for c in self.columnasNumericas if c in df.columns]
            if cols:
                print(df[cols].describe().round(2).to_string())


class AnalizadorOutliers:
    """Regla IQR (k=1.5) en modo flag: marca filas, no elimina pacientes."""

    def __init__(self, columnasNumericas, k=1.5):
        self.columnasNumericas = columnasNumericas
        self.k = k

    def revisarIQR(self, df):
        limites = {}
        for col in self.columnasNumericas:
            if col not in df.columns:
                continue
            serie = df[col].dropna()
            if serie.empty:
                continue
            q1, q3 = serie.quantile([0.25, 0.75])
            iqr = q3 - q1
            if iqr == 0 or pd.isna(iqr):
                print(f"{col}: IQR nulo -> omitido")
                continue
            li = q1 - self.k * iqr
            ls = q3 + self.k * iqr
            fuera = int(((df[col] < li) | (df[col] > ls)).sum())
            limites[col] = (float(li), float(ls))
            print(f"{col}: limites [{li:.2f}, {ls:.2f}], fuera de rango: {fuera}")
        return limites

    def marcar(self, df, limites):
        mask = pd.Series(False, index=df.index)
        colsValidas = 0
        for col, (li, ls) in limites.items():
            colsValidas += 1
            mask = mask | ((df[col] < li) | (df[col] > ls))
        # una fila se marca si supera en al menos 1 columna (NHANES: flag por cualquier columna)
        df = df.copy()
        df["OUTLIER_IQR"] = mask
        print("Columnas validas para IQR:", colsValidas)
        print("Filas marcadas como outlier:", int(mask.sum()), f"({mask.mean()*100:.1f} %)")
        return df


class Validador:
    def __init__(self):
        pass

    def validar(self, df, columnasNumericas=None):
        print("Duplicados:", int(df.duplicated().sum()))
        print("Nulos totales:", int(df.isna().sum().sum()))
        if "OUTLIER_IQR" in df.columns:
            print("Filas marcadas IQR:", int(df["OUTLIER_IQR"].sum()))
        if columnasNumericas:
            print(df[columnasNumericas].describe().round(2).to_string())