#!/usr/bin/env python3
"""Calcula las metricas de ocupacion de DrakesCraft y las deja para la web.

Se ejecuta una vez al dia desde un timer de systemd. Escribe un JSON en el volumen de datos que
el contenedor de la web ya tiene montado, asi que publicar metricas nuevas **no obliga a
reconstruir la imagen**: el contenedor lo lee en caliente.

DECISIONES QUE IMPORTAN

  - Se cuenta **concurrencia**, no conexiones. Un jugador con mala conexion que reconecta veinte
    veces no son veinte personas.
  - El log del servidor va **+1h respecto a Chile**. Todo se convierte antes de agrupar, porque la
    pregunta que se responde es "a que hora se conecta la gente", no que marca el reloj del
    contenedor.
  - Los **reinicios vacian el servidor**: al ver "Starting minecraft server" se limpia el conjunto
    de conectados, o los que estaban dentro quedarian contados para siempre.
  - Es **incremental**: los dias ya resumidos no se vuelven a leer. Solo se reprocesa el dia en
    curso, que aun esta creciendo. Sin esto, cada noche se releerian 166 archivos por SFTP.
"""
import gzip
import io
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import paramiko

DESFASE_HORAS = 1
SALIDA = "/opt/stacks/drakescraft-web/data/metricas.json"
HISTORIAL = "/home/jack/ai-hub/data/metricas-historial.json"

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

RE_HORA = re.compile(r"^\[(\d{2}):\d{2}:\d{2}\]")
RE_ENTRA = re.compile(r"^\[[\d:]+\] \[Server thread/INFO\]: (?:\S+ )?([A-Za-z0-9_.]+) joined the game")
RE_SALE = re.compile(r"^\[[\d:]+\] \[Server thread/INFO\]: (?:\S+ )?([A-Za-z0-9_.]+) left the game")
RE_LOGIN = re.compile(r"([A-Za-z0-9_.]+)\[/(\d+\.\d+\.\d+\.\d+):\d+\] logged in with entity id")

GEO_DB = "/home/jack/ai-hub/data/geo/dbip.mmdb"

# Nombres en castellano de lo que sale por aqui; el resto cae al codigo ISO tal cual.
PAISES = {
    "CL": "Chile", "AR": "Argentina", "PE": "Perú", "BO": "Bolivia", "CO": "Colombia",
    "VE": "Venezuela", "EC": "Ecuador", "UY": "Uruguay", "PY": "Paraguay", "BR": "Brasil",
    "MX": "México", "ES": "España", "US": "Estados Unidos", "CA": "Canadá", "DO": "R. Dominicana",
    "GT": "Guatemala", "CR": "Costa Rica", "PA": "Panamá", "HN": "Honduras", "SV": "El Salvador",
    "NI": "Nicaragua", "CU": "Cuba", "PR": "Puerto Rico", "PT": "Portugal", "FR": "Francia",
    "DE": "Alemania", "IT": "Italia", "GB": "Reino Unido", "NL": "Países Bajos", "PL": "Polonia",
    "RU": "Rusia", "IN": "India", "PH": "Filipinas", "AU": "Australia",
    "IR": "Irán", "AT": "Austria", "EE": "Estonia", "ID": "Indonesia", "MA": "Marruecos",
    "IQ": "Irak", "BD": "Bangladés", "VN": "Vietnam", "FI": "Finlandia", "HU": "Hungría",
    "JP": "Japón", "QA": "Catar", "PK": "Pakistán", "BE": "Bélgica", "CH": "Suiza",
    "SE": "Suecia", "NO": "Noruega", "DK": "Dinamarca", "IE": "Irlanda", "CZ": "Chequia",
    "RO": "Rumanía", "UA": "Ucrania", "TR": "Turquía", "GR": "Grecia", "IL": "Israel",
    "SA": "Arabia Saudí", "AE": "Emiratos Árabes", "EG": "Egipto", "ZA": "Sudáfrica",
    "NG": "Nigeria", "KE": "Kenia", "TH": "Tailandia", "MY": "Malasia", "SG": "Singapur",
    "KR": "Corea del Sur", "CN": "China", "TW": "Taiwán", "NZ": "Nueva Zelanda",
    "JM": "Jamaica", "TT": "Trinidad y Tobago", "BZ": "Belice", "HT": "Haití",
}


def bandera(iso):
    """Emoji de bandera a partir del codigo ISO, sin tabla: son letras desplazadas."""
    if not iso or len(iso) != 2 or not iso.isalpha():
        return "🏳️"
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in iso.upper())


def refrescar_geo():
    """Baja la base del mes si la que hay pasa de 35 dias.

    DB-IP publica una edicion nueva cada mes. La comprobacion es por fecha del fichero, asi que
    aunque esto se llame cada hora solo se descarga algo una vez al mes. Si falla cualquier cosa
    -sin red, mes aun no publicado, disco lleno- se sigue con la base vieja: una geolocalizacion
    de hace unas semanas es infinitamente mejor que ninguna, y esto no puede tumbar las metricas.
    """
    try:
        if os.path.exists(GEO_DB) and time.time() - os.path.getmtime(GEO_DB) < 35 * 86400:
            return
        import urllib.request
        mes = datetime.now().strftime("%Y-%m")
        url = f"https://download.db-ip.com/free/dbip-country-lite-{mes}.mmdb.gz"
        tmp = GEO_DB + ".nuevo"
        # Sin User-Agent propio el CDN de DB-IP responde 403 al de urllib.
        peticion = urllib.request.Request(url, headers={"User-Agent": "drakescraft-metricas/1.0"})
        with urllib.request.urlopen(peticion, timeout=60) as r, open(tmp, "wb") as f:
            f.write(gzip.decompress(r.read()))
        # Solo se pisa la buena si la nueva se abre y responde.
        import maxminddb
        with maxminddb.open_database(tmp) as prueba:
            if not (prueba.get("8.8.8.8") or {}).get("country"):
                raise ValueError("la base descargada no resuelve")
        os.replace(tmp, GEO_DB)
        print(f"  base geo actualizada a {mes}", file=sys.stderr)
    except Exception as error:
        print(f"  no se pudo actualizar la base geo, se sigue con la actual: {error}",
              file=sys.stderr)


def abrir_geo():
    """El lector de GeoIP, o None si no esta disponible.

    La base es DB-IP Lite, **local**. Se resuelve aqui y se guarda solo el pais: las IP de los
    jugadores no se escriben en el historial, no salen en el JSON y no se mandan a ningun
    tercero. Si falta la base, el resto de metricas sigue funcionando igual.
    """
    try:
        import maxminddb
        return maxminddb.open_database(GEO_DB)
    except Exception as error:
        print(f"  sin geolocalizacion: {error}", file=sys.stderr)
        return None


def conectar():
    env = {}
    for linea in open("/opt/stacks/drakes-updater/.env"):
        linea = linea.strip()
        if "=" in linea and not linea.startswith("#"):
            k, v = linea.split("=", 1)
            env.setdefault(k, v.strip().strip('"').strip("'"))
    t = paramiko.Transport((env["SFTP_HOST"], int(env["SFTP_PORT"])))
    t.connect(username=env["SFTP_USER"], password=env["SFTP_PASS"])
    return paramiko.SFTPClient.from_transport(t), t


def resumir_dia(sftp, archivos, fecha_txt, geo=None):
    """Pico por hora y jugadores distintos de una fecha concreta."""
    fecha = datetime.strptime(fecha_txt, "%Y-%m-%d")
    dentro = set()
    pico_hora = defaultdict(int)
    distintos = set()
    horas_jugador = defaultdict(set)     # nick -> horas (Chile) en que estuvo dentro
    entrada = {}                          # nick -> hora (Chile) en que entro, sesion abierta
    pais_jugador = {}                     # nick -> ISO; la IP se descarta en el acto
    ultima_hora = 0

    def cerrar(nick, hasta):
        """Marca como jugadas todas las horas entre la entrada y la salida.

        Anotar solo la hora del evento se quedaba corto: quien juega de 20:00 a 23:00 marcaba
        {20, 23} y las dos horas centrales -las de mas peso- desaparecian.
        """
        desde = entrada.pop(nick, None)
        if desde is None:
            return
        for h in range(desde, max(desde, hasta) + 1):
            horas_jugador[nick].add(h % 24)

    for nombre in archivos:
        try:
            with sftp.open("/logs/" + nombre, "rb") as f:
                f.prefetch()
                datos = f.read()
            texto = gzip.decompress(datos) if nombre.endswith(".gz") else datos
        except Exception as error:
            print(f"  salto {nombre}: {error}", file=sys.stderr)
            continue

        for linea in io.TextIOWrapper(io.BytesIO(texto), encoding="utf-8", errors="replace"):
            m = RE_HORA.match(linea)
            if not m:
                continue
            if "Starting minecraft server version" in linea:
                for nick in list(entrada):
                    cerrar(nick, ultima_hora)
                dentro.clear()
                continue
            if geo is not None and "logged in with entity id" in linea:
                login = RE_LOGIN.search(linea)
                if login:
                    try:
                        dato = geo.get(login.group(2))
                    except Exception:
                        dato = None
                    iso = (dato or {}).get("country", {}).get("iso_code")
                    if iso:
                        pais_jugador[login.group(1)] = iso

            entra = RE_ENTRA.match(linea)
            sale = None if entra else RE_SALE.match(linea)
            if not (entra or sale):
                continue
            quien = (entra or sale).group(1)
            if entra:
                dentro.add(quien)
            else:
                dentro.discard(quien)
            distintos.add(quien)

            chile = fecha.replace(hour=int(m.group(1))) - timedelta(hours=DESFASE_HORAS)
            # Un evento de las 00:xx del log cae en el dia anterior de Chile; se ignora para no
            # atribuirle actividad a una fecha que no le toca.
            if chile.date() != fecha.date():
                continue
            if len(dentro) > pico_hora[chile.hour]:
                pico_hora[chile.hour] = len(dentro)

            ultima_hora = chile.hour
            if entra:
                entrada.setdefault(quien, chile.hour)
            else:
                cerrar(quien, chile.hour)

    # Quien seguia dentro al acabar el dia: se cierra en la ultima hora con actividad.
    for nick in list(entrada):
        cerrar(nick, ultima_hora)

    return {
        "pico": max(pico_hora.values()) if pico_hora else 0,
        "por_hora": {str(h): v for h, v in sorted(pico_hora.items())},
        "distintos": len(distintos),
        "jugadores": sorted(distintos),
        "horas_jugador": {k: sorted(v) for k, v in horas_jugador.items()},
        "pais_jugador": pais_jugador,
    }


def franja_horaria(conteo_horas):
    """En que parte del dia suele jugar alguien, en palabras.

    Se dan franjas anchas a proposito y no la hora exacta: la pagina es publica y varios jugadores
    son menores. Saber que alguien "juega por la tarde" es sabor de comunidad; publicar que se
    conecta a las 19:40 todos los dias es una rutina.
    """
    if not conteo_horas:
        return "sin datos"
    BANDAS = [
        (range(6, 12), "por la mañana"),
        (range(12, 18), "por la tarde"),
        (range(18, 23), "al caer la noche"),
        (list(range(23, 24)) + list(range(0, 6)), "de madrugada"),
    ]
    pesos = {}
    for horas, nombre in BANDAS:
        pesos[nombre] = sum(conteo_horas.get(h, 0) for h in horas)
    return max(pesos, key=pesos.get) if any(pesos.values()) else "sin datos"


def frase_visitas(visitas, paises_visitas):
    """Los que entraron una o dos veces y no volvieron, contados aparte."""
    if not visitas:
        return ""
    return (f"Además han pasado {len(visitas)} personas de visita, desde "
            f"{len(paises_visitas)} países. Llegan por las listas de servidores, miran y no "
            "vuelven; por eso no cuentan en el mapa de arriba.")


def frase_paises(paises, total):
    """Resume de donde es la gente, sin recitar la lista entera."""
    if not paises:
        return "Todavía no hay datos de procedencia."
    cabeza = paises[0]
    txt = (f"La mayoría juega desde {cabeza['nombre']} ({cabeza['porcentaje']} % de "
           f"{total} jugadores habituales)")
    if len(paises) > 1:
        resto = ", ".join(f"{p['nombre']} ({p['jugadores']})" for p in paises[1:4])
        txt += f", pero también hay gente de {resto}"
        if len(paises) > 4:
            txt += f" y {len(paises) - 4} país{'es' if len(paises) - 4 > 1 else ''} más"
    return txt + f". En total, {len(paises)} países distintos."


def frase_hora(horas_medias):
    """Convierte el reparto horario en una frase legible."""
    if not horas_medias:
        return "todavía no hay datos suficientes"
    mejor = max(horas_medias, key=lambda h: horas_medias[h])
    # Se busca la franja continua alrededor del pico que mantenga al menos el 80 %.
    umbral = horas_medias[mejor] * 0.8
    ini = fin = int(mejor)
    while str(ini - 1) in horas_medias and horas_medias[str(ini - 1)] >= umbral:
        ini -= 1
    while str(fin + 1) in horas_medias and horas_medias[str(fin + 1)] >= umbral:
        fin += 1
    if ini == fin:
        return f"a las {ini:02d}:00"
    return f"entre las {ini:02d}:00 y las {fin + 1:02d}:00"


def main():
    os.makedirs(os.path.dirname(HISTORIAL), exist_ok=True)
    historial = {}
    if os.path.exists(HISTORIAL):
        with open(HISTORIAL, encoding="utf-8") as f:
            historial = json.load(f)

    refrescar_geo()
    geo = abrir_geo()
    sftp, transporte = conectar()
    try:
        todos = [n for n in sftp.listdir("/logs") if re.fullmatch(r"2026-\d{2}-\d{2}-\d+\.log(\.gz)?", n)]
        por_fecha = defaultdict(list)
        for n in todos:
            por_fecha[n[:10]].append(n)

        hoy = datetime.now().strftime("%Y-%m-%d")
        for fecha_txt in sorted(por_fecha):
            # Los dias cerrados solo se calculan una vez; el de hoy siempre se rehace.
            if fecha_txt in historial and fecha_txt != hoy:
                continue
            historial[fecha_txt] = resumir_dia(sftp, sorted(por_fecha[fecha_txt]), fecha_txt, geo)
            print(f"  {fecha_txt}: pico {historial[fecha_txt]['pico']}", file=sys.stderr)
    finally:
        sftp.close()
        transporte.close()

    with open(HISTORIAL, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False)

    # ── Agregados ──────────────────────────────────────────────────────────
    def franja(desde):
        return {d: v for d, v in historial.items() if d >= desde}

    hoy_dt = datetime.now()
    ayer = (hoy_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    semana = franja((hoy_dt - timedelta(days=7)).strftime("%Y-%m-%d"))
    mes = franja((hoy_dt - timedelta(days=30)).strftime("%Y-%m-%d"))

    def agregado(datos, etiqueta):
        if not datos:
            return None
        picos = [d["pico"] for d in datos.values() if d["pico"] > 0]
        distintos = set()
        for d in datos.values():
            distintos.update(d.get("jugadores", []))
        suma_hora = defaultdict(list)
        for d in datos.values():
            for h, v in d.get("por_hora", {}).items():
                suma_hora[h].append(v)
        medias_hora = {h: round(sum(v) / len(v), 1) for h, v in suma_hora.items()}
        por_dia_semana = defaultdict(list)
        for fecha_txt, d in datos.items():
            if d["pico"] > 0:
                por_dia_semana[datetime.strptime(fecha_txt, "%Y-%m-%d").weekday()].append(d["pico"])
        mejor_dia = max(por_dia_semana, key=lambda k: sum(por_dia_semana[k]) / len(por_dia_semana[k])) \
            if por_dia_semana else None
        return {
            "etiqueta": etiqueta,
            "dias": len(datos),
            "pico_medio": round(sum(picos) / len(picos), 1) if picos else 0,
            "pico_maximo": max(picos) if picos else 0,
            "jugadores_distintos": len(distintos),
            "por_hora": medias_hora,
            "mejor_dia": DIAS[mejor_dia] if mejor_dia is not None else None,
            "franja_habitual": frase_hora(medias_hora),
        }

    # ── Perfil por jugador ─────────────────────────────────────────────────
    # Se deriva del historial que ya esta en disco, asi que no cuesta ni una lectura extra.
    perfil = {}
    for fecha_txt in sorted(historial):
        dia = historial[fecha_txt]
        for nick in dia.get("jugadores", []):
            p = perfil.setdefault(nick, {"primera": fecha_txt, "ultima": fecha_txt,
                                         "dias": 0, "horas": defaultdict(int),
                                         "paises": defaultdict(int)})
            p["ultima"] = fecha_txt
            p["dias"] += 1
        for nick, iso in (dia.get("pais_jugador") or {}).items():
            if nick in perfil:
                perfil[nick]["paises"][iso] += 1
        for nick, horas in (dia.get("horas_jugador") or {}).items():
            if nick in perfil:
                for h in horas:
                    perfil[nick]["horas"][h] += 1

    primer_dia = min(historial) if historial else "0000-00-00"
    hoy_txt = hoy_dt.strftime("%Y-%m-%d")
    hace_7 = (hoy_dt - timedelta(days=7)).strftime("%Y-%m-%d")
    hace_30 = (hoy_dt - timedelta(days=30)).strftime("%Y-%m-%d")

    jugadores = []
    for nick, p in perfil.items():
        if p["ultima"] < hace_30:
            continue                      # lleva mas de un mes sin aparecer
        iso_habitual = max(p["paises"], key=p["paises"].get) if p["paises"] else None
        jugadores.append({
            "nick": nick,
            "primera": p["primera"],
            "ultima": p["ultima"],
            "dias": p["dias"],
            # Ojo: solo se puede afirmar de quien apareció despues del primer dia registrado.
            "nuevo": p["primera"] >= hace_7 and p["primera"] > primer_dia,
            "franja": franja_horaria(p["horas"]),
            # Con VPN o de viaje puede haber varios; se queda el habitual.
            "pais": iso_habitual,
            "pais_nombre": PAISES.get(iso_habitual, iso_habitual) if iso_habitual else None,
            "bandera": bandera(iso_habitual) if iso_habitual else "",
        })
    # Los mas constantes primero; a igualdad, quien estuvo mas recientemente.
    jugadores.sort(key=lambda j: (j["dias"], j["ultima"]), reverse=True)
    # Solo cuenta como cara nueva quien volvio otro dia: con el criterio anterior salian 32
    # "nuevos" en una semana, y la mayoria no habia vuelto a entrar.
    nuevos = [j for j in jugadores if j["nuevo"] and j["dias"] >= 2]
    curiosos = len([j for j in jugadores if j["nuevo"] and j["dias"] < 2])

    # La mitad de los que aparecen entraron un solo dia: son curiosos que llegan por las listas de
    # servidores. Mezclarlos con la comunidad da un mapa falso -veinte paises de una sola visita-,
    # asi que se reparten en dos grupos y cada uno se etiqueta por lo que es.
    DIAS_HABITUAL = 3
    habituales = [j for j in jugadores if j["dias"] >= DIAS_HABITUAL]
    visitas = [j for j in jugadores if j["dias"] < DIAS_HABITUAL]

    def repartir(gente):
        conteo = Counter(j["pais"] for j in gente if j["pais"])
        total = sum(conteo.values()) or 1
        return [{"iso": iso, "nombre": PAISES.get(iso, iso), "bandera": bandera(iso),
                 "jugadores": n, "porcentaje": round(n * 100 / total, 1)}
                for iso, n in conteo.most_common()]

    paises = repartir(habituales)
    paises_visitas = repartir(visitas)
    sin_pais = len([j for j in jugadores if not j["pais"]])

    resultado = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "hoy": historial.get(hoy_dt.strftime("%Y-%m-%d"), {"pico": 0, "distintos": 0}),
        "ayer": historial.get(ayer, {"pico": 0, "distintos": 0}),
        "semana": agregado(semana, "últimos 7 días"),
        "mes": agregado(mes, "últimos 30 días"),
        "historico": {d: v["pico"] for d, v in sorted(historial.items())[-60:]},
        "jugadores": jugadores,
        "nuevos": [j["nick"] for j in nuevos],
        "paises": paises,
        "paises_visitas": paises_visitas,
        "habituales": len(habituales),
        "visitas": len(visitas),
        "sin_pais": sin_pais,
    }

    # Frases listas para pintar, para que la web no tenga que razonar sobre los numeros.
    m = resultado["mes"]
    s = resultado["semana"]
    resultado["frases"] = {
        "mes": (f"La media de este mes fue de {m['pico_medio']} jugadores conectados a la vez, "
                f"con un máximo de {m['pico_maximo']}. La gente suele estar conectada "
                f"{m['franja_habitual']} (hora chilena), y el día más movido es el {m['mejor_dia']}.")
        if m else "Todavía no hay datos de este mes.",
        "semana": (f"En los últimos 7 días el pico medio fue de {s['pico_medio']} jugadores, "
                   f"con {s['jugadores_distintos']} personas distintas pasando por el servidor.")
        if s else "Todavía no hay datos de esta semana.",
        "paises": frase_paises(paises, len(habituales)),
        "visitas": frase_visitas(visitas, paises_visitas),
        "nuevos": ((f"Esta semana ha llegado {len(nuevos)} jugador nuevo que se ha quedado."
                    if len(nuevos) == 1
                    else f"Esta semana han llegado {len(nuevos)} jugadores nuevos que se han quedado.")
                   if nuevos else "Esta semana no se ha quedado nadie nuevo todavía.")
        + (f" Otras {curiosos} personas entraron una vez y no volvieron." if curiosos else ""),
        "hoy": (f"Hoy el máximo simultáneo va en {resultado['hoy'].get('pico', 0)} jugadores, "
                f"con {resultado['hoy'].get('distintos', 0)} personas distintas."),
    }

    # En hoy/ayer se conservan los nicks: es lo que alimenta "quien anduvo por aqui".
    resultado["hoy"]["jugadores"] = historial.get(hoy_txt, {}).get("jugadores", [])
    for bloque in ("hoy", "ayer"):
        resultado[bloque].pop("horas_jugador", None)

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    tmp = SALIDA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=1)
    os.replace(tmp, SALIDA)      # escritura atomica: la web nunca lee un JSON a medias
    print(f"escrito {SALIDA}", file=sys.stderr)
    print(resultado["frases"]["mes"])


if __name__ == "__main__":
    main()
