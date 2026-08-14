#!/usr/bin/env python3
"""Vigila que DrakesCraft siga en pie y avisa por Discord si no. Se ejecuta EN star.

POR QUE

El fin de semana no hay nadie mirando. Si el servidor se cae un viernes por la noche, sin esto se
entera alguien el lunes -- o un jugador antes, y peor.

QUE HACE

Cada vez que se ejecuta comprueba que el servidor responde. Si no responde DOS veces seguidas, lo
reinicia y avisa. Se exige la segunda confirmacion a proposito: un fallo puntual de la API del
panel o un pico de carga no deberian provocar un reinicio.

Nunca reinicia dos veces en menos de media hora, para no entrar en un bucle si el servidor esta
roto de verdad: en ese caso avisa y se calla, que es mas util que reiniciar sin parar.
"""
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

HUB = pathlib.Path("/home/jack/ai-hub")
ESTADO = HUB / ".vigilante-estado.json"
CONTROL = ["python3", str(HUB / "scripts" / "control_drakescraft.py")]
MARGEN_REINICIO = 30 * 60          # no reiniciar mas de una vez cada media hora
MARGEN_ARRANQUE = 8 * 60           # un arranque tarda ~3 min; pasados 8 esta colgado
ENV = pathlib.Path("/opt/stacks/drakes-updater/.env")


def webhook():
    for linea in ENV.read_text().splitlines():
        if linea.startswith("DISCORD_UPDATER_WEBHOOK="):
            return linea.split("=", 1)[1].strip()
    return None


def avisar(texto):
    url = webhook()
    if not url:
        print("  (sin webhook, no se avisa)"); return
    datos = json.dumps({"content": texto}).encode()
    req = urllib.request.Request(url, data=datos, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception as e:
        print(f"  aviso fallido: {e}")


def vivo():
    """El servidor responde al ping de estado."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:8081/api/mcstatus", timeout=25) as r:
            return bool(json.load(r).get("java", {}).get("online"))
    except Exception:
        return False


def arrancando():
    """El panel dice que el servidor esta arrancando ahora mismo.

    Un arranque de DrakesCraft pasa de los tres minutos, y durante todo ese rato no responde al
    ping. Sin esta comprobacion el vigilante lo tomaria por caido y podria reiniciar un servidor
    que estaba levantandose perfectamente -- dejandolo en un bucle de arranques a medias.
    """
    try:
        r = subprocess.run(CONTROL + ["resources"], capture_output=True, text=True, timeout=60)
        return "starting" in (r.stdout or "").lower()
    except Exception:
        return False


def main():
    estado = json.loads(ESTADO.read_text()) if ESTADO.exists() else {}
    fallos = estado.get("fallos", 0)
    ultimo = estado.get("ultimo_reinicio", 0)
    ahora = time.time()

    if vivo():
        if fallos:
            print(f"  recuperado tras {fallos} fallo(s)")
            avisar("✅ **DrakesCraft** vuelve a responder.")
        estado = {"fallos": 0, "ultimo_reinicio": ultimo, "arrancando_desde": None}
        ESTADO.write_text(json.dumps(estado))
        print("  el servidor responde")
        return 0

    if arrancando():
        # Un arranque normal tarda unos tres minutos. Pero el 14-08 el servidor se quedo
        # colgado a media carga y el panel siguio diciendo "starting" durante TRES HORAS: el
        # proceso estaba vivo, asi que nadie lo tocaba, y los jugadores no podian entrar.
        # Por eso "arrancando" tiene techo: pasado el margen, se trata como colgado.
        desde = estado.get("arrancando_desde") or ahora
        if ahora - desde < MARGEN_ARRANQUE:
            print(f"  arrancando desde hace {int(ahora-desde)}s: se deja en paz")
            ESTADO.write_text(json.dumps({"fallos": fallos, "ultimo_reinicio": ultimo,
                                          "arrancando_desde": desde}))
            return 0
        print(f"  lleva {int(ahora-desde)}s arrancando: se da por colgado")
        avisar("🚨 **DrakesCraft** lleva demasiado tiempo arrancando sin terminar. "
               "Se da por colgado y se reinicia.")
        # Sigue hacia el reinicio de mas abajo.

    fallos += 1
    print(f"  no responde (fallo {fallos})")

    if fallos < 2:
        # Un solo fallo puede ser un pico o un hipo de la API. Se espera a la siguiente pasada.
        ESTADO.write_text(json.dumps({"fallos": fallos, "ultimo_reinicio": ultimo}))
        return 1

    if ahora - ultimo < MARGEN_REINICIO:
        print("  ya se reinicio hace poco: no se insiste")
        avisar("🚨 **DrakesCraft** sigue sin responder y ya se reinicio hace poco. "
               "Necesita una mirada humana.")
        ESTADO.write_text(json.dumps({"fallos": fallos, "ultimo_reinicio": ultimo}))
        return 1

    print("  reiniciando...")
    avisar("⚠️ **DrakesCraft** no responde. Reiniciando automaticamente.")
    subprocess.run(CONTROL + ["restart"], capture_output=True, timeout=120)
    ESTADO.write_text(json.dumps({"fallos": 0, "ultimo_reinicio": ahora}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
