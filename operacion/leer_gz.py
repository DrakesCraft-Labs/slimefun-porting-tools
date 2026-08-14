#!/usr/bin/env python3
"""Lee un log archivado (.gz) del servidor MC. Se ejecuta EN star.

Uso:  leer_gz.py <fichero> [patron] [lineas-contexto]
Sin patron, imprime un resumen: arranques, plugins y errores.
"""
import gzip
import io
import re
import sys

sys.path.insert(0, "/tmp")
import mcfs  # noqa: E402

ruta = mcfs.resolve("./logs/" + sys.argv[1])
with mcfs.sftp.open(ruta, "rb") as f:
    f.prefetch()
    crudo = f.read()
texto = gzip.decompress(crudo).decode("utf-8", "replace")
lineas = texto.split("\n")

if len(sys.argv) > 2:
    patron = re.compile(sys.argv[2], re.IGNORECASE)
    ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    for i, l in enumerate(lineas):
        if patron.search(l):
            for x in lineas[i:i + max(1, ctx)]:
                print(x[:220])
            if ctx:
                print("  " + "-" * 50)
else:
    print(f"  lineas: {len(lineas)}")
    print(f"  primera: {lineas[0][:90] if lineas else '-'}")
    print(f"  ultima:  {[l for l in lineas if l.strip()][-1][:90] if lineas else '-'}")
    print(f"  arranques: {len(re.findall(r'Starting minecraft server version', texto))}")
    print(f"  'Done (': {texto.count('Done (')}")
    print(f"  ERROR: {len(re.findall(r'/ERROR', texto))}  WARN: {len(re.findall(r'/WARN', texto))}")
