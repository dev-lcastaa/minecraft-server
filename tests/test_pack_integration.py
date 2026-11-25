import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tomllib
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
WORD = re.compile(r"[\w$.]")


def rhino_loop_body_declarations(source):
    """Find const/let declared directly inside loop bodies, which Rhino binds once."""
    blank = lambda match: re.sub(r"[^\n]", " ", match.group())
    code = re.sub(r"//[^\n]*|/\*.*?\*/", blank, source, flags=re.S)
    code = re.sub(r"'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"|`(?:\\.|[^`\\])*`", blank, code)
    stack, pending, found, index = [], None, [], 0
    while index < len(code):
        boundary = index == 0 or not WORD.match(code[index - 1])
        rest = code[index:]
        match = boundary and re.match(r"(for|while|do)\b", rest)
        if match:
            pending, index = "loop", index + match.end()
            continue
        match = re.match(r"=>", rest) or (boundary and re.match(r"function\b", rest))
        if match:
            pending, index = "function", index + match.end()
            continue
        if code[index] == "{":
            stack.append(pending or "block")
            pending = None
        elif code[index] == "}" and stack:
            stack.pop()
        elif boundary and re.match(r"(const|let)\s", rest):
            if next((kind for kind in reversed(stack) if kind != "block"), None) == "loop":
                found.append(code.count("\n", 0, index) + 1)
        index += 1
    return found


class PackIntegrationTest(unittest.TestCase):
    def test_kubejs_scripts_parse(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is required for JavaScript syntax checks")
        for folder in ("server-config/kubejs", "client-config/kubejs"):
            for path in (ROOT / folder).rglob("*.js"):
                with self.subTest(script=path.relative_to(ROOT)):
                    result = subprocess.run(
                        [node, "--check", str(path)], capture_output=True, text=True
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_kubejs_scripts_avoid_rhino_pitfalls(self):
        # KubeJS bean properties (kjs$getLevel/kjs$getOverworld) can shadow these vanilla methods.
        shadowed = re.compile(r"\.(level|overworld)\(\)")
        for folder in ("server-config/kubejs", "client-config/kubejs"):
            for path in (ROOT / folder).rglob("*.js"):
                source = path.read_text()
                with self.subTest(script=path.relative_to(ROOT)):
                    self.assertEqual(rhino_loop_body_declarations(source), [])
                    self.assertIsNone(shadowed.search(source))

    def test_server_recipe_scripts_are_in_client_overlay(self):
        scripts = ROOT / "server-config/kubejs/server_scripts"
        for path in scripts.glob("*.js"):
            with self.subTest(script=path.name):
                client = ROOT / "client-config/kubejs/server_scripts" / path.name
                self.assertTrue(client.is_file(), f"Missing singleplayer script: {client}")
                self.assertEqual(path.read_bytes(), client.read_bytes())

    def test_datapacks_parse_and_are_deployed(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn(
            "COPY server-config/new-world/datapacks/ /config/new-world/datapacks/",
            dockerfile,
        )
        for pack in (ROOT / "server-config/new-world/datapacks").iterdir():
            if not pack.is_dir():
                continue
            with self.subTest(pack=pack.name):
                metadata = json.loads((pack / "pack.mcmeta").read_text())
                self.assertEqual(metadata["pack"]["pack_format"], 15)
            for path in pack.rglob("*.json"):
                with self.subTest(json=path.relative_to(ROOT)):
                    json.loads(path.read_text())

    def test_compatibility_addons_are_unique_deployable_and_java17(self):
        registered = {"minecraft", "forge"}
        addons = []
        for path in sorted((ROOT / "mods").glob("*.jar")):
            with ZipFile(path) as jar:
                if "META-INF/mods.toml" not in jar.namelist():
                    continue
                metadata = tomllib.loads(jar.read("META-INF/mods.toml").decode())
                for mod in metadata.get("mods", []):
                    mod_id = mod["modId"]
                    self.assertNotIn(mod_id, registered, f"Duplicate mod ID in {path}")
                    registered.add(mod_id)
                    if mod_id.endswith("_compat"):
                        addons.append((path, metadata, mod_id))
        self.assertTrue(addons)
        for path, metadata, mod_id in addons:
            with self.subTest(addon=mod_id), ZipFile(path) as jar:
                client = ROOT / "client-config/mods" / path.name
                self.assertTrue(client.is_file(), f"Missing client addon: {client}")
                self.assertEqual(path.read_bytes(), client.read_bytes())
                self.assertEqual(
                    json.loads(jar.read("pack.mcmeta"))["pack"]["pack_format"], 15
                )
                for dependency in metadata.get("dependencies", {}).get(mod_id, []):
                    if dependency.get("mandatory"):
                        self.assertIn(dependency["modId"], registered)
                for name in jar.namelist():
                    if name.endswith(".class"):
                        magic, _, major = struct.unpack(">IHH", jar.read(name)[:8])
                        self.assertEqual(magic, 0xCAFEBABE)
                        self.assertLessEqual(major, 61, f"{name} requires newer than Java 17")
        self.assertIn("COPY mods/ /mods/", (ROOT / "Dockerfile").read_text())


if __name__ == "__main__":
    unittest.main()
