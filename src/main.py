import sys
from pathlib import Path

# asegurar que src esta en el path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from repositorios.cargador import CargadorDataset
from repositorios.nhanes import NhanesSchemaMapper, NhanesFusion
from servicios.limpieza import (
    TratadorDuplicados, NormalizadorCodigosNhanes, NormalizadorMenores,
    TypeCleaner, MissingValueHandler,
)
from servicios.calidad import Diagnosticador, AnalizadorOutliers, Validador
from utilidades.constantes import (
    CARPETA_RAW, ARCHIVOS_NHANES, CARPETA_CLEANED, CARPETA_REPORTES,
    ARCHIVO_NHANES_MASTER, ARCHIVO_NHANES_MASTER_CSV, ARCHIVO_CLEANING_SUMMARY, ARCHIVO_CLEANING_REPORT,
    COLUMNAS_CURADAS, COLUMNAS_CATEGORICAS, COLUMNAS_NUMERICAS,
)


def revisar_datos_crudos():
    faltantes = []
    for nombre in ARCHIVOS_NHANES:
        ruta = CARPETA_RAW / nombre
        if not ruta.exists():
            faltantes.append(str(ruta))
    if faltantes:
        raise FileNotFoundError("Faltan archivos crudos de NHANES:\n" + "\n".join(faltantes))
    print("Todos los archivos crudos de NHANES estan presentes.")


class PipelineLimpiezaNhanes:
    def __init__(self):
        self.mapper = NhanesSchemaMapper(COLUMNAS_CURADAS)
        self.fusion = NhanesFusion(self.mapper)

    def ejecutar(self):
        revisar_datos_crudos()

        # 1. Cargar los 5 ciclos
        print("\n=== Cargando ciclos NHANES ===")
        listaDfs = []
        for nombre in ARCHIVOS_NHANES:
            ruta = CARPETA_RAW / nombre
            cargador = CargadorDataset(ruta)
            df = cargador.cargar()
            print(f"{nombre}: shape={df.shape}")
            listaDfs.append(df)

        # 2. Fusionar por interseccion de columnas
        print("\n=== Fusionando ciclos por interseccion de columnas ===")
        fusionado, comunes = self.fusion.fusionar(listaDfs)

        # 3. Diagnostico inicial
        diag = Diagnosticador(COLUMNAS_NUMERICAS)
        diag.diagnosticar(fusionado, "NHANES fusionado (antes)")

        # 4. Duplicados
        print("\n=== Eliminando duplicados ===")
        tratador = TratadorDuplicados("SEQN")
        df = tratador.quitar(fusionado)

        # 5. Codigos de no respuesta -> NaN (solo categoricas, por columna)
        print("\n=== Normalizando codigos de no respuesta (solo categoricas) -> NaN ===")
        normalizador = NormalizadorCodigosNhanes()
        df = normalizador.normalizar(df)

        # 5b. Menores de edad: educacion/estado civil = 'No aplica (menor)'
        print("\n=== Ajustando categorias para menores de edad ===")
        df = NormalizadorMenores().normalizar(df)

        # 6. Tipos de datos
        print("\n=== Convirtiendo tipos de datos ===")
        cleaner = TypeCleaner(COLUMNAS_CATEGORICAS, COLUMNAS_NUMERICAS)
        df = cleaner.limpiar(df)
        memAntes = df.memory_usage(deep=True).sum() / 1024
        print("Columnas categoricas:", [c for c in COLUMNAS_CATEGORICAS if c in df.columns])

        # 7. Imputacion de nulos con mediana/moda
        print("\n=== Imputando valores faltantes (mediana/moda) ===")
        nulosAntes = int(df.isna().sum().sum())
        imputador = MissingValueHandler(COLUMNAS_NUMERICAS, COLUMNAS_CATEGORICAS)
        df = imputador.imputar(df)
        nulosDespues = int(df.isna().sum().sum())
        print("Nulos antes:", nulosAntes, "-> despues:", nulosDespues)

        # 8. Outliers IQR (modo flag)
        print("\n=== Detectando outliers con regla IQR (k=1.5, modo flag) ===")
        analizador = AnalizadorOutliers(COLUMNAS_NUMERICAS, k=1.5)
        limites = analizador.revisarIQR(df)
        df = analizador.marcar(df, limites)

        # 9. Validacion
        print("\n=== Validacion final ===")
        validador = Validador()
        validador.validar(df, COLUMNAS_NUMERICAS)

        # 10. Exportar
        CARPETA_CLEANED.mkdir(parents=True, exist_ok=True)
        df.to_csv(ARCHIVO_NHANES_MASTER, index=False, compression="gzip")
        print("\nArchivo guardado:", ARCHIVO_NHANES_MASTER)
        # CSV plano para lectura continua (Excel/visor)
        df.to_csv(ARCHIVO_NHANES_MASTER_CSV, index=False)
        print("CSV de lectura continua guardado:", ARCHIVO_NHANES_MASTER_CSV)

        # 11. Resumen tabular
        CARPETA_REPORTES.mkdir(parents=True, exist_ok=True)
        filasBrutas = sum(len(d) for d in listaDfs)
        resumen = pd.DataFrame([{
            "dataset": "nhanes_master",
            "raw_rows": filasBrutas,
            "raw_cols": len(comunes),
            "final_rows": len(df),
            "final_cols": len(df.columns),
            "duplicates_dropped": filasBrutas - len(df),
            "rows_flagged_iqr": int(df["OUTLIER_IQR"].sum()),
            "rows_removed_iqr": 0,
            "cols_checked_iqr": len(limites),
            "total_outliers_iqr": int(sum(
                ((df[c] < limites[c][0]) | (df[c] > limites[c][1])).sum()
                for c in limites
            )),
        }])
        resumen.to_csv(ARCHIVO_CLEANING_SUMMARY, index=False)
        print("Resumen guardado:", ARCHIVO_CLEANING_SUMMARY)

        # 12. Reporte markdown
        with open(ARCHIVO_CLEANING_REPORT, "w", encoding="utf-8") as f:
            f.write("# Reporte de limpieza - NHANES\n\n")
            f.write(f"- Filas brutas (5 ciclos): {filasBrutas}\n")
            f.write(f"- Filas finales: {len(df)}\n")
            f.write(f"- Columnas comunes: {len(comunes)}\n")
            f.write(f"- Columnas finales: {len(df.columns)} (incluye OUTLIER_IQR)\n")
            f.write(f"- Duplicados eliminados: {filasBrutas - len(df)}\n")
            f.write(f"- Nulos antes de imputar: {nulosAntes}\n")
            f.write(f"- Nulos despues de imputar: {nulosDespues}\n")
            f.write(f"- Columnas validas para IQR: {len(limites)}\n")
            f.write(f"- Filas marcadas como outlier (IQR, k=1.5): {int(df['OUTLIER_IQR'].sum())}\n")
            f.write("\n## Limites IQR por columna\n")
            for col, (li, ls) in limites.items():
                f.write(f"- {col}: [{li:.2f}, {ls:.2f}]\n")
        print("Reporte guardado:", ARCHIVO_CLEANING_REPORT)

        return df


if __name__ == "__main__":
    PipelineLimpiezaNhanes().ejecutar()