#!/usr/bin/env python3
"""Regresion del validador de ChatGames.

El caso que motiva estas pruebas: siete variantes de reaction.yml se respondian con un comando
("/sellinv", "/pv", "/sf guide"...). PaperChatListener solo escucha AsyncChatEvent, que no
dispara para un mensaje con barra, asi que esas rondas eran imposibles de ganar y el validador
las dejaba pasar porque a las variantes solo les miraba las tildes.
"""
import unittest

from validar_chatgames import es_comando, problemas, revisar


class RespuestaConBarra(unittest.TestCase):
    def test_es_comando_detecta_barra_inicial(self):
        for respuesta in ("/pv", "/sf guide", "  /bank"):
            self.assertTrue(es_comando(respuesta), respuesta)

    def test_es_comando_no_marca_respuestas_normales(self):
        for respuesta in ("pv", "sf guide", "DRAGMAS", "777", ""):
            self.assertFalse(es_comando(respuesta), respuesta)

    def test_pregunta_con_respuesta_de_comando_se_rechaza(self):
        fallos = problemas("Escribe el comando de la guia (comando)", "/sf guide")
        self.assertTrue(any("empieza por" in fallo for fallo in fallos), fallos)

    def test_variante_con_barra_se_rechaza(self):
        malas = revisar("reaction.yml", {"variants": [{"name": "Comando Tienda", "answer": "/sellinv"}]})
        self.assertEqual(len(malas), 1)
        self.assertIn("empieza por", malas[0][2][0])

    def test_variante_sin_barra_pasa(self):
        variantes = [
            {"name": "Comando Tienda", "answer": "shop"},
            {"name": "Comando de guia SF", "answer": "sf guide"},
            {"name": "Click de Hermes", "answer": "CLICK"},
            {"name": "Desafio de Reaccion", "answer": ""},
            {"name": "Velocidad TPS", "answer": "20 TPS SOLIDOS"},
        ]
        self.assertEqual(revisar("reaction.yml", {"variants": variantes}), [])

    def test_variante_con_tilde_sigue_rechazandose(self):
        malas = revisar("reaction.yml", {"variants": [{"name": "Runa", "answer": "Vía Láctea"}]})
        self.assertEqual(len(malas), 1)
        self.assertIn("tilde", malas[0][2][0])


if __name__ == "__main__":
    unittest.main()
