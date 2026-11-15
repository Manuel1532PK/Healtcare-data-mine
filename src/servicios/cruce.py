import pandas as pd

from utilidades.constantes import COLUMNAS_DRUGS


class NormalizadorDrugs:
    """Normaliza columnas de texto del catalogo de farmacos."""

    COLUMNAS_TEXTO = [
        "PROPRIETARYNAME", "NONPROPRIETARYNAME", "SUBSTANCENAME",
        "PHARM_CLASSES", "DOSAGEFORMNAME", "ROUTENAME",
        "MARKETINGCATEGORYNAME", "PRODUCTTYPENAME",
    ]

    def normalizar(self, df):
        for col in self.COLUMNAS_TEXTO:
            if col in df.columns:
                df[col] = df[col].astype("string").str.strip()
        return df


class ResumenDrugs:
    """Reporta cobertura del catalogo Drugs_product (referencia para cruce)."""

    def __init__(self, dfDrugs):
        self.dfDrugs = dfDrugs.copy()

    def resumen(self):
        out = []
        out.append(("Filas", len(self.dfDrugs)))
        out.append(("Columnas", len(self.dfDrugs.columns)))
        out.append(("Duplicados", int(self.dfDrugs.duplicated().sum())))
        out.append(("Nulos totales", int(self.dfDrugs.isna().sum().sum())))
        if "PHARM_CLASSES" in self.dfDrugs.columns:
            out.append(("Clases terapeuticas unicas",
                        self.dfDrugs["PHARM_CLASSES"].nunique(dropna=True)))
        return pd.DataFrame(out, columns=["Indicador", "Valor"])