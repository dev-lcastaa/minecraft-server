# Removes invisible minecraft:light blocks within 15 blocks of the executor.
# Tschipcraft's Dynamic Lights tracks each light with a ts.dl.light marker; when the
# server crashes or is killed, chunks can be saved with the light but without its marker,
# leaving permanent "phantom" light. Active dynamic lights are re-placed on the next tick.
# Survival players cannot obtain light blocks, so every light block here is a Dynamic Lights block.
# Usage (op): stand in the affected area and run /function serverfixes:clear_stray_lights
fill ~-15 ~-15 ~-15 ~15 ~15 ~15 minecraft:water replace minecraft:light[waterlogged=true]
fill ~-15 ~-15 ~-15 ~15 ~15 ~15 minecraft:air replace minecraft:light
