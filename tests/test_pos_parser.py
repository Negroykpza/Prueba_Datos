"""Pruebas unitarias para el servicio de ingesta y normalización de POS."""

import unittest
from datetime import date
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


if __name__ == "__main__":
    unittest.main()
