import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/scp-ultimate-compat"
JAR_NAME = "scp-ultimate-compat-1.20.1-1.0.0.jar"
SCP_JAR = ROOT / "mods/scp_ultimate-1.2.2-forge-1.20.1.jar"


class ScpUltimateCompatTest(unittest.TestCase):
    def test_built_addon_matches_sources(self):
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
        dependencies = {d["modId"]: d for d in metadata["dependencies"]["scp_ultimate_compat"]}
        with ZipFile(SCP_JAR) as jar:
            installed = tomllib.loads(jar.read("META-INF/mods.toml").decode())["mods"][0]["version"]
        self.assertEqual(dependencies["scp_ultimate"]["versionRange"], f"[{installed}]")

    def test_installed_mod_bytecode_transform(self):
        classpath = os.environ.get("SCP_ULTIMATE_TEST_CLASSPATH")
        if not classpath:
            self.skipTest("Set SCP_ULTIMATE_TEST_CLASSPATH to Nashorn and ASM JARs for bytecode execution")
        java = shutil.which("java")
        self.assertTrue(java, "A JDK is required for the bytecode fixture")
        result = subprocess.run(
            [java, "-cp", classpath, str(ROOT / "tests/ScpUltimateCoremodTest.java"),
             str(SOURCE / "coremods/scp250_day_sync.js"), str(SCP_JAR)],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SCP Ultimate installed-bytecode sync tests passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
