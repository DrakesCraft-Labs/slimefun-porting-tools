#!/usr/bin/env python3
"""Revisa los plugins desplegados ANTES de reiniciar. Se ejecuta EN star.

POR QUE

Un reinicio de DrakesCraft carga ~140 jars. Si dos declaran el mismo `name`, Bukkit carga uno y
descarta el otro sin mas aviso que una linea perdida entre miles. Si uno declara un `depend` que
no esta, no arranca. Las dos cosas se ven despues, cuando un jugador dice que algo no funciona.

Comprobarlo antes cuesta segundos y evita la ronda de reinicio-arreglo-reinicio.

QUE MIRA
  - Nombres de plugin duplicados entre jars distintos.
  - Dependencias declaradas (`depend`) que no corresponden a ningun plugin presente.
  - Jars corruptos o sin plugin.yml.
"""
import io
import re
import sys
import zipfile
from collections import defaultdict

sys.path.insert(0, "/tmp")
import mcfs  # noqa: E402


def leer_plugin_yml(datos):
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        for nombre in ("plugin.yml", "paper-plugin.yml"):
            if nombre in z.namelist():
                return z.read(nombre).decode("utf-8", "replace")
    return None


def campo(texto, clave):
    m = re.search(rf"^{clave}:\s*(.+)$", texto, re.M)
    return m.group(1).strip().strip('"\'') if m else None


def lista(texto, clave):
    """Lee `clave: [a, b]` y tambien la forma en varias lineas con guiones."""
    m = re.search(rf"^{clave}:\s*\[(.*?)\]", texto, re.M | re.S)
    if m:
        return [x.strip().strip('"\'') for x in m.group(1).split(",") if x.strip()]
    m = re.search(rf"^{clave}:\s*\n((?:\s*-\s*.+\n?)+)", texto, re.M)
    if m:
        return [l.strip().lstrip("-").strip().strip('"\'') for l in m.group(1).strip().split("\n")]
    return []


def main():
    ruta = mcfs.PLUGINS
    jars = [a.filename for a in mcfs.sftp.listdir_attr(ruta)
            if a.filename.lower().endswith(".jar")]

    nombres = defaultdict(list)
    provistos = set()
    sin_main = []
    depende_de = {}
    rotos = []

    for j in sorted(jars):
        try:
            with mcfs.sftp.open(f"{ruta}/{j}", "rb") as f:
                f.prefetch()
                datos = f.read()
            yml = leer_plugin_yml(datos)
        except Exception as e:
            rotos.append((j, str(e)[:60])); continue
        if yml is None:
            rotos.append((j, "sin plugin.yml")); continue
        n = campo(yml, "name")
        if not n:
            rotos.append((j, "plugin.yml sin name")); continue
        # La clase principal tiene que existir DENTRO del jar. Si el remapeo toco el paquete
        # propio del addon pero no el plugin.yml, el jar compila igual y falla al arrancar con
        # "Cannot find main class". Es barato comprobarlo aqui y carisimo descubrirlo despues.
        principal = campo(yml, "main")
        if principal:
            ruta_clase = principal.replace(".", "/") + ".class"
            with zipfile.ZipFile(io.BytesIO(datos)) as z:
                if ruta_clase not in z.namelist():
                    sin_main.append((j, principal))

        nombres[n].append(j)
        depende_de[n] = lista(yml, "depend")
        # `provides` declara que este jar cubre el nombre de otro plugin. FastAsyncWorldEdit lo
        # usa para satisfacer a quien pida WorldEdit; sin mirarlo, el aviso es un falso positivo.
        for alias in lista(yml, "provides"):
            provistos.add(alias)

    print(f"  jars revisados: {len(jars)}")

    dup = {n: v for n, v in nombres.items() if len(v) > 1}
    print(f"\n  === nombres duplicados: {len(dup)} ===")
    for n, v in dup.items():
        print(f"    >>> {n}")
        for x in v:
            print(f"          {x}")

    presentes = set(nombres) | provistos
    print(f"\n  === dependencias que faltan ===")
    faltan = 0
    for n, deps in depende_de.items():
        for d in deps:
            if d and d not in presentes:
                print(f"    >>> {n} necesita '{d}', que no esta")
                faltan += 1
    if not faltan:
        print("    ninguna")

    print(f"\n  === clase principal ausente: {len(sin_main)} ===")
    for j, m in sin_main:
        print(f"    >>> {j}: no contiene {m}")
    if not sin_main:
        print("    ninguno")

    print(f"\n  === jars ilegibles: {len(rotos)} ===")
    for j, e in rotos:
        print(f"    >>> {j}: {e}")

    return 1 if (dup or faltan or rotos or sin_main) else 0


if __name__ == "__main__":
    sys.exit(main())
