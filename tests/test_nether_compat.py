import json
from pathlib import Path
import re
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "server-config/new-world/datapacks/modpack-fixes/data"
SERVER_SCRIPTS = ROOT / "server-config/kubejs/server_scripts"
CLIENT_KUBEJS = ROOT / "client-config/kubejs"
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


ND_REFERENCE = re.compile(r"(?<![a-z_])nethersdelight:")
ND_SAUSAGE_RECIPE = DATA / "nethersdelight/recipes/cutting/hoglin_sausage_alt.json"


class SkinningToolsTest(unittest.TestCase):
    def test_cleavers_are_forge_knives(self):
        tag = json.loads((DATA / "forge/tags/items/tools/knives.json").read_text())
        self.assertFalse(tag["replace"])
        ids = {value["id"] for value in tag["values"]}
        self.assertTrue(all(not value["required"] for value in tag["values"]))
        for expected in ("#dungeonsdelight:cleavers", "dungeonsdelight:fiery_cleaver"):
            self.assertIn(expected, ids)
        with mod_jar("forge-dungeonsdelight") as jar:
            cleavers = json.loads(jar.read("data/dungeonsdelight/tags/items/cleavers.json"))["values"]
            known = registered_ids(jar, "dungeonsdelight")
        self.assertIn("dungeonsdelight:iron_cleaver", cleavers)
        for item in ids:
            if item.startswith("dungeonsdelight:"):
                self.assertIn(item, known)

    def test_butchers_delight_skins_with_forge_knives(self):
        with mod_jar("Butchersdelight beta") as jar:
            procedure = jar.read("net/mcreator/butchersdelight/procedures/ProhookedcowProcedure.class")
        self.assertIn(b"tools/knives", procedure)


class NethersDelightRemovedTest(unittest.TestCase):
    def test_only_my_nethers_delight_is_installed(self):
        self.assertEqual(list((ROOT / "mods").glob("nethersdelight-*.jar")), [])
        mod_jar("MyNethersDelight").close()

    def test_configs_do_not_reference_nethers_delight(self):
        for base in (ROOT / "server-config", ROOT / "client-config"):
            for path in base.rglob("*"):
                if not path.is_file() or path.suffix not in (".js", ".json", ".toml", ".cfg", ".txt"):
                    continue
                if path == ND_SAUSAGE_RECIPE:
                    continue
                with self.subTest(path=str(path.relative_to(ROOT))):
                    self.assertIsNone(ND_REFERENCE.search(path.read_text(errors="ignore")))

    def test_my_nethers_delight_nd_recipe_only_loads_with_nethers_delight(self):
        override = json.loads(ND_SAUSAGE_RECIPE.read_text())
        self.assertEqual(override.pop("conditions"), [{"type": "forge:mod_loaded", "modid": "nethersdelight"}])
        with mod_jar("MyNethersDelight") as jar:
            shipped = json.loads(jar.read("data/nethersdelight/recipes/cutting/hoglin_sausage_alt.json"))
            nd_files = [n for n in jar.namelist() if n.startswith("data/nethersdelight/") and n.endswith(".json")]
            tags = [
                json.loads(jar.read(n)) for n in jar.namelist()
                if n.startswith("data/mynethersdelight/tags/") and n.endswith(".json")
            ]
        self.assertEqual(override, shipped)
        self.assertEqual(nd_files, ["data/nethersdelight/recipes/cutting/hoglin_sausage_alt.json"])
        # Required references to missing items would make Forge drop the whole tag.
        for tag in tags:
            for value in tag["values"]:
                if isinstance(value, str):
                    self.assertIsNone(ND_REFERENCE.search(value), value)

    def test_strider_keeps_vanilla_drops(self):
        self.assertFalse((DATA / "minecraft/loot_tables/entities/hoglin.json").exists())
        text = (DATA / "minecraft/loot_tables/entities/strider.json").read_text()
        self.assertIn("minecraft:string", text)
        with mod_jar("Butchersdelight beta") as jar:
            self.assertIn("data/minecraft/loot_tables/entities/strider.json", jar.namelist())
        with mod_jar("MyNethersDelight") as jar:
            loin = json.loads(jar.read("data/mynethersdelight/loot_modifiers/remplace_hoglin_pork_loin.json"))
        self.assertEqual(loin["replaces"], "minecraft:porkchop")


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
        name = "festive_delight_fixes.js"
        self.assertEqual(
            (SERVER_SCRIPTS / name).read_text(),
            (CLIENT_KUBEJS / "server_scripts" / name).read_text(),
        )


if __name__ == "__main__":
    unittest.main()
