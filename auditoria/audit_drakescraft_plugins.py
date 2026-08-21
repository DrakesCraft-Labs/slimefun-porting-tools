#!/usr/bin/env python3
"""Audita JARs Bukkit/Paper activos sin cargar código de terceros."""

from __future__ import annotations

import argparse
import json
import struct
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


DESCRIPTORS = ("paper-plugin.yml", "plugin.yml", "bungee.yml")


def string_list(value: Any) -> list[str]:
    """Normaliza listas YAML y valores escalares de dependencias o aliases."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def paper_dependencies(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Extrae dependencias server del descriptor moderno de Paper."""
    hard: list[str] = []
    soft: list[str] = []
    dependencies = data.get("dependencies", {})
    if isinstance(dependencies, list):
        for dependency in dependencies:
            if isinstance(dependency, dict):
                name = str(dependency.get("name", "")).strip()
                if name:
                    (hard if dependency.get("required", True) else soft).append(name)
            elif str(dependency).strip():
                hard.append(str(dependency).strip())
        return hard, soft
    if not isinstance(dependencies, dict):
        return hard, soft
    server = dependencies.get("server", {})
    if not isinstance(server, dict):
        return hard, soft
    for name, settings in server.items():
        required = not isinstance(settings, dict) or settings.get("required", True)
        (hard if required else soft).append(str(name))
    return hard, soft


def class_major(archive: zipfile.ZipFile, class_name: str) -> int | None:
    """Devuelve la versión bytecode de una clase sin ejecutarla."""
    try:
        header = archive.read(class_name)[:8]
        if len(header) != 8 or header[:4] != b"\xca\xfe\xba\xbe":
            return None
        return struct.unpack(">H", header[6:8])[0]
    except (KeyError, OSError, struct.error):
        return None


def audit_jar(path: Path) -> dict[str, Any]:
    """Inspecciona descriptor, entrada principal y versión Java de un JAR."""
    result: dict[str, Any] = {
        "file": path.name,
        "size": path.stat().st_size,
        "issues": [],
        "warnings": [],
    }
    try:
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                result["issues"].append(f"entrada ZIP corrupta: {bad}")
            names = set(archive.namelist())
            descriptor = next((name for name in DESCRIPTORS if name in names), None)
            if descriptor is None:
                result["issues"].append("sin descriptor Bukkit/Paper/Bungee")
                return result
            result["descriptor"] = descriptor
            raw = archive.read(descriptor).decode("utf-8-sig", errors="replace")
            data = yaml.safe_load(raw) or {}
            if not isinstance(data, dict):
                result["issues"].append("descriptor YAML no es un objeto")
                return result

            result["name"] = str(data.get("name", "")).strip()
            result["version"] = str(data.get("version", "")).strip()
            result["main"] = str(data.get("main", "")).strip()
            result["api_version"] = str(data.get("api-version", "")).strip()
            result["provides"] = string_list(data.get("provides"))
            if not result["name"]:
                result["issues"].append("descriptor sin name")
            if not result["main"]:
                result["issues"].append("descriptor sin main")
            else:
                main_class = result["main"].replace(".", "/") + ".class"
                if main_class not in names:
                    result["issues"].append(f"clase principal ausente: {main_class}")
                else:
                    result["class_major"] = class_major(archive, main_class)
                    if result["class_major"] and result["class_major"] > 65:
                        result["issues"].append(
                            f"bytecode Java {result['class_major']} no compatible con Java 21"
                        )

            hard = string_list(data.get("depend"))
            soft = string_list(data.get("softdepend"))
            if descriptor == "paper-plugin.yml":
                paper_hard, paper_soft = paper_dependencies(data)
                hard.extend(paper_hard)
                soft.extend(paper_soft)
            result["depend"] = sorted(set(hard), key=str.casefold)
            result["softdepend"] = sorted(set(soft), key=str.casefold)

            commands = data.get("commands", {})
            result["commands"] = {}
            if isinstance(commands, dict):
                for command, settings in commands.items():
                    aliases = settings.get("aliases") if isinstance(settings, dict) else None
                    result["commands"][str(command)] = string_list(aliases)
    except (OSError, zipfile.BadZipFile, yaml.YAMLError) as error:
        result["issues"].append(f"no se pudo inspeccionar: {error}")
    return result


def audit_directory(plugins_dir: Path) -> dict[str, Any]:
    """Cruza todos los JARs activos y detecta colisiones entre plugins."""
    jars = sorted(plugins_dir.glob("*.jar"), key=lambda item: item.name.casefold())
    records = [audit_jar(path) for path in jars]
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("name"):
            by_name[record["name"].casefold()].append(record)

    for records_with_name in by_name.values():
        if len(records_with_name) > 1:
            files = ", ".join(item["file"] for item in records_with_name)
            for record in records_with_name:
                record["issues"].append(f"nombre de plugin duplicado en: {files}")

    available = set(by_name)
    for record in records:
        available.update(name.casefold() for name in record.get("provides", []))
    for record in records:
        for dependency in record.get("depend", []):
            if dependency.casefold() not in available:
                record["issues"].append(f"dependencia dura ausente: {dependency}")

    owners: dict[str, list[str]] = defaultdict(list)
    for record in records:
        owner = record.get("name") or record["file"]
        for command, aliases in record.get("commands", {}).items():
            for label in [command, *aliases]:
                owners[label.casefold()].append(owner)
    collisions = {
        label: sorted(set(command_owners), key=str.casefold)
        for label, command_owners in owners.items()
        if len(set(command_owners)) > 1
    }
    return {
        "plugins_dir": str(plugins_dir),
        "jar_count": len(jars),
        "issue_count": sum(len(record["issues"]) for record in records),
        "warning_count": sum(len(record["warnings"]) for record in records),
        "command_collisions": collisions,
        "plugins": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugins-dir", default=r"Y:\plugins")
    parser.add_argument("--json", action="store_true", help="Emite el informe JSON completo")
    args = parser.parse_args()
    plugins_dir = Path(args.plugins_dir)
    if not plugins_dir.is_dir():
        print(f"[ERROR] No existe el directorio: {plugins_dir}", file=sys.stderr)
        return 2

    print(f"[INFO] Auditando JARs activos en {plugins_dir}", file=sys.stderr)
    report = audit_directory(plugins_dir)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[SUCCESS] JARs inspeccionados: {report['jar_count']}")
        print(f"[INFO] Hallazgos estructurales: {report['issue_count']}")
        for plugin in report["plugins"]:
            for issue in plugin["issues"]:
                print(f"[ISSUE] {plugin['file']}: {issue}")
        print(f"[INFO] Colisiones de comandos: {len(report['command_collisions'])}")
        for command, owners in sorted(report["command_collisions"].items()):
            print(f"[COLLISION] /{command}: {', '.join(owners)}")
    return 1 if report["issue_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
