#!/usr/bin/env python3
"""Translate visible Han-script fragments in harvested addon sources to Spanish."""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HAN = re.compile(r"[\u3400-\u9fff]+(?:[\u3400-\u9fff\s，。！？、：；（）《》【】…·]+[\u3400-\u9fff]+)*")
TEXT_SUFFIXES = {".java", ".yml", ".yaml", ".json", ".md"}
SKIP_PARTS = {"target", "build", ".git"}
SKIP_NAMES = {"pack-CN.yml", "pack-TW.yml", "zh-CN.yml", "zh-TW.yml"}
CHINESE_LOCALE = re.compile(
    r"(^|[-_.])(zh|cn|tw|chinese)([-_.]|$)|simplified.?chinese|traditional.?chinese",
    re.IGNORECASE,
)


def translate_one(fragment: str) -> tuple[str, str]:
    """Translate one fragment and return its source with the validated result."""
    query = urllib.parse.urlencode({
        "client": "gtx", "sl": "zh-CN", "tl": "es", "dt": "t", "q": fragment
    })
    request = urllib.request.Request(
        "https://translate.googleapis.com/translate_a/single?" + query,
        headers={"User-Agent": "DrakesCraft-Porting/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        value = "".join(part[0] for part in payload[0] if part and part[0]).strip()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"No se pudo traducir {fragment!r}: {exc}") from exc
    if not value:
        raise RuntimeError(f"La traduccion de {fragment!r} llego vacia")
    return fragment, value


def iter_files(root: Path):
    """Yield source files while excluding builds, VCS data, and intentional Chinese locales."""
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative_parts = path.relative_to(root).parts
        if any(part in SKIP_PARTS for part in relative_parts) or path.name in SKIP_NAMES:
            continue
        if any(CHINESE_LOCALE.search(part) for part in relative_parts):
            continue
        yield path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs="+", type=Path)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--cache", type=Path, default=Path("/tmp/drakes-zh-es-cache.json"))
    args = parser.parse_args()

    try:
        cache = json.loads(args.cache.read_text("utf-8")) if args.cache.exists() else {}
    except (OSError, ValueError) as exc:
        print(f"[ERROR] No se pudo cargar la cache: {exc}")
        return 2

    changes = 0
    try:
        documents: list[tuple[Path, str]] = []
        fragments: list[str] = []
        for root in args.roots:
            for path in iter_files(root):
                original = path.read_text("utf-8")
                found = HAN.findall(original)
                if found:
                    documents.append((path, original))
                    fragments.extend(found)
        unique = list(dict.fromkeys(fragments))
        pending = [fragment for fragment in unique if fragment not in cache]
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(translate_one, fragment) for fragment in pending]
            for future in as_completed(futures):
                source, translated = future.result()
                cache[source] = translated
            args.cache.write_text(json.dumps(cache, ensure_ascii=False, indent=2), "utf-8")
        for path, original in documents:
            translated = HAN.sub(lambda match: cache[match.group(0)], original)
            changes += 1
            print(f"[INFO] {path}: {len(HAN.findall(original))} fragmentos")
            if args.write:
                path.write_text(translated, "utf-8")
        args.cache.write_text(json.dumps(cache, ensure_ascii=False, indent=2), "utf-8")
    except (OSError, UnicodeError, RuntimeError) as exc:
        print(f"[ERROR] {exc}")
        return 1

    mode = "modificados" if args.write else "detectados"
    print(f"[SUCCESS] {changes} archivos {mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
