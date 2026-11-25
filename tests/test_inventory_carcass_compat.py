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
SOURCE = ROOT / "tools/inventory-carcass-compat"
JAR = "inventory-carcass-compat-1.20.1-1.0.0.jar"
SCRIPT = Path("kubejs/startup_scripts/inventory_carcass_stacks.js")


class InventoryCarcassCompatTest(unittest.TestCase):
    def test_addon_packaging_and_mirrored_overlay(self):
        server = ROOT / "mods" / JAR
        self.assertEqual(server.read_bytes(), (ROOT / "client-config/mods" / JAR).read_bytes())
        with ZipFile(server) as jar:
            metadata = tomllib.loads(jar.read("META-INF/mods.toml").decode())
            self.assertEqual(metadata["modLoader"], "lowcodefml")
            dependencies = {d["modId"]: d for d in metadata["dependencies"]["inventory_carcass_compat"]}
            self.assertEqual(dependencies["butchersdelight"]["versionRange"], "[1.20.12.1.0]")
            self.assertEqual(dependencies["betterinventory"]["versionRange"], "[2.1.0]")
            self.assertEqual(dependencies["carryon"]["versionRange"], "[2.1.2.7]")
            self.assertEqual(json.loads(jar.read("pack.mcmeta"))["pack"]["pack_format"], 15)
            for folder in ("META-INF", "coremods"):
                for path in (SOURCE / folder).rglob("*"):
                    if path.is_file():
                        self.assertEqual(jar.read(path.relative_to(SOURCE).as_posix()), path.read_bytes())
            helper = jar.read("net/serverfixes/inventory/CarryOnPermissionProbeEvent.class")
            self.assertEqual(struct.unpack(">H", helper[6:8])[0], 61, "Helper must run on Java 17")
            self.assertFalse(any(n.startswith(("net/minecraft/", "net/minecraftforge/")) for n in jar.namelist()))
        self.assertEqual(
            (ROOT / "server-config" / SCRIPT).read_bytes(),
            (ROOT / "client-config" / SCRIPT).read_bytes(),
        )

    def test_stack_script_executes_against_installed_item_ids(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is required for the startup event fixture")
        with ZipFile(ROOT / "mods/Butchersdelight beta 1.20.1 2.1.0.jar") as jar:
            ids = [
                "butchersdelight:" + Path(n).stem for n in jar.namelist()
                if n.startswith("assets/butchersdelight/models/item/") and n.endswith(".json")
            ]
        expected = [i for i in ids if i.split(":")[1].startswith(("dead", "hooked", "hoked", "roasted"))]
        self.assertEqual(len(expected), 87)
        fixture = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const ids = JSON.parse(process.argv[1]);
const items = Object.fromEntries([...ids, 'minecraft:chicken', 'new_mod:dead_animal']
  .map(id => [id, {maxStackSize: 8}]));
vm.runInNewContext(fs.readFileSync(process.argv[2], 'utf8'), {
  ItemEvents: {modification: callback => callback({modify: (pattern, change) => {
    Object.keys(items).filter(id => pattern.test(id)).forEach(id => change(items[id]));
  }})}
});
let changed = 0;
for (const [id, item] of Object.entries(items)) {
  const carcass = /^butchersdelight:(dead|hooked|hoked|roasted)/.test(id);
  assert.equal(item.maxStackSize, carcass ? 16 : 8, id);
  if (carcass) changed++;
}
assert.equal(changed, 87);
"""
        subprocess.run(
            [node, "-e", fixture, json.dumps(ids), str(ROOT / "server-config" / SCRIPT)],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )

    def test_every_installed_butcher_break_callback_is_guarded(self):
        script = (SOURCE / "coremods/inventory_carcass.js").read_text()
        with ZipFile(ROOT / "mods/Butchersdelight beta 1.20.1 2.1.0.jar") as jar:
            callbacks = [
                Path(name).stem.removesuffix("DestroyedByPlayerProcedure")
                for name in jar.namelist()
                if name.endswith(".class") and b"BlockEvent$BreakEvent" in jar.read(name)
            ]
        self.assertEqual(len(callbacks), 11)
        for callback in callbacks:
            self.assertIn("'" + callback + "'", script)

    def test_actual_installed_bytecode_and_serialized_inventory(self):
        classpath = os.environ.get("INVENTORY_CARCASS_TEST_CLASSPATH")
        if not classpath:
            self.skipTest("Set INVENTORY_CARCASS_TEST_CLASSPATH to Nashorn and ASM JARs")
        result = subprocess.run(
            [os.environ.get("JAVA", "java"), "-cp", classpath,
             str(SOURCE / "BytecodeTest.java"), str(ROOT)],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("inventory/carcass bytecode cases passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
