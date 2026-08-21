#!/usr/bin/env python3
import sys
import os
import urllib.request
import urllib.parse
import json
import mimetypes
import socket
import time
from contextlib import contextmanager
from pathlib import Path

import requests

# El panel y el identificador del servidor salen del entorno, no del codigo.
# El id no es un secreto por si solo --hace falta la API key, que se lee aparte-- pero identifica
# la instancia concreta, y este repositorio es publico. Define DRAKES_PANEL_SERVER con el id y,
# si algun dia cambias de proveedor, DRAKES_PANEL_URL con la base del panel.
_PANEL = os.environ.get("DRAKES_PANEL_URL", "https://panel.thegamehosting.com")
_SERVIDOR = os.environ.get("DRAKES_PANEL_SERVER", "")
if not _SERVIDOR:
    print("[ERROR] Falta DRAKES_PANEL_SERVER con el id del servidor en el panel.")
    sys.exit(1)
BASE_URL = f"{_PANEL}/api/client/servers/{_SERVIDOR}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# Buscar la API key en el archivo privado en C:\Users\jack\ai-hub\.pterodactyl_key
dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
key_path = os.path.join(dir_path, ".pterodactyl_key")

if not os.path.exists(key_path):
    print(f"[ERROR] No se encontró la API Key en: {key_path}")
    print("Por favor crea el archivo con la Client API Key de Pterodactyl como única línea.")
    sys.exit(1)

with open(key_path, "r") as f:
    api_key = f.read().strip()


@contextmanager
def temporary_dns_overrides():
    """Aplica overrides DNS durante una conexión sin alterar TLS/SNI."""
    raw_overrides = os.environ.get("DRAKES_DNS_OVERRIDES", "")
    overrides = {}
    for entry in raw_overrides.split(","):
        if "=" in entry:
            host, address = entry.split("=", 1)
            overrides[host.strip().lower()] = address.strip()
    if not overrides:
        yield
        return

    original = socket.getaddrinfo

    def resolve(host, port, family=0, type=0, proto=0, flags=0):
        target = overrides.get(str(host).lower(), host)
        return original(target, port, family, type, proto, flags)

    socket.getaddrinfo = resolve
    try:
        yield
    finally:
        socket.getaddrinfo = original


def open_url(request, *, timeout, data=None):
    """Abre una URL con el override DNS temporal configurado."""
    with temporary_dns_overrides():
        return urllib.request.urlopen(request, data=data, timeout=timeout)


def send_request(endpoint, method="GET", data=None):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", USER_AGENT)
    
    if data is not None:
        req.add_header("Content-Type", "application/json")
        json_data = json.dumps(data).encode("utf-8")
    else:
        json_data = None
        
    try:
        with open_url(req, timeout=60, data=json_data) as res:
            body = res.read().decode("utf-8")
            if body:
                return json.loads(body)
            return {"status": "ok"}
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP Error {e.code}: {e.read().decode('utf-8')}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


def read_server_file(remote_path):
    """Lee un archivo del servidor por la API para evitar caches del montaje Y:."""
    endpoint = "/files/contents?file=" + urllib.parse.quote(remote_path)
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", method="GET")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Accept", "text/plain")
    req.add_header("User-Agent", USER_AGENT)

    try:
        with open_url(req, timeout=30) as res:
            return res.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP Error {e.code} al leer {remote_path}")
        sys.exit(1)
    except Exception as error:
        print(f"[ERROR] No se pudo leer {remote_path}: {type(error).__name__}")
        sys.exit(1)


def download_server_file(remote_path, local_path):
    """Descarga bytes mediante la URL firmada de Pterodactyl."""
    destination = Path(local_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    last_error = None
    for attempt in range(1, 6):
        try:
            response = send_request("/files/download?file=" + urllib.parse.quote(remote_path))
            url = response["attributes"]["url"]
            with temporary_dns_overrides(), requests.get(url, stream=True, timeout=(30, 300)) as result:
                result.raise_for_status()
                with partial.open("wb") as handle:
                    for chunk in result.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            handle.write(chunk)
            partial.replace(destination)
            return destination
        except (Exception, SystemExit) as error:
            last_error = error
            partial.unlink(missing_ok=True)
            if attempt < 5:
                print(f"[WARN] Reintentando descarga ({attempt}/5): {type(error).__name__}")
                time.sleep(5)
    print(f"[ERROR] No se pudo descargar {remote_path}: {type(last_error).__name__}")
    sys.exit(1)


def upload_server_file(local_path, remote_directory):
    """Sube un archivo mediante multipart a la URL firmada del panel."""
    source = Path(local_path)
    if not source.is_file():
        print(f"[ERROR] No existe el archivo local: {source}")
        sys.exit(1)

    response = None
    for attempt in range(1, 6):
        try:
            response = send_request("/files/upload")
            break
        except SystemExit:
            if attempt == 5:
                raise
            print(f"[WARN] Reintentando URL firmada de subida ({attempt}/5)...")
            time.sleep(3)
    if response is None:
        print("[ERROR] El panel no entregó una URL firmada de subida.")
        sys.exit(1)
    url = response["attributes"]["url"]
    content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
    last_error = None
    for attempt in range(1, 6):
        try:
            with source.open("rb") as handle, temporary_dns_overrides():
                upload_url = url + "&directory=" + urllib.parse.quote(remote_directory)
                result = requests.post(
                    upload_url,
                    files={"files": (source.name, handle, content_type)},
                    timeout=(30, 1200),
                )
                result.raise_for_status()
            return
        except Exception as error:
            last_error = error
            if attempt == 5:
                break
            print(f"[WARN] Reintentando transferencia al nodo ({attempt}/5): {type(error).__name__}")
            time.sleep(5)
            try:
                response = send_request("/files/upload")
                url = response["attributes"]["url"]
            except SystemExit:
                time.sleep(5)
    print(f"[ERROR] No se pudo subir {source}: {type(last_error).__name__}")
    sys.exit(1)


def write_server_file(remote_path, local_path):
    """Escribe un archivo textual validado en una ruta exacta del servidor."""
    source = Path(local_path)
    if not source.is_file():
        print(f"[ERROR] No existe el archivo local: {source}")
        sys.exit(1)
    url = f"{BASE_URL}/files/write?file=" + urllib.parse.quote(remote_path)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/octet-stream",
        "User-Agent": USER_AGENT,
    }
    last_error = None
    for attempt in range(1, 4):
        try:
            with source.open("rb") as handle, temporary_dns_overrides():
                result = requests.post(url, headers=headers, data=handle, timeout=(30, 1200))
                result.raise_for_status()
            return
        except Exception as error:
            last_error = error
            if attempt < 3:
                print(f"[WARN] Reintentando escritura vía panel ({attempt}/3): {type(error).__name__}")
                time.sleep(5)
    print(f"[ERROR] No se pudo escribir {remote_path}: {type(last_error).__name__}")
    sys.exit(1)
def print_help():
    print("DrakesCraft Server Control CLI Tool")
    print("-----------------------------------")
    print("Uso: python control_drakescraft.py <acción> [argumentos]")
    print("\nAcciones disponibles:")
    print("  status            Ver estado básico del servidor y límites")
    print("  resources         Ver consumo en tiempo real (CPU, RAM, Disco)")
    print("  cmd <comando>     Enviar un comando de Minecraft a la consola")
    print("  restart           Reiniciar el servidor de Minecraft")
    print("  stop              Detener el servidor de Minecraft")
    print("  start             Iniciar el servidor de Minecraft")
    print("  kill              Forzar apagado del proceso (Kill)")
    print("  logs [líneas]     Leer las últimas líneas del archivo Y:\\logs\\latest.log")
    print("  live-logs [líneas] Leer latest.log directamente por Pterodactyl")
    print("  download <remoto> <local> Descargar un archivo mediante Pterodactyl")
    print("  upload <local> <directorio> Subir un archivo al directorio remoto")
    print("  write <local> <remoto> Escribir un archivo textual exacto")
    print("  list <directorio> Listar un directorio remoto")
    print("  mkdir <raíz> <nombre> Crear un directorio remoto")
    print("  rename <raíz> <origen> <destino> Renombrar o mover una ruta")

def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
        
    action = sys.argv[1].lower()
    
    if action == "status":
        res = send_request("")
        attr = res["attributes"]
        limits = attr["limits"]
        print("=== ESTADO DEL SERVIDOR ===")
        print(f"Nombre:    {attr['name']}")
        print(f"ID:        {attr['identifier']}")
        print(f"Nodo:      {attr['node']}")
        print(f"IP:        {attr['relationships']['allocations']['data'][0]['attributes']['ip']}:{attr['relationships']['allocations']['data'][0]['attributes']['port']}")
        print(f"Memoria:   {limits['memory']} MB")
        print(f"Disco:     {limits['disk']} MB")
        print(f"CPU Limit: {limits['cpu']}%")
        
    elif action == "resources":
        res = send_request("/resources")
        attr = res["attributes"]
        resources = attr["resources"]
        mem_mb = round(resources["memory_bytes"] / (1024 * 1024), 2)
        disk_mb = round(resources["disk_bytes"] / (1024 * 1024), 2)
        print("=== RECURSOS EN TIEMPO REAL ===")
        print(f"Estado:    {attr['current_state']}")
        print(f"CPU:       {attr['resources']['cpu_absolute']}%")
        print(f"Memoria:   {mem_mb} MB")
        print(f"Disco:     {disk_mb} MB")
        print(f"Uptime:    {resources['uptime']} ms")
        
    elif action == "cmd":
        if len(sys.argv) < 3:
            print("[ERROR] Debes especificar el comando entre comillas. Ejemplo: python control_drakescraft.py cmd \"list\"")
            sys.exit(1)
        cmd = sys.argv[2]
        print(f"Enviando comando a consola: {cmd}")
        send_request("/command", method="POST", data={"command": cmd})
        print("Comando enviado con éxito.")
        
    elif action in ["restart", "stop", "start", "kill"]:
        signal = action
        print(f"Enviando señal de energía: {signal}")
        send_request("/power", method="POST", data={"signal": signal})
        print("Señal de energía enviada con éxito.")
        
    elif action == "logs":
        num_lines = 30
        if len(sys.argv) >= 3:
            try:
                num_lines = int(sys.argv[2])
            except ValueError:
                pass
        
        log_path = "Z:\\logs\\latest.log" if os.path.exists("Z:\\logs\\latest.log") else "Y:\\logs\\latest.log"
        if not os.path.exists(log_path):
            print(f"[ERROR] No se pudo encontrar la ruta montada {log_path}")
            print("Asegúrate de que RaiDrive o rclone estén activos y montando la unidad de red.")
            sys.exit(1)
            
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                print(f"=== ÚLTIMAS {num_lines} LÍNEAS DE Y:\\logs\\latest.log ===")
                for line in lines[-num_lines:]:
                    sys.stdout.buffer.write(line.encode("utf-8", errors="replace"))
        except Exception as e:
            print(f"[ERROR] Al leer latest.log: {e}")

    elif action == "live-logs":
        num_lines = 100
        if len(sys.argv) >= 3:
            try:
                num_lines = max(1, int(sys.argv[2]))
            except ValueError:
                print("[ERROR] El número de líneas debe ser un entero positivo.")
                sys.exit(1)

        lines = read_server_file("/logs/latest.log").splitlines()
        print(f"=== ÚLTIMAS {num_lines} LÍNEAS DESDE PTERODACTYL ===")
        for line in lines[-num_lines:]:
            sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))

    elif action == "download":
        if len(sys.argv) != 4:
            print("[ERROR] Uso: download <ruta-remota> <ruta-local>")
            sys.exit(1)
        destination = download_server_file(sys.argv[2], sys.argv[3])
        print(f"Descargado: {destination}")

    elif action == "upload":
        if len(sys.argv) != 4:
            print("[ERROR] Uso: upload <ruta-local> <directorio-remoto>")
            sys.exit(1)
        upload_server_file(sys.argv[2], sys.argv[3])
        print(f"Subido: {sys.argv[2]} -> {sys.argv[3]}")

    elif action == "write":
        if len(sys.argv) != 4:
            print("[ERROR] Uso: write <ruta-local> <ruta-remota>")
            sys.exit(1)
        write_server_file(sys.argv[3], sys.argv[2])
        print(f"Escrito: {sys.argv[2]} -> {sys.argv[3]}")

    elif action == "list":
        if len(sys.argv) != 3:
            print("[ERROR] Uso: list <directorio-remoto>")
            sys.exit(1)
        response = send_request("/files/list?directory=" + urllib.parse.quote(sys.argv[2]))
        for entry in response.get("data", []):
            attributes = entry.get("attributes", {})
            print(f"{attributes.get('name')}\t{attributes.get('size')}\t{attributes.get('is_file')}")

    elif action == "mkdir":
        if len(sys.argv) != 4:
            print("[ERROR] Uso: mkdir <raíz-remota> <nombre>")
            sys.exit(1)
        send_request("/files/create-folder", method="POST", data={"root": sys.argv[2], "name": sys.argv[3]})
        print(f"Directorio creado: {sys.argv[2]}/{sys.argv[3]}")

    elif action == "rename":
        if len(sys.argv) != 5:
            print("[ERROR] Uso: rename <raíz-remota> <origen> <destino>")
            sys.exit(1)
        send_request(
            "/files/rename",
            method="PUT",
            data={"root": sys.argv[2], "files": [{"from": sys.argv[3], "to": sys.argv[4]}]},
        )
        print(f"Renombrado: {sys.argv[3]} -> {sys.argv[4]}")
            
    else:
        print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
