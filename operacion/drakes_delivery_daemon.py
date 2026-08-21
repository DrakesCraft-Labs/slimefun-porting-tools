#!/usr/bin/env python3
"""
drakes_delivery_daemon.py
Daemon de entrega automática de compras DrakesCraft.
Cada 30s consulta la cola de pending-purchases, ejecuta los comandos en el servidor
Minecraft vía Pterodactyl y notifica a Discord.

Variables de entorno requeridas:
  STORE_API_KEY       — clave para /api/store/pending y /api/store/confirm
  PTERODACTYL_KEY     — Client API Key de Pterodactyl (o leer de /opt/keys/pterodactyl_key)
  DISCORD_WEBHOOK_URL — webhook del canal de pagos
  STORE_BASE_URL      — URL base del portal (default: http://127.0.0.1:8081)
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ─── Configuración ───────────────────────────────────────────────────────────

STORE_BASE_URL    = os.environ.get("STORE_BASE_URL", "http://127.0.0.1:8081")
STORE_API_KEY     = os.environ.get("STORE_API_KEY", "")
DISCORD_WEBHOOK   = os.environ.get("DISCORD_WEBHOOK_URL", "")
# El panel y el identificador del servidor salen del entorno, no del codigo.
# El id no es un secreto por si solo --hace falta la API key, que se lee aparte-- pero identifica
# la instancia concreta, y este repositorio es publico. Define DRAKES_PANEL_SERVER con el id y,
# si algun dia cambias de proveedor, DRAKES_PANEL_URL con la base del panel.
_PANEL = os.environ.get("DRAKES_PANEL_URL", "https://panel.thegamehosting.com")
_SERVIDOR = os.environ.get("DRAKES_PANEL_SERVER", "")
if not _SERVIDOR:
    print("[ERROR] Falta DRAKES_PANEL_SERVER con el id del servidor en el panel.")
    sys.exit(1)
PTERO_BASE = f"{_PANEL}/api/client/servers/{_SERVIDOR}"
LOG_FILE          = Path("/opt/stacks/drakes-delivery/delivery.log")
POLL_INTERVAL     = 30  # segundos

# Leer Pterodactyl key: primero env, luego archivo
def load_ptero_key() -> str:
    key = os.environ.get("PTERODACTYL_KEY", "")
    if key:
        return key
    key_file = Path("/opt/keys/pterodactyl_key")
    if key_file.exists():
        return key_file.read_text().strip()
    raise RuntimeError("PTERODACTYL_KEY no configurada")

# ─── Comandos por producto ────────────────────────────────────────────────────
# {nick} se reemplaza por el nick del jugador

PRODUCT_COMMANDS: dict[str, list[str]] = {
    # Rangos VIP (mensual)
    "hercules":  ["lp user {nick} parent set hercules", "ess kit hercules {nick}"],
    "hestia":    ["lp user {nick} parent set hestia",   "ess kit hestia {nick}"],
    "hermes":    ["lp user {nick} parent set hermes",   "ess kit hermes {nick}"],
    "hefesto":   ["lp user {nick} parent set hefesto",  "ess kit hefesto {nick}"],
    "artemisa":  ["lp user {nick} parent set artemisa", "ess kit artemisa {nick}"],
    "afrodita":  ["lp user {nick} parent set afrodita", "ess kit afrodita {nick}"],
    "zeus":      ["lp user {nick} parent set zeus",     "ess kit zeus {nick}"],
    # Kits comprables directamente
    "kit-hermes": ["ess kit hermes {nick}"],
    "kit-zeus":   ["ess kit zeus {nick}"],
    # Roles de juego
    "minero":      ["lp user {nick} parent set minero",      "ess kit minero {nick}"],
    "cazador":     ["lp user {nick} parent set cazador",     "ess kit cazador {nick}"],
    "constructor": ["lp user {nick} parent set constructor", "ess kit constructor {nick}"],
    "lenador":     ["lp user {nick} parent set lenador",     "ess kit lenador {nick}"],
    "alquimista":  ["lp user {nick} parent set alquimista",  "ess kit alquimista {nick}"],
    "nomada":      ["lp user {nick} parent set nomada",      "ess kit nomada {nick}"],
    # Dragmas (economía)
    "dragmas-saco":  ["eco give {nick} 50000"],
    "dragmas-cofre": ["eco give {nick} 250000"],
    "dragmas-anfora":["eco give {nick} 1000000"],
}

# ─── Utilidades HTTP ──────────────────────────────────────────────────────────

def http_get(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())

def http_post(url: str, headers: dict, body: dict | None = None) -> dict | None:
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json",
        **headers
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        text = r.read().decode()
        return json.loads(text) if text else None

# ─── Log ─────────────────────────────────────────────────────────────────────

def log(level: str, msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ─── Pterodactyl: ejecutar comando en consola ─────────────────────────────────

def ptero_send_command(ptero_key: str, command: str) -> bool:
    try:
        http_post(
            f"{PTERO_BASE}/command",
            headers={
                "Authorization": f"Bearer {ptero_key}",
                "Accept": "application/json",
            },
            body={"command": command}
        )
        return True
    except Exception as e:
        log("ERROR", f"Pterodactyl command failed '{command}': {e}")
        return False

# ─── Discord: notificación de entrega ────────────────────────────────────────

def notify_discord(nick: str, product_name: str, txn_id: str) -> None:
    if not DISCORD_WEBHOOK:
        return
    payload = {
        "username": "DrakesCraft · Entregas",
        "avatar_url": "https://web.drakescraft.cl/assets/logo-drakescraft.png",
        "embeds": [{
            "title": "✅ Entrega Completada",
            "description": f"Se entregó **{product_name}** al jugador `{nick}` exitosamente.",
            "color": 3066993,  # verde esmeralda
            "fields": [
                {"name": "🎮 Nick", "value": f"`{nick}`", "inline": True},
                {"name": "📦 Producto", "value": f"`{product_name}`", "inline": True},
                {"name": "🔑 ID Transacción", "value": f"`{txn_id}`", "inline": False},
            ],
            "footer": {
                "text": f"DrakesCraft · Delivery Bot · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
            }
        }]
    }
    try:
        http_post(DISCORD_WEBHOOK, headers={}, body=payload)
    except Exception as e:
        log("WARN", f"Discord notification failed: {e}")

def notify_discord_skipped(txn_id: str, product_name: str, reason: str) -> None:
    """Notifica en Discord cuando se omite una entrega (nick vacío, etc.)."""
    if not DISCORD_WEBHOOK:
        return
    payload = {
        "username": "DrakesCraft · Entregas",
        "avatar_url": "https://web.drakescraft.cl/assets/logo-drakescraft.png",
        "embeds": [{
            "title": "⚠️ Entrega Omitida — Intervención Manual Requerida",
            "description": f"No se pudo entregar **{product_name}** automáticamente.",
            "color": 15158332,  # rojo
            "fields": [
                {"name": "🔑 ID Transacción", "value": f"`{txn_id}`", "inline": False},
                {"name": "❓ Razón", "value": reason, "inline": False},
            ],
            "footer": {"text": "DrakesCraft · Delivery Bot"}
        }]
    }
    try:
        http_post(DISCORD_WEBHOOK, headers={}, body=payload)
    except Exception as e:
        log("WARN", f"Discord skip notification failed: {e}")

# ─── Ciclo principal ──────────────────────────────────────────────────────────

def process_pending(ptero_key: str) -> None:
    store_headers = {"x-api-key": STORE_API_KEY}

    try:
        pending: list[dict] = http_get(f"{STORE_BASE_URL}/api/store/pending", store_headers)
    except Exception as e:
        log("ERROR", f"No se pudo obtener la cola de pendientes: {e}")
        return

    if not pending:
        return

    log("INFO", f"{len(pending)} entrega(s) pendiente(s)")

    for purchase in pending:
        txn_id      = purchase.get("id", "")
        nick        = purchase.get("nick", "").strip()
        product_id  = purchase.get("productId", "")
        product_name= purchase.get("productName", product_id)

        # Nick vacío → notificar y omitir (no se puede entregar sin nick)
        if not nick:
            log("WARN", f"[{txn_id}] Nick vacío para producto '{product_name}' — requiere entrega manual")
            notify_discord_skipped(txn_id, product_name, "El nick del jugador estaba vacío en el momento del pago. Entregar manualmente.")
            # Remover de la cola para no spamear Discord en cada ciclo
            try:
                http_post(f"{STORE_BASE_URL}/api/store/confirm", store_headers, {"id": txn_id})
            except Exception as e:
                log("ERROR", f"No se pudo confirmar/remover {txn_id}: {e}")
            continue

        commands = PRODUCT_COMMANDS.get(product_id)
        if not commands:
            log("WARN", f"[{txn_id}] Producto '{product_id}' sin comandos definidos — requiere entrega manual")
            notify_discord_skipped(txn_id, product_name, f"El producto `{product_id}` no tiene comandos de entrega automática definidos.")
            try:
                http_post(f"{STORE_BASE_URL}/api/store/confirm", store_headers, {"id": txn_id})
            except Exception as e:
                log("ERROR", f"No se pudo confirmar/remover {txn_id}: {e}")
            continue

        log("INFO", f"[{txn_id}] Entregando '{product_name}' → {nick}")
        all_ok = True
        for cmd_template in commands:
            cmd = cmd_template.replace("{nick}", nick)
            success = ptero_send_command(ptero_key, cmd)
            if not success:
                all_ok = False
            time.sleep(0.5)  # pausa entre comandos

        if all_ok:
            # Confirmar entrega en la cola
            try:
                http_post(f"{STORE_BASE_URL}/api/store/confirm", store_headers, {"id": txn_id})
                log("SUCCESS", f"[{txn_id}] '{product_name}' entregado a {nick}")
                notify_discord(nick, product_name, txn_id)
            except Exception as e:
                log("ERROR", f"No se pudo confirmar entrega {txn_id}: {e}")
        else:
            log("ERROR", f"[{txn_id}] Falló la entrega de '{product_name}' a {nick} — se reintentará")


def main() -> None:
    if not STORE_API_KEY:
        print("[ERROR] STORE_API_KEY no configurada", file=sys.stderr)
        sys.exit(1)

    try:
        ptero_key = load_ptero_key()
    except RuntimeError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    log("INFO", "Daemon de entregas DrakesCraft iniciado")

    while True:
        try:
            process_pending(ptero_key)
        except Exception as e:
            log("ERROR", f"Error inesperado en ciclo: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
