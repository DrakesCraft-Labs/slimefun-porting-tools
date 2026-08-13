#!/usr/bin/env python3
"""Lee solo el final de un fichero remoto por SFTP. Se ejecuta EN star.

El latest.log del servidor pasa de 90 MB y el `cat` de mcfs lo trae entero, lo que agota
cualquier tiempo de espera. Aqui se salta al final y se leen los ultimos N bytes.

Uso:  cola_log.py <ruta> [bytes]
"""
import sys

sys.path.insert(0, "/tmp")
import mcfs  # noqa: E402


def main():
    ruta = mcfs.resolve(sys.argv[1])
    cuantos = int(sys.argv[2]) if len(sys.argv) > 2 else 400_000
    with mcfs.sftp.open(ruta, "rb") as f:
        f.seek(0, 2)
        total = f.tell()
        f.seek(max(0, total - cuantos))
        sys.stdout.write(f.read().decode("utf-8", "replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
