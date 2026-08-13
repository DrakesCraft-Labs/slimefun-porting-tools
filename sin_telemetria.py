#!/usr/bin/env python3
"""Arranca de raiz la telemetria bStats de un addon.

POR QUE

bStats abre una conexion a bstats.org cada pocos minutos y le manda datos del servidor: version
del plugin, version de Java, sistema operativo, numero de jugadores y lo que cada addon haya
querido anadir. En DrakesCraft eso no lo decide el autor del addon.

No se sustituye por un stub inerte: eso dejaria el codigo de llamada en pie, aparentando que hay
telemetria y obligando a quien lea el fichero dentro de un ano a comprobar si de verdad sale algo
por ahi. Se quitan las llamadas, los imports y la dependencia, y despues se comprueba que en el
jar construido no queda ni una clase de org/bstats.

QUE TOCA

  - Los `new Metrics(...)`, con o sin asignacion.
  - Los `<algo>.addCustomChart(...)`, que pueden ocupar varias lineas.
  - Los imports de org.bstats.
  - La dependencia y la relocalizacion del shade, tanto en pom.xml como en build.gradle.

Lo que no pueda quitar de forma limpia lo dice y no lo toca. Un fichero cuya clase entera sea
telemetria (por ejemplo un HardcoreMetrics) hay que borrarlo a mano: esta herramienta no decide
eliminar ficheros.

Uso:  python3 sin_telemetria.py <carpeta-del-repo> [--escribir]
"""
import pathlib
import re
import sys

IMPORT_BSTATS = re.compile(r"^\s*import\s+org\.bstats\..*$")
# Reconoce tanto `new Metrics(this, 123);` como `Metrics m = new Metrics(this, 123);` y la forma
# de Kotlin `val m = Metrics(this, 123)`.
CREA_METRICS = re.compile(r"^\s*(?:(?:final\s+)?[\w.<>]+\s+\w+\s*=\s*)?new\s+Metrics\s*\(")
CREA_METRICS_KT = re.compile(r"^\s*(?:va[lr]\s+\w+\s*=\s*)?Metrics\s*\(")
LLAMA_CHART = re.compile(r"^\s*\w+\s*\.\s*addCustomChart\s*\(")


def _fin_de_sentencia(lineas, i):
    """Devuelve el indice de la ultima linea de la sentencia que empieza en i.

    Se cuentan parentesis en vez de buscar el `;`, porque un addCustomChart con una lambda dentro
    ocupa varias lineas y lleva puntos y comas por el medio.
    """
    profundidad = 0
    for j in range(i, len(lineas)):
        profundidad += lineas[j].count("(") - lineas[j].count(")")
        if profundidad <= 0 and j >= i:
            return j
    return i


def limpiar_fuente(texto, es_kotlin):
    lineas = texto.split("\n")
    fuera = set()
    crea = CREA_METRICS_KT if es_kotlin else CREA_METRICS

    for i, linea in enumerate(lineas):
        if i in fuera:
            continue
        if IMPORT_BSTATS.match(linea):
            fuera.add(i)
        elif crea.match(linea) or LLAMA_CHART.match(linea):
            for j in range(i, _fin_de_sentencia(lineas, i) + 1):
                fuera.add(j)

    if not fuera:
        return texto, 0
    return "\n".join(l for i, l in enumerate(lineas) if i not in fuera), len(fuera)


def limpiar_pom(texto):
    """Quita la dependencia de bstats y su relocalizacion del shade."""
    quitados = 0
    for etiqueta in ("dependency", "relocation"):
        salida, pos = [], 0
        while True:
            ini = texto.find(f"<{etiqueta}>", pos)
            if ini == -1:
                salida.append(texto[pos:])
                break
            fin = texto.find(f"</{etiqueta}>", ini)
            if fin == -1:
                salida.append(texto[pos:])
                break
            fin += len(f"</{etiqueta}>")
            if "bstats" in texto[ini:fin].lower():
                salida.append(texto[pos:ini])
                quitados += 1
            else:
                salida.append(texto[pos:fin])
            pos = fin
        texto = "".join(salida)
    return texto, quitados


def limpiar_gradle(texto):
    lineas = texto.split("\n")
    quedan = [l for l in lineas if "bstats" not in l.lower()]
    return "\n".join(quedan), len(lineas) - len(quedan)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    repo = pathlib.Path(sys.argv[1]).resolve()
    escribir = "--escribir" in sys.argv

    print(f"=== {repo.name} ===")
    if not escribir:
        print("  simulacion (usa --escribir)")

    total = 0
    for f in sorted(repo.rglob("*.java")) + sorted(repo.rglob("*.kt")):
        if "/target/" in str(f) or "/build/" in str(f):
            continue
        texto = f.read_text(encoding="utf-8", errors="replace")
        if "bstats" not in texto.lower() and "Metrics" not in texto:
            continue
        nuevo, n = limpiar_fuente(texto, f.suffix == ".kt")
        if n:
            total += n
            print(f"  {f.relative_to(repo)}: {n} lineas fuera")
            if escribir:
                f.write_text(nuevo, encoding="utf-8")
        # Si despues de limpiar sigue nombrando Metrics, es que hay algo que esta herramienta no
        # sabe deshacer sola (una clase entera de telemetria, un campo, una firma).
        if re.search(r"\bMetrics\b", nuevo if n else texto):
            print(f"  REVISAR A MANO -> {f.relative_to(repo)}")

    for nombre, limpiador in (("pom.xml", limpiar_pom),
                              ("build.gradle", limpiar_gradle),
                              ("build.gradle.kts", limpiar_gradle)):
        ruta = repo / nombre
        if not ruta.exists():
            continue
        texto = ruta.read_text(encoding="utf-8")
        nuevo, n = limpiador(texto)
        if n:
            total += n
            print(f"  {nombre}: {n} bloques/lineas fuera")
            if escribir:
                ruta.write_text(nuevo, encoding="utf-8")

    if total == 0:
        print("  sin telemetria que quitar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
