#!/usr/bin/env python3
"""Busca configuracion "zombi": bloques configurados a conciencia que nunca llegan a aplicarse.

Dos formas de estarlo:
  1. El bloque tiene su propio interruptor apagado (enabled/allow/... en false) pero por dentro
     hay ajustes que alguien se molesto en tocar.
  2. Un ajuste de otro archivo cancela el bloque entero (esos van en PAREJAS, a mano, porque la
     relacion no se deduce del YAML).
"""
import sys, glob, os
import yaml

# Valores que se consideran "por defecto"; si un bloque apagado solo tiene defaults, no es zombi:
# nadie lo configuro, simplemente viene asi de fabrica.
INTERRUPTORES = ("enabled", "enable", "active", "allow", "allowed")


def hojas(nodo, prefijo=""):
    """Recorre el arbol y devuelve (ruta, valor) de cada hoja."""
    if isinstance(nodo, dict):
        for clave, valor in nodo.items():
            yield from hojas(valor, f"{prefijo}.{clave}" if prefijo else str(clave))
    elif isinstance(nodo, list):
        if nodo:
            yield prefijo, nodo
    else:
        yield prefijo, nodo


def revisar(ruta_archivo):
    try:
        with open(ruta_archivo, encoding="utf-8-sig", errors="replace") as fichero:
            datos = yaml.safe_load(fichero)
    except Exception as error:
        return [(f"(no se pudo leer: {error})", 0, [])]
    if not isinstance(datos, dict):
        return []

    hallazgos = []

    def bajar(nodo, ruta):
        if not isinstance(nodo, dict):
            return
        apagado = any(nodo.get(s) is False for s in INTERRUPTORES)
        if apagado:
            dentro = [(r, v) for r, v in hojas(nodo)
                      if r.split(".")[-1] not in INTERRUPTORES]
            # Solo interesa si por dentro hay sustancia: listas con contenido, numeros que no son
            # 0, cadenas que no estan vacias ni son plantillas.
            sustancia = [(r, v) for r, v in dentro
                         if (isinstance(v, list) and v)
                         or (isinstance(v, str) and v.strip() and "REPLACE" not in v.upper())
                         or (isinstance(v, (int, float)) and not isinstance(v, bool) and v not in (0, -1))
                         or v is True]
            if len(sustancia) >= 3:
                hallazgos.append((ruta or "(raiz)", len(sustancia), sustancia[:6]))
            return          # no se baja mas: todo lo de dentro ya esta muerto
        for clave, valor in nodo.items():
            bajar(valor, f"{ruta}.{clave}" if ruta else str(clave))

    bajar(datos, "")
    return hallazgos


for archivo in sorted(sys.argv[1:]):
    resultados = revisar(archivo)
    if not resultados:
        continue
    print(f"\n=== {os.path.basename(archivo)} ===")
    for ruta, cuantos, muestra in resultados:
        print(f"  {ruta}   ({cuantos} ajustes dentro de un bloque apagado)")
        for r, v in muestra:
            print(f"        {r} = {v}")
