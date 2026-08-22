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

    # Las cantidades operativas cambian con el servidor y convierten preguntas correctas hoy
    # en respuestas falsas mañana. Ya ocurrió al pasar DrakesCraft de 3 a 5 modalidades.
    if re.search(r"cu[aá]ntas?\s+modalidades", pregunta, re.I):
        fallos.append("pregunta volatil: no fijar en trivia la cantidad de modalidades")

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
    sin_formato = not re.search(
        r"comando|\(.*(palabra|responde|solo|numero|sin tildes).*\)", pregunta, re.I
    )
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

    for entrada in preguntas:
        if not isinstance(entrada, list) or len(entrada) < 2:
            malas.append((str(entrada)[:60], "", ["cada pregunta necesita texto y al menos una respuesta"]))
            continue
        pregunta, *respuestas = entrada
        evaluadas = [(respuesta, problemas(str(pregunta), str(respuesta))) for respuesta in respuestas]
        # Las variantes adicionales son alias permisivos: basta una respuesta breve y fiable.
        # Solo se rechaza la pregunta cuando ninguna de sus respuestas es razonable.
        if all(fallos for _, fallos in evaluadas):
            respuesta, fallos = min(evaluadas, key=lambda evaluada: len(evaluada[1]))
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
        try:
            with open(ruta, encoding="utf-8") as fichero:
                datos = yaml.safe_load(fichero)
            if not isinstance(datos, dict):
                raise ValueError("la raíz YAML debe ser un mapa")
            malas = revisar(ruta, datos)
        except (OSError, ValueError, yaml.YAMLError) as error:
            print(f"{ruta.split('/')[-1]:<22} ERROR: {type(error).__name__}: {error}")
            total += 1
            continue
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
