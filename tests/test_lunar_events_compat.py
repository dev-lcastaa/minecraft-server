import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tomllib
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "server-config/new-world/datapacks/lunar-events-compat"
MOD_JAR = ROOT / "mods/lunar-events-compat-1.20.1-1.0.0.jar"
SOURCE = ROOT / "tools/lunar-events-compat"
NS = "lunar_events_compat"
CORE = "enhancedcelestials2core"
DEFAULTS = "enhancedcelestials2defaultlunarevents"
EVENTS = ("peaceful_moon", "horde_moon", "super_horde_moon", "baby_horde_moon", "miners_moon",
          "black_moon", "ender_moon", "spider_moon", "chaos_moon")
PEACEFUL_DEFAULTS = ("harvest_moon", "super_harvest_moon", "blue_moon", "super_blue_moon")
# Vanilla 1.20.1 entity types referenced by the pack (vanilla has no JAR in mods/).
VANILLA_ENTITIES = {
    "minecraft:zombie", "minecraft:husk", "minecraft:drowned", "minecraft:zombie_villager",
    "minecraft:skeleton", "minecraft:spider", "minecraft:creeper", "minecraft:witch",
    "minecraft:enderman", "minecraft:stray", "minecraft:pillager", "minecraft:vindicator",
    "minecraft:endermite", "minecraft:shulker", "minecraft:cave_spider", "minecraft:silverfish",
    "minecraft:player",
}


def jar(prefix):
    matches = sorted((ROOT / "mods").glob(prefix + "*.jar"))
    if len(matches) != 1:
        raise AssertionError(f"expected one {prefix} jar, found {matches}")
    return ZipFile(matches[0])


def utf8_constant(text):
    return b"\x01" + struct.pack(">H", len(text.encode())) + text.encode()


def mod_jars():
    """Map each declared mod ID to its JAR path."""
    result = {}
    for path in sorted((ROOT / "mods").glob("*.jar")):
        with ZipFile(path) as archive:
            if "META-INF/mods.toml" not in archive.namelist():
                continue
            try:
                metadata = tomllib.loads(archive.read("META-INF/mods.toml").decode())
            except (tomllib.TOMLDecodeError, UnicodeDecodeError):
                continue
            for mod in metadata.get("mods", []):
                result[mod["modId"]] = path
    return result


def pack_json(relative):
    return json.loads((PACK / relative).read_text())


def lunar(namespace, kind, name):
    return PACK / f"data/{namespace}/{CORE}/lunar/{kind}/{name}.json"


class LunarEventsCompatTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with jar("Enhanced-Celestials-2-Default-Lunar-Events-") as defaults:
            cls.default_files = {name: defaults.read(name) for name in defaults.namelist()
                                 if name.endswith(".json")}
        with jar("Enhanced-Celestials-2-Core-") as core:
            cls.modifier_types = core.read(
                "dev/corgitaco/enhancedcelestials2core/api/lunarevent/modifier/LunarEventModifierTypes.class")
            cls.rule_types = core.read(
                "dev/corgitaco/enhancedcelestials2core/api/lunarevent/spawnrule/LunarEventSpawnRuleTypes.class")

    def modifier(self, reference):
        namespace, name = reference.split(":")
        path = lunar(namespace, "event_modifier", name)
        if path.is_file():
            return json.loads(path.read_text())
        default = f"data/{namespace}/{CORE}/lunar/event_modifier/{name}.json"
        self.assertIn(default, self.default_files, f"Missing lunar event modifier {reference}")
        return json.loads(self.default_files[default])

    def test_generator_output_is_committed(self):
        spec = importlib.util.spec_from_file_location("lunar_build", ROOT / "tools/lunar-events-compat/build.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        files, client = module.resources()
        committed = {p.relative_to(PACK).as_posix() for p in PACK.rglob("*") if p.is_file()}
        self.assertEqual(committed, set(files))
        for relative, content in files.items():
            self.assertEqual((PACK / relative).read_bytes(), content, relative)
        for relative, content in client.items():
            self.assertEqual((ROOT / "client-config/kubejs/assets" / relative).read_bytes(), content)
        self.assertEqual(json.loads(files["pack.mcmeta"])["pack"]["pack_format"], 15)

    def test_events_use_valid_unique_modifiers(self):
        events = [lunar(NS, "event", name) for name in EVENTS]
        events += [lunar(DEFAULTS, "event", name) for name in PEACEFUL_DEFAULTS]
        for path in events:
            with self.subTest(event=path.stem):
                types = []
                for reference in json.loads(path.read_text())["modifiers"]:
                    modifier = self.modifier(reference)
                    namespace, kind = modifier["type"].split(":")
                    self.assertEqual(namespace, CORE)
                    self.assertIn(utf8_constant(kind), self.modifier_types, modifier["type"])
                    self.assertIn("settings", modifier)
                    types.append(kind)
                # Enhanced Celestials rejects an event with two modifiers of one type.
                self.assertEqual(len(types), len(set(types)), types)

    def test_peaceful_overrides_keep_default_modifiers(self):
        for name in PEACEFUL_DEFAULTS:
            with self.subTest(event=name):
                original = json.loads(self.default_files[f"data/{DEFAULTS}/{CORE}/lunar/event/{name}.json"])
                override = json.loads(lunar(DEFAULTS, "event", name).read_text())["modifiers"]
                self.assertEqual(override[:len(original["modifiers"])], original["modifiers"])
                self.assertIn(f"{NS}:peaceful_moon_spawn_category_multiplier", override)
        no_monsters = self.modifier(f"{NS}:peaceful_moon_spawn_category_multiplier")
        self.assertEqual(no_monsters["settings"], {"multipliers": {"monster": 0.0}})

    def test_events_registered_in_overworld_pool(self):
        default_weights = []
        for name, content in self.default_files.items():
            if "/lunar/event_probability/" in name:
                default_weights.append(json.loads(content)["dimensions"]["minecraft:overworld"]
                                       ["spawn_requirements"]["weight"])
        new_weights = []
        for name in EVENTS:
            with self.subTest(event=name):
                self.assertTrue(lunar(NS, "event", name).is_file())
                probability = json.loads(lunar(NS, "event_probability", name).read_text())
                self.assertEqual(probability["lunar_event"], f"{NS}:{name}")
                requirements = probability["dimensions"]["minecraft:overworld"]["spawn_requirements"]
                self.assertGreater(requirements["weight"], 0)
                self.assertLess(requirements["weight"], max(default_weights))
                rules = {rule["type"]: rule["settings"] for rule in requirements["rules"]}
                self.assertGreaterEqual(rules[f"{CORE}:min_nights_between"]["min_nights"], 10)
                self.assertTrue(set(rules[f"{CORE}:valid_moon_phase"]["valid_moon_phases"]) <= set(range(8)))
                for rule in rules:
                    self.assertIn(utf8_constant(rule.split(":")[1]), self.rule_types)
                new_weights.append(requirements["weight"])
        # Keep the added events rarer in total than the stock events they share the pool with.
        self.assertLess(sum(new_weights), sum(default_weights))
        self.assertFalse(lunar(CORE, "event_probability", "default").exists())

    def test_referenced_entities_exist_in_installed_jars(self):
        mods = mod_jars()
        referenced = set()
        for path in (PACK / f"data/{NS}/{CORE}/lunar/event_modifier").glob("*.json"):
            modifier = json.loads(path.read_text())
            if modifier["type"] == f"{CORE}:mob_spawn_settings":
                for category, entries in modifier["settings"]["spawn_settings"]["spawners"].items():
                    ids = [entry["type"] for entry in entries]
                    with self.subTest(spawners=path.stem, category=category):
                        vanilla = [id.startswith("minecraft:") for id in ids]
                        # An unknown entity drops the rest of the list, so vanilla goes first.
                        self.assertEqual(vanilla, sorted(vanilla, reverse=True))
                        for entry in entries:
                            self.assertGreaterEqual(entry["maxCount"], entry["minCount"])
                            self.assertGreater(entry["weight"], 0)
                    referenced.update(ids)
            for entry in modifier["settings"].get("effects", []):
                if entry["filter"]["type"] == "corgilib:is_type":
                    referenced.add(entry["filter"]["id"])
        for value in pack_json(f"data/{NS}/tags/entity_types/horde_zombies.json")["values"]:
            if isinstance(value, dict):
                self.assertFalse(value["required"])
                value = value["id"]
            referenced.add(value)
        self.assertGreater(len(referenced), 40)
        for id in sorted(referenced):
            namespace, name = id.split(":")
            with self.subTest(entity=id):
                if namespace == "minecraft":
                    self.assertIn(id, VANILLA_ENTITIES)
                    continue
                self.assertIn(namespace, mods, f"No installed mod provides {namespace}")
                with ZipFile(mods[namespace]) as archive:
                    self.assertTrue(any(entry.endswith(".class") and utf8_constant(name) in archive.read(entry)
                                        for entry in archive.namelist()), f"{id} is not registered")

    def test_tag_filters_and_sounds_resolve(self):
        sounds = json.loads(self.default_files[f"assets/{DEFAULTS}/sounds.json"])
        for path in (PACK / f"data/{NS}/{CORE}/lunar/event_modifier").glob("*.json"):
            modifier = json.loads(path.read_text())
            with self.subTest(modifier=path.stem):
                if modifier["type"] == f"{CORE}:sound_track":
                    namespace, name = modifier["settings"]["sound_track"]["sound_id"].split(":")
                    self.assertEqual(namespace, DEFAULTS)
                    self.assertIn(name, sounds)
                if modifier["type"] == f"{CORE}:mob_effects":
                    for entry in modifier["settings"]["effects"]:
                        if entry["filter"]["type"] == "corgilib:is_type_tag":
                            tag = entry["filter"]["tag"]
                            # Corgilib uses the hashed tag codec.
                            self.assertTrue(tag.startswith("#"), tag)
                            namespace, name = tag[1:].split(":")
                            self.assertTrue((PACK / f"data/{namespace}/tags/entity_types/{name}.json").is_file())
                        self.assertTrue(entry["mob_effect"]["effect"].startswith("minecraft:"))

    def test_client_language(self):
        lang = json.loads((ROOT / f"client-config/kubejs/assets/{NS}/lang/en_us.json").read_text())
        for name in EVENTS:
            with self.subTest(event=name):
                self.assertIn(f"lunar.event.{NS}.{name}", lang)
                components = self.modifier(f"{NS}:{name}_text_components")["settings"]["components"]
                for notification in components.values():
                    self.assertIn(notification["component"]["key"], lang)

    def test_chaos_moon_is_crowded_and_mixed(self):
        multipliers = self.modifier(f"{NS}:chaos_moon_spawn_category_multiplier")["settings"]["multipliers"]
        self.assertGreaterEqual(multipliers["monster"], 4.0)
        self.assertGreaterEqual(multipliers["creature"], 2.0)
        spawners = self.modifier(f"{NS}:chaos_moon_mob_spawn_settings")["settings"]["spawn_settings"]["spawners"]
        self.assertGreaterEqual(len({entry["type"] for entry in spawners["monster"]}), 10)
        self.assertIn(f"{NS}:chaos_moon_force_surface_spawning",
                      json.loads((PACK / f"data/{NS}/{CORE}/lunar/event/chaos_moon.json").read_text())["modifiers"])

    def test_gameplay_is_a_compiled_server_mod_not_a_kubejs_script(self):
        # The KubeJS version failed on the server: vanilla names such as getGameTime() are not remapped there.
        for side in ("server-config", "client-config"):
            self.assertFalse((ROOT / side / "kubejs/server_scripts/lunar_events_compat.js").exists())
        self.assertEqual(MOD_JAR.read_bytes(), (ROOT / "client-config/mods" / MOD_JAR.name).read_bytes())
        with ZipFile(MOD_JAR) as mod:
            metadata = tomllib.loads(mod.read("META-INF/mods.toml").decode())
            self.assertEqual(metadata["mods"][0]["modId"], NS)
            self.assertEqual(metadata["mods"][0]["displayTest"], "IGNORE_ALL_VERSION")
            classes = {n for n in mod.namelist() if n.endswith(".class")}
            self.assertTrue({"serverfixes/lunar/LunarEvents.class", "serverfixes/lunar/ChaosTargetGoal.class",
                             "serverfixes/lunar/ChaosBrawlGoal.class", "serverfixes/lunar/Rules.class"} <= classes)
            for name in classes:
                self.assertEqual(int.from_bytes(mod.read(name)[6:8], "big"), 61, name)

    def test_compiled_against_real_classes_and_rules(self):
        spec = importlib.util.spec_from_file_location("lunar_build", SOURCE / "build.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        classpath = build.classpath()
        if classpath is None:
            self.skipTest("Forge 1.20.1 SRG libraries needed; set MC_LIBRARIES")
        work = SOURCE / (".test-" + __import__("uuid").uuid4().hex)
        work.mkdir()
        try:
            # Compiling against SRG Minecraft/Forge and Enhanced Celestials verifies every API call and override.
            build.compile_to(work, SOURCE / "BehaviorTest.java")
            result = subprocess.run(["java", "-cp", os.pathsep.join([str(work), classpath]), "BehaviorTest"],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        finally:
            shutil.rmtree(work)

    def test_moon_night_follows_seasonal_sunset_and_sunrise(self):
        with ZipFile(MOD_JAR) as mod:
            self.assertEqual(json.loads(mod.read("META-INF/coremods.json")),
                             {"seasonal_moon_night": "coremods/seasonal_moon_night.js"})
            self.assertEqual(mod.read("coremods/seasonal_moon_night.js"),
                             (SOURCE / "coremods/seasonal_moon_night.js").read_bytes())
            self.assertIn("serverfixes/lunar/LunarClock.class", mod.namelist())
        classpath = os.environ.get("LUNAR_EVENTS_TEST_CLASSPATH")
        if not classpath:
            self.skipTest("Set LUNAR_EVENTS_TEST_CLASSPATH to Nashorn and ASM JARs for bytecode execution")
        result = subprocess.run(
            ["java", "-cp", classpath, str(ROOT / "tests/LunarClockCoremodTest.java"),
             str(SOURCE / "coremods/seasonal_moon_night.js"),
             str(ROOT / "mods/Enhanced-Celestials-2-Core-Forge-1.20.1-1.0.3.4.jar")],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Seasonal moon night coremod tests passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
