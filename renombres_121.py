#!/usr/bin/env python3
"""Aplica a un addon los renombres de la API de Bukkit entre 1.16 y 1.21.

POR QUE

Casi todos los addons cosechados son de 2021-2022. Entre esa epoca y 1.21 Mojang paso los enums
de Bukkit a registros y, de paso, les quito los prefijos y los nombres heredados. Un
`PotionEffectType.SLOW` compila en 1.16 y en 1.21 no existe.

Lo peligroso no es que no compile: es que si se compila contra una API vieja y se ejecuta en
1.21, el error salta en tiempo de ejecucion como NoSuchFieldError, con el servidor ya arrancado y
el jugador delante. Por eso conviene compilar SIEMPRE contra paper-api 1.21.11 y arreglar lo que
salte.

Uso:  python3 renombres_121.py <carpeta-del-repo> [--escribir]
"""
import pathlib
import re
import sys

# Cada entrada es (clase, {viejo: nuevo}). Se ancla en la clase para no tocar por accidente una
# constante del propio addon que se llame igual.
RENOMBRES = {
    "PotionEffectType": {
        "SLOW": "SLOWNESS",
        "FAST_DIGGING": "HASTE",
        "SLOW_DIGGING": "MINING_FATIGUE",
        "INCREASE_DAMAGE": "STRENGTH",
        "HEAL": "INSTANT_HEALTH",
        "HARM": "INSTANT_DAMAGE",
        "JUMP": "JUMP_BOOST",
        "CONFUSION": "NAUSEA",
        "DAMAGE_RESISTANCE": "RESISTANCE",
    },
    "Enchantment": {
        "DAMAGE_ALL": "SHARPNESS",
        "DAMAGE_UNDEAD": "SMITE",
        "DAMAGE_ARTHROPODS": "BANE_OF_ARTHROPODS",
        "DIG_SPEED": "EFFICIENCY",
        "DURABILITY": "UNBREAKING",
        "LOOT_BONUS_BLOCKS": "FORTUNE",
        "LOOT_BONUS_MOBS": "LOOTING",
        "PROTECTION_ENVIRONMENTAL": "PROTECTION",
        "PROTECTION_FIRE": "FIRE_PROTECTION",
        "PROTECTION_EXPLOSIONS": "BLAST_PROTECTION",
        "PROTECTION_PROJECTILE": "PROJECTILE_PROTECTION",
        "PROTECTION_FALL": "FEATHER_FALLING",
        "OXYGEN": "RESPIRATION",
        "WATER_WORKER": "AQUA_AFFINITY",
        "ARROW_DAMAGE": "POWER",
        "ARROW_KNOCKBACK": "PUNCH",
        "ARROW_FIRE": "FLAME",
        "ARROW_INFINITE": "INFINITY",
        "LUCK": "LUCK_OF_THE_SEA",
        "SWEEPING": "SWEEPING_EDGE",
    },
    "Particle": {
        # En 1.20.5 las particulas pasaron a registro y se renombraron casi todas. Son de las
        # que mas duelen: compilan contra la API vieja y revientan al arrancar.
        "CRIT_MAGIC": "ENCHANTED_HIT",
        "ENCHANTMENT_TABLE": "ENCHANT",
        "FIREWORKS_SPARK": "FIREWORK",
        "VILLAGER_HAPPY": "HAPPY_VILLAGER",
        "VILLAGER_ANGRY": "ANGRY_VILLAGER",
        "WATER_SPLASH": "SPLASH",
        "WATER_BUBBLE": "BUBBLE",
        "WATER_WAKE": "FISHING",
        "WATER_DROP": "RAIN",
        "SMOKE_NORMAL": "SMOKE",
        "SMOKE_LARGE": "LARGE_SMOKE",
        "EXPLOSION_NORMAL": "POOF",
        "EXPLOSION_LARGE": "EXPLOSION",
        "EXPLOSION_HUGE": "EXPLOSION_EMITTER",
        "SPELL_MOB": "ENTITY_EFFECT",
        "SPELL_WITCH": "WITCH",
        "SPELL_INSTANT": "INSTANT_EFFECT",
        "SPELL": "EFFECT",
        "DRIP_WATER": "DRIPPING_WATER",
        "DRIP_LAVA": "DRIPPING_LAVA",
        "TOWN_AURA": "MYCELIUM",
        "REDSTONE": "DUST",
        "ITEM_CRACK": "ITEM",
        "BLOCK_CRACK": "BLOCK",
        "BLOCK_DUST": "BLOCK",
        "MOB_APPEARANCE": "ELDER_GUARDIAN",
        "TOTEM": "TOTEM_OF_UNDYING",
        "SNOWBALL": "ITEM_SNOWBALL",
        "SLIME": "ITEM_SLIME",
    },
    "Material": {
        # Al aniadir las cadenas de cobre en 1.21.9, la cadena normal paso a IRON_CHAIN.
        "CHAIN": "IRON_CHAIN",
        # Renombres anteriores que siguen apareciendo en addons viejos.
        "GRASS": "SHORT_GRASS",
        "SCUTE": "TURTLE_SCUTE",
    },
    "ItemFlag": {
        "HIDE_POTION_EFFECTS": "HIDE_ADDITIONAL_TOOLTIP",
    },
    "EntityType": {
        "PRIMED_TNT": "TNT",
        "DROPPED_ITEM": "ITEM",
        "LEASH_HITCH": "LEASH_KNOT",
        "ENDER_CRYSTAL": "END_CRYSTAL",
        "FISHING_HOOK": "FISHING_BOBBER",
        "LIGHTNING": "LIGHTNING_BOLT",
        "MUSHROOM_COW": "MOOSHROOM",
        "SNOWMAN": "SNOW_GOLEM",
        "SPLASH_POTION": "POTION",
        "MINECART_CHEST": "CHEST_MINECART",
        "MINECART_FURNACE": "FURNACE_MINECART",
        "MINECART_TNT": "TNT_MINECART",
        "MINECART_HOPPER": "HOPPER_MINECART",
        "MINECART_MOB_SPAWNER": "SPAWNER_MINECART",
        "MINECART_COMMAND": "COMMAND_BLOCK_MINECART",
    },
    "Attribute": {
        "HORSE_JUMP_STRENGTH": "JUMP_STRENGTH",
        "ZOMBIE_SPAWN_REINFORCEMENTS": "SPAWN_REINFORCEMENTS",
    },
}

# Los Attribute perdieron el prefijo GENERIC_ en bloque, asi que van con una regla aparte.
PREFIJO_ATRIBUTO = re.compile(r"\bAttribute\.GENERIC_([A-Z_]+)\b")


def convertir(texto):
    cambios = 0
    for clase, tabla in RENOMBRES.items():
        for viejo, nuevo in tabla.items():
            patron = re.compile(r"\b" + clase + r"\." + viejo + r"\b")
            texto, n = patron.subn(f"{clase}.{nuevo}", texto)
            cambios += n

    texto, n = PREFIJO_ATRIBUTO.subn(r"Attribute.\1", texto)
    cambios += n
    return texto, cambios


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    repo = pathlib.Path(sys.argv[1]).resolve()
    escribir = "--escribir" in sys.argv

    total, ficheros = 0, 0
    for f in repo.rglob("*.java"):
        if "/target/" in str(f) or "/build/" in str(f):
            continue
        texto = f.read_text(encoding="utf-8", errors="replace")
        nuevo, n = convertir(texto)
        if n:
            ficheros += 1
            total += n
            if escribir:
                f.write_text(nuevo, encoding="utf-8")

    print(f"=== {repo.name} ===")
    print(f"  {total} renombres en {ficheros} ficheros"
          f"{'' if escribir else '  (simulacion, usa --escribir)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
