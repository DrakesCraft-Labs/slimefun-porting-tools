#!/usr/bin/env python3
"""Comprueba que una respuesta de ChatGames se pueda acertar de verdad.

ChatGames v1.4.5 admite **una sola respuesta** por pregunta y la compara asi:

    entrada.toLowerCase()  ->  contains(opciones)

Sin quitar acentos y sin recortar espacios. Eso convierte en imposibles respuestas que parecen
razonables:

  - "Via Lactea"            el jugador escribe "Vía Láctea" y falla
  - "Pickaxe of Distortion" hay que clavar tres palabras en ingles, sin erratas
  - "Cordillera de los Andes"  lo mismo, en 23 caracteres

Este validador se ejecuta sobre los cinco archivos antes de subirlos. Verificado leyendo el
bytecode de GameConfig y GameManager, no suponiendolo.
"""
import re
import sys
import unicodedata

MAX_PALABRAS = 2          # mas de dos palabras y casi nadie lo clava a tiempo
MAX_LARGO = 22


def tiene_acento(texto):
    return any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", texto))


def problemas(pregunta, respuesta):
    """Lista de motivos por los que esta respuesta seria injusta. Vacia = correcta."""
    fallos = []
    limpia = str(respuesta)

    if limpia != limpia.strip():
        fallos.append("espacios sobrantes: el plugin no hace trim")
    if tiene_acento(limpia):
        fallos.append("lleva tilde: el plugin no normaliza y el jugador la escribira con tilde")
    if len(limpia) > MAX_LARGO:
        fallos.append(f"demasiado larga ({len(limpia)} caracteres)")

    palabras = limpia.split()
    if len(palabras) > MAX_PALABRAS:
        fallos.append(f"{len(palabras)} palabras: hay que clavarlas todas sin erratas")

    # Si la respuesta tiene mas de una palabra o no es obvia, la pregunta deberia decir el formato.
    sin_formato = not re.search(r"\(.*(palabra|responde|solo|numero|sin tildes|comando).*\)",
                                pregunta, re.I)
    if len(palabras) == MAX_PALABRAS and sin_formato:
        fallos.append("dos palabras y la pregunta no avisa del formato esperado")

    return fallos


def revisar(ruta, datos):
    """Devuelve una lista de (pregunta, respuesta, fallos)."""
    malas = []
    preguntas = datos.get("questions") or []
    # Trivia y math traen [pregunta, respuesta]; multiple-choice trae un mapa con opciones, y ahi
    # solo se responde una letra, asi que nada de esto le aplica.
    if isinstance(preguntas, dict):
        for clave, bloque in preguntas.items():
            letra = str(bloque.get("correct-answer", ""))
            opciones = bloque.get("answers") or []
            if len(letra) != 1 or not opciones:
                malas.append((clave, letra, ["la respuesta correcta deberia ser una sola letra"]))
            elif not any(str(o).upper().startswith(letra.upper()) for o in opciones):
                malas.append((clave, letra, [f"la letra {letra} no coincide con ninguna opcion"]))
        return malas

    for pregunta, respuesta in preguntas:
        fallos = problemas(str(pregunta), str(respuesta))
        if fallos:
            malas.append((re.sub(r"<[^>]+>", "", str(pregunta))[:60], respuesta, fallos))
    for palabra in (datos.get("words") or []):
        if tiene_acento(palabra) or " " in palabra:
            malas.append((f"[unscramble] {palabra}", palabra, ["tilde o espacio en la palabra"]))
    for variante in (datos.get("variants") or []):
        respuesta = str(variante.get("answer", ""))
        if tiene_acento(respuesta):
            malas.append((variante.get("name", "?"), respuesta, ["tilde en la respuesta"]))
    return malas


if __name__ == "__main__":
    import yaml
    total = 0
    for ruta in sys.argv[1:]:
        with open(ruta, encoding="utf-8") as fichero:
            datos = yaml.safe_load(fichero)
        malas = revisar(ruta, datos)
        cuantas = (len(datos.get("questions") or []) + len(datos.get("words") or [])
                   + len(datos.get("variants") or []) + len(datos.get("questions-mc") or []))
        estado = "OK" if not malas else f"{len(malas)} PROBLEMAS"
        print(f"{ruta.split('/')[-1]:<22} {cuantas:>4} elementos   {estado}")
        for pregunta, respuesta, fallos in malas:
            print(f"      resp={respuesta!r}  {pregunta}")
            for fallo in fallos:
                print(f"         · {fallo}")
        total += len(malas)
    sys.exit(1 if total else 0)
