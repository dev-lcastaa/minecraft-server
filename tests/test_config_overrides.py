import hashlib
import json
from pathlib import Path
import tomllib
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server-config" / "config"
CLIENT = ROOT / "client-config" / "config"

DISABLED_QUARK_FEATURES = {
    "automation": (
        "Chute", "Crafter", "Dispensers Place Blocks", "Gravisand", "Iron Rod",
        "Metal Buttons", "Pistons Move Tile Entities",
    ),
    "building": (
        "Celebratory Lamps", "Duskbound Blocks", "Glass Item Frame", "Gold Bars",
        "Hedges", "Hollow Logs", "Industrial Palette", "Japanese Palette", "Leaf Carpet",
        "Midori", "More Brick Types", "More Mud Blocks", "More Stone Variants",
        "Rainbow Lamps", "Raw Metal Bricks", "Rope", "Shingles", "Soul Sandstone",
        "Stools", "Sturdy Stone", "Thatch", "Vertical Planks", "Vertical Slabs",
        "Wooden Posts",
    ),
    "management": (
        "Automatic Tool Restock", "Expanded Item Interactions", "Inventory Sorting",
    ),
    "tools": ("Pickarang",),
    "tweaks": (
        "Better Elytra Rocket", "Compasses Work Everywhere", "Dragon Scales", "Emotes",
        "Horses Swim", "Lock Rotation", "More Banner Layers", "More Note Block Sounds",
        "Reacharound Placing", "Safer Creatures", "Shulker Packing", "Simple Harvest",
        "Utility Recipes",
    ),
    "world": ("Chorus Vegetation", "Glimmering Weald", "New Stone Types", "Spiral Spires"),
    "mobs": ("Crabs", "Foxhound"),
    "client": (
        "Auto Walk Keybind", "Back Button Keybind", "Camera", "Greener Grass",
        "Improved Tooltips", "Microcrafting Helper", "Usage Ticker",
        "Variant Animal Textures",
    ),
    "experimental": (
        "Adjustable Chat", "Climate Control Remover", "Enchantment Predicates",
        "Enchantments Begone", "Game Nerfs", "Narrator Readout", "Overlay Shader",
        "Spawner Replacer", "Variant Selector", "Villager Rerolling Rework",
    ),
    "oddities": ("Backpack", "Crate", "Magnets", "Matrix Enchanting", "Pipes", "Tiny Potato"),
}


def load(root, name):
    with (root / name).open("rb") as stream:
        return tomllib.load(stream)


class ConfigOverridesTest(unittest.TestCase):
    def test_all_toml_files_parse(self):
        for root in (SERVER, CLIENT):
            for path in root.rglob("*.toml"):
                with self.subTest(path=path):
                    load(root, path.relative_to(root))

    def test_client_matches_server_except_admin_config(self):
        for path in SERVER.rglob("*"):
            if not path.is_file():
                continue
            name = path.relative_to(SERVER)
            with self.subTest(path=name):
                if str(name) == "chunky/config.json":
                    self.assertFalse((CLIENT / name).exists())
                    continue
                server = load(SERVER, name)
                client = load(CLIENT, name)
                self.assertEqual(client, server)

    def test_quark_overlap_protections(self):
        config = load(SERVER, "quark-common.toml")
        for key in (
            "Automatic Tool Restock",
            "Expanded Item Interactions",
            "Inventory Sorting",
        ):
            self.assertFalse(config["management"][key])
        self.assertFalse(config["tweaks"]["Horses Swim"])
        self.assertFalse(config["tweaks"]["simple_harvest"]["Villagers Use Simple Harvest"])
        self.assertFalse(config["tweaks"]["Simple Harvest"])
        self.assertFalse(config["client"]["improved_tooltips"]["Shulker Tooltips"])
        self.assertTrue(config["management"]["Quick Armor Swapping"])
        self.assertTrue(config["oddities"]["Totem Of Holding"])
        self.assertFalse(config["oddities"]["Matrix Enchanting"])
        for feature in ("automatic_recipe_unlock", "map_washing"):
            self.assertFalse(config["tweaks"][feature]["Ignore Anti Overlap"])

    def test_all_164_quark_feature_choices(self):
        config = load(SERVER, "quark-common.toml")
        total = enabled = 0
        for category, disabled in DISABLED_QUARK_FEATURES.items():
            features = {
                key: value for key, value in config[category].items()
                if isinstance(value, bool)
            }
            self.assertTrue(set(disabled).issubset(features), category)
            for name, value in features.items():
                with self.subTest(category=category, feature=name):
                    self.assertEqual(value, name not in disabled)
            total += len(features)
            enabled += sum(features.values())
        self.assertEqual(total, 164)
        self.assertEqual(enabled, 86)

    def test_quark_oddities_addon(self):
        path = ROOT / "client-config/mods/QuarkOddities-1.20.1.jar"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(
            digest, "230af45e645ebe36f621d0b4362afed6ad0faf940129f4363aaba8058f245576"
        )
        self.assertIn(f"--checksum=sha256:{digest}", (ROOT / "Dockerfile").read_text())
        with ZipFile(path) as archive:
            metadata = tomllib.loads(archive.read("META-INF/mods.toml").decode())
            self.assertEqual(metadata["mods"][0]["modId"], "quarkoddities")
            self.assertEqual(metadata["mods"][0]["version"], "1.20.1")
            self.assertEqual(metadata["dependencies"]["quarkoddities"][0]["modId"], "quark")

    def test_thirst_values_are_explicit_unique_and_valid(self):
        config = load(SERVER, "thirst/item_settings.toml")
        drinks = config["Drinks"]["drinks"]
        foods = config["Foods"]["foods"]
        self.assertEqual(len(drinks), 92)
        self.assertEqual(len(foods), 126)
        self.assertEqual(
            len({row[0] for row in drinks + foods}), len(drinks) + len(foods)
        )
        for entries in (drinks, foods):
            ids = [row[0] for row in entries]
            self.assertEqual(len(ids), len(set(ids)))
            for item_id, hydration, quenching in entries:
                self.assertRegex(item_id, r"^[a-z0-9_]+:[a-z0-9_/]+$")
                self.assertNotEqual(item_id.split(":")[0], "displaydelight")
                self.assertIs(type(hydration), int)
                self.assertIs(type(quenching), int)
                self.assertGreater(hydration, 0)
                self.assertLessEqual(hydration, 20)
                self.assertGreater(quenching, 0)
                self.assertLessEqual(quenching, 22)
        values = {row[0]: row[1:] for row in drinks}
        self.assertEqual(values["farmersrespite:strong_coffee"], [6, 11])
        self.assertNotIn("farmersrespite:stong_coffee", values)
        self.assertNotIn("farmersrespite:strong_dandelion_tea", values)
        self.assertEqual(values["miners_delight:milk_cup"], [3, 4])
        for namespace in (
            "delightful",
            "abnormals_delight",
            "endersdelight",
            "festive_delight",
            "dungeonsdelight",
            "oceanic_delight",
            "miners_delight",
        ):
            self.assertTrue(any(item.startswith(namespace + ":") for item in values))
        self.assertFalse(
            load(SERVER, "thirst/keyword.toml")["Keyword config"]["enableKeywordConfig"]
        )

    def test_thirst_requested_drinks_and_portion_sizes(self):
        config = load(SERVER, "thirst/item_settings.toml")
        drinks = {row[0]: row[1:] for row in config["Drinks"]["drinks"]}
        foods = {row[0]: row[1:] for row in config["Foods"]["foods"]}
        for item, values in {
            "farmersdelight:hot_cocoa": [6, 8],
            "the_bumblezone:royal_jelly_bottle": [6, 8],
            "unusualend:warped_potion": [6, 8],
            "minecraft:potion": [6, 8],
            "biomeswevegone:aloe_vera_juice": [8, 13],
            "abnormals_delight:cherry_cream_soda": [8, 13],
            "abnormals_delight:passion_aloe_nectar": [8, 13],
            "mbackrooms:almond_water": [6, 8],
            "mbackrooms:water_can": [6, 8],
            "mbackrooms:juice": [8, 13],
            "alexscaves:purple_soda_bottle": [8, 13],
            "alexscaves:hot_chocolate_bottle": [6, 8],
        }.items():
            with self.subTest(item=item):
                self.assertEqual(drinks[item], values)
        for number in range(1, 24):
            expected = [6, 8] if number == 5 else [6, 11] if number == 6 else [8, 13]
            self.assertEqual(drinks[f"scp_ultimate:drink_{number}"], expected)
        for item in (
            "minecraft:suspicious_stew",
            "the_bumblezone:bee_soup",
            "mynethersdelight:dried_ghast_with_milk",
            "mekanismdelight:antimatter_stew",
            "mekanismdelight:robit_stew",
            "dungeonsdelight:ghoulash",
            "dungeonsdelight:rubaboo",
            "dungeonsdelight:sinigang",
            "alexscaves:primordial_soup",
            "alexsdelight:acacia_blossom_soup",
        ):
            self.assertEqual(foods[item], [4, 5])
        self.assertEqual(foods["biomeswevegone:green_apple"], [2, 3])
        self.assertEqual(foods["biomeswevegone:blueberries"], [1, 2])
        self.assertEqual(foods["mbackrooms:food_can"], [2, 3])
        for item, values in foods.items():
            if item.endswith("_cup"):
                bowl = item.removesuffix("_cup")
                if bowl.startswith("miners_delight:"):
                    name = bowl.split(":")[1]
                    bowl = next(
                        candidate for candidate in (
                            f"minecraft:{name}", f"farmersdelight:{name}",
                            f"mynethersdelight:{name}", bowl,
                        ) if candidate in foods
                    )
                self.assertEqual(values, [(value + 1) // 2 for value in foods[bowl]])

    def test_thirst_mod_item_assets_and_soup_coverage(self):
        config = load(SERVER, "thirst/item_settings.toml")
        configured = {
            row[0] for group, key in (("Drinks", "drinks"), ("Foods", "foods"))
            for row in config[group][key]
        }
        models = set()
        soup_namespaces = {
            "miners_delight", "mynethersdelight", "nethersdelight", "delightful",
            "alexsdelight", "alexscaves", "endersdelight", "unusualend",
            "biomeswevegone", "mekanismdelight", "the_bumblezone", "dungeonsdelight",
        }
        for path in (ROOT / "mods").glob("*.jar"):
            with ZipFile(path) as archive:
                for name in archive.namelist():
                    parts = name.split("/")
                    if (
                        len(parts) == 5 and parts[0] == "assets"
                        and parts[2:4] == ["models", "item"] and name.endswith(".json")
                    ):
                        models.add(f"{parts[1]}:{parts[4][:-5]}")
        downloaded_items = set()
        if not list((ROOT / "mods").glob("the_bumblezone-*.jar")):
            self.assertIn("the_bumblezone-7.15.2", (ROOT / "Dockerfile").read_text())
            downloaded_items = {
                "the_bumblezone:bee_soup", "the_bumblezone:royal_jelly_bottle",
                "the_bumblezone:sugar_water_bottle",
            }
        for item in configured:
            if not item.startswith("minecraft:"):
                with self.subTest(item=item):
                    self.assertIn(item, models | downloaded_items)
        for item in models:
            namespace, name = item.split(":")
            if (
                namespace in soup_namespaces and ("soup" in name or "stew" in name)
                and not name.endswith("_wood")
            ):
                with self.subTest(soup=item):
                    self.assertIn(item, configured)
        for unavailable in (
            "mekanismdelight:dt_drink", "mekanismdelight:fissile_fuel_drink",
            "endersdelight:chorus_stew_wood", "endersdelight:endermite_stew_wood",
        ):
            self.assertNotIn(unavailable, configured)

    def test_weather2_removed(self):
        self.assertFalse(list((ROOT / "mods").glob("weather2-*.jar")))
        for root in (SERVER, CLIENT):
            self.assertFalse(list((root / "Weather2").glob("*.toml")))

    def test_death_retention_and_existing_overrides(self):
        backrooms = load(SERVER, "mbackrooms/Mbackrooms-Config-Common.toml")
        self.assertFalse(backrooms["Loot Settings"]["partialLootKeeping"])
        backport = load(SERVER, "vanillabackport-common.toml")
        self.assertFalse(backport["Mounts of Mayhem"]["has_zombie_horses"])
        with (SERVER / "chunky/config.json").open() as stream:
            self.assertEqual(json.load(stream)["updateInterval"], 60)


if __name__ == "__main__":
    unittest.main()
