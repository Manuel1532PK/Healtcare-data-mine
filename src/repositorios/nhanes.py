import pandas as pd

from utilidades.constantes import COLUMNAS_CURADAS


class NhanesSchemaMapper:
    """Resuelve el esquema comun por interseccion de columnas entre ciclos."""

    def __init__(self, columnasDeseadas=None):
        self.columnasDeseadas = columnasDeseadas or COLUMNAS_CURADAS

    def columnasComunes(self, listaDfs):
        comunes = set(listaDfs[0].columns)
        for df in listaDfs[1:]:
            comunes = comunes & set(df.columns)
        # mantener solo las deseadas que sean comunes, en el orden de COLUMNAS_CURADAS
        resultado = [c for c in self.columnasDeseadas if c in comunes]
        return resultado


class NhanesFusion:
    """Integra los ciclos de NHANES por interseccion de columnas, indexados por SEQN."""

    def __init__(self, mapper=None):
        self.mapper = mapper or NhanesSchemaMapper()

    def fusionar(self, listaDfs):
        comunes = self.mapper.columnasComunes(listaDfs)
        partes = []
        for df in listaDfs:
            partes.append(df[comunes].copy())
        fusionado = pd.concat(partes, ignore_index=True)
        # validar unicidad de SEQN
        duplicados = int(fusionado["SEQN"].duplicated().sum())
        print("Filas fusionadas:", len(fusionado))
        print("Columnas comunes:", len(comunes))
        print("Duplicados de SEQN:", duplicados)
        return fusionado, comunes