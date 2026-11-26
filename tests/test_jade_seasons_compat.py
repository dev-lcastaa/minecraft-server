import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
import uuid
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/jade-season-compat"
JAR_NAME = "jade-season-compat-1.20.1-1.0.0.jar"
SEASONS = ROOT / "mods/Ecliptic-Seasons-1.20.1-forge-0.15.5-all.jar"


class JadeSeasonsCompatTest(unittest.TestCase):
    def run_checked(self, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_registry_audit_includes_noncreative_and_new_mod_plants(self):
        server = ROOT / "server-config/kubejs/server_scripts/jade_season_audit.js"
        self.assertEqual(server.read_bytes(), (ROOT / "client-config/kubejs/server_scripts/jade_season_audit.js").read_bytes())
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js needed for KubeJS audit fixture")
        fixture = r"""
const vm = require('node:vm'), fs = require('node:fs'), assert = require('node:assert/strict');
class Plant {}
class Bonemealable {}
class Plain {}
const entries = [new Plant(), new Bonemealable(), new Plant(), new Plain()];
entries.forEach((b,i) => {b.id = ['minecraft:wheat','newmod:hidden_crop','newmod:plant','minecraft:stone'][i]});
let callback;const logs=[];
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'), {
  ServerEvents:{loaded:f=>callback=f}, console:{info:m=>logs.push(m)},
  Java:{loadClass:name=>({
    'net.minecraftforge.registries.ForgeRegistries':{BLOCKS:{getValues:()=>entries,getKey:b=>b.id}},
    'com.teamtea.eclipticseasons.common.core.crop.CropGrowthHandler':{getControlMap:b=>b.id==='minecraft:wheat'?{}:null},
    'net.minecraftforge.common.IPlantable':Plant,
    'net.minecraft.world.level.block.BonemealableBlock':Bonemealable
  })[name]}
});
callback({});
assert.match(logs[0],/1 growth-capable blocks; 2 without configured rules/);
assert.ok(logs[1].includes('newmod:hidden_crop')); assert.ok(logs[1].includes('newmod:plant'));
assert.ok(!logs[1].includes('minecraft:stone'));
"""
        self.run_checked([node, "-e", fixture, str(server)])

    def test_artifact_is_java17_and_does_not_package_api_stubs(self):
        server = ROOT / "mods" / JAR_NAME
        self.assertEqual(server.read_bytes(), (ROOT / "client-config/mods" / JAR_NAME).read_bytes())
        with ZipFile(server) as jar:
            self.assertEqual(json.loads(jar.read("pack.mcmeta"))["pack"]["pack_format"], 15)
            self.assertFalse(any(n.startswith(("net/", "snownee/", "com/")) for n in jar.namelist()))
            classes = [n for n in jar.namelist() if n.endswith(".class")]
            self.assertTrue(classes)
            for name in classes:
                self.assertEqual(int.from_bytes(jar.read(name)[6:8], "big"), 61, name)
            self.assertEqual(jar.read("coremods/jade_seasons.js"), (SOURCE / "coremods/jade_seasons.js").read_bytes())
            self.assertEqual(jar.read("META-INF/compat-source.sha256").decode(),
                             hashlib.sha256((SOURCE / "src/serverfixes/jadeseasons/Compat.java").read_bytes()).hexdigest())

    def test_jade_tooltips_removed(self):
        with ZipFile(ROOT / "mods" / JAR_NAME) as jar:
            self.assertNotIn(b"jade", jar.read("META-INF/mods.toml").replace(b"jade_season_compat", b""))
            for name in jar.namelist():
                if name.endswith(".class"):
                    self.assertNotIn(b"snownee/jade", jar.read(name), name)
            self.assertNotIn(b"snownee", jar.read("coremods/jade_seasons.js"))

    def test_actual_installed_api_and_bytecode_transforms(self):
        classpath = os.environ.get("JADE_SEASONS_TEST_CLASSPATH")
        if not classpath:
            self.skipTest("Set JADE_SEASONS_TEST_CLASSPATH to Nashorn15.4 and ASM9.7.1 jars")
        self.run_checked(["java", "-cp", classpath, str(SOURCE / "BytecodeTest.java"),
                          str(SOURCE / "coremods/jade_seasons.js"), str(SEASONS),
                          str(ROOT / "mods/FarmersDelight-1.20.1-1.3.4.jar")])

    def test_real_compiled_helper_behavior(self):
        spec = importlib.util.spec_from_file_location("jade_build", SOURCE / "build.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        classpath = build.classpath()
        if classpath is None:
            self.skipTest("Forge 1.20.1 SRG libraries needed; set MC_LIBRARIES")
        work = SOURCE / (".test-" + uuid.uuid4().hex)
        work.mkdir()
        try:
            # Compiling against the real SRG Minecraft/Forge and Ecliptic jars verifies every API the helper calls.
            build.compile_to(work, SOURCE / "BehaviorTest.java")
            self.run_checked(["java", "-cp", os.pathsep.join([str(work), classpath]), "BehaviorTest"])
        finally:
            shutil.rmtree(work)


if __name__ == "__main__":
    unittest.main()
