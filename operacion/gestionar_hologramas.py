#!/usr/bin/env python3
"""
Crea y actualiza los hologramas del lobby de DrakesCraft desde un archivo de
definicion, mandando los comandos por la consola de Pterodactyl.

    python3 operacion/gestionar_hologramas.py hologramas-lobby.yml
    python3 operacion/gestionar_hologramas.py hologramas-lobby.yml --solo info_normas
    python3 operacion/gestionar_hologramas.py hologramas-lobby.yml --simular

El de vuelta es `documentar_hologramas.py`, que lee el servidor y regenera
el informe de documentar_hologramas.py. Los dos juntos cierran el circulo: defines, aplicas, verificas.


ANTES DE USARLO: hay que saber DONDE
-------------------------------------------------------------------------------
El script no adivina ubicaciones. Desde la consola no existe "donde estoy
parado", asi que cada panel necesita coordenadas explicitas y hay que haberlas
mirado antes dentro del juego. Lo minimo que hay que tener a mano:

  * El mundo. Los del lobby viven en `SpawnWarps`, que NO es el mundo principal.
  * La altura del piso en esa zona, mirando `/getpos` de pie ahi. Los paneles se
    crean con `down-origin: true`, o sea la coordenada `y` es la BASE del texto:
    con el piso en 24, un `y: 27` deja el texto empezando sobre la cabeza.
  * El area libre real, sus dos esquinas. Un panel de 15 lineas mide ~4,5 bloques
    de alto y varios de ancho; con menos de 8 o 9 bloques de separacion se pisan.
  * Por donde entra y camina la gente. De poco sirve un panel correcto en una
    esquina a la que nadie llega: en este lobby hay franjas de mas de 100 bloques
    donde no pasa nadie.
  * El alcance (`rango`): a cuantos bloques aparece. 24 es el de fabrica y se
    queda corto para un cartel de bienvenida; 40-48 va bien para paneles grandes.

Las zonas ya medidas de este lobby estan documentadas en el informe de documentar_hologramas.py.


FORMATO DEL ARCHIVO DE DEFINICION
-------------------------------------------------------------------------------
    mundo: SpawnWarps
    rango_por_defecto: 40

    hologramas:
      - nombre: info_ejemplo
        x: 197
        y: 27          # base del texto; el piso de esa zona esta en 24
        z: 305
        rango: 48      # opcional
        titulo: "&#FFD700&l✦ TITULO"
        lineas:
          - "&fUna linea normal"
          - "---"      # separador; se expande a una linea tachada gris
          - ""         # hueco; se convierte en un punto tenue

Colores: codigos `&` clasicos y hex `&#RRGGBB`. Cada linea se emite con `&r`
delante para que el formato de la anterior no se arrastre.


DOS TRAMPAS DE DECENTHOLOGRAMS, APRENDIDAS A GOLPES
-------------------------------------------------------------------------------
1. `downorigin` y `setdisplayrange` EXIGEN el prefijo `hologram`:
   `/dh hologram downorigin <n> true`. Sin el responde "Unknown sub command" y
   no pasa nada, pero el comando se envia igual: si solo compruebas el envio,
   crees que funciono. `create`, `move`, `delete` y `line` si van sueltos.
2. Una linea cuyo contenido sea un espacio hace que el plugin escriba
   literalmente `Blank Line`. Por eso "" se traduce a un punto gris.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[ERROR] falta PyYAML (pip install pyyaml)")
    sys.exit(1)

def _localizar_control():
    """Busca control_drakescraft.py al lado de este script, o en el AI Hub."""
    aqui = Path(__file__).resolve().parent / "control_drakescraft.py"
    if aqui.is_file():
        return aqui
    return Path.home() / "ai-hub/scripts/control_drakescraft.py"


CONTROL = _localizar_control()
PAUSA = 0.9                     # el servidor esta en produccion: sin prisa
SEPARADOR = "&8&m--------------------------------------"
HUECO = "&8·"                   # un espacio suelto daria 'Blank Line'


def consola(cmd, simular=False):
    """Manda un comando a la consola del servidor.

    Devuelve True si el ENVIO salio bien. Ojo: no garantiza que el servidor lo
    haya aceptado. Para eso hay que mirar los logs o releer el YAML del
    holograma; ver la trampa 1 del encabezado.
    """
    if simular:
        print(f"        /{cmd}")
        return True
    try:
        r = subprocess.run([sys.executable, str(CONTROL), "cmd", cmd],
                           capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print(f"[ERROR] timeout: {cmd[:70]}")
        return False
    except OSError as e:
        print(f"[ERROR] no se pudo ejecutar el control: {e}")
        return False
    if r.returncode != 0:
        print(f"[ERROR] rc={r.returncode}: {cmd[:70]}")
        return False
    return True


def contenido(linea):
    """Traduce las abreviaturas del archivo al texto que espera el plugin."""
    if linea == "---":
        return "&r" + SEPARADOR
    if not str(linea).strip():
        return "&r" + HUECO
    return "&r" + str(linea)


def aplicar(h, mundo, rango_defecto, simular=False):
    """Borra y rehace un holograma completo. Idempotente a proposito."""
    nombre = h["nombre"]
    x, y, z = h["x"], h["y"], h["z"]
    rango = h.get("rango", rango_defecto)
    lineas = h.get("lineas", [])

    print(f"[INFO] {nombre}  ->  {mundo} {x},{y},{z}  rango {rango}  "
          f"({len(lineas)+1} lineas)")

    pasos = [
        f"dh delete {nombre}",
        f"dh create {nombre} -l:{mundo}:{x}:{y}:{z} &r{h['titulo']}",
    ]
    pasos += [f"dh line add {nombre} 1 {contenido(l)}" for l in lineas]
    # estos dos NO funcionan sin el prefijo 'hologram'
    pasos += [
        f"dh hologram downorigin {nombre} true",
        f"dh hologram setdisplayrange {nombre} {rango}",
    ]

    fallos = 0
    for p in pasos:
        if not consola(p, simular):
            fallos += 1
        if not simular:
            time.sleep(PAUSA)
    if fallos:
        print(f"[ERROR] {nombre}: {fallos} comandos no se pudieron enviar")
    else:
        print(f"[SUCCESS] {nombre}")
    return fallos


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("definicion", help="archivo YAML con los hologramas")
    ap.add_argument("--solo", metavar="NOMBRE", action="append",
                    help="aplicar unicamente estos (repetible)")
    ap.add_argument("--simular", action="store_true",
                    help="imprimir los comandos sin tocar el servidor")
    args = ap.parse_args()

    ruta = Path(args.definicion)
    if not ruta.is_file():
        print(f"[ERROR] no existe {ruta}")
        return 1
    if not args.simular and not CONTROL.is_file():
        print(f"[ERROR] no existe {CONTROL}")
        return 1

    try:
        d = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        print(f"[ERROR] YAML invalido: {e}")
        return 1

    mundo = d.get("mundo", "SpawnWarps")
    rango_defecto = d.get("rango_por_defecto", 40)
    hologramas = d.get("hologramas", [])
    if args.solo:
        hologramas = [h for h in hologramas if h["nombre"] in args.solo]
        if not hologramas:
            print(f"[ERROR] ninguno de {args.solo} esta en {ruta.name}")
            return 1

    if args.simular:
        print("[INFO] modo simulacion: no se envia nada al servidor")

    fallos = sum(aplicar(h, mundo, rango_defecto, args.simular)
                 for h in hologramas)

    print(f"[{'ERROR' if fallos else 'SUCCESS'}] "
          f"{len(hologramas)} hologramas procesados, {fallos} envios fallidos")
    if not args.simular:
        print("[INFO] comprueba el resultado real con:\n"
              "       python3 operacion/documentar_hologramas.py")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
