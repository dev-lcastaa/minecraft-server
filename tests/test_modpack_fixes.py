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

    def test_organ_modifier_registered(self):
        registration = load("forge/loot_modifiers/global_loot_modifiers.json")
        self.assertFalse(registration["replace"])
        self.assertIn("serverfixes:sons_of_sins_blade_slicing", registration["entries"])
        modifier = load("serverfixes/loot_modifiers/sons_of_sins_blade_slicing.json")
        self.assertEqual(modifier["type"], "farmersdelight:add_loot_table")
        self.assertEqual(modifier["lootTable"], "serverfixes:sons_of_sins/blade_slicing")
        self.assertTrue((DATA / "serverfixes/loot_tables/sons_of_sins/blade_slicing.json").is_file())
        text = json.dumps(modifier)
        for required in (
            "minecraft:killed_by_player",
            "serverfixes:tools/organ_slicers",
            "sons_of_sins:is_slicer",
            "minecraft:player",
        ):
            self.assertIn(required, text)

    def test_organ_slicers_cover_blades(self):
        values = load("serverfixes/tags/items/tools/organ_slicers.json")["values"]
        ids = {value if isinstance(value, str) else value["id"] for value in values}
        for blade in (
            "#forge:tools/knives",
            "#farmersdelight:tools/knives",
            "#dungeonsdelight:cleavers",
            "butchersdelight:cleaver",
            "graveyard:bone_dagger",
        ):
            self.assertIn(blade, ids)

    def test_slicing_tables_exist(self):
        table = (DATA / "serverfixes/loot_tables/sons_of_sins/blade_slicing.json").read_text()
        references = set(re.findall(r'"name": "(minecraft:slicing/[^"]+)"', table))
        self.assertTrue(references)
        with mod_jar("sons_of_sins") as jar:
            names = set(jar.namelist())
        for reference in references:
            path = reference.split(":")[1]
            self.assertIn(f"data/minecraft/loot_tables/{path}.json", names)

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

    def test_image_includes_fixes(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn("COPY server-config/new-world/datapacks/ /config/new-world/datapacks/", dockerfile)
        self.assertIn("COPY server-config/kubejs/ /config/kubejs/", dockerfile)


if __name__ == "__main__":
    unittest.main()
