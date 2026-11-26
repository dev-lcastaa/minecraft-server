import json
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tomllib
import unittest
import uuid
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
            self.assertEqual({n for n in jar.namelist() if not n.endswith(".class")}, set(expected))
            self.assertIn("serverfixes/hydration/KettleBoil.class", jar.namelist())
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

    def test_kettle_boils_plain_water(self):
        spec = importlib.util.spec_from_file_location("hydration_build", SOURCE / "build.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        classpath = build.classpath()
        if classpath is None:
            self.skipTest("Forge 1.20.1 SRG libraries needed; set MC_LIBRARIES")
        recipe = json.loads((ROOT / "server-config/new-world/datapacks/water-compat/data/water_compat/recipes"
                             / "kettle_water.json").read_text())
        work = SOURCE / (".test-" + uuid.uuid4().hex)
        work.mkdir()
        try:
            # Compiling against the real SRG Minecraft/Forge, Farmer's Respite and Farmer's Delight jars checks the API.
            build.compile_to(work)
            test = work / "KettleBoilTest.java"
            test.write_text(f"""
import serverfixes.hydration.KettleBoil;
class KettleBoilTest {{ public static void main(String[] a) {{
  if (KettleBoil.BOIL_TICKS != {recipe["brewingtime"]}) throw new AssertionError("boil time must match the shown recipe");
  if (!KettleBoil.shouldBoil(true, 1000, -1, true, true)) throw new AssertionError("untagged water boils");
  if (!KettleBoil.shouldBoil(true, 250, 0, true, true)) throw new AssertionError("dirty water boils");
  if (KettleBoil.shouldBoil(true, 1000, 3, true, true)) throw new AssertionError("pure water is left alone");
  if (KettleBoil.shouldBoil(true, 1000, 0, false, true)) throw new AssertionError("unheated kettle must not boil");
  if (KettleBoil.shouldBoil(true, 1000, 0, true, false)) throw new AssertionError("real brews keep Farmer's Respite logic");
  if (KettleBoil.shouldBoil(false, 1000, 0, true, true)) throw new AssertionError("only water boils");
  if (KettleBoil.shouldBoil(true, 0, 0, true, true)) throw new AssertionError("empty tank does nothing");
}} }}""")
            subprocess.run(["java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "-nowarn", "-proc:none",
                            "-cp", os.pathsep.join([str(work), classpath]), "-d", str(work), str(test)],
                           check=True, cwd=ROOT, capture_output=True)
            result = subprocess.run(["java", "-cp", os.pathsep.join([str(work), classpath]), "KettleBoilTest"],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        finally:
            shutil.rmtree(work)

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
        for key in ("kettle_pour_use", "kettle_boil", "skillet_block", "skillet_item"):
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
