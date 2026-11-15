import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from repositorios.cargador import CargadorDataset
from repositorios.nhanes import NhanesSchemaMapper, NhanesFusion
from servicios.cruce import NormalizadorDrugs, ResumenDrugs
from utilidades.constantes import (
    CARPETA_RAW, ARCHIVOS_NHANES, COLUMNAS_CURADAS,
    ARCHIVO_NHANES_MASTER, ARCHIVO_NHANES_CRUZADO, ARCHIVO_DRUGS_PRODUCT,
)


class PipelineCruce:
    def ejecutar(self):
        print("=== Validando integracion de ciclos NHANES ===")
        listaDfs = []
        for nombre in ARCHIVOS_NHANES:
            df = CargadorDataset(CARPETA_RAW / nombre).cargar()
            listaDfs.append(df)
            print(f"{nombre}: {df.shape}")

        mapper = NhanesSchemaMapper(COLUMNAS_CURADAS)
        fusion = NhanesFusion(mapper)
        fusionado, comunes = fusion.fusionar(listaDfs)
        print("Columnas comunes:", len(comunes))
        # CSV cruzado de lectura continua (integracion de los 5 ciclos)
        fusionado.to_csv(ARCHIVO_NHANES_CRUZADO, index=False)
        print("CSV cruzado guardado:", ARCHIVO_NHANES_CRUZADO)

        print("\n=== Cargando maestro limpio ===")
        if ARCHIVO_NHANES_MASTER.exists():
            limpio = pd.read_csv(ARCHIVO_NHANES_MASTER, compression="gzip")
            print("Forma limpio:", limpio.shape)
            print("Duplicados:", int(limpio.duplicated().sum()))
            print("Nulos totales:", int(limpio.isna().sum().sum()))
            if "OUTLIER_IQR" in limpio.columns:
                print("Filas marcadas IQR:", int(limpio["OUTLIER_IQR"].sum()))
        else:
            print("Maestro limpio no encontrado. Ejecute primero main.py")

        print("\n=== Cargando catalogo Drugs_product ===")
        if ARCHIVO_DRUGS_PRODUCT.exists():
            dfDrugs = CargadorDataset(ARCHIVO_DRUGS_PRODUCT, encoding="latin-1").cargar()
            dfDrugs = NormalizadorDrugs().normalizar(dfDrugs)
            print("Forma Drugs:", dfDrugs.shape)
            resumen = ResumenDrugs(dfDrugs).resumen()
            print(resumen.to_string(index=False))
        else:
            print("Drugs_product.csv no encontrado (cruce opcional).")


if __name__ == "__main__":
    PipelineCruce().ejecutar()