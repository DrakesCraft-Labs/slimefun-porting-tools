#!/usr/bin/env python3
"""Recoge las peticiones de reinicio que deja Odysseia y llama al panel.

Pterodactyl no permite que el servidor de Minecraft se reinicie a si mismo, y la API key del panel
no debe vivir en esa maquina: ahi corren 130 plugins de terceros. Asi que Odysseia solo deja un
archivo y este script, que si tiene la llave, lo recoge.

Se ejecuta desde un timer de systemd cada 20s. Ver drakes-restart-watch.timer.
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import paramiko

AI_HUB = Path(__file__).resolve().parent.parent
CONTROL = AI_HUB / "scripts" / "control_drakescraft.py"
PETICION = "/plugins/Odysseia/restart-request.json"
# Una peticion vieja no se atiende: si este servicio estuvo caido dos dias, al volver no debe
# reiniciar el servidor por algo que se pidio anteayer.
VALIDEZ = timedelta(minutes=5)


def log(mensaje):
    print(f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {mensaje}", flush=True)


def conectar():
    env = {}
    for linea in open("/opt/stacks/drakes-updater/.env"):
        linea = linea.strip()
        if "=" in linea and not linea.startswith("#"):
            clave, valor = linea.split("=", 1)
            env.setdefault(clave, valor.strip().strip('"').strip("'"))
    transporte = paramiko.Transport((env["SFTP_HOST"], int(env["SFTP_PORT"])))
    transporte.connect(username=env["SFTP_USER"], password=env["SFTP_PASS"])
    return paramiko.SFTPClient.from_transport(transporte), transporte


def main():
    try:
        sftp, transporte = conectar()
    except Exception as error:                      # el servidor puede estar apagado o reiniciando
        log(f"sin conexion SFTP ({error}); se reintenta al siguiente ciclo")
        return 0

    try:
        try:
            with sftp.open(PETICION, "r") as archivo:
                datos = json.loads(archivo.read().decode("utf-8"))
        except IOError:
            return 0                                # no hay peticion: el caso normal

        # Se borra ANTES de reiniciar. Si el reinicio falla se avisa, pero no queremos que una
        # peticion atascada dispare un bucle de reinicios.
        sftp.remove(PETICION)

        solicitado = datetime.fromisoformat(datos["solicitado"].replace("Z", "+00:00"))
        edad = datetime.now(timezone.utc) - solicitado
        quien = datos.get("por", "?")
        motivo = datos.get("motivo", "?")

        if edad > VALIDEZ:
            log(f"peticion descartada por vieja ({int(edad.total_seconds())}s) de {quien}: {motivo}")
            return 0

        log(f"reinicio pedido por {quien} hace {int(edad.total_seconds())}s. Motivo: {motivo}")
    finally:
        transporte.close()

    resultado = subprocess.run([sys.executable, str(CONTROL), "restart"],
                               capture_output=True, text=True)
    if resultado.returncode == 0:
        log("señal de reinicio enviada al panel")
    else:
        log(f"FALLO al reiniciar (codigo {resultado.returncode}): {resultado.stderr.strip()}")
    return resultado.returncode


if __name__ == "__main__":
    sys.exit(main())
