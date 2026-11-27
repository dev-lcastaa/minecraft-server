import json
from pathlib import Path
import re
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "server-config/new-world/datapacks/modpack-fixes"
DATA = PACK / "data"
TOTEM_SCRIPT = ROOT / "server-config/kubejs/startup_scripts/htn_extra_totems.js"


def load(relative):
    return json.loads((DATA / relative).read_text())


def mod_jar(prefix):
    matches = sorted((ROOT / "mods").glob(prefix + "*.jar"))
    if len(matches) != 1:
        raise AssertionError(f"expected one {prefix} jar, found {matches}")
    return ZipFile(matches[0])


class ModpackFixesTest(unittest.TestCase):
    def test_pack_format_and_json(self):
        metadata = json.loads((PACK / "pack.mcmeta").read_text())
        self.assertEqual(metadata["pack"]["pack_format"], 15)
        for path in DATA.rglob("*.json"):
            with self.subTest(path=path):
                json.loads(path.read_text())

    def test_bone_meal_from_bone(self):
        recipe = load("serverfixes/recipes/bone_meal_from_bone.json")
        self.assertEqual(recipe["type"], "minecraft:crafting_shapeless")
        self.assertEqual(recipe["ingredients"], [{"item": "minecraft:bone"}])
        self.assertEqual(recipe["result"], {"item": "minecraft:bone_meal", "count": 3})

    def test_mutant_more_trader_map_disabled(self):
        tag = load("mutantmore/tags/worldgen/structure/on_suspicious_entrance_maps.json")
        self.assertEqual(tag, {"replace": True, "values": []})

    def test_blade_organ_slicing_reverted(self):
        # Sons of Sins slicing stays exclusive to its own slicers; the kept file unregisters the old modifier
        # on servers where the deleted JSON still lingers in the world datapack.
        registration = load("forge/loot_modifiers/global_loot_modifiers.json")
        self.assertEqual(registration, {"replace": False, "entries": []})
        for relative in ("serverfixes/loot_modifiers/sons_of_sins_blade_slicing.json",
                         "serverfixes/loot_tables/sons_of_sins/blade_slicing.json",
                         "serverfixes/tags/items/tools/organ_slicers.json"):
            self.assertFalse((DATA / relative).exists(), relative)

    def test_graveyard_illagers_keep_corruption_and_add_loot(self):
        extra = {
            "corrupted_evoker": ["minecraft:entities/evoker", "illagerinvasion:entities/sorcerer"],
            "corrupted_vindicator": ["minecraft:entities/vindicator", "illagerinvasion:entities/basher"],
            "corrupted_pillager": ["minecraft:entities/pillager"],
        }
        with mod_jar("graveyard-FORGE") as graveyard, mod_jar("IllagerInvasion") as invasion:
            invasion_names = set(invasion.namelist())
            for mob, tables in extra.items():
                with self.subTest(mob=mob):
                    relative = f"graveyard/loot_tables/entities/{mob}.json"
                    original = json.loads(graveyard.read("data/" + relative))
                    override = load(relative)
                    self.assertEqual(override["pools"][: len(original["pools"])], original["pools"])
                    text = json.dumps(override)
                    for table in tables:
                        self.assertIn(table, text)
                        namespace, path = table.split(":")
                        if namespace == "illagerinvasion":
                            self.assertIn(f"data/{namespace}/loot_tables/{path}.json", invasion_names)

    def test_totem_nerf_script_covers_modded_totems(self):
        script = TOTEM_SCRIPT.read_text()
        self.assertIn("dev.spagurder.htn.PostTotemHandler", script)
        for totem in (
            "explosive",
            "stinging",
            "teleporting",
            "ghastly",
            "skeletal",
            "tentacled",
            "rotting",
        ):
            self.assertIn(f"moretotems:{totem}_totem_of_undying", script)
        self.assertIn("fangs_n_claws:totem_of_frost", script)
        self.assertIn("unusualend:void_totem", script)

    def test_client_lang_fixes(self):
        lang = ROOT / "client-config/kubejs/assets"
        tooltips = json.loads((lang / "farmersdelight/lang/en_us.json").read_text())
        self.assertIn("tooltip.farmersdelight.purulent_tea", tooltips)
        self.assertTrue(all(key.startswith("tooltip.farmersdelight.") for key in tooltips))
        descriptions = json.loads((lang / "enchdesc/lang/en_us.json").read_text())
        self.assertTrue(all(key.endswith(".desc") for key in descriptions))
        self.assertIn("enchantment.farmersdelight.backstabbing.desc", descriptions)
        names = json.loads((lang / "dawnoftimebuilder/lang/en_us.json").read_text())
        self.assertEqual(len(names), 134)

    def test_spawn_balance_modifiers(self):
        modifiers = sorted((DATA / "serverfixes/forge/biome_modifier/spawn_balance").rglob("*.json"))
        self.assertGreater(len(modifiers), 80)
        for path in modifiers:
            with self.subTest(path=path):
                modifier = json.loads(path.read_text())
                self.assertEqual(modifier["type"], "forge:add_spawns")
                rel = path.relative_to(DATA / "serverfixes/forge/biome_modifier").with_suffix("")
                self.assertEqual(modifier["biomes"], f"#serverfixes:{rel.as_posix()}")
                tag = load(f"serverfixes/tags/worldgen/biome/{rel.as_posix()}.json")
                biome = f"{rel.parts[1]}:{rel.parts[2]}"
                self.assertEqual(tag["values"], [{"id": biome, "required": False}])
                self.assertTrue(modifier["spawners"])
                for spawner in modifier["spawners"]:
                    namespace = spawner["type"].split(":")[0]
                    self.assertIn(namespace, {"minecraft", "alexsmobs", "backported_animal_variants"})
                    self.assertGreater(spawner["weight"], 0)
                    self.assertLessEqual(1, spawner["minCount"])
                    self.assertLessEqual(spawner["minCount"], spawner["maxCount"])

    def test_alexs_mobs_dominant_weights_lowered(self):
        spawning = json.loads((ROOT / "server-config/config/amc.json").read_text())["spawning"]
        for key, weight in {
            "gazelleSpawnWeight": 20,
            "elephantSpawnWeight": 15,
            "kangarooSpawnWeight": 12,
            "tigerSpawnWeight": 21,
            "hummingbirdSpawnWeight": 10,
        }.items():
            self.assertEqual(spawning[key], weight, key)

    def test_client_stat_tooltips(self):
        script = (ROOT / "client-config/kubejs/client_scripts/item_stat_tooltips.js").read_text()
        self.assertIn("ItemEvents.tooltip", script)
        self.assertIn("addAdvancedToAll", script)
        for label in (
            "Durability: ",
            "Armor: ",
            "Enchantability: ",
            "Mining level: ",
            "Repair material: ",
            "Food: ",
            "Fuel: smelts ",
            "Hardness: ",
            "Blast resistance: ",
            "Stacks to ",
        ):
            self.assertIn(label, script)
        self.assertNotIn("const ", script)

    def test_clear_stray_lights_function(self):
        lines = [
            line
            for line in (DATA / "serverfixes/functions/clear_stray_lights.mcfunction").read_text().splitlines()
            if line and not line.startswith("#")
        ]
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].endswith("minecraft:water replace minecraft:light[waterlogged=true]"))
        self.assertTrue(lines[1].endswith("minecraft:air replace minecraft:light"))
        for line in lines:
            coords = [int(token[1:] or 0) for token in line.split()[1:7]]
            volume = 1
            for low, high in zip(coords[:3], coords[3:]):
                volume *= high - low + 1
            self.assertLessEqual(volume, 32768)
        with mod_jar("dynamiclights-") as jar:
            remover = jar.read("data/dynamiclights/functions/internal/remove_light.mcfunction").decode()
        self.assertIn("minecraft:air replace minecraft:light", remover)

    def test_dynamic_lights_scan_limited_to_nearby_entities(self):
        functions = "data/dynamiclights/functions/internal/"
        with mod_jar("dynamiclights-") as jar:
            original = jar.read(functions + "main.mcfunction").decode().splitlines()
            main_exec = jar.read(functions + "main_exec.mcfunction").decode()
        # The range check this override relies on must still be in main_exec.
        self.assertIn("if entity @p[gamemode=!spectator,distance=..55] run function "
                      "dynamiclights:internal/main_exec_pass", main_exec)
        scan = [line for line in original if "run function dynamiclights:internal/main_exec" in line
                and "as @e[" in line]
        self.assertEqual(len(scan), 1)
        guard = "execute if score $enable ts.dl.settings matches 1..2 unless score $global ts.dl.tnt.fuse matches 1 "
        self.assertTrue(scan[0].startswith(guard + "as @e["))
        selector = re.search(r"@e\[([^\]]*),limit=1000\]", scan[0]).group(1)

        override = (DATA / "dynamiclights/functions/internal/main.mcfunction").read_text().splitlines()
        code = [line for line in override if line and not line.startswith("#")]
        expected = [line for line in original if line and not line.startswith("#")]
        index = expected.index(scan[0])
        expected[index:index + 1] = [
            guard + "if score $unlimited ts.dl.settings matches 1..2 " + scan[0][len(guard):],
            guard + "unless score $unlimited ts.dl.settings matches 1..2 run function "
                    "serverfixes:dynamic_lights/limited",
        ]
        self.assertEqual(code, expected)

        limited = (DATA / "serverfixes/functions/dynamic_lights/limited.mcfunction").read_text()
        tagging = [line for line in limited.splitlines() if " add ts.dl.near" in line]
        self.assertEqual(len(tagging), 2)
        for line in tagging:
            self.assertIn("as @a[gamemode=!spectator] at @s run tag @e[" + selector + ",", line)
            self.assertIn("distance=..55,limit=1000]", line)
        self.assertIn("type=!minecraft:ghast", tagging[0])
        self.assertNotIn("minecraft:ghast", tagging[1])
        process = (DATA / "serverfixes/functions/dynamic_lights/process.mcfunction").read_text()
        self.assertIn("execute if entity @s[tag=ts.dl.near] run function dynamiclights:internal/main_exec",
                      process)
        self.assertIn("tag @s remove ts.dl.near", process)

    def test_bumblezone_is_warm_not_lethal(self):
        # Bumblezone biomes are vanilla temperature 1.85, which Cold Sweat reads as 115 °F,
        # above the 100 °F maximum habitable temperature.
        data = load("serverfixes/cold_sweat/world/biome_temp/bumblezone.json")
        self.assertEqual(data["biomes"], ["#the_bumblezone:the_bumblezone"])
        self.assertEqual(data["units"], "f")
        self.assertTrue(70 <= data["temperature"] < 100)
        self.assertEqual(data["required_mods"], ["the_bumblezone"])
        with mod_jar("the_bumblezone-") as jar:
            tag = json.loads(jar.read("data/the_bumblezone/tags/worldgen/biome/the_bumblezone.json"))
            biomes = {name[len("data/the_bumblezone/worldgen/biome/"):-len(".json")]
                      for name in jar.namelist()
                      if re.fullmatch(r"data/the_bumblezone/worldgen/biome/[a-z_]+\.json", name)}
        self.assertEqual(set(tag["values"]), {"the_bumblezone:" + biome for biome in biomes})
        with mod_jar("ColdSweat-") as jar:
            self.assertIn("data/cold_sweat/cold_sweat/world/dimension_temp/adastra/venus.json",
                          jar.namelist())

    def test_image_includes_fixes(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn("COPY server-config/new-world/datapacks/ /config/new-world/datapacks/", dockerfile)
        self.assertIn("COPY server-config/kubejs/ /config/kubejs/", dockerfile)


if __name__ == "__main__":
    unittest.main()
