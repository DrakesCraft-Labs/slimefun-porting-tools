#!/usr/bin/env python3
"""Corrige coordenadas absolutas de entidades colgantes en estructuras NBT."""

from __future__ import annotations

import gzip
import io
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import nbtlib


ENTIDADES_COLGANTES = {
    "minecraft:glow_item_frame",
    "minecraft:item_frame",
    "minecraft:leash_knot",
    "minecraft:painting",
}


def cargar_nbt(contenido: bytes) -> tuple[nbtlib.File, bool]:
    """Carga un NBT y devuelve también si venía comprimido con gzip."""
    comprimido = contenido.startswith(b"\x1f\x8b")
    bruto = gzip.decompress(contenido) if comprimido else contenido
    return nbtlib.File.parse(io.BytesIO(bruto)), comprimido


def guardar_nbt(documento: nbtlib.File, comprimido: bool) -> bytes:
    """Serializa un NBT conservando su modalidad de compresión."""
    salida = io.BytesIO()
    documento.write(salida)
    bruto = salida.getvalue()
    return gzip.compress(bruto, mtime=0) if comprimido else bruto


def reparar_nbt(contenido: bytes) -> tuple[bytes, int]:
    """Alinea TileX/Y/Z con blockPos solo en entidades colgantes inconsistentes."""
    documento, comprimido = cargar_nbt(contenido)
    cambios = 0

    for entidad in documento.get("entities", []):
        datos = entidad.get("nbt", {})
        identificador = str(datos.get("id", ""))
        if identificador not in ENTIDADES_COLGANTES:
            continue
        if not all(clave in datos for clave in ("TileX", "TileY", "TileZ")):
            continue
        posicion = entidad.get("blockPos")
        if posicion is None or len(posicion) != 3:
            continue

        actual = tuple(int(datos[clave]) for clave in ("TileX", "TileY", "TileZ"))
        correcta = tuple(int(valor) for valor in posicion)
        if actual == correcta:
            continue
        datos["TileX"], datos["TileY"], datos["TileZ"] = map(nbtlib.Int, correcta)
        cambios += 1

    if not cambios:
        return contenido, 0
    return guardar_nbt(documento, comprimido), cambios


def contar_inconsistencias(contenido: bytes) -> int:
    """Cuenta entidades colgantes cuyas coordenadas Tile no coinciden con blockPos."""
    documento, _ = cargar_nbt(contenido)
    total = 0
    for entidad in documento.get("entities", []):
        datos = entidad.get("nbt", {})
        if str(datos.get("id", "")) not in ENTIDADES_COLGANTES:
            continue
        if not all(clave in datos for clave in ("TileX", "TileY", "TileZ")):
            continue
        posicion = entidad.get("blockPos")
        if posicion is None or len(posicion) != 3:
            continue
        actual = tuple(int(datos[clave]) for clave in ("TileX", "TileY", "TileZ"))
        if actual != tuple(int(valor) for valor in posicion):
            total += 1
    return total


def reparar_datapack(origen: Path, destino: Path) -> int:
    """Copia el datapack y reemplaza únicamente los NBT con coordenadas inválidas."""
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
                    print(f"[INFO] {info.filename}: {cambios} entidad(es) corregida(s)")

        if total == 0:
            raise ValueError("No se encontraron entidades colgantes con coordenadas absolutas")

        with zipfile.ZipFile(ruta_temporal, "r") as verificacion:
            archivo_malo = verificacion.testzip()
            if archivo_malo:
                raise zipfile.BadZipFile(f"Entrada dañada tras la reparación: {archivo_malo}")
            restantes = sum(
                contar_inconsistencias(verificacion.read(nombre))
                for nombre in verificacion.namelist()
                if nombre.endswith(".nbt")
            )
            if restantes:
                raise ValueError(f"Persistieron {restantes} coordenadas inconsistentes")

        shutil.move(ruta_temporal, destino)
        print(f"[SUCCESS] {total} entidad(es) corregida(s): {destino}")
        return total
    except Exception:
        ruta_temporal.unlink(missing_ok=True)
        raise


def main() -> int:
    """Valida argumentos y entrega errores legibles para automatización."""
    if len(sys.argv) != 3:
        print("Uso: reparar_entidades_colgantes.py <origen.zip> <destino.zip>")
        return 2
    try:
        reparar_datapack(Path(sys.argv[1]), Path(sys.argv[2]))
        return 0
    except Exception as error:
        print(f"[ERROR] {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
