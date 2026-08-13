#!/usr/bin/env python3
"""Traduce lo que quedaba en chino de tres addons ya desplegados.

POR QUE QUEDABA

RandomExpansion y SlimefunOreChunks se portaron antes de que existiera la tabla de traduccion, y
IDreamOfEasy se porto ayer y se paso por alto. En el juego se veian los grupos de la guia en
chino -- 随机拓展, 矿石块, 易梦 -- que es lo primero que ve cualquiera al abrirla.

Se sustituye de la cadena mas larga a la mas corta: varias son subcadena de otra.

Uso:  python3 traducir_resto.py [--escribir]
"""
import pathlib
import re
import sys

BASE = pathlib.Path(__file__).parent / "limpio"


RANDOM_EXPANSION = {
    "&4随机拓展": "&4Expansión Aleatoria",
    "&4黑暗之心": "&4Corazón de las Tinieblas",
    "&4一种神秘的肉粉": "&4Un polvo de carne misterioso",
    "&4一种神秘的肉锭": "&4Un lingote de carne misterioso",
    "&4禽兽粉": "&4Polvo Bestial",
    "&4禽兽锭": "&4Lingote Bestial",
    "&7&n用于制造怪兽盔甲的抗性膜": "&7&nMembrana resistente para forjar la armadura monstruosa",
    "&7包含各种生物的精华...": "&7Contiene la esencia de toda clase de criaturas...",
    "&8+25%恐吓并提供夜视能力": "&8+25% de intimidación y visión nocturna",
    "&8+25%恐吓": "&8+25% de intimidación",
    "&8怪兽头盔": "&8Casco Monstruoso",
    "&8怪兽胸甲": "&8Peto Monstruoso",
    "&8怪兽护腿": "&8Grebas Monstruosas",
    "&8怪兽靴子": "&8Botas Monstruosas",
}

ORE_CHUNKS = {
    "&6矿石块": "&6Fragmentos de Mineral",
    "&7使用矿石粉碎机粉碎以获得矿粉": "&7Tritúralo en la Trituradora para sacar polvo",
    "&7可在冶炼炉种烧成锭": "&7Se funde en lingote en el horno",
    "金矿石块": "Fragmento de Oro",
    "钴矿石块": "Fragmento de Cobalto",
    "铁矿石块": "Fragmento de Hierro",
    "铅矿石块": "Fragmento de Plomo",
    "铜矿石块": "Fragmento de Cobre",
    "铝矿石块": "Fragmento de Aluminio",
    "银矿石块": "Fragmento de Plata",
    "锌矿石块": "Fragmento de Zinc",
    "锡矿石块": "Fragmento de Estaño",
    "镁矿石块": "Fragmento de Magnesio",
    "镍矿石块": "Fragmento de Níquel",
}

IDOE = {
    # --- marca ---
    "    易梦 - 粘液科技简中汉化组汉化    ": "    IDreamOfEasy - traducido para DrakesCraft    ",
    "&2易梦": "&2IDreamOfEasy",

    # --- maquinas y objetos ---
    "&a创造 GPS 发射器": "&aEmisor GPS Creativo",
    "&a创造发电机": "&aGenerador Creativo",
    "&a创造电容": "&aCondensador Creativo",
    "&a史莱姆增生餐": "&aBanquete de Crecimiento para Slimes",
    "&a史莱姆抑制器": "&aInhibidor de Slimes",
    "&a僵尸抑制器": "&aInhibidor de Zombis",
    "&a女巫抑制器": "&aInhibidor de Brujas",
    "&a苦力怕抑制器": "&aInhibidor de Creepers",
    "&a蜘蛛抑制器": "&aInhibidor de Arañas",
    "&a蝙蝠抑制器": "&aInhibidor de Murciélagos",
    "&a骷髅抑制器": "&aInhibidor de Esqueletos",
    "&a僵尸村民": "&aAldeano Zombi",
    "&a不详药水": "&aPoción Nefasta",
    "&a凿子": "&aCincel",
    "&a启蒙之书": "&aLibro de la Iluminación",
    "&a堆叠发射器": "&aLanzador de Pilas",
    "&a头颅移除器": "&aExtractor de Cabezas",
    "&a岩浆船": "&aBarca de Lava",
    "&a末影人": "&aEnderman",
    "&a玩家漏斗": "&aTolva de Jugador",
    "&a补给漏斗": "&aTolva de Suministro",
    "&a生物群系探针": "&aSonda de Biomas",
    "&a电力剪毛机": "&aEsquiladora Eléctrica",
    "&a电力毒药提取器": "&aExtractor de Veneno Eléctrico",
    "&a电力爆炸铲": "&aPala Explosiva Eléctrica",
    "&a电力爆炸镐": "&aPico Explosivo Eléctrico",
    "&a电力去皮器 &7(&eIII&7)": "&aDescortezadora Eléctrica &7(&eIII&7)",
    "&a电力去皮器 &7(&eII&7)": "&aDescortezadora Eléctrica &7(&eII&7)",
    "&a电力去皮器": "&aDescortezadora Eléctrica",
    "&a电力烟熏炉 &7(&eIII&7)": "&aAhumador Eléctrico &7(&eIII&7)",
    "&a电力烟熏炉 &7(&eII&7)": "&aAhumador Eléctrico &7(&eII&7)",
    "&a电力烟熏炉": "&aAhumador Eléctrico",
    "&a电力高炉 &7(&eIII&7)": "&aAlto Horno Eléctrico &7(&eIII&7)",
    "&a电力高炉 &7(&eII&7)": "&aAlto Horno Eléctrico &7(&eII&7)",
    "&a电力高炉": "&aAlto Horno Eléctrico",
    "&a电线 &7(&eIII&7)": "&aCable &7(&eIII&7)",
    "&a电线 &7(&eII&7)": "&aCable &7(&eII&7)",
    "&a电线": "&aCable",
    "&a辐射吸收器 &7(&eIII&7)": "&aAbsorbedor de Radiación &7(&eIII&7)",
    "&a辐射吸收器 &7(&eII&7)": "&aAbsorbedor de Radiación &7(&eII&7)",
    "&a辐射吸收器": "&aAbsorbedor de Radiación",
    "&a盔甲纹饰宝库": "&aBóveda de Grabados de Armadura",
    "&a磁石": "&aPiedra Imán",
    "&a闹钟": "&aDespertador",
    "&a韦斯特之剪": "&aTijeras de Wester",
    "&a+ 精准采集": "&a+ Toque de Seda",

    # --- idolos ---
    "&a&l人族神像": "&a&lÍdolo Humano",
    "&b&l激流神像": "&b&lÍdolo del Torrente",
    "&c&l火焰之心神像": "&c&lÍdolo del Corazón de Fuego",

    # --- tuneladoras ---
    "&e精英盾构机": "&eTuneladora de Élite",
    "&e高级盾构机": "&eTuneladora Avanzada",
    "&e盾构机": "&eTuneladora",

    # --- atributos de los idolos ---
    "&8⇨ &a长大吧，超级史莱姆们！": "&8⇨ &a¡Creced, superslimes!",
    "&8⇨ &a不会对拥有者生效": "&8⇨ &aNo afecta a su dueño",
    "&8⇨ &a可记忆位置": "&8⇨ &aRecuerda la posición",
    "&8⇨ &a瞬间研究": "&8⇨ &aInvestigación instantánea",
    "&8⇨ &a不可破坏": "&8⇨ &aIrrompible",
    "&8⇨ &a岩浆行者：&720%": "&8⇨ &aCaminante de Lava: &720%",
    "&8⇨ &a穴居者：&750%": "&8⇨ &aTroglodita: &750%",
    "&8⇨ &a消防员：&720%": "&8⇨ &aBombero: &720%",
    "&8⇨ &a潜水者：&720%": "&8⇨ &aBuceador: &720%",
    "&8⇨ &a旅行者：&760%": "&8⇨ &aViajero: &760%",
    "&8⇨ &a魔法师：&780%": "&8⇨ &aHechicero: &780%",
    "&8⇨ &a铁砧： &720%": "&8⇨ &aYunque: &720%",
    "&8⇨ &a旋风：&760%": "&8⇨ &aTorbellino: &760%",
    "&8⇨ &a天使：&775%": "&8⇨ &aÁngel: &775%",
    "&8⇨ &a骑士：&730%": "&8⇨ &aCaballero: &730%",
    "&8⇨ &a农夫：&720%": "&8⇨ &aGranjero: &720%",
    "&8⇨ &a战士：&720%": "&8⇨ &aGuerrero: &720%",
    "&8⇨ &a猎人：&720%": "&8⇨ &aCazador: &720%",
    "&8⇨ &a矿工：&720%": "&8⇨ &aMinero: &720%",
    "&8⇨ &a巫师：&720%": "&8⇨ &aBrujo: &720%",
    "&8⇨ &a智者：&720%": "&8⇨ &aSabio: &720%",
    "&8⇨ &4不会吸取护甲与副手物品": "&8⇨ &4No absorbe la armadura ni lo de la mano secundaria",
    "&8⇨ &4在水中无浮力": "&8⇨ &4No flota en el agua",
    "&8⇨ &4烫烫烫！": "&8⇨ &4¡Quema, quema, quema!",

    # --- descripciones ---
    "&7仅能通过&e/sf cheat &7获取": "&7Solo se consigue con &e/sf cheat&7",
    "&f一个可以几乎提供无限": "&fCapaz de dar prácticamente energía",
    "&fGPS 复杂度的发射器": "&fEmisor de complejidad GPS",
    "&f一整组物品": "&fUna pila entera de objetos",
    "&f下方 11x11 区域内的": "&fen el área de 11x11 de debajo",
    "&f下方 21x21 区域内的": "&fen el área de 21x21 de debajo",
    "&f下方 7x7 区域内的": "&fen el área de 7x7 de debajo",
    "&f以在岩浆上行驶": "&fpara navegar sobre la lava",
    "&f会伤害任何触碰的实体": "&fHace daño a lo que la toque",
    "&f会试图发射": "&fIntentará lanzar",
    "&f作为机器燃料。": "&fcomo combustible de la máquina.",
    "&f使用材料和玻璃瓶": "&fUsa materiales y una botella",
    "&f制作剧毒药水": "&fpara preparar veneno concentrado",
    "&f可以修剪所有的东西": "&fPoda cualquier cosa",
    "&f可增大其体积": "&fpara que crezca de tamaño",
    "&f可瞬间破坏任何头颅": "&fRompe al instante cualquier cabeza",
    "&f吸取你物品栏中的物品": "&fSaca objetos de tu inventario",
    "&f在区块中放置该机器": "&fColoca esta máquina en el chunk",
    "&f在脚下放置一艘防火船": "&fPone bajo tus pies una barca ignífuga",
    "&f对史莱姆使用": "&fÚsalo sobre un slime",
    "&f将&n随机&r&f知识": "&fMete conocimiento &naleatorio&r&f",
    "&f将部分方块雕纹": "&fGraba algunos bloques",
    "&f将阻止指定生物的生acion": "&fImpide que aparezca esa criatura",
    "&f将阻止指定生物的生成": "&fImpide que aparezca esa criatura",
    "&f指定的生物群系。优先指向新区域。": "&fel bioma indicado. Prioriza zonas nuevas.",
    "&f接收物品到你的物品栏": "&fRecibe objetos en tu inventario",
    "&f放入煤矿或其他相似物品": "&fMete carbón u otro material parecido",
    "&f电动的爆炸铲": "&fLa pala explosiva, con motor",
    "&f电动的爆炸镐": "&fEl pico explosivo, con motor",
    "&f盔甲纹饰模版": "&fPlantillas de grabado de armadura",
    "&f直接灌输进你的脑袋": "&fdirectamente en tu cabeza",
    "&f破坏以获得随机的": "&fRómpelo para sacar algo al azar",
    "&f磁石会不断吸收周围的物品": "&fLa piedra imán atrae lo que hay alrededor",
    "&f站在该漏斗上方会自动": "&fPonte encima de la tolva y",
    "&f站在该漏斗下方会自动": "&fPonte debajo de la tolva y",
    "&f该多方块结构会挖掘": "&fEsta estructura excava",
    "&f跳过了那些沉闷的研究步骤": "&fsaltándote los pasos aburridos de investigar",
    "&c任何方块&f。": "&ccualquier bloque&f.",
    "&c防火": "&cIgnífugo",
    "&e不会消耗": "&eNo se gasta",
    "&e伤害：&72": "&eDaño: &72",
    "&e伤害：&74": "&eDaño: &74",
    "&e伤害：&76": "&eDaño: &76",
    "&f在": "&fen",

    # --- controles ---
    "&e蹲下 + 右键点击 任意方块&7切换到上一个生物群系":
        "&eAgáchate + clic derecho en un bloque&7 para ir al bioma anterior",
    "&e蹲下 + 右键点击 空气&7切换到下一个生物群系":
        "&eAgáchate + clic derecho al aire&7 para ir al siguiente bioma",
    "&e蹲下 + 右键点击&7切换闹钟模式": "&eAgáchate + clic derecho&7 para cambiar el modo del despertador",
    "&e右键点击&7切换消息显示": "&eClic derecho&7 para mostrar u ocultar los mensajes",
    "&e右键点击&7对生物使用": "&eClic derecho&7 sobre una criatura",
    "&e右键点击&7设置计时器": "&eClic derecho&7 para poner el temporizador",
    "&e右键点击&7进行搜索": "&eClic derecho&7 para buscar",
    "&e右键点击&7以使用": "&eClic derecho&7 para usarlo",
    "&e副手手持&7以使用": "&eLlévalo en la mano secundaria&7 para que funcione",
    "&e左键点击&7以修剪树叶于草丛": "&eClic izquierdo&7 para podar hojas y hierba",

    # --- mensajes en juego ---
    "§c你必须等待一段时间才能再次使用该物品。": "§cTienes que esperar un poco para volver a usarlo.",
    "§c无效的输entrada，请输入有效的数字。": "§cEntrada no válida, escribe un número.",
    "§c无效的输入，请输入有效的数字。": "§cEntrada no válida, escribe un número.",
    "§c经验不足或你已解锁所有研究。": "§cNo tienes experiencia suficiente, o ya lo has desbloqueado todo.",
    "§e将不再于该区块中生成。": "§eya no aparecerá en este chunk.",
    "§e将恢复于该区块中的生成。": "§evuelve a aparecer en este chunk.",
    "§e已选定生物群系：": "§eBioma elegido: ",
    "§e定时器已设置为§f": "§eTemporizador puesto en §f",
    "§a闹钟已启用。": "§aDespertador activado.",
    "§c闹钟已禁用。": "§cDespertador desactivado.",
    "§c附近没有找到 ": "§cNo hay cerca ningún ",
    "§a输入秒数": "§aEscribe los segundos",
    "§a找到 ": "§aEncontrado ",
    "§e秒。": "§e segundos.",
    " §a消息已启用": " §amensajes activados",
    " §c消息已禁用": " §cmensajes desactivados",
    " §a生物群系, 距离你 ": " §a, a una distancia de ",
    " §c生物群系。": " §c.",
    " §a格！": " §abloques!",
    " 可储存": " almacenable",
    "格内搜索": "de búsqueda",

    # --- efectos de los idolos ---
    ": §r§a已添加时运 II 附魔!": ": §r§a¡Fortuna II añadida!",
    ": §r§a已免疫摔落伤害！": ": §r§a¡Inmune al daño por caída!",
    ": §r§a已反弹投射物！": ": §r§a¡Proyectil rebotado!",
    ": §r§a双倍矿物掉落！": ": §r§a¡Botín de mineral doble!",
    ": §r§a双倍掉落！": ": §r§a¡Botín doble!",
    ": §r§a双倍作物！": ": §r§a¡Cosecha doble!",
    ": §r§a双倍经验！": ": §r§a¡Experiencia doble!",
    ": §r§a强化附魔!": ": §r§a¡Encantamiento reforzado!",
    ": §r§a已保住 ": ": §r§aSalvado ",
    ": §r§a+水下呼吸": ": §r§a+Respiración acuática",
    ": §r§a+火焰保护": ": §r§a+Protección contra el fuego",
    ": §r§a+生命恢复": ": §r§a+Regeneración",
    ": §r§a+速度 II": ": §r§a+Velocidad II",
    ": §r§a+力量 III": ": §r§a+Fuerza III",
    ": §r§a+急迫 II": ": §r§a+Prisa II",

    # --- nombres de criatura sueltos ---
    "僵尸村民": "Aldeano Zombi",
    "僵尸": "Zombi",
    "史莱姆": "Slime",
    "女巫": "Bruja",
    "末影人": "Enderman",
    "苦力怕": "Creeper",
    "蜘蛛": "Araña",
    "蝙蝠": "Murciélago",
    "骷髅": "Esqueleto",
}


TABLAS = [
    ("RandomExpansion", RANDOM_EXPANSION),
    ("SlimefunOreChunks", ORE_CHUNKS),
    ("IDreamOfEasy", IDOE),
]


def main():
    escribir = "--escribir" in sys.argv

    for addon, tabla in TABLAS:
        base = BASE / addon
        if not base.is_dir():
            print(f"  falta el repo: {addon}")
            continue

        pares = sorted(tabla.items(), key=lambda kv: -len(kv[0]))
        tocados = 0
        for f in base.rglob("*.java"):
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
        for f in base.rglob("*.java"):
            if "/target/" in str(f):
                continue
            for m in re.finditer(r'"([^"]*[一-鿿][^"]*)"',
                                 f.read_text(encoding="utf-8", errors="replace")):
                restantes.add(m.group(1))

        print(f"  {addon}: {tocados} ficheros, quedan {len(restantes)} cadenas")
        for r in sorted(restantes)[:6]:
            print(f"      {r!r}")

    if not escribir:
        print("  (simulacion; usa --escribir)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
