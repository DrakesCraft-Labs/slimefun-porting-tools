"""Puente SFTP al host de Minecraft. Se ejecuta EN star.

El servidor de MC vive en un host externo (Pterodactyl) al que solo se llega por SFTP. Este
modulo abre una unica conexion reutilizable: repetir el handshake en cada script es lo caro.

"@plugins" se traduce a la ruta real de plugins para no repetirla en cada script, y "./x" se
resuelve contra la raiz del servidor (donde viven logs/, world/, purpur.yml...).

Uso como modulo:  import mcfs; mcfs.sftp.open(mcfs.resolve("@plugins/x.jar"))
Uso por CLI:      mcfs.py <ls|cat|stat> <ruta>
"""
import sys
import posixpath

import paramiko


def _cargar_env(ruta="/opt/stacks/drakes-updater/.env"):
    datos = {}
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                clave, valor = linea.split("=", 1)
                datos[clave.strip()] = valor.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return datos


_env = _cargar_env()
HOST = _env.get("SFTP_HOST")
PORT = int(_env.get("SFTP_PORT", "2022"))
USER = _env.get("SFTP_USER")
PASS = _env.get("SFTP_PASS")
PLUGINS = _env.get("SFTP_PLUGINS_PATH", "/plugins")

_transporte = paramiko.Transport((HOST, PORT))
_transporte.connect(username=USER, password=PASS)
sftp = paramiko.SFTPClient.from_transport(_transporte)


def resolve(ruta):
    """@plugins -> ruta real; ./x -> relativo a la raiz del servidor; el resto, tal cual."""
    if ruta.startswith("@plugins"):
        return posixpath.normpath(PLUGINS + ruta[len("@plugins"):])
    raiz = posixpath.dirname(PLUGINS.rstrip("/"))
    if ruta.startswith("./"):
        return posixpath.normpath(raiz + "/" + ruta[2:])
    if ruta.startswith("/"):
        return posixpath.normpath(ruta)
    return posixpath.normpath(raiz + "/" + ruta)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("uso: mcfs.py <ls|cat|stat> <ruta>")
        sys.exit(1)
    accion, ruta = sys.argv[1], resolve(sys.argv[2])
    if accion == "ls":
        import stat as S
        for e in sorted(sftp.listdir_attr(ruta), key=lambda x: x.filename):
            print("%s %12d %s" % ("D" if S.S_ISDIR(e.st_mode) else "F", e.st_size, e.filename))
    elif accion == "cat":
        with sftp.open(ruta, "rb") as f:
            f.prefetch()
            sys.stdout.write(f.read().decode("utf-8", "replace"))
    elif accion == "stat":
        st = sftp.stat(ruta)
        print(st.st_size, st.st_mtime)
