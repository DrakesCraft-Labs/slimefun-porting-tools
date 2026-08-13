#!/usr/bin/env python3
"""Saca la traza CONTIGUA que sigue a una linea del log. Se ejecuta EN star.

Sacar lineas sueltas con grep de un log con varias excepciones entrelazadas mezcla causas de unas
con marcos de otras, y lleva a diagnosticar el plugin equivocado.

Uso:  traza.py <patron> [lineas]
"""
import re
import sys

sys.path.insert(0, "/tmp")
import mcfs  # noqa: E402

with mcfs.sftp.open(mcfs.resolve("./logs/latest.log"), "rb") as f:
    f.prefetch()
    f.seek(0, 2)
    total = f.tell()
    f.seek(max(0, total - (12 << 20)))
    lineas = f.read().decode("utf-8", "replace").split("\n")

patron = re.compile(sys.argv[1])
cuantas = int(sys.argv[2]) if len(sys.argv) > 2 else 25
for i, l in enumerate(lineas):
    if patron.search(l):
        for x in lineas[i:i + cuantas]:
            print(x[:220])
        print("  " + "-" * 60)
