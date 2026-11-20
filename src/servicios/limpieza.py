import numpy as np
import pandas as pd

from utilidades.constantes import (
    COLUMNAS_CATEGORICAS, CODIGOS_NO_RESPUESTA_CAT, COLUMNAS_NO_IMPUTAR, EDAD_ADULTO,
)


class TratadorDuplicados:
    def __init__(self, columnaClave="SEQN"):
        self.columnaClave = columnaClave

    def quitar(self, df):
        antes = len(df)
        df = df.drop_duplicates().reset_index(drop=True)
        if self.columnaClave in df.columns:
            df = df.drop_duplicates(subset=[self.columnaClave], keep="first").reset_index(drop=True)
        print("Duplicados eliminados:", antes - len(df))
        return df


class NormalizadorCodigosNhanes:
    """Reemplaza codigos de no respuesta SOLO en columnas categoricas (por columna)."""

    def __init__(self, codigosPorColumna=None):
        self.codigosPorColumna = codigosPorColumna or CODIGOS_NO_RESPUESTA_CAT

    def normalizar(self, df):
        for col, codigos in self.codigosPorColumna.items():
            if col in df.columns:
                df[col] = df[col].replace(codigos, np.nan)
        return df


class NormalizadorMenores:
    """Para menores de edad, DMDEDUC2/DMDMARTL = 'No aplica (menor)' (codigo 0)."""

    def __init__(self, colEdad="RIDAGEYR", columnas=None, edadMenor=EDAD_ADULTO):
        self.colEdad = colEdad
        self.columnas = columnas or ["DMDEDUC2", "DMDMARTL"]
        self.edadMenor = edadMenor

    def normalizar(self, df):
        if self.colEdad not in df.columns:
            return df
        mask = df[self.colEdad] < self.edadMenor
        for col in self.columnas:
            if col in df.columns:
                df.loc[mask, col] = 0
        print("Menores (<%d anos) con educacion/estado civil = 'No aplica': %d" % (self.edadMenor, int(mask.sum())))
        return df


class TypeCleaner:
    """Convierte columnas categoricas a 'category' y asegura numericas."""

    def __init__(self, columnasCategoricas=None, columnasNumericas=None):
        self.columnasCategoricas = columnasCategoricas or COLUMNAS_CATEGORICAS
        self.columnasNumericas = columnasNumericas

    def limpiar(self, df):
        for col in self.columnasCategoricas:
            if col in df.columns:
                df[col] = df[col].astype("category")
        if self.columnasNumericas:
            for col in self.columnasNumericas:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
        return df


class MissingValueHandler:
    """Imputa nulos con mediana (numericas) y moda (categoricas).

    Las columnas de COLUMNAS_NO_IMPUTAR (labs de ayuno y respuestas de diabetes)
    NO se imputan: se dejan como NaN.
    """

    def __init__(self, columnasNumericas=None, columnasCategoricas=None, columnasNoImputar=None):
        self.columnasNumericas = columnasNumericas
        self.columnasCategoricas = columnasCategoricas or COLUMNAS_CATEGORICAS
        self.columnasNoImputar = columnasNoImputar if columnasNoImputar is not None else COLUMNAS_NO_IMPUTAR

    def imputar(self, df):
        nums = self.columnasNumericas if self.columnasNumericas is not None else [
            c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != "SEQN"
        ]
        for col in nums:
            if col in df.columns and col not in self.columnasNoImputar:
                mediana = df[col].median()
                nulos = int(df[col].isna().sum())
                if nulos > 0:
                    df[col] = df[col].fillna(mediana)
                    print("Imputando %s: mediana=%.2f, nulos=%d" % (col, mediana, nulos))
            elif col in self.columnasNoImputar and col in df.columns:
                nulos = int(df[col].isna().sum())
                if nulos > 0:
                    print("NO imputado %s: nulos=%d (ayuno o respuesta de diabetes)" % (col, nulos))
        for col in self.columnasCategoricas:
            if col in df.columns:
                nulos = int(df[col].isna().sum())
                if nulos > 0:
                    moda = df[col].mode()
                    if len(moda) > 0:
                        df[col] = df[col].fillna(moda.iloc[0])
                        print("Imputando %s: moda=%s, nulos=%d" % (col, moda.iloc[0], nulos))
        return df