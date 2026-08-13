#!/usr/bin/env python3
"""Comprueba que el ultimo arranque de DrakesCraft salio limpio. Se ejecuta EN star.

POR QUE NO VALE MIRAR "Done ("

El latest.log acumula todos los arranques del dia. Buscar `Done (` a secas encuentra el del
arranque ANTERIOR y hace creer que todo fue bien aunque el de ahora se haya quedado a medias. Por
eso aqui se corta el fichero desde la ultima linea `Starting minecraft server version` y solo se
mira lo que hay a partir de ahi.

QUE INFORMA
  - Si el arranque termino (linea Done).
  - Plugins que fallaron al cargar o al activarse.
  - Excepciones durante el arranque, agrupadas por tipo.
  - Cuantos plugins cargaron, para comparar con lo esperado.
"""
import re
import sys
from collections import Counter

sys.path.insert(0, "/tmp")
import mcfs  # noqa: E402

RUTA = "./logs/latest.log"
# Cuanto leer del final. Un arranque completo de DrakesCraft ocupa bastante, y ademas el log puede
# venir inflado por errores repetidos, asi que se lee generoso.
BYTES = 12 << 20


def main():
    ruta = mcfs.resolve(RUTA)
    with mcfs.sftp.open(ruta, "rb") as f:
        f.prefetch()
        f.seek(0, 2)
        total = f.tell()
        f.seek(max(0, total - BYTES))
        texto = f.read().decode("utf-8", "replace")

    marcas = [m.start() for m in re.finditer(r"Starting minecraft server version", texto)]
    if not marcas:
        print("  no se ve ningun arranque en lo leido (¿log enorme o servidor sin reiniciar?)")
        return 2
    arranque = texto[marcas[-1]:]
    print(f"  log total: {total/1e6:.1f} MB · analizando el ultimo arranque ({len(arranque)/1e6:.1f} MB)")

    done = re.search(r'Done \(([^)]+)\)', arranque)
    print(f"  arranque terminado: {'SI, en ' + done.group(1) if done else 'NO (o aun en curso)'}")

    cargados = len(re.findall(r"\] Loading server plugin ", arranque))
    activados = len(re.findall(r"\] Enabling ", arranque))
    print(f"  plugins cargados: {cargados} · activados: {activados}")

    fallos = re.findall(r"Could not load '([^']+)'|Error occurred while enabling ([^\s]+)|"
                        r"\[([^\]]+)\] Loading server plugin .*\n.*Exception", arranque)
    fallos = [a or b or c for a, b, c in fallos]
    print(f"\n  === plugins que fallaron: {len(fallos)} ===")
    for x in dict.fromkeys(fallos):
        print(f"    >>> {x}")
    if not fallos:
        print("    ninguno")

    excepciones = Counter(re.findall(r"([A-Za-z.]*(?:Exception|Error))(?::|\s)", arranque))
    # Ruido normal de arranque que no indica un problema real.
    for benigno in ("NoSuchFieldException",):
        excepciones.pop(benigno, None)
    print(f"\n  === excepciones durante el arranque ===")
    if excepciones:
        for e, n in excepciones.most_common(10):
            print(f"    {n:>5}x  {e}")
    else:
        print("    ninguna")

    return 0 if (done and not fallos) else 1


if __name__ == "__main__":
    sys.exit(main())
