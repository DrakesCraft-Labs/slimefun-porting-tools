# Copia versionada de las configuraciones de ChatGames

`plugins/ChatGames/games/*.yml` solo existia en el servidor. Sin copia versionada, un fichero
podia quedarse anos con respuestas imposibles sin que nadie lo notara: fue el caso del ticket 280,
siete variantes de `reaction.yml` respondidas con un comando con barra.

Aqui se guarda el estado propuesto de los ficheros ya validados. Antes de subir cualquiera:

    python3 auditoria/validar_chatgames.py auditoria/config-chatgames/*.yml

El despliegue lo hace el rol integrador sobre `plugins/ChatGames/games/`, con respaldo previo y
verificacion SHA-256, y termina con `/chatgames reload`. Comprobar antes que el fichero vivo sigue
coincidiendo con el que se tomo como base: estas configuraciones se editan tambien a mano.
