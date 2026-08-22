#!/usr/bin/env python3
"""Amplia y corrige el contenido de ChatGames.

Regla de oro, impuesta por como compara el plugin (ver cg_validar.py): la respuesta va **sin
tildes**, en **una palabra** siempre que se pueda, y si son dos la pregunta avisa del formato.
"""
import re
import sys
from pathlib import Path

import yaml

CARPETA = Path(sys.argv[1])

# ── Preguntas de trivia que hoy son imposibles de acertar ────────────────────
# Se localizan por su respuesta actual y se reemplaza el par entero.
ARREGLOS = {
    "ps add": ("<yellow>[DRAKES] Comando para gestionar tu proteccion de terreno? (una palabra, sin barra)</yellow>", "ps"),
    "sf guide": ("<yellow>[SLIMEFUN] Que palabra va despues de /sf para abrir la guia? (una palabra)</yellow>", "guide"),
    "Pickaxe of Distortion": ("<yellow>[SLIMEFUN] El pico que recoge maquinas intactas es el 'Pickaxe of...'? (una palabra en ingles)</yellow>", "distortion"),
    "Trial Chambers": ("<yellow>[MC 1.21] Estructura con desafios y llaves de prueba? (dos palabras en ingles)</yellow>", "trial chambers"),
    "Ancient Debris": ("<yellow>[MINECRAFT] Mineral del Nether del que sale la netherita? (dos palabras en ingles)</yellow>", "ancient debris"),
    "Deep Dark": ("<yellow>[MINECRAFT] Bioma oscuro donde habita el Warden? (dos palabras en ingles)</yellow>", "deep dark"),
    "Via Lactea": ("<yellow>[ASTRONOMIA] Cuantos planetas tiene el Sistema Solar? (solo el numero)</yellow>", "8"),
    "Agujero negro": ("<yellow>[ASTRONOMIA] Objeto del que ni la luz escapa? (dos palabras, sin tildes)</yellow>", "agujero negro"),
    "Ticks por segundo": ("<yellow>[LOGICA] Siglas que miden el rendimiento de un servidor de Minecraft?</yellow>", "TPS"),
    "Cordillera de los Andes": ("<yellow>[GEOGRAFIA] Cordillera que recorre Chile de norte a sur? (una palabra)</yellow>", "Andes"),
    "Da Vinci": ("<yellow>[CULTURA] Apellido del pintor de la Mona Lisa? (dos palabras)</yellow>", "da vinci"),
}

TRIVIA_NUEVA = [
    # ── DrakesCraft ──
    ("[DRAKES] Comando para ver tus bovedas personales? (sin barra)", "pv"),
    ("[DRAKES] Comando para teletransportarte a un lugar aleatorio?", "rtp"),
    ("[DRAKES] Comando para volver al punto donde moriste?", "back"),
    ("[DRAKES] Comando para fijar tu casa en el mapa?", "sethome"),
    ("[DRAKES] Comando para pedir teletransporte a otro jugador?", "tpa"),
    ("[DRAKES] Comando para aceptar un teletransporte?", "tpaccept"),
    ("[DRAKES] Comando para ver el ranking de los mas ricos?", "baltop"),
    ("[DRAKES] Como se llama el plugin propio del servidor? (una palabra)", "odysseia"),
    ("[DRAKES] Comando para tirar basura sin dejarla en el suelo?", "trash"),
    ("[DRAKES] Comando para elegir tu idioma de traduccion en el chat?", "wwct"),
    # ── Slimefun ──
    ("[SLIMEFUN] Maquina basica que genera energia quemando carbon? (una palabra en ingles)", "generator"),
    ("[SLIMEFUN] Como se llama la barra de energia de una maquina? (una palabra en ingles)", "capacitor"),
    ("[SLIMEFUN] Metal ficticio de Slimefun hecho con oro y hierro? (una palabra)", "reinforced"),
    ("[SLIMEFUN] Herramienta que muestra la energia de una red? (una palabra en ingles)", "multimeter"),
    ("[SLIMEFUN] Que se necesita investigar antes de fabricar un item? (una palabra)", "research"),
    ("[SLIMEFUN] Bloque que mueve items sin cables, por canales? (una palabra)", "cargo"),
    ("[SLIMEFUN] Mesa donde se fabrican los items basicos? (dos palabras en ingles)", "enhanced crafting"),
    ("[SLIMEFUN] Como se llama el libro que abre el menu de Slimefun? (una palabra en ingles)", "guide"),
    # ── Minecraft ──
    ("[MINECRAFT] Cuantos bloques mide de alto un jugador? (solo el numero)", "2"),
    ("[MINECRAFT] Que mob explota al acercarse? (una palabra)", "creeper"),
    ("[MINECRAFT] Mineral mas raro que se usa para encantar? (una palabra)", "lapislazuli"),
    ("[MINECRAFT] Cuantos lingotes de hierro necesita un yunque? (solo el numero)", "31"),
    ("[MINECRAFT] Nivel Y donde mas diamantes aparecen en 1.21? (numero negativo)", "-59"),
    ("[MINECRAFT] Que mob suelta perlas de ender? (una palabra)", "enderman"),
    ("[MINECRAFT] Cuantos jugadores caben en una cama? (solo el numero)", "1"),
    ("[MINECRAFT] Bloque que no se puede romper en supervivencia? (una palabra)", "bedrock"),
    ("[MINECRAFT] Que necesita un aldeano para convertirse en zombi curado? (una palabra)", "manzana"),
    ("[MINECRAFT] Cuantos ojos de ender lleva un portal completo? (solo el numero)", "12"),
    ("[MINECRAFT] Como se llama el jefe final del juego? (dos palabras, sin tildes)", "ender dragon"),
    ("[MINECRAFT] Cuantos corazones tiene un jugador? (solo el numero)", "10"),
    # ── Ciencia ──
    ("[CIENCIA] Simbolo quimico del hierro?", "Fe"),
    ("[CIENCIA] Simbolo quimico del oxigeno?", "O"),
    ("[CIENCIA] Cuantos huesos tiene el cuerpo humano adulto? (solo el numero)", "206"),
    ("[CIENCIA] Gas que respiramos y forma el 78% del aire? (una palabra, sin tildes)", "nitrogeno"),
    ("[CIENCIA] Organo que bombea la sangre? (una palabra)", "corazon"),
    ("[CIENCIA] Velocidad de la luz en km/s, redondeada? (solo el numero)", "300000"),
    ("[CIENCIA] Unidad de fuerza en el sistema internacional? (una palabra)", "newton"),
    ("[CIENCIA] Cuantos grados Celsius hierve el agua a nivel del mar? (solo el numero)", "100"),
    ("[CIENCIA] Particula del atomo con carga negativa? (una palabra)", "electron"),
    ("[CIENCIA] Formula quimica del agua? (sin espacios)", "H2O"),
    # ── Astronomia ──
    ("[ASTRONOMIA] Estrella del centro del Sistema Solar? (una palabra)", "sol"),
    ("[ASTRONOMIA] Planeta conocido como el planeta rojo? (una palabra)", "marte"),
    ("[ASTRONOMIA] Planeta mas grande del Sistema Solar? (una palabra, sin tildes)", "jupiter"),
    ("[ASTRONOMIA] Cuantas lunas tiene la Tierra? (solo el numero)", "1"),
    ("[ASTRONOMIA] Planeta con los anillos mas visibles? (una palabra)", "saturno"),
    # ── Matematicas ──
    ("[MATES] Cuanto vale Pi con dos decimales? (usa punto)", "3.14"),
    ("[MATES] Cuantos lados tiene un hexagono? (solo el numero)", "6"),
    ("[MATES] Resultado de 12 al cuadrado? (solo el numero)", "144"),
    ("[MATES] Como se llama el numero que solo se divide por 1 y por si mismo? (una palabra)", "primo"),
    ("[MATES] Cuantos grados suman los angulos de un triangulo? (solo el numero)", "180"),
    # ── Geografia e historia ──
    ("[GEOGRAFIA] Capital de Chile? (una palabra)", "santiago"),
    ("[GEOGRAFIA] Oceano que baña la costa chilena? (una palabra, sin tildes)", "pacifico"),
    ("[GEOGRAFIA] Desierto mas arido del mundo, en el norte de Chile? (una palabra)", "atacama"),
    ("[GEOGRAFIA] Rio mas caudaloso del mundo? (una palabra)", "amazonas"),
    ("[GEOGRAFIA] Continente mas grande? (una palabra)", "asia"),
    ("[HISTORIA] En que ano llego el ser humano a la Luna? (solo el numero)", "1969"),
    ("[HISTORIA] Civilizacion que construyo Machu Picchu? (una palabra)", "inca"),
    ("[HISTORIA] Que muro cayo en 1989? (una palabra)", "berlin"),
    # ── Tecnologia ──
    ("[TECNO] Lenguaje en el que estan escritos los plugins de Minecraft? (una palabra)", "java"),
    ("[TECNO] Cuantos bits tiene un byte? (solo el numero)", "8"),
    ("[TECNO] Siglas del sistema que traduce nombres de dominio a IPs?", "DNS"),
    ("[TECNO] Que significa la 'S' de HTTPS? (una palabra en ingles)", "secure"),
    ("[TECNO] Sistema operativo del pinguino? (una palabra)", "linux"),
]

MATH_NUEVA = [
    ("[FACIL] 17 + 45 = ?", "62"), ("[FACIL] 96 - 38 = ?", "58"),
    ("[FACIL] 13 * 6 = ?", "78"), ("[FACIL] 144 / 12 = ?", "12"),
    ("[FACIL] 25% de 200 = ?", "50"), ("[FACIL] 8 * 8 - 14 = ?", "50"),
    ("[FACIL] Cuantos bloques hay en un stack completo?", "64"),
    ("[FACIL] Cuantos bloques hay en 3 stacks completos?", "192"),
    ("[FACIL] Un cofre doble tiene cuantos huecos?", "54"),
    ("[MEDIA] 23 * 11 = ?", "253"), ("[MEDIA] 7 al cubo = ?", "343"),
    ("[MEDIA] Raiz cuadrada de 625 = ?", "25"), ("[MEDIA] 15% de 840 = ?", "126"),
    ("[MEDIA] 2 elevado a 10 = ?", "1024"),
    ("[MEDIA] Cuantos segundos tiene un dia de Minecraft (20 min reales)?", "1200"),
    ("[MEDIA] 1000 - 37 * 12 = ?", "556"),
    ("[DIFICIL] 47 * 23 = ?", "1081"), ("[DIFICIL] Raiz cuadrada de 4096 = ?", "64"),
    ("[DIFICIL] 3 elevado a 7 = ?", "2187"),
    ("[DIFICIL] Cuantos bloques tiene un chunk (16x16x384)?", "98304"),
    ("[DIFICIL] MCD de 84 y 126 = ?", "42"),
    ("[EXPERTO] Binario 0b101101 en decimal = ?", "45"),
    ("[EXPERTO] Hexadecimal 0xFF en decimal = ?", "255"),
    ("[EXPERTO] Hexadecimal 0x1A4 en decimal = ?", "420"),
    ("[EXPERTO] MCM de 12, 18 y 24 = ?", "72"),
    ("[EXPERTO] Cuantos diamantes hay en 7 stacks y 13 unidades?", "461"),
]

UNSCRAMBLE_NUEVAS = [
    # Slimefun y tecnologia del server
    "MULTIMETRO", "CONDENSADOR", "REACTOR", "TURBINA", "GENERADOR", "ENERGIA",
    "INVESTIGACION", "ALEACION", "FUNDICION", "TRANSPORTE", "AUTOMATIZACION",
    "MAQUINARIA", "CIRCUITO", "BATERIA", "PANEL", "SOLAR", "NUCLEAR", "CARBON",
    # Minecraft
    "DIAMANTE", "ESMERALDA", "NETHERITA", "OBSIDIANA", "REDSTONE", "ANTORCHA",
    "ENCANTAMIENTO", "YUNQUE", "CALDERO", "ESTANDARTE", "ANDAMIO", "BRUJULA",
    "ZOMBI", "ESQUELETO", "ARANA", "ALDEANO", "CREEPER", "ENDERMAN", "GHAST",
    "PIGLIN", "WARDEN", "AXOLOTL", "ALLAY", "SNIFFER", "CAMELLO", "TORTUGA",
    "FORTALEZA", "MAZMORRA", "SANTUARIO", "MANSION", "PORTAL", "BIOMA",
    # Ciencia y cultura
    "GRAVEDAD", "ELECTRON", "MOLECULA", "GALAXIA", "PLANETA", "ASTEROIDE",
    "TELESCOPIO", "MICROSCOPIO", "EXPERIMENTO", "HIPOTESIS", "TEOREMA",
    "ALGORITMO", "VARIABLE", "SERVIDOR", "MEMORIA", "PROCESADOR",
    "CORDILLERA", "VOLCAN", "TERREMOTO", "GLACIAR", "ARCHIPIELAGO",
    # DrakesCraft
    "TITANES", "OLIMPO", "HERMES", "POSEIDON", "AFRODITA", "HEFESTO",
    "ARTEMISA", "HERCULES", "HESTIA", "ANUBIS", "CRONOS", "HIPERION",
    "MODALIDAD", "SUPERVIVENCIA", "SKYBLOCK", "ONEBLOCK", "BOVEDA", "RANGO",
]

REACTION_NUEVAS = [
    ("Grito de Zeus", "Escribe exactamente: <yellow>RELAMPAGO</yellow>", "RELAMPAGO"),
    ("Llamado de Poseidon", "Escribe exactamente: <yellow>TRIDENTE</yellow>", "TRIDENTE"),
    ("Forja de Hefesto", "Escribe exactamente: <yellow>YUNQUE</yellow>", "YUNQUE"),
    ("Flecha de Artemisa", "Escribe exactamente: <yellow>ARCO</yellow>", "ARCO"),
    ("Comando de bovedas", "Escribe el comando de tus bovedas: <yellow>/pv</yellow>", "/pv"),
    ("Comando de subasta", "Escribe el comando del mercado: <yellow>/ah</yellow>", "/ah"),
    ("Comando de guia SF", "Escribe el comando de la guia: <yellow>/sf guide</yellow>", "/sf guide"),
    ("Comando de warps", "Escribe el comando de warps: <yellow>/pwarp</yellow>", "/pwarp"),
    ("Moneda del reino", "Escribe la moneda del servidor: <yellow>DRAGMAS</yellow>", "DRAGMAS"),
    ("Grito de guerra", "Escribe exactamente: <yellow>DRAKESCRAFT</yellow>", "DRAKESCRAFT"),
    ("Numero de la suerte", "Escribe exactamente: <yellow>777</yellow>", "777"),
    ("Stack completo", "Cuantos items tiene un stack? Escribe el numero", "64"),
    ("Reflejo veloz", "Escribe exactamente: <yellow>RAPIDO</yellow>", "RAPIDO"),
    ("Eco del Hades", "Escribe exactamente: <yellow>INFRAMUNDO</yellow>", "INFRAMUNDO"),
    ("Runa antigua", "Escribe exactamente: <yellow>ODYSSEIA</yellow>", "ODYSSEIA"),
]


def marcar(texto):
    """Envuelve la pregunta en el color que ya usan las demas."""
    return f"<yellow>{texto}</yellow>"


def cargar(nombre):
    ruta = CARPETA / f"{nombre}.yml"
    with ruta.open(encoding="utf-8") as fichero:
        return ruta, yaml.safe_load(fichero)


def guardar(ruta, datos):
    with ruta.open("w", encoding="utf-8") as fichero:
        yaml.safe_dump(datos, fichero, allow_unicode=True, sort_keys=False, width=200)


# ── trivia: arreglar las rotas y anadir las nuevas ──────────────────────────
ruta, trivia = cargar("trivia")
arregladas = 0
for par in trivia["questions"]:
    if str(par[1]) in ARREGLOS:
        par[0], par[1] = ARREGLOS[str(par[1])]
        arregladas += 1
antes = len(trivia["questions"])
trivia["questions"].extend([[marcar(q), a] for q, a in TRIVIA_NUEVA])
guardar(ruta, trivia)
print(f"trivia:          {antes} -> {len(trivia['questions'])}  ({arregladas} corregidas)")

# ── math ────────────────────────────────────────────────────────────────────
ruta, math = cargar("math")
antes = len(math["questions"])
math["questions"].extend([[marcar(q), a] for q, a in MATH_NUEVA])
guardar(ruta, math)
print(f"math:            {antes} -> {len(math['questions'])}")

# ── unscramble ──────────────────────────────────────────────────────────────
ruta, uns = cargar("unscramble")
antes = len(uns["words"])
existentes = {w.upper() for w in uns["words"]}
uns["words"].extend([w for w in UNSCRAMBLE_NUEVAS if w not in existentes])
guardar(ruta, uns)
print(f"unscramble:      {antes} -> {len(uns['words'])}")

# ── reaction ────────────────────────────────────────────────────────────────
ruta, rea = cargar("reaction")
antes = len(rea["variants"])
rea["variants"].extend([{"name": n, "challenge": f"<gold><bold>{c}</bold></gold>", "answer": a}
                        for n, c, a in REACTION_NUEVAS])
guardar(ruta, rea)
print(f"reaction:        {antes} -> {len(rea['variants'])}")
