#!/usr/bin/env python3
"""Traduce al español el catalogo de ObsidianExpansion.

Dos avisos sobre el criterio:

1. El fork distingue 发电机 (genera ELECTRICIDAD) de 发生器 (genera MATERIAL), y en chino se
   parecen mucho. Traducirlos igual dejaria dos maquinas distintas con el mismo nombre, que es
   justo lo que confunde a un jugador delante de la guia. Aqui van como "Generador Electrico" y
   "Generador" respectivamente.

2. Buena parte del lore son versos clasicos chinos -- hay al menos un verso de Wang Han, de la
   dinastia Tang. Traducidos palabra por palabra no dicen nada en español, asi que se traducen
   por su sentido, buscando que suenen a lo que son: texto de ambientacion.

Se sustituye de la cadena mas larga a la mas corta, porque varias son subcadena de otra.
"""
import pathlib
import sys

BASE = pathlib.Path(__file__).parent / "limpio" / "ObsidianExpansion"

T = {
    # --- grupos de la guia ---
    "<gradient:#8100D1:#D320FC>黑曜石科技</gradient>": "<gradient:#8100D1:#D320FC>Tecnología de Obsidiana</gradient>",
    "<gradient:#8100D1:#D320FC>材料发生器</gradient>": "<gradient:#8100D1:#D320FC>Generadores de Material</gradient>",
    "<gradient:#8100D1:#D320FC>生物掉落物</gradient>": "<gradient:#8100D1:#D320FC>Botín de Criaturas</gradient>",
    "<gradient:#8100D1:#D320FC>机器</gradient>": "<gradient:#8100D1:#D320FC>Máquinas</gradient>",
    "<gradient:#8100D1:#D320FC>物品</gradient>": "<gradient:#8100D1:#D320FC>Objetos</gradient>",
    "<gradient:#8100D1:#D320FC>资源</gradient>": "<gradient:#8100D1:#D320FC>Recursos</gradient>",
    "<gradient:#8100D1:#D320FC>锻造</gradient>": "<gradient:#8100D1:#D320FC>Forja</gradient>",
    "&2资源发生器": "&2Generadores de Recursos",
    "&2机器": "&2Máquinas",
    "&2材料": "&2Materiales",
    "&b机器": "&bMáquinas",
    "&a发电机": "&aGeneradores",
    "&8工具": "&8Herramientas",
    "&7资源": "&7Recursos",

    # --- maquinas ---
    "&8&l虚空&c&l黑曜石发生器": "&8&lGenerador de Obsidiana del &c&lVacío",
    "&b&l高级&5&l黑曜石发电机": "&b&lGenerador Eléctrico de Obsidiana &5&lAvanzado",
    "&l&4下界合金转换机": "&l&4Conversor de Netherita",
    "&l&5黑曜石锻造桌": "&l&5Mesa de Forja de Obsidiana",
    "&5&l黑曜石发电机": "&5&lGenerador Eléctrico de Obsidiana",
    "&c&l黑曜石发生器": "&c&lGenerador de Obsidiana",

    # --- materiales ---
    "&4&l深渊&8&l黑曜石核心": "&4&lNúcleo de Obsidiana &8&lAbisal",
    "&4&l远古黑曜石板": "&4&lPlaca de Obsidiana Ancestral",
    "&6&l强化飞行核心 &5&lIII": "&6&lNúcleo de Vuelo Reforzado &5&lIII",
    "&6&l强化飞行核心 &5&lII": "&6&lNúcleo de Vuelo Reforzado &5&lII",
    "&6&l强化飞行核心 &5&lI": "&6&lNúcleo de Vuelo Reforzado &5&lI",
    "&7&l黑曜石齿轮": "&7&lEngranaje de Obsidiana",
    "&5&l黑曜石板": "&5&lPlaca de Obsidiana",
    "&5&l幽魂元": "&5&lEsencia Espectral",
    "&d&l龙角": "&d&lCuerno de Dragón",
    "虚空核心": "Núcleo del Vacío",

    # --- armadura ---
    "&5&l捍卫者之铠": "&5&lCoraza del Defensor",
    "&5&l穹顶之靴": "&5&lBotas de la Bóveda",
    "&5&l虚空之冠": "&5&lCorona del Vacío",
    "&5&l鬼泣之裤": "&5&lGrebas del Lamento",

    # --- herramientas ---
    "&l强化刷怪笼之镐": "&lPico Reforzado de Generadores",
    "用于收集刷怪笼": "Sirve para recoger generadores de monstruos",

    # --- obsidiana comprimida y cantidades ---
    "&7&l压缩黑曜石 x1": "&7&lObsidiana Comprimida x1",
    "&7&l压缩黑曜石 x2": "&7&lObsidiana Comprimida x2",
    "&7&l压缩黑曜石 x3": "&7&lObsidiana Comprimida x3",
    "&8&l压缩黑曜石 x4": "&8&lObsidiana Comprimida x4",
    "&8&l压缩黑曜石 x5": "&8&lObsidiana Comprimida x5",
    "&l&7 59049 &7个黑曜石": "&l&7 59.049 &7de obsidiana",
    "&l&7 6561 &7个黑曜石": "&l&7 6.561 &7de obsidiana",
    "&7&l 729 &7个黑曜石": "&7&l 729 &7de obsidiana",
    "&7&l 81 &7个黑曜石": "&7&l 81 &7de obsidiana",
    "&7&l 9 &7个黑曜石": "&7&l 9 &7de obsidiana",

    # --- efectos ---
    "&7海豚的恩惠 III": "&7Gracia del Delfín III",
    "&7抗性提升 II": "&7Resistencia II",
    "&7跳跃提升 III": "&7Salto Mejorado III",
    "&7水下呼吸 I": "&7Respiración Acuática I",
    "&7生命恢复 II": "&7Regeneración II",
    "&7生命提升 I": "&7Vida Extra I",
    "&7急迫 III": "&7Prisa III",
    "&7夜视 I": "&7Visión Nocturna I",
    "&7幸运 II": "&7Suerte II",
    "&7力量 II": "&7Fuerza II",
    "&7饱和 IV": "&7Saturación IV",
    "&7速度 I": "&7Velocidad I",

    # --- vuelo ---
    "&f给予你永久飞行能力": "&fTe deja volar para siempre",
    "&f可以调节飞行速度": "&fSe le puede regular la velocidad",
    "&f&o像鸟一样飞翔~": "&f&oVolar como un pájaro~",
    "&7最大速度: 0.1": "&7Velocidad máxima: 0.1",
    "&7最大速度: 0.2": "&7Velocidad máxima: 0.2",
    "&7最大速度: 0.3": "&7Velocidad máxima: 0.3",
    "&7飞行开关: <enabled>": "&7Vuelo: <enabled>",
    "&7飞行速度: <speed>": "&7Velocidad de vuelo: <speed>",
    "飞行开关: <enabled>": "Vuelo: <enabled>",
    "飞行速度: ": "Velocidad de vuelo: ",

    # --- descripciones ---
    "&8将圆石转换为下界合金锭": "&8Convierte roca en lingotes de netherita",
    "&8用于合成更先进的机器物品": "&8Sirve para fabricar máquinas más avanzadas",
    "&8利用黑曜石发电机": "&8Aprovecha el generador eléctrico de obsidiana",
    "&8更高效的发电机": "&8Un generador más eficiente",
    "&5无限生产黑曜石": "&5Produce obsidiana sin límite",
    "&0&l拥有坚硬的外壳": "&0&lDe caparazón durísimo",
    "&0&l与神秘的内芯...": "&0&ly núcleo misterioso...",
    "&a神秘且珍奇": "&aMisterioso y difícil de encontrar",

    # --- interfaz ---
    "&b锻造 &7- &c作弊模式": "&bForja &7- &cmodo trampa",
    "&a右击 制作多个": "&aClic derecho: fabricar varios",
    "&a左击 制作1个": "&aClic izquierdo: fabricar uno",
    "&a> 单击解锁": "&a> Clic para desbloquear",
    "&a生产中...": "&aProduciendo...",
    "使用储存中的物品: ": "Usar objetos del almacén: ",
    "感受深渊的力量吧！": "¡Siente el poder del abismo!",
    " &c类别查看正确的配方!": " &cpara ver la receta correcta!",
    "电量不足!": "¡Energía insuficiente!",
    "电能: ": "Energía: ",
    "&7耗费: &b": "&7Cuesta: &b",
    "&6输出": "&6Salida",
    "&7生成": "&7Genera",
    " 等级": " nivel",
    "&c请在 ": "&cMira en ",
    "关": "No",
    "开": "Sí",

    # --- lore: versos clasicos, traducidos por sentido ---
    "&l当天堂塌陷，地狱升起": "&lCuando el cielo se derrumba y el infierno asciende",
    "&l醉卧沙场君莫笑": "&lNo te rías del que duerme ebrio en el campo de batalla",
    "&l人间是否还会存在": "&l¿Seguirá existiendo el mundo de los hombres?",
    "&l古来征战几人回": "&lDe tantas guerras, ¿cuántos han vuelto?",
    "&l一统于天下...": "&lUn solo dueño bajo el cielo...",
    "&l鬼泣于黑暗": "&lLos espectros lloran en la oscuridad",
    "&l魂出于於菟": "&lEl alma escapa por las fauces del tigre",
    "&5&l鬼可控否？": "&5&l¿Se puede dominar a un espectro?",
    "&5&l答曰:否...": "&5&lY la respuesta fue: no...",
    "&7未能止其步履": "&7Nada logró detener sus pasos",
    "&7满面疮痍": "&7El rostro cubierto de cicatrices",
    "&7囷囷而延": "&7Se extiende en espirales",
    "&l吾主": "&lMi señor",
}


def main():
    escribir = "--escribir" in sys.argv
    pares = sorted(T.items(), key=lambda kv: -len(kv[0]))

    tocados = 0
    for f in BASE.rglob("*.java"):
        if "/target/" in str(f):
            continue
        texto = original = f.read_text(encoding="utf-8", errors="replace")
        for zh, es in pares:
            texto = texto.replace(zh, es)
        if texto != original:
            tocados += 1
            if escribir:
                f.write_text(texto, encoding="utf-8")

    restantes = set()
    import re
    for f in BASE.rglob("*.java"):
        if "/target/" in str(f):
            continue
        for m in re.finditer(r'"([^"]*[一-鿿][^"]*)"', f.read_text(encoding="utf-8", errors="replace")):
            restantes.add(m.group(1))

    print(f"  ficheros tocados: {tocados}")
    print(f"  cadenas con chino que quedan: {len(restantes)}")
    for r in sorted(restantes)[:10]:
        print(f"    {r!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
