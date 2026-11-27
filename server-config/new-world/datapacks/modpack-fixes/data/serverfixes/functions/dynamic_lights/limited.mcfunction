# Replacement for Dynamic Lights' all-entity scan when $unlimited is off.
# The original ran dynamiclights:internal/main_exec for every loaded entity each tick, only for
# main_exec to drop those without a non-spectator player within 55 blocks. Distance-bounded
# selectors use the chunk entity lookup, so only nearby entities are visited.

# Ghast fireball lights ignore the range limit in the original, so all ghasts are still visited.
execute if score $enable_ghast ts.dl.settings matches 1..2 as @e[type=minecraft:ghast,tag=!smithed.strict,tag=!global.ignore,tag=!global.ignore.gui,tag=!ts.dl.ignore,tag=!ts.sa.hidden] at @s run function dynamiclights:internal/main_exec
execute if score $enable_ghast ts.dl.settings matches 1..2 as @a[gamemode=!spectator] at @s run tag @e[type=!minecraft:player,type=!#dynamiclights:dyn_ignore,tag=!smithed.strict,tag=!global.ignore,tag=!global.ignore.gui,tag=!ts.dl.ignore,tag=!ts.sa.hidden,type=!minecraft:ghast,distance=..55,limit=1000] add ts.dl.near
execute unless score $enable_ghast ts.dl.settings matches 1..2 as @a[gamemode=!spectator] at @s run tag @e[type=!minecraft:player,type=!#dynamiclights:dyn_ignore,tag=!smithed.strict,tag=!global.ignore,tag=!global.ignore.gui,tag=!ts.dl.ignore,tag=!ts.sa.hidden,distance=..55,limit=1000] add ts.dl.near
# Selectors are resolved before queued functions run, so process re-checks the tag to run
# each entity once even when it is near several players.
execute as @a[gamemode=!spectator] at @s as @e[tag=ts.dl.near,distance=..55] at @s run function serverfixes:dynamic_lights/process
