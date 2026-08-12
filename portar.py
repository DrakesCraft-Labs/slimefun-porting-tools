#!/usr/bin/env python3
"""Porta un addon de Slimefun al ecosistema DrakesCraft (Paper/Purpur 1.21.11, Java 21).

QUE HACE Y POR QUE

El core de DrakesCraft repaqueto Slimefun a `com.github.drakescraft_labs`. Cualquier addon de
fuera compila contra `io.github.thebusybiscuit` y por tanto no encuentra nada. Comprobado leyendo
las declaraciones `package` del propio core, el mapeo real es:

    io.github.thebusybiscuit        ->  com.github.drakescraft_labs
    me.mrCookieSlime.Slimefun       ->  com.github.drakescraft_labs.slimefun4.legacy
    me.mrCookieSlime.CSCoreLibPlugin                               (se queda igual)
    io.github.bakedlibs.dough  ->  com.github.drakescraft_labs.slimefun4.libraries.dough

Ojo con la segunda: el segmento `Slimefun` DESAPARECE. En el arbol de ficheros la carpeta sigue
llamandose `legacy/Slimefun/`, pero dentro los ficheros declaran `legacy.Objects...` y
`legacy.api...`, sin ese trozo. Guiarse por las carpetas y no por los `package` deja un prefijo
que no existe y el addon no compila.

La tercera tambien engana: CSCoreLibPlugin se movio de carpeta pero NO se repaqueto, asi que sus
clases siguen siendo `me.mrCookieSlime.CSCoreLibPlugin...` de verdad.

Y la cuarta es la mas traicionera: el core compila contra `dev.drake.dough`, pero al empaquetar
el shade la relocaliza a `com.github.drakescraft_labs.slimefun4.libraries.dough`. Lo que ve un
addon en el jar publicado es ESA, no `dev.drake.dough` ni la original de bakedlibs. Se comprobo
en los imports de addons que ya funcionan.

Ademas se reescribe el pom para compilar contra el maven de DrakesCraft y para Java 21.

NO se toca el paquete propio del addon ni sus nombres de clase: eso es del autor original y
mantenerlo intacto hace que las actualizaciones de arriba sigan siendo legibles.

Uso:  python3 portar.py <carpeta-del-repo> [--escribir]
      Sin --escribir solo informa de lo que haria.
"""
import pathlib
import re
import sys

PREFIJO_VIEJO = "io.github.thebusybiscuit"
PREFIJO_NUEVO = "com.github.drakescraft_labs"

# Orden importante: el mapeo de me.mrCookieSlime.Slimefun tiene que ir ANTES que cualquier regla
# mas corta sobre me.mrCookieSlime, o se aplicaria la generica y quedaria a medias.
REMAPEOS = [
    ("io.github.thebusybiscuit", "com.github.drakescraft_labs"),
    ("me.mrCookieSlime.Slimefun", "com.github.drakescraft_labs.slimefun4.legacy"),
    ("io.github.bakedlibs.dough", "com.github.drakescraft_labs.slimefun4.libraries.dough"),
    ("dev.drake.dough", "com.github.drakescraft_labs.slimefun4.libraries.dough"),
]

MAVEN_DRAKE = """        <repository>
            <id>drakescraft-labs-maven</id>
            <url>https://drakescraft-labs.github.io/maven-repo/</url>
        </repository>
"""

DEP_DRAKE = """        <dependency>
            <groupId>com.github.drakescraft_labs</groupId>
            <artifactId>slimefun-core</artifactId>
            <version>11.0-Drake-1.21.11-SNAPSHOT</version>
            <scope>provided</scope>
        </dependency>
"""


def _remapear(linea):
    """Aplica todos los remapeos de paquete a una linea."""
    for viejo, nuevo in REMAPEOS:
        linea = re.sub(r"\b" + re.escape(viejo) + r"\b", nuevo, linea)
    return linea


def portar_fuentes(repo, escribir):
    """Reescribe el prefijo de Slimefun en todos los .java."""
    tocados = 0
    for f in repo.rglob("*.java"):
        if "/target/" in str(f) or "/build/" in str(f):
            continue
        texto = f.read_text(encoding="utf-8", errors="replace")
        # Se ancla en el prefijo completo para no pillar por accidente un paquete propio del
        # addon que empiece igual.
        # El namespace propio de algunos addons también comienza por el prefijo histórico
        # (por ejemplo SlimefunOreChunks). Su declaración package forma parte de la identidad
        # del plugin y debe conservarse; sólo se migran imports y referencias de API.
        nuevo = "\n".join(
            linea if linea.lstrip().startswith("package ") else _remapear(linea)
            for linea in texto.split("\n")
        )
        if nuevo != texto:
            tocados += 1
            if escribir:
                f.write_text(nuevo, encoding="utf-8")
    return tocados


def _sustituir_dependencia_slimefun(texto):
    """Cambia por la nuestra cualquier <dependency> cuyo artifactId hable de Slimefun.

    Se localizan los bloques completos <dependency>...</dependency> y se mira dentro, porque el
    contenido varia mucho de un addon a otro: unos llevan <exclusions>, otros <classifier>, y
    un patron unico no los cubre todos.
    """
    salida = []
    pos = 0
    sustituidas = 0

    while True:
        ini = texto.find("<dependency>", pos)
        if ini == -1:
            salida.append(texto[pos:])
            break
        fin = texto.find("</dependency>", ini)
        if fin == -1:
            salida.append(texto[pos:])
            break
        fin += len("</dependency>")

        bloque = texto[ini:fin]
        artifact = re.search(r"<artifactId>([^<]*)</artifactId>", bloque)
        if artifact and "slimefun" in artifact.group(1).lower():
            salida.append(texto[pos:ini])
            salida.append(DEP_DRAKE.strip())
            sustituidas += 1
        else:
            salida.append(texto[pos:fin])
        pos = fin

    return "".join(salida), sustituidas


def _fuentes_del_repo(repo):
    """Todo el codigo del repo en un solo texto, para buscar dependencias implicitas."""
    trozos = []
    for f in repo.rglob("*.java"):
        if "/target/" not in str(f):
            trozos.append(f.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(trozos)


def portar_pom(repo, escribir):
    """Apunta el build al maven de DrakesCraft y a Java 21."""
    pom = repo / "pom.xml"
    if not pom.exists():
        return "sin pom.xml (build de Gradle: hay que portarlo a mano)"

    texto = pom.read_text(encoding="utf-8")
    antes = texto

    # Java 21: los addons viejos declaran 8, 11 o 16 y no compilan contra el core actual.
    texto = re.sub(r"<maven\.compiler\.(source|target)>[\d.]+</maven\.compiler\.\1>",
                   lambda m: f"<maven.compiler.{m.group(1)}>21</maven.compiler.{m.group(1)}>",
                   texto)
    texto = re.sub(r"<release>\d+</release>", "<release>21</release>", texto)

    # Paper: los addons viejos apuntan a 1.16/1.18 y al repo antiguo de PaperMC, que hoy
    # responde 403. Sin esto ni siquiera se resuelven las dependencias.
    #
    # Se fija 1.21.11, la MISMA que corre en produccion. Con una anterior el codigo compila y
    # luego revienta al arrancar con NoSuchFieldError, porque los enums renombrados se resuelven
    # por nombre en tiempo de ejecucion: el fallo se traslada del build al servidor.
    PAPER = "1.21.11-R0.1-SNAPSHOT"
    texto = re.sub(r"<artifactId>paper-api</artifactId>\s*<version>[^<]*</version>",
                   f"<artifactId>paper-api</artifactId>\n            "
                   f"<version>{PAPER}</version>", texto)
    # spigot-api pasa a paper-api: el servidor es Purpur, y hay addons que usan metodos que solo
    # existen en Paper (por ejemplo Block#getState(boolean)). Con spigot-api no compilan.
    texto = re.sub(r"<groupId>org\.spigotmc</groupId>(\s*)<artifactId>spigot-api</artifactId>"
                   r"\s*<version>[^<]*</version>",
                   f"<groupId>io.papermc.paper</groupId>\\1<artifactId>paper-api</artifactId>\n"
                   f"            <version>{PAPER}</version>", texto)
    # El groupId de paper-api cambio de com.destroystokyo.paper a io.papermc.paper.
    texto = texto.replace("<groupId>com.destroystokyo.paper</groupId>",
                          "<groupId>io.papermc.paper</groupId>")
    texto = texto.replace("https://papermc.io/repo/repository/maven-public/",
                          "https://repo.papermc.io/repository/maven-public/")
    # repo.destroystokyo.com murio; lo que colgaba de ahi vive hoy en jitpack o en papermc.
    texto = texto.replace("https://repo.destroystokyo.com/repository/maven-public/",
                          "https://repo.papermc.io/repository/maven-public/")

    # Lombok anterior a 1.18.30 no compila con Java 21: revienta con IllegalAccessError contra
    # jdk.compiler. Se sube a una version que si lo soporta.
    texto = re.sub(r"(<artifactId>lombok</artifactId>\s*<version>)[^<]*(</version>)",
                   r"\g<1>1.18.34\g<2>", texto)

    # La dependencia de Slimefun pasa a la nuestra, sea cual sea la que traiga.
    #
    # Se recorre bloque a bloque en vez de con un patron: hay poms cuyo <dependency> lleva
    # <exclusions> u otros elementos detras del <scope>, y un patron rigido los dejaba pasar.
    # El resultado era tener DOS dependencias de Slimefun y un fallo de resolucion.
    texto, sustituidas = _sustituir_dependencia_slimefun(texto)
    if sustituidas == 0 and "slimefun-core" not in texto:
        # Solo si no dependia de Slimefun por pom Y no se la hemos puesto ya. Sin la segunda
        # comprobacion, ejecutar el portador dos veces dejaba la dependencia duplicada y el
        # build fallaba por conflicto.
        texto = texto.replace("<dependencies>", "<dependencies>\n" + DEP_DRAKE, 1)

    # Paper dejo de traer commons-lang en 1.21. Los addons que lo usaban compilaban "gratis"
    # y ahora no encuentran el paquete, asi que se declara explicitamente.
    if "org.apache.commons.lang" in _fuentes_del_repo(repo) and "commons-lang</artifactId>" not in texto:
        texto = texto.replace("<dependencies>", """<dependencies>
        <dependency>
            <groupId>commons-lang</groupId>
            <artifactId>commons-lang</artifactId>
            <version>2.6</version>
            <scope>provided</scope>
        </dependency>
""", 1)

    # El maven-shade-plugin anterior a 3.5 no sabe leer bytecode de Java 21 (major 65) y falla
    # con IllegalArgumentException al empaquetar. Los addons viejos traen 3.2.x o 3.3.x.
    texto = re.sub(r"(<artifactId>maven-shade-plugin</artifactId>\s*<version>)[^<]*(</version>)",
                   r"\g<1>3.6.1\g<2>", texto)

    # paperlib se movio de coordenadas y de version.
    texto = re.sub(r"<groupId>io\.papermc</groupId>\s*<artifactId>paperlib</artifactId>\s*"
                   r"<version>[^<]*</version>",
                   "<groupId>io.papermc</groupId>\n            "
                   "<artifactId>paperlib</artifactId>\n            <version>1.0.8</version>",
                   texto)

    if "drakescraft-labs.github.io/maven-repo" not in texto:
        texto = texto.replace("<repositories>", "<repositories>\n" + MAVEN_DRAKE, 1)

    # paper-api arrastra `com.mojang:brigadier`, que solo se publica en el repositorio de
    # Mojang. Sin declararlo, el build muere en resolucion de dependencias sin llegar a compilar
    # -- y el sintoma engana, porque el contador de errores de compilacion se queda en cero.
    if "libraries.minecraft.net" not in texto and "<repositories>" in texto:
        texto = texto.replace("<repositories>", """<repositories>
        <repository>
            <id>minecraft-libraries</id>
            <url>https://libraries.minecraft.net</url>
        </repository>
""", 1)

    # jitpack: aqui viven casi todas las dependencias sueltas de estos addons, y varios
    # apuntaban a repos que ya no responden.
    if "jitpack.io" not in texto and "<repositories>" in texto:
        texto = texto.replace("<repositories>", """<repositories>
        <repository>
            <id>jitpack.io</id>
            <url>https://jitpack.io</url>
        </repository>
""", 1)

    if texto == antes:
        return "el pom no necesito cambios (revisar a mano)"
    if escribir:
        pom.write_text(texto, encoding="utf-8")
    return "pom actualizado"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    repo = pathlib.Path(sys.argv[1]).resolve()
    escribir = "--escribir" in sys.argv
    if not repo.is_dir():
        print(f"no existe: {repo}")
        return 1

    java = [f for f in repo.rglob("*.java") if "/target/" not in str(f)]
    usan = sum(1 for f in java if PREFIJO_VIEJO in f.read_text(encoding="utf-8", errors="replace"))

    print(f"=== {repo.name} ===")
    print(f"  ficheros java: {len(java)}")
    print(f"  usan el prefijo de upstream: {usan}")
    print(f"  {'APLICANDO' if escribir else 'simulacion (usa --escribir)'}")

    tocados = portar_fuentes(repo, escribir)
    print(f"  fuentes reescritas: {tocados}")
    print(f"  {portar_pom(repo, escribir)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
