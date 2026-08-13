#!/usr/bin/env python3
"""Reinicia DrakesCraft avisando antes y guardando. Se ejecuta EN star.

POR QUE NO SE USA /restart30

Ese es un comando de JUGADOR. Mandado por consola no produce ni una linea en el log: ni error ni
cuenta atras. El 12-08-2026 se intento y el servidor siguio en pie con el despliegue a medias.
Desde fuera del juego la unica via que funciona es la señal de energia de Pterodactyl, que no
avisa a nadie -- de ahi que la cuenta atras haya que darla a mano con `say`.

QUE HACE

  1. Avisa con cuenta atras por el chat.
  2. Cierra los inventarios abiertos, para que nadie pierda objetos que esten en un menu de
     maquina cuando el servidor caiga.
  3. `save-all flush`, y espera a que termine.
  4. Manda la señal de reinicio.

Uso:  reinicio_seguro.py [segundos-de-aviso] ["motivo"]
"""
import subprocess
import sys
import time

CONTROL = ["python3", "/home/jack/ai-hub/scripts/control_drakescraft.py"]


def consola(comando):
    subprocess.run(CONTROL + ["cmd", comando], capture_output=True, timeout=60)


def anunciar(texto):
    consola(f"say {texto}")
    print(f"  aviso: {texto}")


def main():
    espera = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    motivo = sys.argv[2] if len(sys.argv) > 2 else "actualizacion de plugins"

    # Los avisos se dan en los momentos en que a un jugador le da tiempo a reaccionar: guardar lo
    # que lleva, salir de una cueva, cerrar un cofre.
    hitos = [h for h in (120, 60, 30, 10) if h <= espera]
    anunciar(f"§e§lREINICIO§r §7en §f{espera}s §7por §f{motivo}§7. Terminad lo que esteis haciendo.")

    restante = espera
    for h in hitos:
        if h >= restante:
            continue
        time.sleep(restante - h)
        restante = h
        anunciar(f"§e§lREINICIO§r §7en §f{h}s§7.")
    if restante > 0:
        time.sleep(restante)

    anunciar("§c§lREINICIANDO§r §7ahora. Volvemos en un par de minutos.")

    # Cerrar menus abiertos: si el servidor cae con un jugador dentro del menu de una maquina, lo
    # que tenga en el cursor se pierde.
    consola("kick @a Reinicio del servidor. Vuelve en un par de minutos.")
    time.sleep(2)

    print("  guardando...")
    consola("save-all flush")
    time.sleep(20)

    print("  mandando la señal de reinicio...")
    r = subprocess.run(CONTROL + ["restart"], capture_output=True, text=True, timeout=120)
    print("  ", (r.stdout or r.stderr).strip()[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
