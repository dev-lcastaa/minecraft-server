# syntax=docker/dockerfile:1.6
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
ADD --chmod=644 --checksum=sha256:230af45e645ebe36f621d0b4362afed6ad0faf940129f4363aaba8058f245576 \
    https://cdn.modrinth.com/data/qeEEslrN/versions/NrzERFzz/QuarkOddities-1.20.1.jar \
    /mods/QuarkOddities-1.20.1.jar
ADD --chmod=644 --checksum=sha256:0aa95b7aab2dbea44b6cbace2f3556670fd8bd613937c736df7cbd9b9de8e8a9 \
    https://cdn.modrinth.com/data/38tpSycf/versions/XiIv5rDL/the_bumblezone-7.15.2%2B1.20.1-forge.jar \
    /mods/the_bumblezone-7.15.2+1.20.1-forge.jar
COPY server.properties /config/server.properties
COPY server-config/config/ /config/config/
