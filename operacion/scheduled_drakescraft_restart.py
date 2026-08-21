#!/usr/bin/env python3
"""Reinicio diario seguro de DrakesCraft mediante la API de Pterodactyl."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import time
from pathlib import Path

from control_drakescraft import send_request


HUB_ROOT = Path(__file__).resolve().parent.parent
LOCK_PATH = HUB_ROOT / ".drakescraft-restart.lock"
LOG_PATH = HUB_ROOT / "log" / "scheduled-restarts.log"


def log(level: str, message: str) -> None:
    """Registra cada etapa con hora local para facilitar auditorías."""
    timestamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"[{timestamp}] [{level}] {message}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def acquire_lock() -> int:
    """Crea un lock atómico y rechaza reinicios concurrentes."""
    try:
        descriptor = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exception:
        raise RuntimeError(f"ya existe un reinicio en curso: {LOCK_PATH}") from exception
    os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
    return descriptor


def command(value: str, dry_run: bool) -> None:
    """Envía un comando de consola o lo informa durante una simulación."""
    if dry_run:
        log("DRY-RUN", f"comando: {value}")
        return
    send_request("/command", method="POST", data={"command": value})


def sleep_until(seconds: int, dry_run: bool) -> None:
    """Espera entre hitos sin retrasar las simulaciones."""
    if not dry_run and seconds > 0:
        time.sleep(seconds)


def require_running(dry_run: bool) -> None:
    """Evita iniciar el flujo si el servidor ya está detenido."""
    if dry_run:
        return
    response = send_request("/resources")
    state = response.get("attributes", {}).get("current_state")
    if state != "running":
        raise RuntimeError(f"el servidor no está en ejecución (estado: {state})")


def run_restart(reason: str, dry_run: bool) -> None:
    """Ejecuta el aviso, cierre transaccional y reinicio en orden fijo."""
    require_running(dry_run)
    log("INFO", f"reinicio programado iniciado: {reason}")

    command(f"say [DrakesCraft] Reinicio diario en 15 minutos: {reason}.", dry_run)
    sleep_until(600, dry_run)
    command("say [DrakesCraft] Reinicio diario en 5 minutos. Terminen máquinas y movimientos de inventario.", dry_run)
    sleep_until(240, dry_run)
    command("say [DrakesCraft] Reinicio diario en 1 minuto. Los contenedores quedarán protegidos.", dry_run)
    command("odysseia maintenance start 60", dry_run)
    sleep_until(30, dry_run)
    command("say [DrakesCraft] Reinicio en 30 segundos.", dry_run)
    sleep_until(20, dry_run)
    command("say [DrakesCraft] Reinicio en 10 segundos.", dry_run)
    sleep_until(10, dry_run)
    command("save-all flush", dry_run)
    sleep_until(5, dry_run)

    if dry_run:
        log("DRY-RUN", "señal Pterodactyl: restart")
    else:
        send_request("/power", method="POST", data={"signal": "restart"})
    log("SUCCESS", "señal de reinicio enviada")


def parse_args() -> argparse.Namespace:
    """Procesa parámetros explícitos para uso manual y pruebas."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reason",
        default="mantenimiento preventivo y guardado diario",
        help="motivo visible en el primer aviso",
    )
    parser.add_argument("--dry-run", action="store_true", help="valida el flujo sin esperar ni enviar comandos")
    return parser.parse_args()


def main() -> int:
    """Controla el lock y garantiza su limpieza incluso ante errores."""
    args = parse_args()
    descriptor: int | None = None
    try:
        descriptor = acquire_lock()
        run_restart(args.reason, args.dry_run)
        return 0
    except Exception as exception:
        log("ERROR", str(exception))
        return 1
    finally:
        if descriptor is not None:
            os.close(descriptor)
            try:
                LOCK_PATH.unlink()
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    sys.exit(main())
