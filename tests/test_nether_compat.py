import json
from pathlib import Path
import re
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "server-config/new-world/datapacks/modpack-fixes/data"
SERVER_SCRIPTS = ROOT / "server-config/kubejs/server_scripts"
CLIENT_KUBEJS = ROOT / "client-config/kubejs"
UNIFY_SCRIPT = SERVER_SCRIPTS / "nethers_delight_unify.js"
CINNAMON_SCRIPT = SERVER_SCRIPTS / "festive_delight_fixes.js"


def mod_jar(prefix):
    matches = sorted((ROOT / "mods").glob(prefix + "*.jar"))
    if len(matches) != 1:
        raise AssertionError(f"expected one {prefix} jar, found {matches}")
    return ZipFile(matches[0])


def registered_ids(jar, namespace):
    lang = json.loads(jar.read(f"assets/{namespace}/lang/en_us.json"))
    ids = set()
    for key in lang:
        parts = key.split(".")
        if len(parts) == 3 and parts[0] in ("item", "block") and parts[1] == namespace:
            ids.add(f"{namespace}:{parts[2]}")
    return ids


def duplicate_map():
    script = UNIFY_SCRIPT.read_text()
    body = re.search(r"NETHERS_DELIGHT_DUPLICATES = \{(.*?)\n\}", script, re.S).group(1)
    return dict(re.findall(r"'(nethersdelight:[a-z_]+)': '(mynethersdelight:[a-z_]+)'", body))


class SkinningToolsTest(unittest.TestCase):
    def test_cleavers_and_machetes_are_forge_knives(self):
        tag = json.loads((DATA / "forge/tags/items/tools/knives.json").read_text())
        self.assertFalse(tag["replace"])
        ids = {value["id"] for value in tag["values"]}
        self.assertTrue(all(not value["required"] for value in tag["values"]))
        for expected in ("#dungeonsdelight:cleavers", "#nethersdelight:tools/machetes", "dungeonsdelight:fiery_cleaver"):
            self.assertIn(expected, ids)
        with mod_jar("forge-dungeonsdelight") as jar:
            cleavers = json.loads(jar.read("data/dungeonsdelight/tags/items/cleavers.json"))["values"]
            known = registered_ids(jar, "dungeonsdelight")
        self.assertIn("dungeonsdelight:iron_cleaver", cleavers)
        for item in ids:
            if item.startswith("dungeonsdelight:"):
                self.assertIn(item, known)
        with mod_jar("nethersdelight") as jar:
            machetes = json.loads(jar.read("data/nethersdelight/tags/items/tools/machetes.json"))["values"]
        self.assertIn("nethersdelight:iron_machete", machetes)

    def test_butchers_delight_skins_with_forge_knives(self):
        with mod_jar("Butchersdelight beta") as jar:
            procedure = jar.read("net/mcreator/butchersdelight/procedures/ProhookedcowProcedure.class")
        self.assertIn(b"tools/knives", procedure)


class NethersDelightDuplicatesTest(unittest.TestCase):
    def test_every_shared_id_is_unified_to_my_nethers_delight(self):
        with mod_jar("nethersdelight") as nd, mod_jar("MyNethersDelight") as mnd:
            nd_ids = registered_ids(nd, "nethersdelight")
            mnd_ids = registered_ids(mnd, "mynethersdelight")
        shared = {i.split(":")[1] for i in nd_ids} & {i.split(":")[1] for i in mnd_ids}
        mapping = duplicate_map()
        for name in shared:
            self.assertEqual(mapping.get(f"nethersdelight:{name}"), f"mynethersdelight:{name}", name)
        self.assertEqual(mapping["nethersdelight:ground_strider"], "mynethersdelight:minced_strider")
        self.assertEqual(mapping["nethersdelight:plate_of_stuffed_hoglin_roast"], "mynethersdelight:plate_of_stuffed_hoglin")
        for source, target in mapping.items():
            self.assertIn(source, nd_ids)
            self.assertIn(target, mnd_ids)

    def test_removed_and_patched_recipes_exist(self):
        script = UNIFY_SCRIPT.read_text()
        body = re.search(r"NETHERS_DELIGHT_REDUNDANT_RECIPES = \[(.*?)\]", script, re.S).group(1)
        removed = re.findall(r"'([a-z_]+:[a-z_/]+)'", body)
        patched = re.findall(r"\{ id: '([a-z_]+:[a-z_/]+)' \}", script)
        self.assertEqual(len(removed), 7)
        with mod_jar("nethersdelight") as jar:
            names = set(jar.namelist())
            for recipe in removed + patched:
                namespace, path = recipe.split(":")
                self.assertIn(f"data/{namespace}/recipes/{path}.json", names, recipe)
            for recipe in removed:
                namespace, path = recipe.split(":")
                text = jar.read(f"data/{namespace}/recipes/{path}.json").decode()
                self.assertTrue(any(f'"{source}"' in text for source in duplicate_map()), recipe)

    def test_nd_duplicate_loot_is_disabled(self):
        modifier = json.loads((DATA / "nethersdelight/loot_modifiers/scavenging_hide_from_hoglin.json").read_text())
        self.assertEqual(modifier["conditions"], [{"condition": "minecraft:random_chance", "chance": 0.0}])
        with mod_jar("nethersdelight") as jar:
            registration = json.loads(jar.read("data/forge/loot_modifiers/global_loot_modifiers.json"))
        self.assertIn("nethersdelight:scavenging_hide_from_hoglin", registration["entries"])
        for mob, drop in (("hoglin", "minecraft:porkchop"), ("strider", "minecraft:string")):
            text = (DATA / f"minecraft/loot_tables/entities/{mob}.json").read_text()
            self.assertNotIn("nethersdelight", text)
            self.assertIn(drop, text)
        with mod_jar("MyNethersDelight") as jar:
            loin = json.loads(jar.read("data/mynethersdelight/loot_modifiers/remplace_hoglin_pork_loin.json"))
        self.assertEqual(loin["replaces"], "minecraft:porkchop")

    def test_client_hides_the_same_duplicates(self):
        mapping = duplicate_map()
        hide = (CLIENT_KUBEJS / "client_scripts/nethers_delight_hide.js").read_text()
        self.assertIn("JEIEvents.hideItems", hide)
        self.assertEqual(set(re.findall(r"'(nethersdelight:[a-z_]+)'", hide)), set(mapping))
        emi = json.loads((CLIENT_KUBEJS / "assets/emi/index/stacks/nethersdelight_duplicates.json").read_text())
        self.assertEqual({entry.removeprefix("item:") for entry in emi["removed"]}, set(mapping))


class CinnamonHarvestTest(unittest.TestCase):
    def test_script_uses_festive_delight_ids(self):
        script = CINNAMON_SCRIPT.read_text()
        with mod_jar("festive_delight") as jar:
            known = registered_ids(jar, "festive_delight")
            self.assertIn(
                "net/toopa/festivedelight/procedures/CinnamonRecoltProcedure.class", jar.namelist()
            )
        for item in re.findall(r"'(festive_delight:[a-z_]+)'", script):
            self.assertIn(item, known)
        self.assertIn("BlockEvents.rightClicked(CINNAMON_BUSH_RIPE", script)
        self.assertLess(script.index("block.set(CINNAMON_BUSH)"), script.index("event.cancel()"))


class ClientOverlayCopiesTest(unittest.TestCase):
    def test_server_scripts_match_client_copies(self):
        for name in ("nethers_delight_unify.js", "festive_delight_fixes.js"):
            with self.subTest(name=name):
                self.assertEqual(
                    (SERVER_SCRIPTS / name).read_text(),
                    (CLIENT_KUBEJS / "server_scripts" / name).read_text(),
                )


if __name__ == "__main__":
    unittest.main()
