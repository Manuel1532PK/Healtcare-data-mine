import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import matplotlib
matplotlib.use("Agg")

from servicios.eda import AnalizadorDescriptivo, Visualizador, AnalizadorCorrelacion
from servicios.transformacion import DerivadorEtiqueta
from utilidades.constantes import CARPETA_OUTPUTS, nombre_legible

CARPETA_FIGURAS = CARPETA_OUTPUTS / "figuras"
CARPETA_FIGURAS.mkdir(parents=True, exist_ok=True)
CARPETA_REPORTES = CARPETA_OUTPUTS / "reportes"
CARPETA_REPORTES.mkdir(parents=True, exist_ok=True)
CARPETA_EDA = CARPETA_OUTPUTS / "eda"
CARPETA_EDA.mkdir(parents=True, exist_ok=True)
CARPETA_TRANSFORMED = CARPETA_OUTPUTS / "transformed"
ARCHIVO_RESUMEN = CARPETA_EDA / "resumen_descriptivo.csv"
ARCHIVO_OUTLIERS = CARPETA_EDA / "outliers_iqr.csv"
ARCHIVO_CORR = CARPETA_EDA / "pares_correlacion.csv"
ARCHIVO_VARIANZA = CARPETA_TRANSFORMED / "varianza_pca.csv"
ARCHIVO_INFORME = CARPETA_REPORTES / "informe_eda_nhanes.docx"

NUMS_EDA = ["RIDAGEYR", "BMXWT", "BMXHT", "BMXBMI", "BMXWAIST",
            "LBXGLU", "LBXTC", "LBDLDL", "LBXTR",
            "DR1TKCAL", "DR1TSUGR", "DR1TPROT", "DR1TCARB", "DR1TFIBE", "DR1TTFAT"]


def derivar_etiqueta(df):
    return DerivadorEtiqueta().derivar(df)


def hallazgos_calculados(df, resumen, out, cruces, pares, varianza):
    """Redacta los hallazgos con cifras tomadas de los datos (no escritas a mano)."""
    h = []

    grupos = pd.cut(df["RIDAGEYR"], [0, 19, 39, 59, 120], labels=["<20", "20-39", "40-59", "60+"], right=True)
    tasaEdad = df.groupby(grupos, observed=True)["Disease_Indicator"].mean()
    partes = ", ".join(f"{k}: {v*100:.1f} %" for k, v in tasaEdad.items())
    mayor, menor = tasaEdad.idxmax(), tasaEdad.idxmin()
    h.append((
        f"La tasa del indicador de enfermedad es mayor en el grupo {mayor} y menor en el grupo {menor}.",
        f"Tasa por grupo de edad: {partes}. Acción: priorizar prevención en los grupos de mayor tasa.",
    ))

    top = out.dropna(subset=["lim_inf"]).sort_values("outliers", ascending=False).head(3)
    detalle = "; ".join(f"{r['variable']} ({r['outliers']:,} filas)" for _, r in top.iterrows())
    nota = out[out["nota"].fillna("").str.contains("IQR nulo")]["variable"].tolist()
    h.append((
        "Las variables con más valores atípicos (regla IQR, k=1,5) son: " + ", ".join(top["variable"]) + ".",
        f"Mayor número de atípicos: {detalle}. Sin dispersión (IQR nulo, omitidas): {', '.join(nota) if nota else 'ninguna'}. "
        "Se marcan y no se eliminan; revisar con el equipo clínico si son valores reales. Acción: usar RobustScaler si se modela con distancias.",
    ))

    asim = resumen[resumen["skew"].abs() > 1].sort_values("skew", ascending=False)
    lista = ", ".join(f"{idx} ({r['skew']:.2f})" for idx, r in asim.iterrows())
    h.append((
        "Varias variables tienen asimetría fuerte (|skew| > 1).",
        f"Variables: {lista}. Acción: reportar la mediana como centro y considerar transformación logarítmica en modelos lineales.",
    ))

    if len(pares) > 0:
        fuertes = pares.head(3)
        lista = "; ".join(f"{r['variable_1']} ↔ {r['variable_2']} (r={r['r']:.2f})" for _, r in fuertes.iterrows())
        h.append((
            f"Existen {len(pares)} pares de variables con |r| >= 0,5 (posible multicolinealidad).",
            f"Pares de mayor |r|: {lista}. Acción: en modelos lineales, usar PCA o seleccionar variables.",
        ))

    if varianza is not None:
        p80 = int((varianza["varianza_acumulada"] < 0.80).sum()) + 1
        p90 = int((varianza["varianza_acumulada"] < 0.90).sum()) + 1
        h.append((
            "PCA permite comprimir las variables numéricas escaladas.",
            f"Componentes para ≥80 %: {p80}; para ≥90 %: {p90} de {len(varianza)}. "
            "Acción: decidir en la fase de modelado si se aplica PCA, documentando la varianza retenida.",
        ))
    return h


class PipelineEDA:
    def ejecutar(self):
        print("=== Cargando maestro limpio ===")
        df = pd.read_csv(CARPETA_OUTPUTS / "cleaned" / "nhanes_master_cleaned.csv")
        print("Forma:", df.shape)
        df = derivar_etiqueta(df)
        dfEtiquetado = df.loc[df["Disease_Indicator"].notna()].copy()
        dfEtiquetado["Disease_Indicator"] = dfEtiquetado["Disease_Indicator"].astype(int)

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
            if col in dfEtiquetado.columns:
                tasa = dfEtiquetado.groupby(col, observed=True)["Disease_Indicator"].mean().round(3)
                cruces[col] = tasa
                print(f"\n{col}:\n{tasa.to_string()}")

        # 5. Correlacion Pearson
        print("\n=== Correlacion de Pearson (pares destacados |r|>=0.5) ===")
        corr = AnalizadorCorrelacion(nums)
        pares = corr.paresDestacados(df, umbral=0.5)
        pares.to_csv(ARCHIVO_CORR, index=False)
        print(pares.to_string(index=False) if len(pares) > 0 else "No hay pares con |r|>=0.5")
        print("Guardado:", ARCHIVO_CORR)

        # 6. Informe docx (6 secciones)
        varianza = pd.read_csv(ARCHIVO_VARIANZA) if ARCHIVO_VARIANZA.exists() else None
        print("\n=== Generando informe EDA (docx) ===")
        self._generarInforme(df, dfEtiquetado, resumen, out, cruces, pares, varianza)
        print("Informe guardado:", ARCHIVO_INFORME)

        print("\nFase 3 completada.")
        return df

    def _generarInforme(self, df, dfEtiquetado, resumen, out, cruces, pares, varianza):
        from docx import Document
        from docx.shared import Inches, Pt

        doc = Document()
        estilo = doc.styles["Normal"]
        estilo.font.name = "Calibri"
        estilo.font.size = Pt(11)

        # 1. Portada y contexto
        doc.add_heading("Informe de Análisis Exploratorio de Datos (EDA)", level=0)
        doc.add_paragraph("Proyecto: Minería de Datos — NHANES (2005–2014)")
        doc.add_paragraph("Equipo (MIMETIC): Manuel José Rivera Guzmán · Julián Andrés Correa Cuevas")
        doc.add_paragraph("Asignatura: Minería de Datos · UNIMINUTO Ibagué · 2026-2")
        doc.add_paragraph("Pregunta de negocio: ¿qué variables demográficas, antropométricas, de laboratorio y nutricionales se asocian con el indicador de enfermedad (diabetes, obesidad o colesterol alto) en la población NHANES 2005–2014?")
        doc.add_paragraph("Objetivo del análisis: escuchar a los datos antes de modelarlos (EDA univariado, bivariado y multivariado), cuantificar outliers y correlaciones, y redactar hallazgos accionables.")

        # 2. Calidad de datos
        doc.add_heading("2. Calidad de datos (herencia sesiones 3–4)", level=1)
        doc.add_paragraph(f"Filas: {len(df)} · Columnas: {len(df.columns)} · Nulos: {int(df.isna().sum().sum())} · Duplicados: {int(df.duplicated().sum())}")
        doc.add_paragraph("Decisiones: códigos de no respuesta NHANES (7, 9, …) tratados como NaN SOLO en categóricas (por columna); menores de 20 años con educación/estado civil = 'No aplica (menor)'; labs de ayuno (glucosa, LDL, triglicéridos) y respuestas de diabetes NO imputados; outliers marcados con regla IQR (k=1,5, modo flag, sin eliminar pacientes).")
        doc.add_paragraph(f"Filas marcadas como outlier (IQR): {int(df['OUTLIER_IQR'].sum())} ({df['OUTLIER_IQR'].mean()*100:.1f} %).")
        doc.add_paragraph(f"Filas con indicador de enfermedad desconocido (excluidas del análisis de tasas): {int(df['Disease_Indicator'].isna().sum())}.")
        doc.add_paragraph("Nota: la población incluye menores (< 20 años); los umbrales clínicos de adultos (IMC >= 30, colesterol >= 200) se aplican a todos los participantes. Los labs de ayuno tienen nulos estructurales (submuestra NHANES).")

        # 3. Análisis univariado
        doc.add_heading("3. Análisis univariado", level=1)
        doc.add_paragraph("Tablas descriptivas (media, mediana, desviación, asimetría, curtosis). Con asimetría alta se reporta la mediana.")
        tabla = doc.add_table(rows=1, cols=6)
        tabla.style = "Table Grid"
        for i, h in enumerate(["Variable", "Media", "Mediana", "Desv.", "Skew", "Curtosis"]):
            tabla.rows[0].cells[i].text = h
        for var, row in resumen.iterrows():
            cells = tabla.add_row().cells
            cells[0].text = str(var)
            cells[1].text = f"{row['mean']:.1f}"
            cells[2].text = f"{row['50%']:.1f}"
            cells[3].text = f"{row['std']:.1f}"
            cells[4].text = f"{row['skew']:.2f}"
            cells[5].text = f"{row['kurtosis']:.2f}"
        for col in ["RIDAGEYR", "BMXBMI", "LBXGLU", "LBXTC", "DR1TKCAL"]:
            for tipo in ["hist", "box"]:
                ruta = CARPETA_FIGURAS / f"fig_{tipo}_{col}.png"
                if ruta.exists():
                    doc.add_paragraph(f"{'Histograma' if tipo == 'hist' else 'Boxplot'} de {nombre_legible(col)}").runs[0].bold = True
                    doc.add_picture(str(ruta), width=Inches(5.5))

        # 4. Bivariado / multivariado
        doc.add_heading("4. Análisis bivariado / multivariado", level=1)
        doc.add_paragraph("Tasa de indicador de enfermedad por segmento (sin filas de indicador desconocido).")
        for col, tasa in cruces.items():
            doc.add_paragraph(f"{nombre_legible(col)}:").runs[0].bold = True
            doc.add_paragraph(tasa.to_string())
        for nombre in ["fig_scatter_RIDAGEYR_BMXBMI.png", "fig_scatter_LBXGLU_BMXBMI.png", "fig_heatmap_corr.png", "fig_matriz_dispersion.png"]:
            ruta = CARPETA_FIGURAS / nombre
            if ruta.exists():
                doc.add_picture(str(ruta), width=Inches(5.5))
        doc.add_paragraph("Correlaciones de Pearson destacadas (|r| >= 0,5):")
        if len(pares) > 0:
            t2 = doc.add_table(rows=1, cols=4)
            t2.style = "Table Grid"
            for i, h in enumerate(["Variable 1", "Variable 2", "r", "Fuerza"]):
                t2.rows[0].cells[i].text = h
            for _, row in pares.iterrows():
                c = t2.add_row().cells
                c[0].text = str(row.get("variable_1", row["var1"]))
                c[1].text = str(row.get("variable_2", row["var2"]))
                c[2].text = str(row["r"])
                c[3].text = str(row["fuerza"])
        else:
            doc.add_paragraph("No se encontraron pares con |r| >= 0,5.")
        doc.add_paragraph("Nota: la correlación mide asociación lineal; NO implica causalidad. Las variables de dieta de un mismo día y las de antropometría están correlacionadas por construcción.")

        # 5. Hallazgos y recomendaciones (calculados desde los datos)
        doc.add_heading("5. Hallazgos y recomendaciones (accionables)", level=1)
        for i, (titulo, evidencia) in enumerate(hallazgos_calculados(dfEtiquetado, resumen, out, cruces, pares, varianza), 1):
            doc.add_paragraph().add_run(f"Hallazgo {i}: {titulo}").bold = True
            doc.add_paragraph(evidencia)

        # 6. Anexos
        doc.add_heading("6. Anexos", level=1)
        doc.add_paragraph("Notebook reproducible: docs/eda_nhanes.ipynb.")
        doc.add_paragraph("Figuras en outputs/figuras/: histogramas, boxplots, barras, scatter, heatmap y matriz de dispersión.")
        doc.add_paragraph("Datos: outputs/cleaned/nhanes_master_cleaned.csv(.gz), outputs/transformed/X_nhanes.csv, y_nhanes.csv.")

        doc.save(ARCHIVO_INFORME)


if __name__ == "__main__":
    PipelineEDA().ejecutar()
