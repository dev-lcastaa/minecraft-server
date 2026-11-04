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

    def test_client_matches_server_except_rendering_and_admin_config(self):
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
                if str(name) == "Weather2/Sand.toml":
                    for key in (
                        "Sandstorm_Particle_Dust_effect_rate",
                        "Sandstorm_Particle_Debris_effect_rate",
                    ):
                        self.assertEqual(client["general"].pop(key), 0.2)
                        server["general"].pop(key)
                if str(name) == "Weather2/Storm.toml":
                    self.assertEqual(client["general"].pop("Storm_ParticleSpawnDelay"), 6)
                    server["general"].pop("Storm_ParticleSpawnDelay")
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
        self.assertEqual(len(drinks), 48)
        self.assertEqual(len(foods), 25)
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

    def test_weather_keeps_danger_with_capped_workload(self):
        storm = load(SERVER, "Weather2/Storm.toml")["general"]
        tornado = load(SERVER, "Weather2/Tornado.toml")["general"]
        self.assertEqual(storm["Storm_MaxPerPlayerPerLayer"], 4)
        self.assertEqual(storm["Storm_HailPerTick"], 2)
        self.assertFalse(tornado["Storm_NoTornadosOrCyclones"])
        self.assertTrue(tornado["Storm_Tornado_grabBlocks"])
        self.assertTrue(tornado["Storm_Tornado_grabPlayer"])
        self.assertEqual(tornado["Storm_Tornado_maxFlyingEntityBlocks"], 40)
        self.assertEqual(tornado["Storm_Tornado_maxBlocksGrabbedPerTick"], 1)
        for kind in ("Sand", "Snow"):
            config = load(SERVER, f"Weather2/{kind}.toml")["general"]
            prefix = f"{kind}storm_{kind}_Buildup"
            self.assertEqual(config[f"{prefix}_TickRate"], 100)
            self.assertEqual(config[f"{prefix}_LoopAmountBase"], 200)

    def test_client_particle_limits(self):
        config = load(CLIENT, "Weather2/Particle.toml")["general"]
        self.assertEqual(config["Particle_effect_rate"], 0.35)
        self.assertEqual(config["Precipitation_Particle_effect_rate"], 0.3)
        self.assertEqual(config["Particle_Tornado_extraParticleCubes"], 0)
        self.assertTrue(config["Particle_engine_weather2"])
        misc = load(CLIENT, "Weather2/Misc.toml")["general"]
        self.assertEqual(misc["Cloud_ParticleSpawnDelay"], 6)
        self.assertFalse(misc["Aesthetic_Only_Mode"])

    def test_death_retention_and_existing_overrides(self):
        backrooms = load(SERVER, "mbackrooms/Mbackrooms-Config-Common.toml")
        self.assertFalse(backrooms["Loot Settings"]["partialLootKeeping"])
        backport = load(SERVER, "vanillabackport-common.toml")
        self.assertFalse(backport["Mounts of Mayhem"]["has_zombie_horses"])
        with (SERVER / "chunky/config.json").open() as stream:
            self.assertEqual(json.load(stream)["updateInterval"], 60)


if __name__ == "__main__":
    unittest.main()
