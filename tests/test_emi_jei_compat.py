import os
from pathlib import Path
import subprocess
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/emi-jei-compat"
JAR = ROOT / "client-config/mods/emi-jei-compat-1.20.1-1.0.0.jar"


class EmiJeiCompatTest(unittest.TestCase):
    def test_jar_matches_sources_and_is_client_only(self):
        with ZipFile(JAR) as jar:
            expected = {p.relative_to(SOURCE).as_posix(): p.read_bytes()
                        for d in ("META-INF", "coremods") for p in (SOURCE / d).rglob("*") if p.is_file()}
            expected["pack.mcmeta"] = (SOURCE / "pack.mcmeta").read_bytes()
            self.assertEqual(set(jar.namelist()), set(expected))
            for name, data in expected.items():
                self.assertEqual(jar.read(name), data, name)
        self.assertFalse((ROOT / "mods" / JAR.name).exists(), "EMI/JEI bridge fix is client-only")
        installed = {p.name for p in (ROOT / "mods").glob("*.jar")}
        self.assertIn("emi-1.1.24+1.20.1+forge.jar", installed)
        self.assertIn("jei-1.20.1-forge-15.74.0.234.jar", installed)

    def test_coremod_applies_to_installed_emi_and_jei(self):
        classpath = os.environ.get("EMI_JEI_TEST_CLASSPATH")
        if not classpath:
            self.skipTest("Set EMI_JEI_TEST_CLASSPATH to Nashorn 15.4 and ASM (incl. commons) jars")
        result = subprocess.run(["java", "-cp", classpath, str(SOURCE / "Verify.java"),
                                 str(SOURCE / "coremods/emi_jei.js"), str(ROOT / "mods/emi-1.1.24+1.20.1+forge.jar"),
                                 str(ROOT / "mods/jei-1.20.1-forge-15.74.0.234.jar")],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("getAllIngredientsList verified", result.stdout)


if __name__ == "__main__":
    unittest.main()
