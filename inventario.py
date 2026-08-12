#!/usr/bin/env python3
"""Inventario de la cosecha: que trae cada repo y cuanto cuesta traerlo a 1.21.11.

Se mide antes de tocar nada porque el orden de trabajo depende de esto. Un addon de 2022 con
ocho items cuesta lo mismo de portar que uno con cien, asi que conviene saber cual es cual.

Se distingue ademas entre los que merecen repo propio y los que son un puñado de clases que
encajan mejor dentro de un plugin que ya tenemos.
"""
import json
import pathlib
import re
import subprocess

RAIZ = pathlib.Path(__file__).parent


def texto(ruta):
    try:
        return ruta.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def git(repo, *args):
    try:
        return subprocess.run(["git", "-C", str(repo), *args],
                              capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ""


filas = []
for repo in sorted(p for p in RAIZ.iterdir() if p.is_dir() and (p / ".git").exists()):
    java = list((repo / "src/main/java").rglob("*.java")) if (repo / "src/main/java").exists() else []
    fuente = "\n".join(texto(f) for f in java)

    # Items registrados: es la medida honesta de "cuanto contenido trae".
    items = len(set(re.findall(r'"([A-Z][A-Z_0-9]{3,})"\s*,', fuente)))

    build = texto(repo / "pom.xml") + texto(repo / "build.gradle") + texto(repo / "build.gradle.kts")
    mc = re.findall(r"1\.(?:1[4-9]|2[0-9])(?:\.\d+)?", build)
    mc = sorted(set(mc), key=lambda v: [int(x) for x in v.split(".")])[-1] if mc else "?"

    lic = "sin-licencia"
    for nombre in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"):
        if (repo / nombre).exists():
            t = texto(repo / nombre)[:400].upper()
            lic = ("GPL-3.0" if "GNU GENERAL PUBLIC" in t else
                   "MIT" if "MIT LICENSE" in t or "PERMISSION IS HEREBY GRANTED" in t else
                   "otra")
            break

    filas.append({
        "repo": repo.name,
        "clases": len(java),
        "lineas": sum(1 for _ in fuente.splitlines()),
        "items": items,
        "mc": mc,
        "licencia": lic,
        "ultimo": git(repo, "log", "-1", "--format=%ad", "--date=short"),
        # Depender del core chino lo ata a la migracion; sin eso, entra hoy mismo.
        "core_chino": len([f for f in java if "com.xzavier0722" in texto(f)
                           or "StorageCacheUtils" in texto(f)]),
    })

filas.sort(key=lambda f: -f["items"])
(RAIZ / "inventario.json").write_text(json.dumps(filas, indent=1, ensure_ascii=False), encoding="utf-8")

print(f"{'repo':<24}{'clases':>7}{'lineas':>8}{'items':>7}{'MC':>9}{'licencia':>14}{'ultimo':>12}{'core':>6}")
print("-" * 88)
for f in filas:
    print(f"{f['repo']:<24}{f['clases']:>7}{f['lineas']:>8}{f['items']:>7}"
          f"{f['mc']:>9}{f['licencia']:>14}{f['ultimo']:>12}{f['core_chino']:>6}")
