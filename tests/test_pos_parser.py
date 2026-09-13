"""Pruebas unitarias para el servicio de ingesta y normalización de POS."""

import unittest
from datetime import date
import pandas as pd
from src.services.pos_parser import POSParser


class TestPOSParser(unittest.TestCase):

    def setUp(self):
        self.parser = POSParser()

    def test_delimiter_and_encoding_detection(self):
        csv_semicolon = "fecha;producto;cantidad\n01/08/2026;Ceviche Clásico;10\n02/08/2026;Lomo Saltado;15\n".encode("utf-8")
        encoding, delimiter = self.parser.detect_encoding_and_delimiter(csv_semicolon)
        self.assertEqual(delimiter, ";")
        self.assertIn("utf-8", encoding.lower())

    def test_parse_csv_with_chilean_dates_and_aliases(self):
        csv_content = (
            "Fecha Venta,Item Name,Cant Vendida\n"
            "05/08/2026,Ceviche Mixto,12\n"
            "05/08/2026,ceviche mixto,8\n"
            "06/08/2026,Lomo Saltado,14\n"
        ).encode("utf-8")

        df, summary = self.parser.load_from_bytes(csv_content)

        # Debe agrupar los 2 ceviches mixtos del mismo día (12 + 8 = 20)
        self.assertEqual(len(df), 2)
        ceviche_row = df[df["plato"] == "Ceviche Mixto"].iloc[0]
        self.assertEqual(ceviche_row["cantidad"], 20.0)
        self.assertEqual(ceviche_row["fecha"], date(2026, 8, 5))
        self.assertEqual(summary["total_unidades_vendidas"], 34.0)

    def test_invalid_rows_handling(self):
        csv_with_errors = (
            "fecha,plato,cantidad\n"
            "invalid_date,Ceviche,10\n"
            "10/08/2026,,15\n"
            "11/08/2026,Pastel Choclo,-5\n"
            "12/08/2026,Salmón Grillé,8\n"
        ).encode("utf-8")

        df, summary = self.parser.load_from_bytes(csv_with_errors)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["plato"], "Salmón Grillé")
        self.assertEqual(df.iloc[0]["cantidad"], 8.0)

    def test_load_demo_data(self):
        df = self.parser.load_demo_data()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertIn("fecha", df.columns)
        self.assertIn("plato", df.columns)
        self.assertIn("cantidad", df.columns)
        self.assertGreater(len(df), 50)

    def test_parse_csv(self):
        csv_bytes = b"Fecha,Plato,Cantidad\n01/08/2026,Ceviche Mixto,10\n"
        df = self.parser.parse_csv(csv_bytes)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["plato"], "Ceviche Mixto")

    def test_extract_unique_dishes(self):
        df = pd.DataFrame([
            {"plato": "Lomo Saltado", "cantidad": 5},
            {"plato": "Ceviche Mixto", "cantidad": 3},
            {"plato": "Lomo Saltado", "cantidad": 2}
        ])
        dishes = self.parser.extract_unique_dishes(df)
        self.assertEqual(dishes, ["Ceviche Mixto", "Lomo Saltado"])

    def test_get_summary(self):
        df = pd.DataFrame([
            {"fecha": date(2026, 8, 1), "plato": "Ceviche Mixto", "cantidad": 10.0, "dia_semana_num": 5},
            {"fecha": date(2026, 8, 2), "plato": "Lomo Saltado", "cantidad": 20.0, "dia_semana_num": 6},
        ])
        summary = self.parser.get_summary(df)
        self.assertEqual(summary["total_unidades"], 30)
        self.assertEqual(summary["total_platos"], 2)
        self.assertEqual(summary["dias_totales"], 2)
        self.assertEqual(summary["pct_fin_semana"], 100.0)


if __name__ == "__main__":
    unittest.main()
