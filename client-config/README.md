# Client config import

For the Minecraft 1.20.1 Forge pack used by this server.

1. Close Minecraft completely.
2. Back up your instance's `config/` directory.
3. Extract the client ZIP into the **instance directory**, merging its `config/`,
   `kubejs/`, `mods/`, and `resourcepacks/` folders with yours. Alternatively copy this directory's
   `config/` and `kubejs/` contents into the instance's matching folders and copy
   all JARs in `mods/` into the instance's `mods/` folder and the
   `resourcepacks/butchers-delight-refresh/` folder into its `resourcepacks/`.
   Overwrite
   matching files; do not delete other configs, and do not create `config/config/`.
4. Restart Minecraft. In **Options > Resource Packs**, enable **Butcher's Delight
   Refresh** above other packs that change Butcher textures, then connect to the server.

Remove `weather2-1.20.1-2.8.3.jar` and the outdated duplicate
`alexsmobs-1.22.9.jar` (keep Alex's Mobs 2.2.4) from the client `mods/` folder.
Weather2 was removed from the server after profiling showed storm biome checks
blocking the server thread on chunk loads. Its config overlay is no longer included.
Keep CoroUtil: What Are They Up To and Zombie Awareness still require it.

This is a config overlay with Quark Oddities, lunch basket and Cravings add-ons, not a complete
launcher-importable modpack or a world download. It contains no server passwords,
player data, or server properties. Quark Oddities 1.20.1 is the official small
marker add-on that unlocks Oddities features already implemented in Quark.
It requires the pack's existing Quark and must be present on clients too.

Published download: https://modrinth.com/mod/quark-oddities/version/NrzERFzz

SHA-256: `230af45e645ebe36f621d0b4362afed6ad0faf940129f4363aaba8058f245576`

## Included settings

- Butcher's Delight Refresh (`resourcepacks/butchers-delight-refresh/`): original
  16x16 pixel-art meat, tool, hide, equipment and carcass icons for Butcher's
  Delight 2.1.0 and Foods 1.0.3. Carcass/block UV sheets retain their original
  dimensions, UVs and model geometry, with new pixel art rather than resized photographs.
  Hooked hoglins retain the original mod palette and hoof/cut details with
  Krea-designed darker muscle and fat layers; the final processing stage adds
  the Krea spine profile through a stage-specific texture reference.
  Raw/cooked cuts and partial carcasses are visually distinct. Also corrects the
  mislabeled llama loin and adds the missing "Raw" prefix to sheep loin/rack.
  This is visual only; the server's separate `butchers-delight-compat` datapack
  provides cooked cutting recipes and shared meat/tool tags.

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
- Nether's Delight duplicates (`kubejs/client_scripts/nethers_delight_hide.js`
  and `kubejs/assets/emi/index/stacks/nethersdelight_duplicates.json`): hides
  the 12 Nether's Delight items replaced by My Nether's Delight in JEI and EMI.
  The included server scripts `nethers_delight_unify.js` and
  `festive_delight_fixes.js` apply the recipe unification and cinnamon-bush
  harvest fix in singleplayer. The datapack changes to skinning tools and loot
  are server-only.
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
This overlay adds Quark Oddities, Lunch Basket Food Compatibility and Cravings Food Compatibility; it does not
re-enable disabled JARs.

## Lunch basket food compatibility

`mods/lunch-basket-compat-1.20.1-1.0.0.jar` must be installed on clients as well
as the server. It allows all registered edible items and the pack's placeable
cakes, pies, feasts, pancakes and plated foods in Supplementaries lunch baskets.
Whole meals must still be removed and placed/served normally; the add-on does
not make them directly edible or change food effects and container returns.
It requires Supplementaries 1.20-3.1.44, Forge 1.20.1 and the existing KubeJS.
The included `kubejs/server_scripts/lunch_basket_foods.js` also generates the
food tag for singleplayer. Restart Minecraft after installing the JAR.

If Minecraft reports that the add-on failed to load a valid `resourcePackInfo`,
replace its older JAR with the current overlay copy, even though the filename is
unchanged. The updated JAR includes the missing Minecraft 1.20.1 pack metadata.

## Cravings food compatibility and feedback

Install `mods/cravings-compat-1.20.1-1.0.0.jar` alongside the lunch basket
add-on, and merge all included `kubejs/` files. Restart Minecraft and the
server. This targets the pack's Cravings 1.2.1 and placeable-food mod versions;
the new startup hooks cannot be installed with a script reload.

All registered edible items, supported placeable foods and non-potion drinks
receive craving categories and meal tiers. Candy satisfies Sweet; pancakes
are edible in hand and satisfy Hearty. One plain pancake keeps its placed
food values; topping effects remain exclusive to placed pancakes.
Simple foods grant 2.5-minute buffs, regular foods 5 minutes, and big meals
10 minutes at the default settings. Raw's Nausea stays unchanged, as do XP,
saturation, effect levels, streak bonuses and container returns.

Hovering or holding a food matching your current craving plays the new-craving
amethyst chime, with a shared two-second cooldown and no repeated ringing
while stationary. Matching tooltips show the craving and reward multiplier.
These checks use the server's synchronized tags and craving state; the
included server scripts also generate coverage for singleplayer.
