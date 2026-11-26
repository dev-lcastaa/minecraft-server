import json
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tomllib
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/hydration-compat"
JAR = "hydration-compat-1.20.1-1.0.0.jar"


class HydrationCompatTest(unittest.TestCase):
    def test_installed_vendor_recipe_coverage(self):
        spec = importlib.util.spec_from_file_location("hydration_audit", SOURCE / "audit.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = module.audit()
        self.assertEqual(report["configured_drink_ids"], 103)
        self.assertEqual(report["unsupported_output_shapes"], [])
        self.assertEqual(report["drink_ids_with_declared_recipes"], report["drink_ids_with_supported_output_shapes"])
        self.assertGreater(report["conditional_drink_ids"], 10)

    def test_reproducible_jars_and_client_scripts(self):
        self.assertEqual((ROOT / "mods" / JAR).read_bytes(), (ROOT / "client-config/mods" / JAR).read_bytes())
        with ZipFile(ROOT / "mods" / JAR) as jar:
            expected = {path.relative_to(SOURCE).as_posix(): path.read_bytes()
                        for folder in ("META-INF", "coremods")
                        for path in (SOURCE / folder).rglob("*") if path.is_file()}
            expected["pack.mcmeta"] = (SOURCE / "pack.mcmeta").read_bytes()
            datapack = ROOT / "server-config/new-world/datapacks/water-compat"
            expected.update({path.relative_to(datapack).as_posix(): path.read_bytes()
                             for path in (datapack / "data").rglob("*") if path.is_file()})
            self.assertEqual(set(jar.namelist()), set(expected))
            for path, contents in expected.items():
                self.assertEqual(jar.read(path), contents)
            self.assertEqual(json.loads(jar.read("pack.mcmeta"))["pack"]["pack_format"], 15)
            metadata = tomllib.loads(jar.read("META-INF/mods.toml").decode())
            self.assertEqual(metadata["modLoader"], "lowcodefml")
            respite = next(d for d in metadata["dependencies"]["hydration_compat"] if d["modId"] == "farmersrespite")
            self.assertEqual(respite["versionRange"], "[1.20.1-2.1,1.20.1-2.2)")
        for name in ("startup_scripts/hydration_hooks.js", "server_scripts/hydration_recipes.js"):
            self.assertEqual((ROOT / "server-config/kubejs" / name).read_bytes(),
                             (ROOT / "client-config/kubejs" / name).read_bytes())

    def test_purification_conserves_containers_and_fluid(self):
        recipes = ROOT / "server-config/new-world/datapacks/water-compat/data/water_compat/recipes"
        pot = json.loads((recipes / "pot_water.json").read_text())
        kettle = json.loads((recipes / "kettle_water.json").read_text())
        self.assertEqual(pot["container"], {"item": "minecraft:glass_bottle"})
        self.assertIn("Purity:3", pot["result"]["nbt"])
        self.assertTrue(all(i["type"] == "forge:nbt" for i in pot["ingredients"][0]))
        self.assertTrue(all("Potion:'minecraft:water'" in i["nbt"] for i in pot["ingredients"][0]))
        self.assertEqual(kettle["base"], kettle["result"])
        self.assertEqual(kettle["brewingtime"], 200)
        self.assertNotIn("cookingtime", kettle)
        pouring = json.loads((recipes / "kettle_pouring_water.json").read_text())
        self.assertEqual((pouring["fluid"], pouring["amount"], pouring["container"]),
                         ("minecraft:water", 250, {"item": "minecraft:glass_bottle"}))
        # Thirst's kettle mixin copies the tank's purity onto the poured bottle; the recipe must not fix one.
        self.assertEqual(pouring["output"]["item"], "minecraft:potion")
        self.assertNotIn("Purity", pouring["output"]["nbt"])

    def test_client_guidance_syntax(self):
        node = shutil.which("node")
        self.assertTrue(node)
        subprocess.run([node, "--check", str(ROOT / "client-config/kubejs/client_scripts/hydration_tooltips.js")],
                       cwd=ROOT, check=True, capture_output=True)

    def test_actual_installed_bytecode(self):
        classpath = os.environ.get("HYDRATION_TEST_CLASSPATH")
        if not classpath:
            self.skipTest("Set HYDRATION_TEST_CLASSPATH to local Nashorn/ASM jars")
        java = shutil.which("java") or "/usr/lib/jvm/java-25-openjdk-amd64/bin/java"
        result = subprocess.run([java, "-cp", classpath, str(SOURCE / "Verify.java"), str(ROOT)],
                                cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hydration_pot: installed bytecode verified", result.stdout)
        self.assertIn("hydration_kettle: installed bytecode verified", result.stdout)
        self.assertIn("hydration_monster_pot: installed bytecode verified", result.stdout)
        self.assertIn("hydration_create: installed bytecode verified", result.stdout)
        for key in ("kettle_pour_use", "kettle_pour_tick", "skillet_block", "skillet_item"):
            self.assertIn(f"hydration_{key}: installed bytecode verified", result.stdout)

    def test_recipe_and_brewing_runtime_fixture(self):
        node = shutil.which("node")
        self.assertTrue(node, "Node is required for the script execution fixture")
        result = subprocess.run([node, str(SOURCE / "fixture.js"), str(ROOT)],
                                cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_actual_rhino_hooks(self):
        classpath = os.environ.get("HYDRATION_RHINO_TEST_CLASSPATH")
        if not classpath:
            self.skipTest("Set HYDRATION_RHINO_TEST_CLASSPATH to Gson and Commons Lang JARs")
        java = shutil.which("java")
        self.assertTrue(java, "Java is required for Rhino hydration verification")
        result = subprocess.run(
            [java, "-cp", str(ROOT / "mods/rhino-forge-2001.2.3-build.10.jar") + os.pathsep + classpath,
             str(ROOT / "tests/HydrationHooksRhinoTest.java"),
             str(ROOT / "server-config/kubejs/startup_scripts/hydration_hooks.js")],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Rhino hydration hooks passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
