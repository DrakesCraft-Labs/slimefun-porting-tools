import glob, os, yaml

def num(v):
    try: return float(str(v).strip())
    except Exception: return None

def precio(item, clave):
    sec = item.get(clave)
    if not isinstance(sec, dict): return None
    mejor = None
    for _, entry in sec.items():
        if isinstance(entry, dict):
            v = num(entry.get("amount"))
            if v is not None and (mejor is None or v < mejor): mejor = v
    return mejor

filas = []
for path in sorted(glob.glob("/tmp/ushop/*.yml")):
    try: data = yaml.safe_load(open(path, encoding="utf-8-sig", errors="replace"))
    except Exception as e:
        print("SKIP", os.path.basename(path), e); continue
    if not isinstance(data, dict): continue
    for slot, item in (data.get("items") or {}).items():
        if not isinstance(item, dict): continue
        prods = item.get("products") or {}
        mat, cant = "?", 1
        for _, p in prods.items():
            if isinstance(p, dict):
                mat = p.get("material", "?"); cant = p.get("amount", 1) or 1
                break
        compra, venta = precio(item, "buy-prices"), precio(item, "sell-prices")
        if compra and venta:
            filas.append((venta / compra, os.path.basename(path), slot, mat, cant, compra, venta))

filas.sort(reverse=True)
print(f"items con compra Y venta: {len(filas)}")
print()
for ratio, f, slot, mat, cant, c, v in filas[:15]:
    marca = "  <<< ARBITRAJE" if ratio >= 1.0 else ""
    print(f"{ratio:6.3f}  {f:<18} {slot:<4} {mat:<24} x{cant:<4} compra={c:<10.0f} venta={v:<10.0f}{marca}")
