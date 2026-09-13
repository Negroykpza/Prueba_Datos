"""Servicio de lectura, detección y normalización de archivos de ventas exportados desde sistemas POS."""

import io
import re
from typing import Dict, Optional, Tuple, Any, Union, List
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
        except Exception:
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

    def parse_csv(
        self,
        file_source: Any,
        custom_mapping: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        Lee y procesa un archivo CSV desde un Streamlit UploadedFile, bytes, o ruta de archivo.
        Retorna el DataFrame normalizado.
        """
        if hasattr(file_source, "getvalue"):
            file_bytes = file_source.getvalue()
        elif isinstance(file_source, bytes):
            file_bytes = file_source
        elif hasattr(file_source, "read"):
            file_bytes = file_source.read()
        elif isinstance(file_source, (str, Path)):
            with open(file_source, "rb") as f:
                file_bytes = f.read()
        else:
            raise TypeError(f"Tipo de origen no soportado para parse_csv: {type(file_source)}")

        df, _ = self.load_from_bytes(file_bytes, custom_mapping)
        return df

    def load_demo_data(self) -> pd.DataFrame:
        """
        Carga el conjunto de datos de demostración de 90 días de ventas POS.
        Busca en disco (data/sample_pos_sales.csv o data/ventas_pos_90dias.csv)
        y si no existe, genera una muestra sintética en memoria.
        """
        possible_paths = [
            Path("data/sample_pos_sales.csv"),
            Path(__file__).resolve().parent.parent.parent / "data" / "sample_pos_sales.csv",
            Path("data/ventas_pos_90dias.csv"),
            Path(__file__).resolve().parent.parent.parent / "data" / "ventas_pos_90dias.csv",
        ]

        for p in possible_paths:
            if p.exists() and p.is_file():
                try:
                    df, _ = self.load_from_path(p)
                    if not df.empty:
                        return df
                except Exception:
                    continue

        return self._generate_synthetic_demo_data()

    def _generate_synthetic_demo_data(self) -> pd.DataFrame:
        """Genera 90 días de ventas sintéticas para restaurantes chilenos en caso de que no exista el archivo en disco."""
        import random
        from datetime import date, timedelta

        end_date = date.today()
        start_date = end_date - timedelta(days=90)

        dishes = [
            ("Ceviche Mixto", 18, 35),
            ("Ceviche Clásico", 15, 30),
            ("Lomo Saltado", 16, 32),
            ("Pastel de Choclo", 12, 28),
            ("Salmón Grillé", 10, 22),
            ("Tartar de Atún", 8, 18),
            ("Empanada de Pino", 25, 55),
            ("Machas a la Parmesana", 12, 28),
            ("Cazuela de Vacuno", 10, 22)
        ]

        rows = []
        cur = start_date
        # Semilla fija para reproducibilidad
        rng = random.Random(42)
        while cur <= end_date:
            is_weekend = cur.weekday() in [4, 5, 6]  # Viernes, Sábado, Domingo
            multiplier = 1.5 if is_weekend else 1.0
            for dish, base_min, base_max in dishes:
                qty = int(rng.randint(base_min, base_max) * multiplier)
                rows.append({
                    "Fecha": cur.strftime("%d/%m/%Y"),
                    "Plato": dish,
                    "Cantidad": qty
                })
            cur += timedelta(days=1)

        raw_df = pd.DataFrame(rows)
        df, _ = self.process_dataframe(raw_df)
        return df

    def extract_unique_dishes(self, df: Optional[pd.DataFrame] = None) -> List[str]:
        """Extrae la lista ordenada de nombres únicos de platos de un DataFrame de ventas."""
        target_df = df if df is not None else self.cleaned_df
        if target_df is None or target_df.empty or "plato" not in target_df.columns:
            return []
        return sorted(target_df["plato"].dropna().astype(str).unique().tolist())

    def get_summary(self, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Calcula métricas estadísticas y de diagnóstico a partir del DataFrame de ventas."""
        target_df = df if df is not None else self.cleaned_df
        if target_df is None or target_df.empty:
            return {
                "total_unidades": 0,
                "total_platos": 0,
                "dias_totales": 0,
                "pct_fin_semana": 0.0,
                "rango_fechas": "N/A",
                "fecha_inicio": None,
                "fecha_fin": None,
                "total_unidades_vendidas": 0.0,
                "platos_unicos": 0,
                "promedio_diario": 0.0
            }

        total_unidades = float(target_df["cantidad"].sum())
        total_platos = int(target_df["plato"].nunique())
        dias_totales = int(target_df["fecha"].nunique())

        # Cálculo de ventas en fin de semana (Viernes=4, Sábado=5, Domingo=6)
        if "dia_semana_num" in target_df.columns:
            weekend_mask = target_df["dia_semana_num"].isin([4, 5, 6])
        else:
            weekend_mask = pd.to_datetime(target_df["fecha"]).dt.dayofweek.isin([4, 5, 6])

        weekend_unidades = float(target_df[weekend_mask]["cantidad"].sum())
        pct_fin_semana = (weekend_unidades / total_unidades * 100.0) if total_unidades > 0 else 0.0

        min_fecha = target_df["fecha"].min()
        max_fecha = target_df["fecha"].max()
        rango_str = f"{min_fecha.strftime('%d/%m/%Y')} - {max_fecha.strftime('%d/%m/%Y')}" if hasattr(min_fecha, "strftime") else f"{min_fecha} - {max_fecha}"
        promedio_diario = round(total_unidades / dias_totales, 1) if dias_totales > 0 else 0.0

        return {
            "total_unidades": int(total_unidades),
            "total_platos": total_platos,
            "dias_totales": dias_totales,
            "pct_fin_semana": round(pct_fin_semana, 1),
            "rango_fechas": rango_str,
            "fecha_inicio": min_fecha,
            "fecha_fin": max_fecha,
            "total_unidades_vendidas": total_unidades,
            "platos_unicos": total_platos,
            "promedio_diario": promedio_diario
        }

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
        summary = self.get_summary(aggregated)
        summary["total_filas_originales"] = len(df)
        summary["total_registros_validos"] = len(aggregated)

        return aggregated, summary
