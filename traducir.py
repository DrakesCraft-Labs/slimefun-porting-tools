#!/usr/bin/env python3
"""Traduce al español las cadenas chinas que quedan en los addons cosechados.

Los forks chinos tradujeron nombres, descripciones y mensajes; sin esto el addon llega al
servidor en chino. Se traduce del chino y no del ingles original porque en varios sitios el fork
cambio el texto ademas de traducirlo.

IMPORTANTE: se sustituye de la cadena mas larga a la mas corta. Varias son subcadena de otra
("&f普通" lo es de "&f普通击退力"), y en el orden natural la corta parte a la larga y deja un
resto en chino pegado a la traduccion.

Los codigos de color (&c, &7...) y los marcadores ({0}) se conservan tal cual.

Uso:  python3 traducir.py <addon> [--escribir]
"""
import pathlib
import sys

BASE = pathlib.Path(__file__).parent / "limpio"

HARDCORE = {
    "&c你丢失了一个已解锁的研究!": "&cHas perdido una investigación que ya tenías desbloqueada!",
    "&c你丢失了所有研究!": "&cHas perdido todas tus investigaciones!",
    "&c你的机器人出了点故障! 它将在一段时间后恢复工作.":
        "&cTu robot se ha averiado! Volverá a funcionar dentro de un rato.",
    "&c研究失败!": "&cLa investigación ha fallado!",
    "你没有安装 Slimefun! 本插件将不会启用...":
        "No tienes Slimefun instalado! Este plugin no se va a activar...",
}

NEA = {
    # --- marca y grupos de la guia ---
    "&2&n&l多&a彩&2&l科&r&a技 &r&7> &r": "&2&n&lNot&aEnough&2&lAdd&r&aons &r&7> &r",
    "&2多彩科技": "&2NotEnoughAddons",
    "&b多彩科技 - 机器": "&bNotEnoughAddons - Máquinas",
    "&b多彩科技 - 物品": "&bNotEnoughAddons - Objetos",

    # --- objetos ---
    "&6天使方块": "&6Bloque Ángel",
    "&6矿工背包 &r已满": "&6Mochila de Minero &rllena",
    "&6矿工背包": "&6Mochila de Minero",
    "&6经济型矿粉制造机": "&6Fabricador de Polvo Económico",
    "&6飞行泡泡": "&6Burbuja Voladora",

    # --- descripciones ---
    "&7&o为懒狗制作的机器...": "&7&oUna máquina para vagos...",
    "&7一个经济型多合一机器,": "&7Una máquina todo en uno y barata,",
    "&7可以直接使用圆石或者其他变种来获取矿粉":
        "&7saca polvo de mineral directamente de la roca o sus variantes",
    "&7在你脚下放置一个方块": "&7Coloca un bloque bajo tus pies",
    "&7大小: &e54 (大箱子)": "&7Tamaño: &e54 (cofre grande)",
    "&7当你在空中时非常好用": "&7Viene muy bien cuando estás en el aire",
    "&f任何圆石变种": "&fCualquier variante de roca",
    "&f可以在周围45格内获得创造模式飞行的能力":
        "&fDeja volar en modo creativo a 45 bloques a la redonda",
    "&f可以存储矿物": "&fGuarda minerales",
    "&f在捡起矿物时自动存入": "&fLos guarda solos al recogerlos",
    "&f在物品栏中时生效": "&fBasta con llevarlo en el inventario",

    # --- piedras ---
    "&7圆石": "&7Roca",
    "&7安山岩": "&7Andesita",
    "&7花岗岩": "&7Granito",
    "&7闪长岩": "&7Diorita",

    # --- escala de retroceso ---
    "&f无击退力": "&fSin retroceso",
    "&f极弱击退力": "&fRetroceso mínimo",
    "&f很弱击退力": "&fRetroceso muy débil",
    "&f较弱击退力": "&fRetroceso débil",
    "&f普通击退力": "&fRetroceso normal",
    "&f较强击退力": "&fRetroceso fuerte",
    "&f很强击退力": "&fRetroceso muy fuerte",
    "&f极强击退力": "&fRetroceso extremo",
    "&f疯狂击退力": "&fRetroceso brutal",
    "&f未知击退力": "&fRetroceso desconocido",

    # --- escala de velocidad ---
    "&f蜗牛": "&fCaracol",
    "&f极慢": "&fLentísimo",
    "&f很慢": "&fMuy lento",
    "&f慢": "&fLento",
    "&f普通": "&fNormal",
    "&f很快": "&fMuy rápido",
    "&f超快": "&fRapidísimo",
    "&f快": "&fRápido",

    # --- dagas ---
    "&f金短剑": "&fDaga de Oro",
    "&f钨短剑": "&fDaga de Tungsteno",
    "&f铁短剑": "&fDaga de Hierro",
    "&f铂金短剑": "&fDaga de Platino",
    "&f铅短剑": "&fDaga de Plomo",
    "&f铜短剑": "&fDaga de Cobre",
    "&f银短剑": "&fDaga de Plata",
    "&f锡短剑": "&fDaga de Estaño",

    # --- estadisticas y mensajes ---
    " 近战伤害": " de daño cuerpo a cuerpo",
    "% 暴击率": "% de probabilidad de crítico",
    "&a已设置信息.": "&aInformación guardada.",
    "&c你必须看向一个Slimefun方块": "&cTienes que estar mirando a un bloque de Slimefun",
    "&c只有玩家才能执行该指令": "&cEste comando solo lo puede usar un jugador",
    "&c指令不存在": "&cEse comando no existe",
    "&c请指定键值": "&cTienes que indicar la clave",
    "&e当前插件版本为: ": "&eVersión del plugin: ",
    "已保存 {0} 位玩家的数据!": "Datos de {0} jugadores guardados!",
}

TABLAS = {
    "HardcoreSlimefun": HARDCORE,
    "NotEnoughAddons": NEA,
}


def traducir(addon, tabla, escribir):
    repo = BASE / addon
    if not repo.is_dir():
        print(f"  no existe: {addon}")
        return

    # De mas larga a mas corta: ver la nota de la cabecera.
    pares = sorted(tabla.items(), key=lambda kv: -len(kv[0]))

    tocados = 0
    for f in repo.rglob("*.java"):
        if "/target/" in str(f):
            continue
        texto = original = f.read_text(encoding="utf-8", errors="replace")
        for zh, es in pares:
            texto = texto.replace(zh, es)
        if texto != original:
            tocados += 1
            if escribir:
                f.write_text(texto, encoding="utf-8")

    restantes = sum(
        1 for f in repo.rglob("*.java")
        if "/target/" not in str(f)
        and any("一" <= c <= "鿿" for c in f.read_text(encoding="utf-8", errors="replace"))
    )
    print(f"  {addon}: {tocados} ficheros, quedan {restantes} con chino")


def main():
    escribir = "--escribir" in sys.argv
    pedidos = [a for a in sys.argv[1:] if not a.startswith("--")] or list(TABLAS)
    for addon in pedidos:
        if addon in TABLAS:
            traducir(addon, TABLAS[addon], escribir)
        else:
            print(f"  sin tabla para {addon}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
