# Herramientas de operación

Lo que se usa para desplegar y reiniciar DrakesCraft sin romper nada. Todas se ejecutan **en
star**, que es donde vive la clave del panel; copias en `~/ai-hub/scripts/`.

> **Credenciales.** Ninguna clave vive en este repositorio. `control_drakescraft.py` y
> `drakes_delivery_daemon.py` leen la API key del panel de un fichero fuera del árbol, y el
> identificador del servidor sale de `DRAKES_PANEL_SERVER`. `mcfs.py` saca las suyas del `.env`
> del stack. Si clonas esto en una máquina nueva, esas tres cosas hay que ponerlas a mano.

| Script | Para qué |
|---|---|
| `preflight.py` | Antes de reiniciar: nombres duplicados, dependencias que faltan, clase principal ausente |
| `reinicio_seguro.py` | Avisa con cuenta atrás, guarda y reinicia |
| `verificar_arranque.py` | Después: plugins caídos y excepciones del **último** arranque |
| `vigilante.py` | Cada 5 min: si no responde dos veces seguidas, reinicia y avisa por Discord |
| `subir_jar.py` | Sustituye un jar: sube, verifica y sólo entonces cambia |
| `traza.py` | Saca una traza contigua del log |
| `busca_log.py` / `cola_log.py` | Buscar o leer el final de un log de decenas de MB |
| `leer_gz.py` | Leer los logs archivados (`.gz`) de días anteriores |
| `mcfs.py` | Puente SFTP al host de Minecraft: `ls`, `cat`, `stat`. Del que dependen los demás |
| `subir_archivo.py` | Sustituye un config con respaldo atómico, igual que `subir_jar.py` con los jars |
| `control_drakescraft.py` | Consola y energía del servidor vía panel: `status`, `resources`, `cmd`, `restart` |
| `atender_reinicio.py` | Atiende un reinicio programado y confirma que volvió |
| `scheduled_drakescraft_restart.py` | Reinicio diario programado |
| `drakes_delivery_daemon.py` | Entrega de compras de la tienda |
| `metricas_drakescraft.py` | Métricas del servidor |

## Tres trampas que costaron un reinicio cada una

**`Done (` engaña.** El log acumula todos los arranques del día, así que buscarlo a secas
encuentra el anterior y hace creer que todo fue bien. Hay que cortar desde la última línea
`Starting minecraft server version` — y aun así, si el arranque nuevo todavía no la ha escrito,
se lee el viejo. La señal fiable es que el panel diga `running`.

**Editar no es compilar.** Un `mvn package` olvidado entre el arreglo y el `scp` sube el jar de
antes, y el fallo reaparece idéntico. Merece la pena comprobar la cadena nueva *dentro* del jar
que ya está en el servidor.

**Subir antes de apartar.** `subir_jar.py` sube a un nombre temporal y sólo cambia el bueno
cuando ha verificado el tamaño. Al revés, un fallo de subida deja el plugin sin jar: pasó, y
cinco plugins se quedaron sin fichero hasta que se restauraron.

## El arranque colgado del 14-08

El reinicio diario dejó el servidor tres horas sin arrancar. En el log no había ningún error
— por eso costó verlo —: la última línea del hilo del servidor era el banner de EquivalencyTech,
y después sólo mensajes de Discord retransmitidos, porque DiscordSRV conecta pronto y el proceso
seguía vivo. Parecía encendido y no lo estaba.

La causa es `EmcDefinitions`, que recorre los 14.886 objetos de Slimefun resolviendo recetas con
una función **recursiva sin límite de profundidad ni guarda contra ciclos** — su parámetro
`nestLevel` sólo sirve para indentar el log. Sólo memoriza lo ya terminado, no lo que está a
medias, así que un grafo de recetas en diamante explota de forma combinatoria. Tarda 57 segundos
cuando sale bien; cuando no, no termina.

Empezó a fallar justo al añadir diez addons, que agrandaron el grafo.

De ahí el techo de 8 minutos en el vigilante: mientras el panel diga `starting` nadie interviene,
y ese era exactamente el hueco por el que se colaron tres horas de caída.

## Hologramas del lobby

Dos piezas que se complementan: una define y aplica, la otra lee el servidor y
documenta lo que hay puesto.

```bash
# ver los comandos sin tocar el servidor
python3 operacion/gestionar_hologramas.py operacion/hologramas-ejemplo.yml --simular

# aplicar de verdad, o solo un panel
python3 operacion/gestionar_hologramas.py mis-hologramas.yml
python3 operacion/gestionar_hologramas.py mis-hologramas.yml --solo info_normas

# leer el servidor y volcar que dice cada holograma
python3 operacion/documentar_hologramas.py
```

`gestionar_hologramas.py` habla por la consola de Pterodactyl, asi que necesita
`control_drakescraft.py` al lado y su API key. Es idempotente: borra y rehace,
se puede correr las veces que haga falta.

`documentar_hologramas.py` lee el YAML de DecentHolograms directamente del
servidor. Por defecto busca el montaje sshfs; se cambia con `MSC_HOLOGRAMAS`.
Sirve sobre todo para responder "¿donde dice esto?" sin entrar al juego —por
ejemplo al cambiar el enlace de Discord, que suele estar en varios paneles.

**Antes de colocar un panel hay que saber donde**, y eso la herramienta no lo
adivina: el mundo, la altura del piso, las dos esquinas del area libre, por
donde camina la gente y el alcance de vision. Esta explicado en la cabecera del
script y en `hologramas-ejemplo.yml`.

### Dos trampas de DecentHolograms

1. `downorigin` y `setdisplayrange` **exigen el prefijo `hologram`**:
   `/dh hologram downorigin <n> true`. Sin el responde *"Unknown sub command"*
   y no hace nada, pero el comando se envia igual: si solo compruebas el envio,
   crees que funciono.
2. Una linea cuyo contenido sea un espacio hace que el plugin escriba
   literalmente **`Blank Line`**. Para un hueco hay que mandar un caracter que
   sobreviva al parser; el gestor usa un punto gris.
