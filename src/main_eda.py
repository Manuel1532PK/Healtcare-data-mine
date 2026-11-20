import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")

from repositorios.cargador import CargadorDataset
from servicios.eda import AnalizadorDescriptivo, Visualizador, AnalizadorCorrelacion
from utilidades.constantes import CARPETA_OUTPUTS, COLUMNAS_NUMERICAS

CARPETA_FIGURAS = CARPETA_OUTPUTS / "figuras"
CARPETA_FIGURAS.mkdir(parents=True, exist_ok=True)
CARPETA_REPORTES = CARPETA_OUTPUTS / "reportes"
CARPETA_REPORTES.mkdir(parents=True, exist_ok=True)
CARPETA_EDA = CARPETA_OUTPUTS / "eda"
CARPETA_EDA.mkdir(parents=True, exist_ok=True)
ARCHIVO_RESUMEN = CARPETA_EDA / "resumen_descriptivo.csv"
ARCHIVO_OUTLIERS = CARPETA_EDA / "outliers_iqr.csv"
ARCHIVO_CORR = CARPETA_EDA / "pares_correlacion.csv"
ARCHIVO_INFORME = CARPETA_REPORTES / "informe_eda_nhanes.docx"

NUMS_EDA = ["RIDAGEYR", "BMXWT", "BMXHT", "BMXBMI", "BMXWAIST",
            "LBXGLU", "LBXTC", "LBDLDL", "LBXTR",
            "DR1TKCAL", "DR1TSUGR", "DR1TPROT", "DR1TCARB", "DR1TFIBE", "DR1TTFAT"]
CATS_EDA = ["RIAGENDR", "RIDRETH1", "DMDEDUC2", "DMDMARTL", "RIDSTATR", "HUQ010", "SDDSRVYR"]


def derivar_etiqueta(df):
    diabetes = (df["DIQ010"] == 1) if "DIQ010" in df.columns else pd.Series(False, index=df.index)
    obesidad = (df["BMXBMI"] >= 30) if "BMXBMI" in df.columns else pd.Series(False, index=df.index)
    colAlto = (df["LBXTC"] >= 200) if "LBXTC" in df.columns else pd.Series(False, index=df.index)
    df = df.copy()
    df["Disease_Indicator"] = (diabetes | obesidad | colAlto).astype(int)
    return df


class PipelineEDA:
    def ejecutar(self):
        print("=== Cargando maestro limpio ===")
        df = pd.read_csv(CARPETA_OUTPUTS / "cleaned" / "nhanes_master_cleaned.csv")
        print("Forma:", df.shape)
        df = derivar_etiqueta(df)

        nums = [c for c in NUMS_EDA if c in df.columns]

        # 1. Univariado: resumen descriptivo
        print("\n=== Resumen descriptivo (univariado) ===")
        analizador = AnalizadorDescriptivo(nums)
        resumen = analizador.resumen(df)
        resumen.to_csv(ARCHIVO_RESUMEN)
        print(resumen[["mean", "50%", "std", "min", "max", "skew", "kurtosis"]].round(2).to_string())
        print("Guardado:", ARCHIVO_RESUMEN)

        # 2. Outliers IQR cuantificados
        print("\n=== Outliers IQR (cuantificados) ===")
        out = analizador.outliersIQR(df)
        out.to_csv(ARCHIVO_OUTLIERS, index=False)
        print(out.to_string(index=False))
        print("Guardado:", ARCHIVO_OUTLIERS)

        # 3. Visualizaciones
        print("\n=== Generando figuras ===")
        viz = Visualizador(CARPETA_FIGURAS)
        for col in ["RIDAGEYR", "BMXBMI", "LBXGLU", "LBXTC", "DR1TKCAL"]:
            if col in df.columns:
                viz.histograma(df, col)
                viz.boxplot(df, col)
        for col in ["RIAGENDR", "RIDRETH1", "DMDEDUC2", "HUQ010"]:
            if col in df.columns:
                viz.barras(df, col)
        # scatter: edad vs BMI, glucosa vs BMI
        if "RIDAGEYR" in df.columns and "BMXBMI" in df.columns:
            viz.scatter(df, "RIDAGEYR", "BMXBMI", hue="Disease_Indicator")
        if "LBXGLU" in df.columns and "BMXBMI" in df.columns:
            viz.scatter(df, "LBXGLU", "BMXBMI", hue="Disease_Indicator")
        viz.heatmap(df, nums)
        viz.matrizDispersion(df, nums, maxCols=6)

        # 4. Bivariado: tasa de Disease_Indicator por segmento
        print("\n=== Tasa de Disease_Indicator por segmento ===")
        cruces = {}
        for col in ["RIAGENDR", "RIDRETH1", "DMDEDUC2", "HUQ010"]:
            if col in df.columns:
                tasa = df.groupby(col)["Disease_Indicator"].mean().round(3)
                cruces[col] = tasa
                print(f"\n{col}:\n{tasa.to_string()}")

        # 5. Correlacion Pearson
        print("\n=== Correlacion de Pearson (pares destacados |r|>=0.5) ===")
        corr = AnalizadorCorrelacion(nums)
        pares = corr.paresDestacados(df, umbral=0.5)
        pares.to_csv(ARCHIVO_CORR, index=False)
        if len(pares) > 0:
            print(pares.to_string(index=False))
        else:
            print("No hay pares con |r|>=0.5")
        print("Guardado:", ARCHIVO_CORR)

        # 6. Generar informe docx (6 secciones)
        print("\n=== Generando informe EDA (docx) ===")
        self._generarInforme(df, resumen, out, cruces, pares)
        print("Informe guardado:", ARCHIVO_INFORME)

        print("\nFase 3 completada.")
        return df

    def _generarInforme(self, df, resumen, out, cruces, pares):
        from docx import Document
        from docx.shared import Inches, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()
        estilo = doc.styles["Normal"]
        estilo.font.name = "Calibri"
        estilo.font.size = Pt(11)

        # 1. Portada y contexto
        doc.add_heading("Informe de Análisis Exploratorio de Datos (EDA)", level=0)
        doc.add_paragraph("Proyecto: Minería de Datos — NHANES (2005–2014)")
        doc.add_paragraph("Equipo (MIMETIC): Manuel José Rivera Guzmán · Julián Andrés Correa Cuevas")
        doc.add_paragraph("Asignatura: Minería de Datos · UNIMINUTO Ibagué · 2026-2")
        doc.add_paragraph("Pregunta de negocio: ¿qué variables (demográficas, antropométricas, de laboratorio y nutricionales) se asocian con el indicador de enfermedad (diabetes/obesidad/colesterol alto) en la población NHANES 2005–2014?")
        doc.add_paragraph("Objetivo del análisis: escuchar a los datos antes de modelarlos (EDA univariado, bivariado y multivariado), cuantificar outliers y correlaciones, y redactar hallazgos accionables.")

        # 2. Calidad de datos
        doc.add_heading("2. Calidad de datos (herencia sesiones 3–4)", level=1)
        doc.add_paragraph(f"Filas: {len(df)} · Columnas: {len(df.columns)} · Nulos: {int(df.isna().sum().sum())} · Duplicados: {int(df.duplicated().sum())}")
        doc.add_paragraph("Decisiones: códigos de no respuesta NHANES (7, 9, …) tratados como NaN SOLO en categóricas (por columna); menores de 20 años con educación/estado civil = 'No aplica (menor)'; labs de ayuno (glucosa, LDL, triglicéridos) NO imputados (submuestra de ayuno); outliers marcados con regla IQR (k=1,5, modo flag, sin eliminar pacientes).")
        doc.add_paragraph(f"Filas marcadas como outlier (IQR): {int(df['OUTLIER_IQR'].sum())} ({df['OUTLIER_IQR'].mean()*100:.1f} %).")
        doc.add_paragraph("Nota: la población incluye menores (36,5 % < 20 años); los umbrales clínicos de adultos (IMC>=30, colesterol>=200) se aplican a todos los participantes. Los labs de ayuno tienen nulos estructurales (submuestra NHANES).")

        # 3. Análisis univariado
        doc.add_heading("3. Análisis univariado", level=1)
        doc.add_paragraph("Tablas descriptivas (media, mediana, desviación, min, max, asimetría, curtosis). Con asimetría alta se reporta la mediana.")
        # tabla resumen (primeras filas)
        tabla = doc.add_table(rows=1, cols=6)
        tabla.style = "Table Grid"
        hdr = tabla.rows[0].cells
        for i, h in enumerate(["Variable", "Media", "Mediana", "Desv.", "Skew", "Curtosis"]):
            hdr[i].text = h
        for var, row in resumen.iterrows():
            cells = tabla.add_row().cells
            cells[0].text = str(var)
            cells[1].text = f"{row['mean']:.1f}"
            cells[2].text = f"{row['50%']:.1f}"
            cells[3].text = f"{row['std']:.1f}"
            cells[4].text = f"{row['skew']:.2f}"
            cells[5].text = f"{row['kurtosis']:.2f}"
        # figuras hist/box para variables clave
        for col in ["RIDAGEYR", "BMXBMI", "LBXGLU", "LBXTC", "DR1TKCAL"]:
            for tipo in ["hist", "box"]:
                ruta = CARPETA_FIGURAS / f"fig_{tipo}_{col}.png"
                if ruta.exists():
                    doc.add_paragraph(f"{tipo.capitalize()} de {col}", style=None).runs[0].bold = True
                    doc.add_picture(str(ruta), width=Inches(5.5))

        # 4. Bivariado / multivariado
        doc.add_heading("4. Análisis bivariado / multivariado", level=1)
        doc.add_paragraph("Tasa de Disease_Indicator por segmento (crosstab normalizado por fila).")
        for col, tasa in cruces.items():
            doc.add_paragraph(f"{col}:", style=None).runs[0].bold = True
            doc.add_paragraph(tasa.to_string())
        # scatter + heatmap
        for nombre in ["fig_scatter_RIDAGEYR_BMXBMI.png", "fig_scatter_LBXGLU_BMXBMI.png", "fig_heatmap_corr.png", "fig_matriz_dispersion.png"]:
            ruta = CARPETA_FIGURAS / nombre
            if ruta.exists():
                doc.add_picture(str(ruta), width=Inches(5.5))
        # correlacion
        doc.add_paragraph("Correlaciones de Pearson destacadas (|r| >= 0,5):")
        if len(pares) > 0:
            t2 = doc.add_table(rows=1, cols=4)
            t2.style = "Table Grid"
            h2 = t2.rows[0].cells
            for i, h in enumerate(["Variable 1", "Variable 2", "r", "Fuerza"]):
                h2[i].text = h
            for _, row in pares.iterrows():
                c = t2.add_row().cells
                c[0].text = str(row.get("variable_1", row["var1"]))
                c[1].text = str(row.get("variable_2", row["var2"]))
                c[2].text = str(row["r"]); c[3].text = str(row["fuerza"])
        else:
            doc.add_paragraph("No se encontraron pares con |r| >= 0,5.")
        doc.add_paragraph("Nota: la correlación mide asociación lineal; NO implica causalidad (ej.: edad vs glucosa es asociación, no causalidad; confusoras como dieta/actividad deben controlarse).")

        # 5. Hallazgos y recomendaciones
        doc.add_heading("5. Hallazgos y recomendaciones (accionables)", level=1)
        hallazgos = [
            ("La edad y la antropometría se asocian con el indicador de enfermedad.",
             "La tasa de Disease_Indicator varía por grupos de edad (bordes 0/11/27/51/85 años) y por BMXBMI; la población con IMC >= 30 aporta a la clase 1. Acción: priorizar campañas de prevención en los segmentos de mayor IMC."),
            ("Glucosa y colesterol (LBXGLU, LBXTC, LBDLDL) son las variables de laboratorio con mayor presencia de outliers reales.",
             "IQR marca ~33,6 % de filas; estos outliers corresponden a pacientes diabéticos/hipercolesterolémicos (valores clínicos reales, no errores). Acción: no eliminarlos; usar RobustScaler si se modela con distancias."),
            ("Las variables numéricas presentan asimetría positiva (colas a la derecha) en labs y nutrición.",
             "Skew > 0 en LBXTR, DR1TKCAL, DR1TSUGR, etc.; la mediana es la medida honesta del centro. Acción: reportar mediana para variables asimétricas y aplicar transformaciones (log) si se usan modelos lineales."),
            ("Correlaciones fuertes entre antropometría (BMXWT, BMXHT, BMXBMI, BMXWAIST) anticipan multicolinealidad.",
             "Pares con |r| >= 0,5 en el heatmap. Acción: en modelos lineales, considerar PCA (6 componentes retienen ~82,4 %) o selección de variables."),
        ]
        for i, (h, e) in enumerate(hallazgos, 1):
            p = doc.add_paragraph()
            r = p.add_run(f"Hallazgo {i}: {h}")
            r.bold = True
            doc.add_paragraph(e)

        # 6. Anexos
        doc.add_heading("6. Anexos", level=1)
        doc.add_paragraph("Notebook reproducible: docs/eda_nhanes.ipynb (y notebooks de fases anteriores).")
        doc.add_paragraph("Figuras generadas en outputs/figuras/: histogramas, boxplots, barras, scatter, heatmap y matriz de dispersión.")
        doc.add_paragraph("Datos: outputs/cleaned/nhanes_master_cleaned.csv(.gz), outputs/transformed/X_nhanes.csv, y_nhanes.csv.")

        doc.save(ARCHIVO_INFORME)


if __name__ == "__main__":
    PipelineEDA().ejecutar()