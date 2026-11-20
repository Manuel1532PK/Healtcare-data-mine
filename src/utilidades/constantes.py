from pathlib import Path

CARPETA_UTILIDADES = Path(__file__).resolve().parent
CARPETA_CODIGO = CARPETA_UTILIDADES.parent
CARPETA_PROYECTO = CARPETA_CODIGO.parent
CARPETA_DATA = CARPETA_PROYECTO / "data"
CARPETA_DATA.mkdir(parents=True, exist_ok=True)
CARPETA_RAW = CARPETA_DATA / "raw"
CARPETA_RAW.mkdir(parents=True, exist_ok=True)
CARPETA_OUTPUTS = CARPETA_PROYECTO / "outputs"
CARPETA_OUTPUTS.mkdir(parents=True, exist_ok=True)
CARPETA_CLEANED = CARPETA_OUTPUTS / "cleaned"
CARPETA_CLEANED.mkdir(parents=True, exist_ok=True)
CARPETA_REPORTES = CARPETA_OUTPUTS / "reportes"
CARPETA_REPORTES.mkdir(parents=True, exist_ok=True)

# Archivos de entrada (NHANES)
ARCHIVOS_NHANES = [
    "Nhanes_2005_2006.csv",
    "Nhanes_2007_2008.csv",
    "Nhanes_2009_2010.csv",
    "Nhanes_2011_2012.csv",
    "Nhanes_2013_2014.csv",
]

# Archivo de salida (limpio)
ARCHIVO_NHANES_MASTER = CARPETA_CLEANED / "nhanes_master_cleaned.csv.gz"
ARCHIVO_NHANES_MASTER_CSV = CARPETA_CLEANED / "nhanes_master_cleaned.csv"
ARCHIVO_NHANES_CRUZADO = CARPETA_CLEANED / "nhanes_master_cruzado.csv"
ARCHIVO_CLEANING_SUMMARY = CARPETA_REPORTES / "cleaning_summary.csv"
ARCHIVO_CLEANING_REPORT = CARPETA_REPORTES / "cleaning_report.md"

# Dataset de farmacos (catalogo) usado para el cruce opcional
ARCHIVO_DRUGS_PRODUCT = CARPETA_RAW / "Drugs_product.csv"

# Columnas curadas de NHANES (interseccion entre ciclos)
# Columnas comunes a los 5 ciclos (interseccion), verificadas empiricamente
COLUMNAS_CURADAS = [
    "SEQN", "RIAGENDR", "RIDAGEYR", "RIDRETH1", "DMDEDUC2",
    "BMXWT", "BMXHT", "BMXBMI", "BMXWAIST",
    "LBXGLU", "LBXTC", "LBDLDL", "LBXTR",
    "DR1TKCAL", "DR1TSUGR", "DR1TPROT", "DR1TCARB", "DR1TFIBE", "DR1TTFAT",
    "HUQ010", "DIQ010", "DIQ160", "DIQ170",
    "RIDSTATR", "SDDSRVYR", "DMDMARTL",
]

# Columnas que se convierten a category (codigos NHANES)
COLUMNAS_CATEGORICAS = [
    "RIAGENDR", "RIDRETH1", "DMDEDUC2", "DMDMARTL", "RIDSTATR", "HUQ010", "SDDSRVYR",
]

# Columnas numericas para imputacion/outliers
COLUMNAS_NUMERICAS = [
    "RIDAGEYR",
    "BMXWT", "BMXHT", "BMXBMI", "BMXWAIST",
    "LBXGLU", "LBXTC", "LBDLDL", "LBXTR",
    "DR1TKCAL", "DR1TSUGR", "DR1TPROT", "DR1TCARB", "DR1TFIBE", "DR1TTFAT",
    "DIQ010", "DIQ160", "DIQ170",
]

# Codigos de no respuesta por columna (solo categoricas; NO aplicar a numericas)
CODIGOS_NO_RESPUESTA_CAT = {
    "RIAGENDR": [7, 9],
    "RIDRETH1": [7, 9],
    "DMDEDUC2": [7, 9, 77, 99],
    "DMDMARTL": [7, 9, 77, 99],
    "HUQ010": [7, 9],
    "DIQ010": [7, 9],
    "DIQ160": [7, 9],
    "DIQ170": [7, 9],
    "RIDSTATR": [],
    "SDDSRVYR": [],
}

# Columnas de laboratorio de ayuno (submuestra): NO se imputan (se dejan NaN)
COLUMNAS_AYUNO = ["LBXGLU", "LBDLDL", "LBXTR"]

# Edad a partir de la cual aplican los umbrales clinicos de adultos
EDAD_ADULTO = 20

# Nombres legibles en espanol para variables NHANES (lectura continua)
NOMBRES_VARIABLES = {
    "RIDAGEYR": "Edad (anos)",
    "BMXWT": "Peso (kg)",
    "BMXHT": "Talla (cm)",
    "BMXBMI": "IMC (kg/m2)",
    "BMXWAIST": "Cintura (cm)",
    "LBXGLU": "Glucosa (mg/dL)",
    "LBXTC": "Colesterol total (mg/dL)",
    "LBDLDL": "LDL (mg/dL)",
    "LBXTR": "Trigliceridos (mg/dL)",
    "DR1TKCAL": "Energia (kcal)",
    "DR1TSUGR": "Azucar (g)",
    "DR1TPROT": "Proteina (g)",
    "DR1TCARB": "Carbohidratos (g)",
    "DR1TFIBE": "Fibra (g)",
    "DR1TTFAT": "Grasa total (g)",
    "RIAGENDR": "Sexo",
    "RIDRETH1": "Raza/etnia",
    "DMDEDUC2": "Educacion",
    "DMDMARTL": "Estado civil",
    "RIDSTATR": "Estado del examen",
    "HUQ010": "Salud general",
    "SDDSRVYR": "Ciclo NHANES",
    "Disease_Indicator": "Indicador de enfermedad",
    "OUTLIER_IQR": "Outlier IQR",
    "SEQN": "ID participante",
}

def nombre_legible(variable):
    return NOMBRES_VARIABLES.get(variable, variable)

# Medicamentos para cruce opcional con Drugs_product
MEDICAMENTOS_MAPEO = {
    "Aspirin": ["aspirin", "acetylsalicylic"],
    "Ibuprofen": ["ibuprofen"],
    "Lipitor": ["lipitor", "atorvastatin"],
    "Paracetamol": ["paracetamol", "acetaminophen"],
    "Penicillin": ["penicillin"],
}

COLUMNAS_DRUGS = [
    "SUBSTANCENAME", "NONPROPRIETARYNAME", "PHARM_CLASSES",
    "DOSAGEFORMNAME", "ROUTENAME", "DEASCHEDULE",
]

DRUGS_NOMINALES_ONEHOT = ["PRODUCTTYPENAME", "MARKETINGCATEGORYNAME"]