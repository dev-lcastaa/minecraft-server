# Client config import

For the Minecraft 1.20.1 Forge pack used by this server.

1. Close Minecraft completely.
2. Back up your instance's `config/` directory.
3. Extract the client ZIP into the **instance directory**, merging its `config/`,
   `kubejs/`, and `mods/` folders with yours. Alternatively copy this directory's
   `config/` and `kubejs/` contents into the instance's matching folders and copy
   `mods/QuarkOddities-1.20.1.jar` into the instance's `mods/` folder. Overwrite
   matching files; do not delete other configs, and do not create `config/config/`.
4. Restart Minecraft and connect to the server.

Remove `weather2-1.20.1-2.8.3.jar` and the outdated duplicate
`alexsmobs-1.22.9.jar` (keep Alex's Mobs 2.2.4) from the client `mods/` folder.
Weather2 was removed from the server after profiling showed storm biome checks
blocking the server thread on chunk loads. Its config overlay is no longer included.
Keep CoroUtil: What Are They Up To and Zombie Awareness still require it.

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
- Thirst Was Taken: 103 drinks and 165 foods, verified against the live item
  registry. Includes milk buckets, Cold Sweat's filled waterskin, Doggy Talents
  drinks, Farmer's Respite strong hot cocoa, and the remaining Delight soups,
  salads, fruit, and jellies. Includes suspicious stew, bee soup, royal jelly, hot cocoa, all 23
  SCP drinks, Miner's Delight soup cups, My Nether's Delight, Unusual End,
  Biomes We've Gone, Delightful, Alex's Delight/Caves, Dungeons Delight,
  Backrooms, Ender's Delight, and Abnormals Delight drinks. Existing values
  are retained; new soups use 4/5, cups half the bowl values rounded up,
  fruit 1/2 or 2/3, juices/milkshakes 8/13, teas 10/14, and water/cocoa/potions
  6/8. Water/milk cups use 3/4. Keyword matching remains off.
  Unusual End's brewed potions already use the vanilla potion entry; its
  Warped Potion is now explicit. Mekanism Delight drinks that require
  uninstalled Mekanism add-ons are excluded. Harmful drink effects and crafting recipes are unchanged.
- Tooltips (`kubejs/assets/`, loaded automatically by KubeJS): restores 33
  Farmer's Respite, Dungeons Delight, and My Nether's Delight item tooltips
  that use Farmer's Delight's old key format, adds Enchantment Descriptions text
  for 8 Fangs & Claws, Storms of the Wild, and End of Herobrine enchantments,
  and names 134 unnamed Dawn of Time blocks. Farmer's Delight Backstabbing's
  description is mapped to the key Enchantment Descriptions reads, so all
  enchantments in the pack now show a description.
- Item stat tooltips (`kubejs/client_scripts/item_stat_tooltips.js`): every
  item shows gray stat lines. Tools, weapons, armor, shields, and bows show
  durability, armor/toughness, mining level/speed, enchantability, and repair
  material; other items show food values, fuel value, block hardness, blast
  resistance and light level, and stack size.
- Alex's Mobs (`config/amc.json`): matches the server's lowered spawn weights
  for 36 dominant animals; only matters in singleplayer.
- Better Days (`config/betterdays-common.toml`): 60-minute day/night cycle
  (one third of vanilla speed). Clients must also install
  `betterdays-1.20.1-3.3.4.5-FORGE.jar` from
  https://modrinth.com/mod/betterdays so the sun moves smoothly.
- Backrooms: disable its 30% partial-loot retention. The server still determines
  multiplayer death drops. This also applies to a local singleplayer world.
- Vanilla Backport: preserve disabled natural zombie horses to avoid duplicating
  Zombie Horse Spawn.

Common gameplay settings match `server-config/config/`;
Chunky's server admin config is not included.

Back up existing saves before changing configs used in singleplayer. Keep the
client mod list aligned with the server, including previously disabled mods.
This overlay adds only Quark Oddities; it does not re-enable disabled JARs.
