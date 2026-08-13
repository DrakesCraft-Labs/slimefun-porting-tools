#!/usr/bin/env python3
"""Genera el banner SVG animado de un addon portado, al estilo de la organizacion.

La plantilla sale de los banners que ya existen en el workspace (DynaTech, Galaxyfun,
SlimeMarket): fondo oscuro en degradado, titulo con degradado propio que late, subtitulo
espaciado y una fila de chapas. Se mantiene igual a proposito, para que los repos nuevos no
desentonen con los que ya estaban.

Lo unico que cambia de un addon a otro es el color de acento y la figura del centro. Con
veinte repos por delante, que todos compartan silueta pero se distingan de un vistazo importa
mas que hacer cada uno especial.

El SVG es autonomo: sin fuentes externas ni imagenes, porque GitHub no carga nada de fuera al
renderizar un README y lo que dependa de la red sale en blanco.
"""
import pathlib
import sys

# Acento y figura de cada addon. La figura es un fragmento SVG que se dibuja centrado en 0,0.
ADDONS = {
    "SFPortalGun": {
        "acento": "#A855F7",
        "acento2": "#22D3EE",
        "sub": "SLIMEFUN4 ADDON · PORTALES Y TELETRANSPORTE",
        # Dos anillos concentricos: un portal.
        "figura": """
    <ellipse cx="0" cy="0" rx="38" ry="42" fill="none" stroke="url(#acG)" stroke-width="4"/>
    <ellipse cx="0" cy="0" rx="22" ry="26" fill="none" stroke="{acento2}" stroke-width="2.5" opacity="0.8">
      <animate attributeName="rx" values="22;16;22" dur="3s" repeatCount="indefinite"/>
    </ellipse>
    <circle cx="0" cy="0" r="7" fill="{acento}"/>""",
    },
    "SlimefunOreChunks": {
        "acento": "#F59E0B",
        "acento2": "#38BDF8",
        "sub": "SLIMEFUN4 ADDON · VETAS Y FRAGMENTOS DE MINERAL",
        # Un cristal facetado.
        "figura": """
    <polygon points="0,-44 30,-14 20,40 -20,40 -30,-14" fill="#0F172A" stroke="url(#acG)" stroke-width="3.5"/>
    <polygon points="0,-44 0,40 -30,-14" fill="{acento}" opacity="0.25"/>
    <circle cx="0" cy="4" r="8" fill="{acento}"/>""",
    },
    "RandomExpansion": {
        "acento": "#10B981",
        "acento2": "#A3E635",
        "sub": "SLIMEFUN4 ADDON · MAQUINAS Y UTILIDADES VARIADAS",
        # Un dado: lo aleatorio.
        "figura": """
    <rect x="-34" y="-34" width="68" height="68" rx="12" fill="#0F172A" stroke="url(#acG)" stroke-width="3.5"/>
    <circle cx="-16" cy="-16" r="6" fill="{acento}"/>
    <circle cx="16" cy="16" r="6" fill="{acento}"/>
    <circle cx="0" cy="0" r="6" fill="{acento2}"/>""",
    },
    "DemonicExpansion": {
        "acento": "#DC2626",
        "acento2": "#F97316",
        "sub": "SLIMEFUN4 ADDON · CRIATURAS Y EQUIPO DEL NETHER",
        # Un tridente/horca sobre un circulo: lo demoniaco.
        "figura": """
    <circle cx="0" cy="0" r="42" fill="#0F172A" stroke="url(#acG)" stroke-width="3.5"/>
    <path d="M -20 -16 L -20 6 M 0 -22 L 0 6 M 20 -16 L 20 6 M -20 6 L 20 6 M 0 6 L 0 30"
          stroke="{acento}" stroke-width="4" fill="none" stroke-linecap="round"/>
    <circle cx="0" cy="-30" r="5" fill="{acento2}"/>""",
    },
    "HardcoreSlimefun": {
        "acento": "#EF4444",
        "acento2": "#FBBF24",
        "sub": "SLIMEFUN4 ADDON · MODO DURO OPCIONAL, APAGADO POR DEFECTO",
        # Una calavera esquematica.
        "figura": """
    <path d="M -30 -10 a 30 32 0 0 1 60 0 l 0 18 a 8 8 0 0 1 -8 8 l -44 0 a 8 8 0 0 1 -8 -8 Z"
          fill="#0F172A" stroke="url(#acG)" stroke-width="3.5"/>
    <circle cx="-13" cy="-6" r="7" fill="{acento}"/>
    <circle cx="13" cy="-6" r="7" fill="{acento}"/>
    <path d="M -10 26 L -10 36 M 0 26 L 0 36 M 10 26 L 10 36"
          stroke="{acento2}" stroke-width="4" stroke-linecap="round"/>""",
    },
    "NotEnoughAddons": {
        "acento": "#22C55E",
        "acento2": "#38BDF8",
        "sub": "SLIMEFUN4 ADDON · MAQUINAS, MOCHILAS Y ARMAS CORTAS",
        # Tres piezas encajando: el cajon de sastre.
        "figura": """
    <rect x="-34" y="-34" width="30" height="30" rx="5" fill="#0F172A" stroke="url(#acG)" stroke-width="3"/>
    <rect x="4" y="-34" width="30" height="30" rx="5" fill="{acento}" opacity="0.3" stroke="{acento}" stroke-width="3"/>
    <rect x="-15" y="4" width="30" height="30" rx="5" fill="#0F172A" stroke="{acento2}" stroke-width="3"/>""",
    },
    "BreweryMenu": {
        "acento": "#F59E0B", "acento2": "#84CC16",
        "sub": "SLIMEFUN4 ADDON · MENU DE DESTILERIA",
        "figura": """
    <path d="M -16 -38 L -16 -10 L -34 26 A 6 6 0 0 0 -28 36 L 28 36 A 6 6 0 0 0 34 26 L 16 -10 L 16 -38 Z"
          fill="#0F172A" stroke="url(#acG)" stroke-width="3.5" stroke-linejoin="round"/>
    <path d="M -26 14 L 26 14 L 30 26 A 4 4 0 0 1 26 32 L -26 32 A 4 4 0 0 1 -30 26 Z" fill="{acento}" opacity="0.5"/>
    <circle cx="-8" cy="24" r="3" fill="{acento2}"><animate attributeName="cy" values="24;16;24" dur="2.6s" repeatCount="indefinite"/></circle>""",
    },
    "Cringle-Bosses": {
        "acento": "#EF4444", "acento2": "#FBBF24",
        "sub": "SLIMEFUN4 ADDON · JEFES POR RITUAL",
        "figura": """
    <path d="M 0 -40 L 34 -14 L 26 34 L -26 34 L -34 -14 Z" fill="#0F172A" stroke="url(#acG)" stroke-width="3.5" stroke-linejoin="round"/>
    <circle cx="-11" cy="-2" r="5" fill="{acento2}"><animate attributeName="opacity" values="1;0.2;1" dur="1.8s" repeatCount="indefinite"/></circle>
    <circle cx="11" cy="-2" r="5" fill="{acento2}"><animate attributeName="opacity" values="1;0.2;1" dur="1.8s" repeatCount="indefinite"/></circle>
    <path d="M -13 16 L -6 22 L 0 16 L 6 22 L 13 16" fill="none" stroke="{acento}" stroke-width="3"/>""",
    },
    "Drugfun": {
        "acento": "#22C55E", "acento2": "#A3E635",
        "sub": "SLIMEFUN4 ADDON · ALQUIMIA Y BREBAJES",
        "figura": """
    <path d="M -12 -36 L 12 -36 L 12 -12 L 30 24 A 8 8 0 0 1 22 36 L -22 36 A 8 8 0 0 1 -30 24 L -12 -12 Z"
          fill="#0F172A" stroke="url(#acG)" stroke-width="3.5" stroke-linejoin="round"/>
    <path d="M -22 12 L 22 12 L 28 26 A 4 4 0 0 1 24 32 L -24 32 A 4 4 0 0 1 -28 26 Z" fill="{acento}" opacity="0.55"/>
    <circle cx="6" cy="22" r="3.5" fill="{acento2}"><animate attributeName="cy" values="22;14;22" dur="2.2s" repeatCount="indefinite"/></circle>""",
    },
    "GlobiaMachines": {
        "acento": "#0EA5E9", "acento2": "#A78BFA",
        "sub": "SLIMEFUN4 ADDON · MAQUINARIA INDUSTRIAL",
        "figura": """
    <rect x="-36" y="-24" width="72" height="52" rx="6" fill="#0F172A" stroke="url(#acG)" stroke-width="3.5"/>
    <g><path d="M 0 -34 L 6 -28 L 0 -22 L -6 -28 Z" fill="{acento2}"/>
      <animateTransform attributeName="transform" type="rotate" values="0;360" dur="8s" repeatCount="indefinite"/></g>
    <rect x="-22" y="-8" width="44" height="8" rx="3" fill="{acento}" opacity="0.7"/>
    <rect x="-22" y="8" width="28" height="8" rx="3" fill="{acento}" opacity="0.45"/>""",
    },
    "Nexcavate": {
        "acento": "#F97316", "acento2": "#FDE047",
        "sub": "SLIMEFUN4 ADDON · EXCAVACION Y MINERIA",
        "figura": """
    <path d="M -38 12 A 44 44 0 0 1 38 12" fill="none" stroke="url(#acG)" stroke-width="5" stroke-linecap="round"/>
    <rect x="-3" y="4" width="6" height="34" rx="3" fill="{acento}"/>
    <circle cx="0" cy="12" r="5" fill="{acento2}"><animate attributeName="r" values="5;8;5" dur="2s" repeatCount="indefinite"/></circle>""",
    },
    "PrivateStorage": {
        "acento": "#14B8A6", "acento2": "#FBBF24",
        "sub": "SLIMEFUN4 ADDON · COFRES PRIVADOS",
        "figura": """
    <rect x="-34" y="-10" width="68" height="42" rx="5" fill="#0F172A" stroke="url(#acG)" stroke-width="3.5"/>
    <path d="M -18 -10 L -18 -24 A 18 18 0 0 1 18 -24 L 18 -10" fill="none" stroke="{acento2}" stroke-width="4"/>
    <circle cx="0" cy="8" r="6" fill="{acento}"><animate attributeName="opacity" values="1;0.4;1" dur="2.4s" repeatCount="indefinite"/></circle>
    <rect x="-2.5" y="8" width="5" height="14" rx="2" fill="{acento}"/>""",
    },
    "SlimyBees": {
        "acento": "#FACC15", "acento2": "#F97316",
        "sub": "SLIMEFUN4 ADDON · ABEJAS Y GENETICA",
        "figura": """
    <ellipse cx="0" cy="6" rx="20" ry="26" fill="#0F172A" stroke="url(#acG)" stroke-width="3.5"/>
    <path d="M -19 -4 L 19 -4 M -20 8 L 20 8 M -17 20 L 17 20" stroke="{acento}" stroke-width="4"/>
    <ellipse cx="-24" cy="-14" rx="15" ry="9" fill="{acento2}" opacity="0.55" transform="rotate(-25 -24 -14)">
      <animate attributeName="opacity" values="0.55;0.2;0.55" dur="0.5s" repeatCount="indefinite"/></ellipse>
    <ellipse cx="24" cy="-14" rx="15" ry="9" fill="{acento2}" opacity="0.55" transform="rotate(25 24 -14)">
      <animate attributeName="opacity" values="0.55;0.2;0.55" dur="0.5s" repeatCount="indefinite"/></ellipse>""",
    },
    "Netheopoiesis": {
        "acento": "#84CC16",
        "acento2": "#F43F5E",
        "sub": "SLIMEFUN4 ADDON · TERRAFORMAR EL NETHER",
        # Un brote saliendo de piedra agrietada: el Nether volviendose verde.
        "figura": """
    <path d="M -38 26 L -20 12 L -4 24 L 12 10 L 30 22 L 38 26 L 38 38 L -38 38 Z"
          fill="#0F172A" stroke="url(#acG)" stroke-width="3"/>
    <path d="M 0 26 L 0 -10" stroke="{acento}" stroke-width="4" stroke-linecap="round"/>
    <path d="M 0 -2 C -20 -6 -24 -22 -22 -30 C -10 -28 -2 -16 0 -2 Z" fill="{acento}" opacity="0.85">
      <animate attributeName="opacity" values="0.85;0.45;0.85" dur="3.4s" repeatCount="indefinite"/>
    </path>
    <path d="M 0 -8 C 20 -12 24 -28 22 -36 C 10 -34 2 -22 0 -8 Z" fill="{acento}" opacity="0.6">
      <animate attributeName="opacity" values="0.6;0.9;0.6" dur="3.4s" repeatCount="indefinite"/>
    </path>
    <circle cx="-26" cy="16" r="3" fill="{acento2}" opacity="0.8"/>
    <circle cx="24" cy="14" r="2.5" fill="{acento2}" opacity="0.6"/>""",
    },
    "Obsidian-Armor": {
        "acento": "#8B5CF6",
        "acento2": "#38BDF8",
        "sub": "SLIMEFUN4 ADDON · ARMADURA DE OBSIDIANA",
        # Un peto: hombros, torso y el cuello en hueco.
        "figura": """
    <path d="M -34 -30 L -12 -38 L 0 -26 L 12 -38 L 34 -30 L 30 30 L -30 30 Z"
          fill="#0F172A" stroke="url(#acG)" stroke-width="3.5" stroke-linejoin="round"/>
    <path d="M -12 -38 L 0 -26 L 12 -38" fill="none" stroke="{acento2}" stroke-width="2.5"/>
    <path d="M -18 -4 L 18 -4 M -16 12 L 16 12" stroke="{acento}" stroke-width="2.5" opacity="0.75">
      <animate attributeName="opacity" values="0.75;0.25;0.75" dur="3s" repeatCount="indefinite"/>
    </path>""",
    },
    "MagicXpansion": {
        "acento": "#D946EF",
        "acento2": "#FBBF24",
        "sub": "SLIMEFUN4 ADDON · MAGIA, HECHIZOS Y REACTORES",
        # Una estrella de seis puntas que gira despacio, con un nucleo que late.
        "figura": """
    <g>
      <path d="M 0 -42 L 10 -12 L 40 -12 L 16 8 L 26 38 L 0 20 L -26 38 L -16 8 L -40 -12 L -10 -12 Z"
            fill="none" stroke="url(#acG)" stroke-width="3.5" stroke-linejoin="round"/>
      <animateTransform attributeName="transform" type="rotate"
                        values="0;360" dur="24s" repeatCount="indefinite"/>
    </g>
    <circle cx="0" cy="0" r="9" fill="{acento2}" opacity="0.9">
      <animate attributeName="r" values="9;13;9" dur="2.4s" repeatCount="indefinite"/>
    </circle>""",
    },
    "ObsidianExpansion": {
        "acento": "#7C3AED",
        "acento2": "#22D3EE",
        "sub": "SLIMEFUN4 ADDON · OBSIDIANA, FORJA Y GENERADORES",
        # Bloque de obsidiana facetado, en perspectiva isometrica.
        "figura": """
    <polygon points="0,-42 36,-21 36,21 0,42 -36,21 -36,-21" fill="#0F172A" stroke="url(#acG)" stroke-width="3.5"/>
    <polygon points="0,-42 36,-21 0,0 -36,-21" fill="{acento}" opacity="0.35"/>
    <path d="M 0 0 L 0 42 M 0 0 L -36 -21 M 0 0 L 36 -21" stroke="{acento2}" stroke-width="2" opacity="0.8"/>""",
    },
    "GlobalWarming": {
        "acento": "#F97316",
        "acento2": "#38BDF8",
        "sub": "SLIMEFUN4 ADDON · CONTAMINACION Y TEMPERATURA",
        # Termometro con el bulbo lleno.
        "figura": """
    <rect x="-9" y="-42" width="18" height="52" rx="9" fill="#0F172A" stroke="url(#acG)" stroke-width="3.5"/>
    <circle cx="0" cy="22" r="16" fill="#0F172A" stroke="url(#acG)" stroke-width="3.5"/>
    <circle cx="0" cy="22" r="9" fill="{acento}"/>
    <rect x="-3" y="-16" width="6" height="34" rx="3" fill="{acento}"/>
    <path d="M 14 -30 L 24 -30 M 14 -18 L 24 -18 M 14 -6 L 24 -6" stroke="{acento2}" stroke-width="2.5" stroke-linecap="round"/>""",
    },
    "SlimefunAdvancements": {
        "acento": "#EAB308",
        "acento2": "#A78BFA",
        "sub": "SLIMEFUN4 ADDON · PROGRESOS Y LOGROS PROPIOS",
        # El marco de logro de Minecraft: un rombo.
        "figura": """
    <rect x="-30" y="-30" width="60" height="60" rx="6" transform="rotate(45)" fill="#0F172A" stroke="url(#acG)" stroke-width="3.5"/>
    <path d="M -16 0 L -5 12 L 18 -12" fill="none" stroke="{acento}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>""",
    },
    "InfernalExpansion": {
        "acento": "#EF4444",
        "acento2": "#FB923C",
        "sub": "SLIMEFUN4 ADDON · OBJETOS Y RUNAS DEL NETHER",
        # Una llama.
        "figura": """
    <path d="M 0 -44 C 16 -22 30 -14 30 6 a 30 30 0 0 1 -60 0 C -30 -12 -14 -18 -6 -34 C -2 -24 -6 -14 0 -8 C 6 -16 4 -30 0 -44 Z"
          fill="#0F172A" stroke="url(#acG)" stroke-width="3.5"/>
    <path d="M 0 -8 C 10 2 10 14 0 22 C -10 14 -10 2 0 -8 Z" fill="{acento2}"/>""",
    },
    "InfinityLib-Drake": {
        "acento": "#06B6D4",
        "acento2": "#A78BFA",
        "sub": "LIBRERIA DE APOYO · MAQUINAS, GRUPOS Y RECETAS",
        # El simbolo de infinito.
        "figura": """
    <path d="M -34 0 a 17 17 0 1 1 17 17 a 17 17 0 1 0 17 -34 a 17 17 0 1 1 17 17 a 17 17 0 1 0 -17 34 a 17 17 0 1 1 -17 -34 Z"
          fill="none" stroke="url(#acG)" stroke-width="5" stroke-linecap="round"/>
    <circle cx="0" cy="0" r="6" fill="{acento2}"/>""",
    },
    "IDreamOfEasy": {
        "acento": "#38BDF8",
        "acento2": "#C084FC",
        "sub": "SLIMEFUN4 ADDON · HERRAMIENTAS, MAQUINAS E IDOLOS",
        # Una luna creciente con estrellas: lo de "soñar".
        "figura": """
    <path d="M 12 -40 a 40 40 0 1 0 0 80 a 32 32 0 1 1 0 -80 Z" fill="#0F172A" stroke="url(#acG)" stroke-width="3.5"/>
    <circle cx="20" cy="-22" r="4" fill="{acento2}"/>
    <circle cx="30" cy="-2" r="3" fill="{acento}"/>
    <circle cx="22" cy="20" r="3.5" fill="{acento2}"/>""",
    },
    "EquivalencyTech": {
        "acento": "#EC4899",
        "acento2": "#FBBF24",
        "sub": "SLIMEFUN4 ADDON · TRANSMUTACION Y EQUIVALENCIAS",
        # Balanza: el intercambio equivalente.
        "figura": """
    <circle cx="0" cy="0" r="42" fill="none" stroke="url(#acG)" stroke-width="3.5"/>
    <path d="M -26 -10 L 26 -10 M 0 -10 L 0 26 M -18 26 L 18 26" stroke="{acento}" stroke-width="4" fill="none" stroke-linecap="round"/>
    <circle cx="0" cy="-18" r="7" fill="{acento2}"/>""",
    },
}

PLANTILLA = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 300" width="920" height="300">
  <defs>
    <linearGradient id="bgG" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F172A" />
      <stop offset="50%" stop-color="#1E293B" />
      <stop offset="100%" stop-color="#020617" />
    </linearGradient>

    <linearGradient id="acG" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{acento}" />
      <stop offset="50%" stop-color="{acento2}" />
      <stop offset="100%" stop-color="{acento}" />
    </linearGradient>

    <filter id="glowF">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <style>
    @keyframes latido {{
      0%, 100% {{ opacity: 0.85; filter: drop-shadow(0 0 15px {acento}b3); }}
      50%      {{ opacity: 1;    filter: drop-shadow(0 0 30px {acento2}); }}
    }}
    @keyframes giro {{
      from {{ transform: rotate(0deg); }}
      to   {{ transform: rotate(360deg); }}
    }}
    .fondo  {{ fill: url(#bgG); }}
    .titulo {{ font-family: 'Outfit', 'Segoe UI', sans-serif; font-weight: 900; font-size: {tam}px;
               fill: url(#acG); animation: latido 3.5s infinite ease-in-out; }}
    .sub    {{ font-family: 'Inter', 'Segoe UI', sans-serif; font-weight: 700; font-size: 14px;
               fill: #94A3B8; letter-spacing: 3px; }}
    .chapa  {{ fill: #0F172A; stroke-width: 1.5; rx: 6px; }}
    .ctexto {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; }}
  </style>

  <rect class="fondo" width="920" height="300" rx="14" stroke="{acento}" stroke-width="1.5" />

  <g transform="translate(460, 95)" filter="url(#glowF)">
    <!-- El giro va en SMIL y no en CSS a proposito: GitHub sirve el banner dentro de un <img>,
         y ahi `transform-box: fill-box` no se aplica igual en todos los navegadores, con lo que
         la figura giraba alrededor de la esquina del SVG en vez de sobre si misma. -->
    <g>
      <animateTransform attributeName="transform" type="rotate"
                        from="0 0 0" to="360 0 0" dur="24s" repeatCount="indefinite"/>{figura}
    </g>
  </g>

  <text x="460" y="185" text-anchor="middle" class="titulo">{titulo}</text>
  <text x="460" y="215" text-anchor="middle" class="sub">{sub}</text>

  <g transform="translate(240, 245)">
    <rect x="0" y="0" width="145" height="30" class="chapa" stroke="{acento}" />
    <text x="12" y="20" class="ctexto" fill="{acento}">DRAKES LABS</text>

    <rect x="165" y="0" width="135" height="30" class="chapa" stroke="#38BDF8" />
    <text x="177" y="20" class="ctexto" fill="#38BDF8">PAPER 1.21.11</text>

    <rect x="320" y="0" width="120" height="30" class="chapa" stroke="#A3E635" />
    <text x="332" y="20" class="ctexto" fill="#A3E635">JAVA 21</text>
  </g>
</svg>
"""


def generar(nombre, datos):
    titulo = nombre.upper()
    # El titulo se encoge si no cabe: a 42px entran unas 15 letras en 920 de ancho, y
    # SLIMEFUNORECHUNKS son 17. Sin esto se sale del banner.
    tam = 42 if len(titulo) <= 15 else max(28, int(42 * 15 / len(titulo)))

    figura = datos["figura"].format(acento=datos["acento"], acento2=datos["acento2"])
    return PLANTILLA.format(
        acento=datos["acento"], acento2=datos["acento2"],
        titulo=titulo, sub=datos["sub"], figura=figura, tam=tam,
    )


def main():
    base = pathlib.Path(__file__).parent / "limpio"
    for nombre, datos in ADDONS.items():
        repo = base / nombre
        if not repo.is_dir():
            print(f"  falta el repo: {nombre}")
            continue
        # docs/banner.svg es la ruta que ya referencian los README de estos repos.
        destino = repo / "docs" / "banner.svg"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(generar(nombre, datos), encoding="utf-8")
        # Un banner suelto en la raiz de una pasada anterior; sobra y confunde.
        raiz = repo / "banner.svg"
        if raiz.exists():
            raiz.unlink()
        print(f"  {nombre}/banner.svg  ({destino.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
