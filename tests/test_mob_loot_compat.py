import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/mob-loot-compat"
PACK = ROOT / "server-config/new-world/datapacks/mob-loot-compat"
JAR = "mob-loot-compat-1.20.1-1.0.0.jar"


class MobLootCompatTests(unittest.TestCase):
    def test_reproducible_build_and_client_parity(self):
        spec = importlib.util.spec_from_file_location("mob_loot_build", SOURCE / "build.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        expected = module.resources()
        for folder in ("META-INF", "coremods"):
            expected.update({p.relative_to(SOURCE).as_posix(): p.read_bytes()
                             for p in (SOURCE / folder).rglob("*") if p.is_file()})
        expected["pack.mcmeta"] = (SOURCE / "pack.mcmeta").read_bytes()
        self.assertEqual((ROOT / "mods" / JAR).read_bytes(),
                         (ROOT / "client-config/mods" / JAR).read_bytes())
        with ZipFile(ROOT / "mods" / JAR) as jar:
            self.assertEqual(set(jar.namelist()), set(expected))
            for name, content in expected.items():
                self.assertEqual(jar.read(name), content)
                if name.startswith("data/") and name != "data/forge/loot_modifiers/global_loot_modifiers.json":
                    self.assertEqual((PACK / name).read_bytes(), content)
        self.assertFalse((PACK / "data/forge/loot_modifiers/global_loot_modifiers.json").exists(),
                         "The world override must not register the JAR modifiers a second time")
        for scope in ("startup_scripts", "server_scripts"):
            path = Path("kubejs") / scope / "mob_loot_compat.js"
            self.assertEqual((ROOT / "server-config" / path).read_bytes(),
                             (ROOT / "client-config" / path).read_bytes())

    def test_all_explicit_ids_have_registry_constructor_evidence(self):
        evidence = json.loads((SOURCE / "verified_entities.json").read_text())
        classes = json.loads((SOURCE / "classifications.json").read_text())
        for category, ids in json.loads((SOURCE / "audited_extensions.json").read_text()).items():
            classes[category].extend(ids)
        all_ids = [id for values in classes.values() for id in values]
        self.assertEqual(len(all_ids), len(set(all_ids)))
        for id in all_ids:
            self.assertIn(id, evidence, id)
            with ZipFile(ROOT / "mods" / evidence[id]["jar"]) as jar:
                registry = jar.read(evidence[id]["registry"].replace(".", "/") + ".class")
                entity = jar.read(evidence[id]["class"].replace(".", "/") + ".class")
                self.assertIn(id.split(":")[1].encode(), registry)
                self.assertTrue(entity.startswith(b"\xca\xfe\xba\xbe"))
        for species in ("cow", "pig", "chicken"):
            for climate in ("cold", "warm"):
                self.assertIn(f"backported_animal_variants:{climate}_{species}", evidence)

    def test_additive_loot_rates_and_items(self):
        data = PACK / "data/mob_loot_compat"
        bat = json.loads((data / "loot_tables/evil_bat_wings.json").read_text())
        entry = bat["pools"][0]["entries"][0]
        self.assertEqual(entry["name"], "miners_delight:bat_wing")
        self.assertEqual(entry["functions"][0]["count"],
                         {"type": "minecraft:uniform", "min": 1, "max": 2})
        zombie = json.loads((data / "loot_tables/zombie_food.json").read_text())["pools"][0]
        self.assertEqual(zombie["conditions"], [{"condition": "minecraft:random_chance", "chance": 0.05}])
        self.assertEqual(zombie["rolls"], 1)
        self.assertEqual(len(zombie["entries"]), 6)
        for entry in zombie["entries"]:
            self.assertEqual(entry["weight"], 1)
            with ZipFile(ROOT / "mods/FarmersDelight-1.20.1-1.3.4.jar") as jar:
                registry = jar.read("vectorwing/farmersdelight/common/registry/ModItems.class")
                self.assertIn(entry["name"].split(":")[1].encode(), registry)
        for name in ("evil_bat_wings", "zombie_food"):
            modifier = json.loads((data / f"loot_modifiers/{name}.json").read_text())
            self.assertEqual(modifier["type"], "farmersdelight:add_loot_table")
            self.assertIn({"condition": "minecraft:killed_by_player"}, modifier["conditions"])
        self.assertNotIn("looting", json.dumps(zombie).lower())

    def test_gameplay_execution(self):
        node = shutil.which("node")
        self.assertTrue(node, "Node.js is required for mob loot gameplay verification")
        result = subprocess.run([node, str(SOURCE / "test_fixture.js"), str(ROOT)],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_installed_kubejs_damage_mappings(self):
        java = shutil.which("java")
        self.assertTrue(java, "Java is required for Rhino damage-source verification")
        kubejs = ROOT / "mods/kubejs-forge-2001.6.5-build.26.jar"
        mixin = subprocess.run(
            [java, "-m", "jdk.jdeps/com.sun.tools.javap.Main", "-p", "-v",
             "-classpath", str(kubejs), "dev.latvian.mods.kubejs.core.mixin.common.DamageSourceMixin"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(mixin.returncode, 0, mixin.stdout + mixin.stderr)
        for method, alias in (("m_7639_", "getActual"), ("m_7640_", "getImmediate")):
            match = re.search(rf"public abstract [^\n]+ {method}\(\);(.*?)(?=\n  public|\n}})",
                              mixin.stdout, re.DOTALL)
            self.assertIsNotNone(match, method)
            self.assertIn("dev.latvian.mods.rhino.util.RemapForJS", match.group(1), method)
            self.assertIn(f'value="{alias}"', match.group(1), method)

    def test_actual_rhino_damage_source_gameplay(self):
        classpath = os.environ.get("MOB_LOOT_RHINO_TEST_CLASSPATH")
        if not classpath:
            self.skipTest("Set MOB_LOOT_RHINO_TEST_CLASSPATH to Gson and Commons Lang JARs")
        java = shutil.which("java")
        self.assertTrue(java, "Java is required for Rhino damage-source verification")
        result = subprocess.run(
            [java, "-cp", str(ROOT / "mods/rhino-forge-2001.2.3-build.10.jar") + os.pathsep + classpath,
             str(ROOT / "tests/DamageSourceRhinoTest.java"),
             str(ROOT / "server-config/kubejs/server_scripts/mob_loot_compat.js")],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Rhino remapped damage-source gameplay passed", result.stdout)

    def test_actual_installed_bytecode(self):
        classpath = os.environ.get("MOB_LOOT_TEST_CLASSPATH")
        if not classpath:
            self.skipTest("Set MOB_LOOT_TEST_CLASSPATH to Nashorn and ASM dependencies")
        result = subprocess.run(["java", "-cp", classpath, str(SOURCE / "CoremodTest.java"),
                                 str(SOURCE), str(ROOT / "mods")],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_measurable_complete_constructor_coverage(self):
        coverage = json.loads((SOURCE / "blood_coverage.json").read_text())
        entities = json.loads((SOURCE / "verified_entities.json").read_text())
        self.assertEqual(set(coverage), set(entities))
        self.assertEqual(len(coverage), len(entities))
        self.assertGreaterEqual(len(coverage), 296)
        eligible = sum(row["eligible"] for row in coverage.values())
        excluded = sum(not row["eligible"] for row in coverage.values())
        self.assertEqual(eligible + excluded, len(entities))
        self.assertTrue(all(row["category"] in {
            "primary", "winged", "wide", "humanoid", "aquatic", "adaptive_animal", "bloodless"
        } for row in coverage.values()))
        self.assertTrue(all(row["basis"] and row["ancestors"] for row in coverage.values()))
        if os.environ.get("MOB_LOOT_TEST_CLASSPATH"):
            spec = importlib.util.spec_from_file_location("mob_loot_audit", SOURCE / "audit.py")
            audit = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(audit)
            self.assertEqual(audit.audit(), coverage,
                             "Reverify constructor binding, hierarchy, native flags, lore and models from current JARs")


if __name__ == "__main__":
    unittest.main()
