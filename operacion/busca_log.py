#!/usr/bin/env python3
"""Busca un patron en un log remoto grande, leyendo por trozos. Se ejecuta EN star.

El latest.log pasa de 90 MB: traerselo entero para hacerle grep agota el tiempo de espera y
gasta la red sin necesidad. Aqui se lee en bloques y se filtra en el propio star.

Uso:  busca_log.py <ruta> <patron> [max-resultados]
"""
import re
import sys

sys.path.insert(0, "/tmp")
import mcfs  # noqa: E402


def main():
    ruta = mcfs.resolve(sys.argv[1])
    patron = re.compile(sys.argv[2], re.IGNORECASE)
    tope = int(sys.argv[3]) if len(sys.argv) > 3 else 60

    encontrados = 0
    resto = b""
    with mcfs.sftp.open(ruta, "rb") as f:
        f.prefetch()
        while True:
            trozo = f.read(4 << 20)
            if not trozo:
                break
            lineas = (resto + trozo).split(b"\n")
            resto = lineas.pop()
            for l in lineas:
                t = l.decode("utf-8", "replace")
                if patron.search(t):
                    print(t[:300])
                    encontrados += 1
                    if encontrados >= tope:
                        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
