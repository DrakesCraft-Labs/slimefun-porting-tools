#!/usr/bin/env python3
"""
Regenera HOLOGRAMAS-LOBBY.md leyendo el estado real del servidor.

Lee `plugins/DecentHolograms/holograms/` a traves del montaje sshfs y vuelca
cada panel con su posicion y su texto sin codigos de color. Sirve para saber
que dice cada holograma sin entrar al juego, y sobre todo para localizar que
hay que tocar cuando cambie el enlace de Discord.

    python3 operacion/documentar_hologramas.py
"""

import datetime
import os
import pathlib
import re
import sys

try:
    import yaml
except ImportError:
    print("[ERROR] falta PyYAML (pip install pyyaml)")
    sys.exit(1)

# Ruta al servidor. Por defecto el montaje sshfs de DrakesCraft; se puede
# cambiar con la variable de entorno MSC_HOLOGRAMAS o con el primer argumento.
DIR = pathlib.Path(os.environ.get(
    "MSC_HOLOGRAMAS",
    pathlib.Path.home() / "mnt/drakes/plugins/DecentHolograms/holograms"))
SALIDA = pathlib.Path(os.environ.get("MSC_HOLOGRAMAS_SALIDA", "HOLOGRAMAS-LOBBY.md"))

# Las zonas del lobby, en el orden en que las recorre un jugador
ZONAS = {
    "corto":   ("Pasillo corto — junto al spawn", "x 190-205, z 263-294"),
    "extenso": ("Pasillo extenso — manual de comandos", "x 149-221, z 301-310"),
    "este":    ("Franja este — normas y créditos", "x 213-221, desde z 310"),
    "oeste":   ("Franja oeste — ayuda y dudas", "x 149-157, desde z 310"),
    "suelto":  ("Sin zona asignada", ""),
}


def zona(x, z):
    """Deduce a que zona pertenece un holograma por sus coordenadas."""
    if z >= 301:
        return "extenso"
    if x >= 213:
        return "este"
    if x <= 157:
        return "oeste"
    if 190 <= x <= 205:
        return "corto"
    return "suelto"


def limpio(s):
    """Quita los codigos de color para que el texto se lea en el documento."""
    s = re.sub(r"&#[0-9A-Fa-f]{6}", "", s)
    s = re.sub(r"&[0-9a-fk-orA-FK-OR]", "", s)
    return s.strip()


def leer():
    """Carga todos los hologramas del servidor."""
    if not DIR.is_dir():
        raise FileNotFoundError(f"no se ve {DIR} (¿montaje de drakes caído?)")
    datos = []
    for f in sorted(DIR.glob("*.yml")):
        try:
            d = yaml.safe_load(f.read_text(encoding="utf-8"))
            x, y, z = (float(v) for v in d["location"].split(":")[1:])
            datos.append(dict(
                nombre=f.stem, x=int(x), y=int(y), z=int(z),
                rango=d.get("display-range"),
                lineas=[l.get("content", "") for l in d["pages"][0]["lines"]],
                zona=zona(int(x), int(z))))
        except Exception as e:                      # noqa: BLE001
            print(f"[ERROR] {f.name}: {type(e).__name__}: {e}")
    return datos


def main():
    try:
        datos = leer()
    except Exception as e:                          # noqa: BLE001
        print(f"[ERROR] {e}")
        return 1

    discord = sorted({m for d in datos for l in d["lineas"]
                      for m in re.findall(r"discord\.gg/\S+", limpio(l))})
    afectados = [d["nombre"] for d in datos
                 if any("discord.gg" in limpio(l) for l in d["lineas"])]

    L = [
        "# Hologramas del lobby — DrakesCraft\n",
        f"> Generado el {datetime.date.today().isoformat()} leyendo "
        "`plugins/DecentHolograms/holograms/` del servidor.\n",
        "> Regenerar con `scripts/documentar_hologramas.py` en vez de editar a mano.\n",
        f"\n**{len(datos)} hologramas**, mundo `SpawnWarps`, todos con "
        "`down-origin: true` (la coordenada es la base del texto, no el techo).\n",
        "\n## ⚠ Qué hay que tocar cuando cambie el Discord\n",
        f"Invitación actual: **`{discord[0] if discord else '(ninguna)'}`**\n",
        f"\nAparece en {len(afectados)} holograma(s): "
        + ", ".join(f"`{n}`" for n in afectados) + ".\n",
        "\nPara cambiarla, por cada uno:\n",
        "\n```\n/dh lines <holograma> 1\n"
        "/dh line set <holograma> 1 <numero_de_linea> <texto nuevo>\n```\n",
        "\nFuera de los hologramas, la misma invitación vive en el repo "
        "`drakescraft-web` y en la configuración de los plugins que la publiquen:\n",
        "\n```bash\ngrep -rn 'discord.gg' <repo de la web>\n```\n",
        "\n## Mapa de zonas\n\n| Zona | Área | Hologramas |\n|---|---|---|\n",
    ]
    for k, (titulo, area) in ZONAS.items():
        n = [d for d in datos if d["zona"] == k]
        if n:
            L.append(f"| {titulo} | `{area}` | {len(n)} |\n")

    for k, (titulo, area) in ZONAS.items():
        grupo = sorted([d for d in datos if d["zona"] == k],
                       key=lambda d: (-d["z"], d["x"]))
        if not grupo:
            continue
        L.append(f"\n---\n\n## {titulo}\n")
        if area:
            L.append(f"\nÁrea disponible: `{area}`\n")
        for d in grupo:
            L.append(f"\n### `{d['nombre']}`\n")
            L.append(f"\n`{d['x']}, {d['y']}, {d['z']}` · alcance {d['rango']} "
                     f"bloques · {len(d['lineas'])} líneas\n\n```\n")
            for i, l in enumerate(d["lineas"], 1):
                t = limpio(l)
                L.append(f"{i:>3}  {t if t else '·'}\n")
            L.append("```\n")

    SALIDA.write_text("".join(L), encoding="utf-8")
    print(f"[SUCCESS] {SALIDA} — {len(datos)} hologramas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
