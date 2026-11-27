# Runs Dynamic Lights' unchanged per-entity logic for a tagged nearby entity, once per tick.
execute if entity @s[tag=ts.dl.near] run function dynamiclights:internal/main_exec
tag @s remove ts.dl.near
