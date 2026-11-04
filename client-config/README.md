# Client config import

For the Minecraft 1.20.1 Forge pack used by this server.

1. Close Minecraft completely.
2. Back up your instance's `config/` directory.
3. Extract the client ZIP into the **instance directory**, merging its `config/`
   and `mods/` folders with yours. Alternatively copy this directory's `config/`
   contents into the instance's `config/` folder and copy
   `mods/QuarkOddities-1.20.1.jar` into the instance's `mods/` folder. Overwrite
   matching files; do not delete other configs, and do not create `config/config/`.
4. Restart Minecraft and connect to the server.

This is a config overlay with the Quark Oddities add-on, not a complete
launcher-importable modpack or a world download. It contains no server passwords,
player data, or server properties. Quark Oddities 1.20.1 is the official small
marker add-on that unlocks Oddities features already implemented in Quark.
It requires the pack's existing Quark and must be present on clients too.

Published download: https://modrinth.com/mod/quark-oddities/version/NrzERFzz

SHA-256: `230af45e645ebe36f621d0b4362afed6ad0faf940129f4363aaba8058f245576`

## Included settings

- Quark: all 164 feature toggles reflect the selected profile: 86 enabled and
  78 disabled. Armor-stand Quick Armor Swapping and Totem of Holding are enabled;
  tool restock, sorting, Simple Harvest, Expanded Item Interactions, Horses Swim,
  and Improved Tooltips are disabled. Category switches and internal tuning
  remain unchanged, including disabled villager harvesting and Shulker Tooltips.
  Totem of Holding intentionally uses a recovery totem for eligible death drops,
  rather than ordinary loose drops; it does not restore Backrooms' random keeping.
  Existing items/blocks from disabled features may remain, but their recipes,
  generation, and feature behavior can be unavailable.
  Quark still suppresses Automatic Recipe Unlock when NERB is installed and Map
  Washing when Supplementaries is installed; their selected toggles remain True
  without overriding Quark's compatibility protection.
- Thirst Was Taken: 48 verified drink IDs, including Delight add-ons; correct
  `strong_coffee`, remove nonexistent/default entries for unloaded mods, and keep
  keyword matching off. Existing hydration balance is retained; new juices and
  milkshakes use 8/13, teas use 10/14, and Miner's Delight's smaller milk cup
  uses 3/4. Drinking effects and crafting recipes are unchanged.
- Backrooms: disable its 30% partial-loot retention. The server still determines
  multiplayer death drops. This also applies to a local singleplayer world.
- Vanilla Backport: preserve disabled natural zombie horses to avoid duplicating
  Zombie Horse Spawn.
- Weather2: retain dangerous, destructive tornadoes with lower entity/block
  budgets and hail output, plus the existing slower sand/snow accumulation.
  Client-only tuning reduces particles without switching off the Weather2
  particle engine.

| Client rendering setting | Value |
| --- | --- |
| Overall particle multiplier | `0.35` |
| Precipitation particle multiplier | `0.3` |
| Extra tornado block particles | `0` |
| Sand dust/debris multipliers | `0.2` each |
| Cloud particle spawn delay | `6` ticks |
| Storm particle spawn delay | `6` ticks |

Common gameplay settings match `server-config/config/`. Intentional rendering
differences are in Weather2's `Misc.toml`, `Particle.toml`, `Sand.toml`, and
`Storm.toml`; Chunky's server admin config is not included.

Back up existing saves before changing configs used in singleplayer. Keep the
client mod list aligned with the server, including previously disabled mods.
This overlay adds only Quark Oddities; it does not re-enable disabled JARs.
