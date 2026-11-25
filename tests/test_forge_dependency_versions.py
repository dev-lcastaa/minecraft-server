import os
from pathlib import Path
import shutil
import subprocess
import tomllib
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


def mod_version(archive, mod):
    version = mod["version"]
    if version != "${file.jarVersion}":
        return version
    headers = {}
    key = None
    for line in archive.read("META-INF/MANIFEST.MF").decode("utf-8").splitlines():
        if not line:
            break
        if line.startswith(" ") and key is not None:
            headers[key] += line[1:]
        else:
            key, value = line.split(": ", 1)
            headers[key] = value
    return headers["Implementation-Version"]


class ForgeDependencyVersionsTest(unittest.TestCase):
    def test_hydration_thirst_dependency_is_pinned_to_installed_version(self):
        jars = list((ROOT / "mods").glob("ThirstWasTaken-*.jar"))
        self.assertEqual(len(jars), 1)
        with ZipFile(jars[0]) as jar:
            metadata = tomllib.loads(jar.read("META-INF/mods.toml").decode())
            thirst = next(mod for mod in metadata["mods"] if mod["modId"] == "thirst")
            installed_version = mod_version(jar, thirst)
        hydration = tomllib.loads(
            (ROOT / "tools/hydration-compat/META-INF/mods.toml").read_text()
        )
        dependency = next(
            item for item in hydration["dependencies"]["hydration_compat"]
            if item["modId"] == "thirst"
        )
        self.assertTrue(dependency["mandatory"])
        self.assertEqual(dependency["versionRange"], f"[{installed_version}]")

    def test_all_addon_ranges_accept_installed_versions_with_forge_maven(self):
        classpath = os.environ.get("FORGE_VERSION_TEST_CLASSPATH")
        if not classpath:
            self.skipTest("Set FORGE_VERSION_TEST_CLASSPATH to Forge's Maven Artifact and Commons Lang JARs")
        java = shutil.which("java")
        self.assertTrue(java, "Java is required for Forge dependency version checks")

        installed = {}
        addons = {}
        for path in sorted((ROOT / "mods").glob("*.jar")):
            with ZipFile(path) as jar:
                if "META-INF/mods.toml" not in jar.namelist():
                    continue
                metadata = tomllib.loads(jar.read("META-INF/mods.toml").decode())
                for mod in metadata.get("mods", []):
                    mod_id = mod["modId"]
                    self.assertNotIn(mod_id, installed, f"Duplicate mod ID: {mod_id}")
                    installed[mod_id] = (path, mod)
                    if mod_id.endswith("_compat"):
                        addons[mod_id] = metadata.get("dependencies", {}).get(mod_id, [])

        builtins = {"minecraft": "1.20.1", "forge": os.environ.get("FORGE_TEST_VERSION", "47.4.28")}
        rows = []
        thirst_range = None
        for addon, dependencies in sorted(addons.items()):
            for dependency in dependencies:
                if not dependency.get("mandatory"):
                    continue
                mod_id = dependency["modId"]
                if mod_id in builtins:
                    version = builtins[mod_id]
                else:
                    self.assertIn(mod_id, installed, f"{addon} is missing {mod_id}")
                    path, mod = installed[mod_id]
                    with ZipFile(path) as jar:
                        version = mod_version(jar, mod)
                version_range = dependency["versionRange"]
                rows.append((addon, mod_id, version, version_range, "true"))
                if addon == "hydration_compat" and mod_id == "thirst":
                    thirst_range = version_range
        self.assertGreater(len(rows), 20)
        self.assertIsNotNone(thirst_range)
        for version in ("1.4.0", "1.20.1-1.4.1"):
            rows.append(("hydration_compat", "thirst", version, thirst_range, "false"))
        result = subprocess.run(
            [java, "-cp", classpath, str(ROOT / "tests/ForgeDependencyVersionTest.java")],
            input="".join("\t".join(row) + "\n" for row in rows),
            capture_output=True, text=True, cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"Forge Maven version checks passed: {len(rows)}", result.stdout)


if __name__ == "__main__":
    unittest.main()
