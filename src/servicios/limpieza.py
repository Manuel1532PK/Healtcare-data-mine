import numpy as np
import pandas as pd

from utilidades.constantes import COLUMNAS_CATEGORICAS, CODIGOS_NO_RESPUESTA


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
    """Reemplaza codigos especiales de no respuesta (7, 9, ...) por NaN."""

    def __init__(self, columnas=None):
        self.columnas = columnas

    def normalizar(self, df):
        cols = self.columnas if self.columnas is not None else df.columns
        for col in cols:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].replace(CODIGOS_NO_RESPUESTA, np.nan)
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
    """Imputa nulos con mediana (numericas) y moda (categoricas)."""

    def __init__(self, columnasNumericas=None, columnasCategoricas=None):
        self.columnasNumericas = columnasNumericas
        self.columnasCategoricas = columnasCategoricas or COLUMNAS_CATEGORICAS

    def imputar(self, df):
        nums = self.columnasNumericas if self.columnasNumericas is not None else [
            c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != "SEQN"
        ]
        for col in nums:
            if col in df.columns:
                mediana = df[col].median()
                nulos = int(df[col].isna().sum())
                if nulos > 0:
                    df[col] = df[col].fillna(mediana)
                    print(f"Imputando {col}: mediana={mediana:.2f}, nulos={nulos}")
        for col in self.columnasCategoricas:
            if col in df.columns:
                nulos = int(df[col].isna().sum())
                if nulos > 0:
                    moda = df[col].mode()
                    if len(moda) > 0:
                        df[col] = df[col].fillna(moda.iloc[0])
                        print(f"Imputando {col}: moda={moda.iloc[0]}, nulos={nulos}")
        return df