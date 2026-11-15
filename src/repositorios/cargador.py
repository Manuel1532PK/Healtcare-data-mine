import pandas as pd


class CargadorDataset:
    """Carga un CSV con codificacion robusta (utf-8 -> cp1252 -> latin-1)."""

    def __init__(self, archivo, encoding=None):
        self.archivo = archivo
        self.encoding = encoding

    def cargar(self):
        if self.encoding:
            return pd.read_csv(self.archivo, encoding=self.encoding)
        # intento robusto
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                return pd.read_csv(self.archivo, encoding=enc)
            except UnicodeDecodeError:
                continue
        return pd.read_csv(self.archivo)