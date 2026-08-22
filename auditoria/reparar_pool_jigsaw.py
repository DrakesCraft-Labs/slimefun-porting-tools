#!/usr/bin/env python3
"""Repara referencias obsoletas a pools de jigsaw dentro de un datapack ZIP."""

from __future__ import annotations

import gzip
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


# Incluye los dos bytes big-endian de longitud del TAG_String para no dejar un NBT corrupto.
REFERENCIAS = {
    b"\x00\x17minecraft:village/empty": b"\x00\x0fminecraft:empty",
}


def reparar_nbt(contenido: bytes) -> tuple[bytes, int]:
    """Reemplaza referencias conocidas y conserva la compresión original."""
    comprimido = contenido.startswith(b"\x1f\x8b")
    bruto = gzip.decompress(contenido) if comprimido else contenido
    cambios = 0
    for obsoleta, vigente in REFERENCIAS.items():
        ocurrencias = bruto.count(obsoleta)
        bruto = bruto.replace(obsoleta, vigente)
        cambios += ocurrencias
    if not cambios:
        return contenido, 0
    return (gzip.compress(bruto, mtime=0) if comprimido else bruto), cambios


def reparar_datapack(origen: Path, destino: Path) -> int:
    """Copia el ZIP, modifica solo NBT afectados y verifica el resultado."""
    if not origen.is_file():
        raise FileNotFoundError(f"No existe el datapack: {origen}")
    if origen.resolve() == destino.resolve():
        raise ValueError("El destino debe ser distinto del archivo original")

    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destino.parent, suffix=".zip", delete=False) as temporal:
        ruta_temporal = Path(temporal.name)

    total = 0
    try:
        with zipfile.ZipFile(origen, "r") as entrada, zipfile.ZipFile(
            ruta_temporal, "w", allowZip64=True
        ) as salida:
            for info in entrada.infolist():
                contenido = entrada.read(info.filename)
                cambios = 0
                if info.filename.endswith(".nbt"):
                    contenido, cambios = reparar_nbt(contenido)
                salida.writestr(info, contenido)
                if cambios:
                    total += cambios
                    print(f"[INFO] {info.filename}: {cambios} referencia(s) corregida(s)")

        if total == 0:
            raise ValueError("No se encontraron referencias minecraft:village/empty")

        with zipfile.ZipFile(ruta_temporal, "r") as verificacion:
            archivo_malo = verificacion.testzip()
            if archivo_malo:
                raise zipfile.BadZipFile(f"Entrada dañada tras la reparación: {archivo_malo}")
            for nombre in verificacion.namelist():
                if not nombre.endswith(".nbt"):
                    continue
                contenido = verificacion.read(nombre)
                bruto = gzip.decompress(contenido) if contenido.startswith(b"\x1f\x8b") else contenido
                if any(obsoleta in bruto for obsoleta in REFERENCIAS):
                    raise ValueError(f"Persistió una referencia obsoleta en {nombre}")

        shutil.move(ruta_temporal, destino)
        print(f"[SUCCESS] {total} referencia(s) corregida(s): {destino}")
        return total
    except Exception:
        ruta_temporal.unlink(missing_ok=True)
        raise


def main() -> int:
    """Valida argumentos y entrega errores legibles para automatización."""
    if len(sys.argv) != 3:
        print("Uso: reparar_pool_jigsaw.py <origen.zip> <destino.zip>")
        return 2
    try:
        reparar_datapack(Path(sys.argv[1]), Path(sys.argv[2]))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"[ERROR] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
