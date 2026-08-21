#!/usr/bin/env python3
"""Sustituye un fichero cualquiera del servidor MC (configs, datapacks). Se ejecuta EN star.

Mismo orden de operaciones que subir_jar.py --subir a un temporal, verificar el tamano, apartar
el viejo y solo entonces poner el nuevo-- pero admitiendo una ruta de destino completa en vez de
solo un nombre bajo plugins/. Sirve para editar un config sin dejarlo nunca a medias: si la
subida se corta, el fichero original sigue en su sitio intacto.

Uso:  subir_archivo.py <local-en-star> <ruta-destino> <sufijo-copia>
      la ruta admite los alias de mcfs, p.ej. @plugins/Slimefun/config.yml
"""
import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(1, "/tmp")
import mcfs  # noqa: E402

sftp = mcfs.sftp


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    local, destino, sufijo = sys.argv[1], mcfs.resolve(sys.argv[2]), sys.argv[3]
    temporal = destino + ".subiendo"

    esperado = os.path.getsize(local)
    sftp.put(local, temporal)
    llegado = sftp.stat(temporal).st_size
    if llegado != esperado:
        sftp.remove(temporal)
        print(f"ABORTADO: llegaron {llegado} bytes de {esperado}")
        return 1

    try:
        sftp.rename(destino, destino + "." + sufijo)
    except IOError as e:
        sftp.remove(temporal)
        print(f"ABORTADO: no se pudo apartar el viejo ({e})")
        return 1

    sftp.rename(temporal, destino)
    print(f"OK: {destino} ({llegado} bytes), copia en {destino}.{sufijo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
