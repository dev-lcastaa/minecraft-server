FROM itzg/minecraft-server:java17

ENV TYPE=FORGE \
    VERSION=1.20.1 \
    REMOVE_OLD_MODS=TRUE \
    COPY_CONFIG_DEST=/data \
    SYNC_SKIP_NEWER_IN_DESTINATION=false \
    REPLACE_ENV_DURING_SYNC=true \
    REPLACE_ENV_IN_PLACE=false \
    REPLACE_ENV_VARIABLE_PREFIX=CFG_RCON_ \
    REPLACE_ENV_SUFFIXES=properties \
    SKIP_SERVER_PROPERTIES=true

COPY mods/ /mods/
COPY server.properties /config/server.properties
