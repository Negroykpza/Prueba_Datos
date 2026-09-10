"""Motor de proyección de demanda basado en promedios por día de la semana con margen de seguridad del 15%."""

from datetime import date, timedelta
from typing import Optional, Dict, Tuple, List
import pandas as pd
import numpy as np
from src.config import (
    DEFAULT_SAFETY_MARGIN,
    FORECAST_DAYS_HORIZON,
    DAYS_OF_WEEK_ES,
    WEEKEND_DAY_INDICES
)
from src.models.schema import DishForecast


class ForecastingEngine:
    """Calcula la demanda futura esperada de platos a partir de patrones históricos por día de la semana."""

    def __init__(self, safety_margin: float = DEFAULT_SAFETY_MARGIN):
        self.safety_margin = safety_margin

    def calculate_day_of_week_profiles(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula el promedio representativo por día de la semana para cada plato.
        Considera el total de fechas históricas registradas para cada día de la semana,
        asegurando que días sin venta se ponderen correctamente.
        """
        if sales_df.empty:
            return pd.DataFrame()

        df = sales_df.copy()
        df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
        df["dia_semana_num"] = pd.to_datetime(df["fecha"]).dt.dayofweek

        # Total de fechas distintas registradas por día de la semana en la historia
        dates_per_dow = (
            df.groupby("dia_semana_num")["fecha"]
            .nunique()
            .to_dict()
        )

        # Suma total de unidades vendidas por plato y día de la semana
        totals = (
            df.groupby(["plato", "dia_semana_num"], as_index=False)["cantidad"]
            .sum()
        )

        # Promedio = Total de unidades / Cantidad de veces que ocurrió ese día de la semana
        totals["total_dias_historicos"] = totals["dia_semana_num"].map(dates_per_dow).fillna(1)
        totals["promedio_diario"] = totals["cantidad"] / totals["total_dias_historicos"]
        totals["dia_semana_nombre"] = totals["dia_semana_num"].map(DAYS_OF_WEEK_ES)

        return totals

    def project_next_days(
        self,
        sales_df: pd.DataFrame,
        start_date: Optional[date] = None,
        days_horizon: int = FORECAST_DAYS_HORIZON,
        safety_margin: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Proyecta la demanda de los próximos N días a partir de la fecha de inicio.
        Aplica: Demanda Proyectada = Promedio(Día de Semana) * (1 + Margen de Seguridad).
        """
        if sales_df.empty:
            return pd.DataFrame()

        margin = safety_margin if safety_margin is not None else self.safety_margin

        # Determinar fecha de inicio: día posterior a la última venta si no se indica
        if start_date is None:
            max_date = pd.to_datetime(sales_df["fecha"]).dt.date.max()
            start_date = max_date + timedelta(days=1)

        # Perfiles históricos por día de la semana
        dow_profiles = self.calculate_day_of_week_profiles(sales_df)
        if dow_profiles.empty:
            return pd.DataFrame()

        # Diccionario rápido: (plato, dia_semana_num) -> promedio
        profile_map = {
            (row["plato"], row["dia_semana_num"]): row["promedio_diario"]
            for _, row in dow_profiles.iterrows()
        }

        unique_dishes = sorted(sales_df["plato"].unique())
        projections: List[Dict] = []

        for offset in range(days_horizon):
            current_date = start_date + timedelta(days=offset)
            dow_num = current_date.weekday()
            dow_name = DAYS_OF_WEEK_ES.get(dow_num, "")
            is_weekend = dow_num in WEEKEND_DAY_INDICES

            for dish in unique_dishes:
                base_demand = profile_map.get((dish, dow_num), 0.0)
                safety_buffer = base_demand * margin
                demand_with_margin = base_demand + safety_buffer

                projections.append({
                    "fecha": current_date,
                    "dia_semana_num": dow_num,
                    "dia_semana_nombre": dow_name,
                    "es_fin_de_semana": is_weekend,
                    "plato": dish,
                    "demanda_base": round(base_demand, 2),
                    "margen_seguridad_pct": round(margin * 100, 1),
                    "margen_seguridad_unidades": round(safety_buffer, 2),
                    "demanda_con_margen": round(demand_with_margin, 2)
                })

        proj_df = pd.DataFrame(projections)
        return proj_df

    def get_summary_by_dish(
        self,
        forecast_df: pd.DataFrame,
        only_weekend: bool = False
    ) -> pd.DataFrame:
        """Agrega la demanda proyectada por plato en el horizonte seleccionado."""
        if forecast_df.empty:
            return pd.DataFrame()

        df = forecast_df.copy()
        if only_weekend:
            df = df[df["es_fin_de_semana"]].copy()

        summary = (
            df.groupby("plato", as_index=False)
            .agg({
                "demanda_base": "sum",
                "margen_seguridad_unidades": "sum",
                "demanda_con_margen": "sum"
            })
            .sort_values(by="demanda_con_margen", ascending=False)
            .reset_index(drop=True)
        )

        summary["demanda_base"] = summary["demanda_base"].round(1)
        summary["margen_seguridad_unidades"] = summary["margen_seguridad_unidades"].round(1)
        summary["demanda_con_margen"] = summary["demanda_con_margen"].round(1)

        return summary
