import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/cravings-compat"
JAR_NAME = "cravings-compat-1.20.1-1.0.0.jar"


class CravingsCompatTest(unittest.TestCase):
    def test_built_overlays_match_sources(self):
        server = ROOT / "mods" / JAR_NAME
        self.assertEqual(server.read_bytes(), (ROOT / "client-config/mods" / JAR_NAME).read_bytes())
        with ZipFile(server) as jar:
            expected = {path.relative_to(SOURCE).as_posix(): path.read_bytes()
                        for folder in ("META-INF", "coremods")
                        for path in (SOURCE / folder).rglob("*") if path.is_file()}
            expected["pack.mcmeta"] = (SOURCE / "pack.mcmeta").read_bytes()
            self.assertEqual(set(jar.namelist()), set(expected))
            for name, content in expected.items():
                self.assertEqual(jar.read(name), content, name)
            self.assertEqual(json.loads(jar.read("pack.mcmeta"))["pack"]["pack_format"], 15)
            metadata = tomllib.loads(jar.read("META-INF/mods.toml").decode())
            self.assertEqual(metadata["modLoader"], "lowcodefml")
            self.assertEqual(metadata["loaderVersion"], "[47,48)")
            dependencies = metadata["dependencies"]["cravings_compat"]
            self.assertEqual({dependency["modId"] for dependency in dependencies},
                             {"cravings", "kubejs", "lunch_basket_compat"})
            self.assertTrue(all(dependency["mandatory"] for dependency in dependencies))
        for name in ("startup_scripts/craving_pancakes.js", "server_scripts/craving_foods.js"):
            path = Path("kubejs") / name
            self.assertEqual((ROOT / "server-config" / path).read_bytes(),
                             (ROOT / "client-config" / path).read_bytes())

    def test_registry_coverage_tiers_and_feedback(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is required for the KubeJS execution fixture")
        result = subprocess.run(
            [node, str(ROOT / "tests/cravings_fixture.js"), str(ROOT)],
            check=True, cwd=ROOT, capture_output=True, text=True,
        )
        self.assertIn("Craving registry, pancake and client feedback fixtures passed", result.stdout)

    def test_installed_mod_bytecode_transforms(self):
        classpath = os.environ.get("CRAVINGS_TEST_CLASSPATH")
        if not classpath:
            self.skipTest("Set CRAVINGS_TEST_CLASSPATH to Nashorn and ASM JARs for bytecode execution")
        java = shutil.which("java")
        self.assertTrue(java, "A JDK is required for the bytecode fixture")
        result = subprocess.run(
            [java, "-cp", classpath, str(ROOT / "tests/CravingsCoremodTest.java"),
             str(SOURCE / "coremods/craving_foods.js"), str(ROOT / "mods")],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Cravings installed-bytecode and duration tests passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
