#!/usr/bin/env python3
"""Sustituye un jar de plugin en el servidor MC. Se ejecuta EN star.

POR QUE ESTE ORDEN

Primero sube el jar nuevo con un nombre temporal y comprueba que llego entero. Solo entonces
aparta el viejo y pone el nuevo en su sitio. Asi el unico momento en que el plugin no tiene jar
son dos renombrados seguidos, en vez de todo el rato que dure una subida -- que es justo lo que
fallo antes y dejo cinco plugins sin jar.

Se usa sftp.put y no el put-b64 de mcfs porque aquel recibe el contenido como argumento de linea
de comandos, y un jar de megabyte y medio en base64 no cabe ahi.

Uso:  subir_jar.py <jar-local-en-star> <nombre-en-plugins> <sufijo-copia>
"""
import sys
import posixpath

sys.path.insert(0, "/tmp")
import mcfs  # noqa: E402

sftp = mcfs.sftp


def main():
    local, nombre, sufijo = sys.argv[1], sys.argv[2], sys.argv[3]
    destino = posixpath.join(mcfs.PLUGINS, nombre)
    temporal = destino + ".subiendo"

    esperado = __import__("os").path.getsize(local)
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
    print(f"OK: {nombre} ({llegado} bytes), copia en {nombre}.{sufijo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
