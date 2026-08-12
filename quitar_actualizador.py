#!/usr/bin/env python3
"""Quita el autoactualizador de GuizhanBuilds de un addon.

OJO: la clase NO siempre se llama igual. Hay addons con `GuizhanBuildsUpdater` y
otros con `GuizhanUpdater` a secas. Se buscan ambos: el 12-08 se escapo el segundo
en SlimefunAdvancements y el addon llego a produccion lanzando NoClassDefFoundError
en cada clic de inventario.

POR QUE

Los addons del ecosistema chino traen un actualizador que, al arrancar, se descarga el jar mas
reciente de un repositorio ajeno y se reemplaza a si mismo. En un servidor en produccion eso no
es una comodidad: es que cualquier cambio alla llega aqui sin que nadie lo revise, y ademas
pisaria precisamente los arreglos que hemos hecho nosotros.

En todos los addons revisados hasta ahora, el actualizador es el UNICO uso de GuizhanLib, asi que
quitarlo elimina tambien la dependencia entera -- que ya no se resuelve desde ningun repo
configurado.

Uso:  python3 quitar_actualizador.py <carpeta-del-repo> [--escribir]
"""
import pathlib
import re
import sys

# Las dos formas con las que aparece en los addons cosechados.
NOMBRES = ("GuizhanBuildsUpdater", "GuizhanUpdater")


def limpiar_fuentes(repo, escribir):
    """Quita el import, la construccion del actualizador y el if que lo envuelve."""
    tocados = []
    for f in repo.rglob("*.java"):
        if "/target/" in str(f):
            continue
        texto = original = f.read_text(encoding="utf-8", errors="replace")
        if not any(n in texto for n in NOMBRES):
            continue

        texto = re.sub(r"^import net\.guizhanss\.[a-zA-Z.]*updater\.[A-Za-z]+;\n", "", texto, flags=re.M)

        # La llamada suele ir dentro de un `if (config auto-update ...) { ... }`. Se intenta
        # primero quitar el bloque entero; si no encaja, se quita solo la sentencia y se deja el
        # if vacio, que es inofensivo pero feo -- por eso se avisa.
        antes = texto
        texto = re.sub(
            r"[ \t]*if \([^\n]*(?:auto-?[Uu]pdate|autoUpdate)[^\n]*\)\s*\{[^{}]*?Guizhan[A-Za-z]*Updater[^{}]*?\}\n",
            "", texto, flags=re.S)
        if texto == antes:
            texto = re.sub(r"[ \t]*(?:new )?Guizhan[A-Za-z]*Updater[.(][^;]*?;\n", "", texto, flags=re.S)

        if texto != original:
            tocados.append(f)
            if escribir:
                f.write_text(texto, encoding="utf-8")
    return tocados


def limpiar_pom(repo, escribir):
    pom = repo / "pom.xml"
    if not pom.exists():
        return "sin pom.xml"
    texto = original = pom.read_text(encoding="utf-8")
    texto = re.sub(r"\s*<dependency>\s*<groupId>net\.guizhanss</groupId>.*?</dependency>",
                   "", texto, flags=re.S)
    if texto == original:
        return "el pom no declaraba GuizhanLib"
    if escribir:
        pom.write_text(texto, encoding="utf-8")
    return "GuizhanLib fuera del pom"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    repo = pathlib.Path(sys.argv[1]).resolve()
    escribir = "--escribir" in sys.argv

    tocados = limpiar_fuentes(repo, escribir)
    print(f"=== {repo.name} ===")
    for f in tocados:
        print(f"  {f.relative_to(repo)}")
    print(f"  {limpiar_pom(repo, escribir)}")

    if escribir:
        restos = [f for f in repo.rglob("*.java")
                  if "/target/" not in str(f)
                  and any(n in f.read_text(encoding="utf-8", errors="replace") for n in NOMBRES)]
        if restos:
            print("  AVISO, quedan referencias a mano:")
            for f in restos:
                print(f"    {f.relative_to(repo)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
