#!/usr/bin/env python3
"""Genera el icono cuadrado de un addon para Modrinth.

POR QUE APARTE DEL BANNER

Modrinth pide un icono CUADRADO y lo recorta a un circulo redondeado en las tarjetas del
buscador. El banner es apaisado (920x240) y ahi se ve fatal: se recorta el titulo y queda un
trozo de fondo. Por eso el icono es una pieza propia, no un recorte del banner.

512x512 es la medida que recomienda Modrinth: por debajo se ve borroso en la ficha del proyecto
y por encima no aporta nada porque lo reescala igual.

ESTATICO A PROPOSITO

El banner late y se mueve, pero el icono se ve a 40 pixeles en una lista de resultados: una
animacion ahi no se aprecia y solo gasta bateria del que navega. Ademas Modrinth no anima el
icono en las tarjetas, asi que seria trabajo perdido.

Se reutiliza el acento y la figura que ya define banner.py para cada addon, de modo que icono y
banner se reconozcan como del mismo sitio. La figura se dibuja centrada en 0,0 y aqui se escala
para llenar el cuadrado.
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent

def catalogo():
    """El diccionario ADDONS de banner.py, sin importarlo (banner.py corre al importarse)."""
    ns = {}
    texto = (RAIZ / "banner.py").read_text(encoding="utf-8")
    m = re.search(r"^ADDONS = \{.*?^\}", texto, re.S | re.M)
    if not m:
        raise SystemExit("No encuentro ADDONS en banner.py")
    exec(m.group(0), {}, ns)
    return ns["ADDONS"]

PLANTILLA = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512" role="img" aria-label="{nombre}">
  <defs>
    <linearGradient id="fondo" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0B1220"/>
      <stop offset="100%" stop-color="#131C2E"/>
    </linearGradient>
    <linearGradient id="acG" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{acento}"/>
      <stop offset="100%" stop-color="{acento2}"/>
    </linearGradient>
    <radialGradient id="halo" cx="50%" cy="42%" r="55%">
      <stop offset="0%" stop-color="{acento}" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="{acento}" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <!-- Fondo redondeado: Modrinth recorta a circulo en las tarjetas, asi que el contenido
       importante se mantiene dentro del 70% central para que no se pierda al recortar. -->
  <rect width="512" height="512" rx="96" fill="url(#fondo)"/>
  <rect width="512" height="512" rx="96" fill="url(#halo)"/>
  <rect x="4" y="4" width="504" height="504" rx="92" fill="none" stroke="url(#acG)" stroke-width="6" opacity="0.55"/>

  <g transform="translate(256,248) scale(2.45)">
{figura}
  </g>
</svg>
"""

def generar(nombre, datos):
    figura = datos["figura"].format(acento=datos["acento"], acento2=datos["acento2"])
    # El icono es estatico: se quitan las animaciones que trae la figura del banner.
    figura = re.sub(r"\s*<animate[^>]*/>", "", figura)
    figura = re.sub(r"\s*<animate[^>]*>.*?</animate>", "", figura, flags=re.S)
    return PLANTILLA.format(
        nombre=nombre,
        acento=datos["acento"],
        acento2=datos["acento2"],
        figura=figura,
    )

if __name__ == "__main__":
    addons = catalogo()
    destino = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if destino:
        nombre = destino.name
        if nombre not in addons:
            print(f"SIN_FIGURA|{nombre}")
            raise SystemExit(0)
        (destino / "docs").mkdir(exist_ok=True)
        (destino / "docs" / "icon.svg").write_text(generar(nombre, addons[nombre]), encoding="utf-8")
        print(f"OK|{nombre}")
    else:
        for n in sorted(addons):
            print(n)
