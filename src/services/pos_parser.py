"""Servicio de lectura, detección y normalización de archivos de ventas exportados desde sistemas POS."""

import io
import re
from typing import Dict, Optional, Tuple, Any, Union
from pathlib import Path
import pandas as pd
from src.config import POS_COLUMN_ALIASES, DAYS_OF_WEEK_ES


class POSParser:
    """Parser robusto para ingestar ventas desde POS chilenos (Toteat, Bsale, Fudo, Loyverse, etc.)."""

    def __init__(self):
        self.raw_df: Optional[pd.DataFrame] = None
        self.cleaned_df: Optional[pd.DataFrame] = None
        self.column_mapping: Dict[str, str] = {}

    @staticmethod
    def detect_encoding_and_delimiter(file_bytes: bytes) -> Tuple[str, str]:
        """Detecta automáticamente la codificación y el delimitador de un archivo CSV."""
        encodings_to_try = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
        sample_bytes = file_bytes[:8192]

        chosen_encoding = "utf-8"
        for enc in encodings_to_try:
            try:
                sample_text = sample_bytes.decode(enc)
                chosen_encoding = enc
                break
            except UnicodeDecodeError:
                continue

        # Detectar delimitador inspeccionando las primeras líneas
        sample_text = sample_bytes.decode(chosen_encoding, errors="ignore")
        lines = [line for line in sample_text.splitlines() if line.strip()][:5]
        if not lines:
            return chosen_encoding, ","

        delimiters = [",", ";", "\t", "|"]
        counts = {delim: sum(line.count(delim) for line in lines) for delim in delimiters}
        chosen_delimiter = max(counts, key=counts.get)
        if counts[chosen_delimiter] == 0:
            chosen_delimiter = ","

        return chosen_encoding, chosen_delimiter

    def auto_detect_columns(self, df_columns: list) -> Dict[str, Optional[str]]:
        """Busca coincidencias con los alias conocidos de sistemas POS."""
        mapping: Dict[str, Optional[str]] = {"fecha": None, "plato": None, "cantidad": None}

        cleaned_cols = {col: re.sub(r"[_\s\-]+", "", str(col).lower()) for col in df_columns}

        for canonical, aliases in POS_COLUMN_ALIASES.items():
            for col, clean_col in cleaned_cols.items():
                for alias in aliases:
                    clean_alias = re.sub(r"[_\s\-]+", "", alias.lower())
                    if clean_alias == clean_col or clean_alias in clean_col:
                        mapping[canonical] = col
                        break
                if mapping[canonical]:
                    break

        return mapping

    def load_from_bytes(
        self,
        file_bytes: bytes,
        custom_mapping: Optional[Dict[str, str]] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Lee bytes de un CSV, normaliza columnas y genera un DataFrame estandarizado."""
        encoding, delimiter = self.detect_encoding_and_delimiter(file_bytes)
        
        try:
            df = pd.read_csv(
                io.BytesIO(file_bytes),
                encoding=encoding,
                sep=delimiter,
                engine="python"
            )
        except Exception as e:
            # Fallback en caso de problemas con el delimitador detectado
            df = pd.read_csv(
                io.BytesIO(file_bytes),
                encoding="latin-1",
                sep=None,
                engine="python"
            )

        return self.process_dataframe(df, custom_mapping)

    def load_from_path(
        self,
        file_path: Union[str, Path],
        custom_mapping: Optional[Dict[str, str]] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Lee un CSV desde una ruta en disco."""
        path = Path(file_path)
        with open(path, "rb") as f:
            file_bytes = f.read()
        return self.load_from_bytes(file_bytes, custom_mapping)

    def process_dataframe(
        self,
        df: pd.DataFrame,
        custom_mapping: Optional[Dict[str, str]] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Limpia, valida y estandariza un DataFrame de ventas."""
        self.raw_df = df.copy()

        # Determinar mapeo de columnas
        mapping = self.auto_detect_columns(list(df.columns))
        if custom_mapping:
            mapping.update(custom_mapping)
        self.column_mapping = {k: v for k, v in mapping.items() if v is not None}

        # Validar que las 3 columnas requeridas existan
        missing = [k for k in ["fecha", "plato", "cantidad"] if k not in self.column_mapping]
        if missing:
            raise ValueError(
                f"No se pudieron identificar las siguientes columnas requeridas: {missing}. "
                f"Columnas disponibles en archivo: {list(df.columns)}"
            )

        col_fecha = self.column_mapping["fecha"]
        col_plato = self.column_mapping["plato"]
        col_cant = self.column_mapping["cantidad"]

        work_df = df[[col_fecha, col_plato, col_cant]].copy()
        work_df.columns = ["fecha_raw", "plato_raw", "cantidad_raw"]

        # 1. Limpieza de nombres de plato
        work_df["plato"] = (
            work_df["plato_raw"]
            .astype(str)
            .str.strip()
            .str.title()
        )
        work_df = work_df[work_df["plato"] != ""]

        # 2. Limpieza y parseo de fechas (formato chileno con dayfirst=True)
        work_df["fecha"] = pd.to_datetime(
            work_df["fecha_raw"],
            format="mixed",
            dayfirst=True,
            errors="coerce"
        )
        # Descartar filas con fechas no válidas
        work_df = work_df.dropna(subset=["fecha"]).copy()
        work_df["fecha"] = work_df["fecha"].dt.date

        # 3. Limpieza de cantidad vendida
        def parse_qty(val: Any) -> float:
            if pd.isna(val):
                return 0.0
            if isinstance(val, (int, float)):
                return float(val)
            s = str(val).strip().replace(" ", "")
            # Manejar formato numérico chileno: punto para miles, coma para decimal
            if "," in s and "." in s:
                s = s.replace(".", "").replace(",", ".")
            elif "," in s:
                s = s.replace(",", ".")
            try:
                return float(s)
            except ValueError:
                return 0.0

        work_df["cantidad"] = work_df["cantidad_raw"].apply(parse_qty)
        work_df = work_df[work_df["cantidad"] > 0].copy()

        # 4. Asignación de días de la semana
        work_df["dia_semana_num"] = pd.to_datetime(work_df["fecha"]).dt.dayofweek
        work_df["dia_semana_nombre"] = work_df["dia_semana_num"].map(DAYS_OF_WEEK_ES)

        # 5. Agrupación por si un plato se vendió en múltiples boletas el mismo día
        aggregated = (
            work_df.groupby(["fecha", "plato", "dia_semana_num", "dia_semana_nombre"], as_index=False)["cantidad"]
            .sum()
            .sort_values(by=["fecha", "plato"])
            .reset_index(drop=True)
        )

        self.cleaned_df = aggregated

        # Metadatos del archivo procesado
        summary = {
            "total_filas_originales": len(df),
            "total_registros_validos": len(aggregated),
            "platos_unicos": int(aggregated["plato"].nunique()),
            "fecha_inicio": aggregated["fecha"].min() if not aggregated.empty else None,
            "fecha_fin": aggregated["fecha"].max() if not aggregated.empty else None,
            "total_unidades_vendidas": float(aggregated["cantidad"].sum()),
            "dias_totales": int(aggregated["fecha"].nunique())
        }

        return aggregated, summary
