# Herramientas de operación

Lo que se usa para desplegar y reiniciar DrakesCraft sin romper nada. Todas se ejecutan **en
star**, que es donde vive la clave del panel; copias en `~/ai-hub/scripts/`.

| Script | Para qué |
|---|---|
| `preflight.py` | Antes de reiniciar: nombres duplicados, dependencias que faltan, clase principal ausente |
| `reinicio_seguro.py` | Avisa con cuenta atrás, guarda y reinicia |
| `verificar_arranque.py` | Después: plugins caídos y excepciones del **último** arranque |
| `vigilante.py` | Cada 5 min: si no responde dos veces seguidas, reinicia y avisa por Discord |
| `subir_jar.py` | Sustituye un jar: sube, verifica y sólo entonces cambia |
| `traza.py` | Saca una traza contigua del log |
| `busca_log.py` / `cola_log.py` | Buscar o leer el final de un log de decenas de MB |

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
