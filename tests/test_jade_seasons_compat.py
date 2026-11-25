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
JADE = ROOT / "mods/Jade-1.20.1-Forge-11.13.3.jar"
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

    def test_actual_installed_api_and_bytecode_transforms(self):
        classpath = os.environ.get("JADE_SEASONS_TEST_CLASSPATH")
        if not classpath:
            self.skipTest("Set JADE_SEASONS_TEST_CLASSPATH to Nashorn15.4 and ASM9.7.1 jars")
        self.run_checked(["java", "-cp", classpath, str(SOURCE / "BytecodeTest.java"),
                          str(SOURCE / "coremods/jade_seasons.js"), str(JADE), str(SEASONS),
                          str(ROOT / "mods/FarmersDelight-1.20.1-1.3.4.jar")])

    def test_real_compiled_helper_behavior(self):
        spec = importlib.util.spec_from_file_location("jade_build", SOURCE / "build.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        stubs = dict(build.STUBS)
        stubs.update({
            "net.minecraft.network.chat.Component":
                "public interface Component { static MutableComponent m_237113_(String s){return new MutableComponent(s);} public static class Serializer { public static String m_130703_(Component c){return ((MutableComponent)c).text;} public static Component m_130691_(String s){return new MutableComponent(s);} } }",
            "net.minecraft.network.chat.MutableComponent":
                "public class MutableComponent implements Component {public final String text; public MutableComponent(String s){text=s;} }",
            "net.minecraft.world.entity.Entity":
                "public class Entity {public Object m_6095_(){return \"entity.test.mob\";} }",
            "net.minecraft.world.entity.LivingEntity":
                "public class LivingEntity extends Entity {public float m_21223_(){return 8;} public float m_21233_(){return 20;} public int m_21230_(){return 3;} }",
            "net.minecraft.world.entity.AgeableMob":
                "public class AgeableMob extends LivingEntity {public int m_146764_(){return -40;} }",
            "net.minecraft.world.entity.TamableAnimal":
                "public class TamableAnimal extends AgeableMob {public boolean m_21824_(){return true;} }",
            "net.minecraft.nbt.CompoundTag":
                "public class CompoundTag { public final java.util.Map<String,Object> data=new java.util.HashMap<>(); public void m_128359_(String k,String v){data.put(k,v);} public void m_128405_(String k,int v){data.put(k,v);} public String m_128461_(String k){return (String)data.getOrDefault(k,\"\");} public int m_128451_(String k){return (Integer)data.getOrDefault(k,0);} }",
            "net.minecraft.core.BlockPos":
                "public class BlockPos { public int m_123341_(){return 11;} public int m_123342_(){return 64;} public int m_123343_(){return -7;} }",
            "net.minecraft.core.Direction": "public enum Direction { UP }",
            "net.minecraft.network.FriendlyByteBuf": "public class FriendlyByteBuf {}",
            "net.minecraft.world.level.block.BonemealableBlock":
                "public interface BonemealableBlock { boolean m_7370_(net.minecraft.world.level.Level l, net.minecraft.core.BlockPos p, net.minecraft.world.level.block.state.BlockState s, boolean client); }",
            "net.minecraft.world.level.block.Block":
                "public class Block implements BonemealableBlock { public boolean valid=true; public int age; public void fertileGrowth(){if(!valid)throw new AssertionError();age++;} public boolean m_7370_(net.minecraft.world.level.Level l,net.minecraft.core.BlockPos p,net.minecraft.world.level.block.state.BlockState s,boolean c) {return valid;} }",
            "net.minecraft.world.level.block.SaplingBlock": "public class SaplingBlock extends Block {}",
            "net.minecraft.world.level.block.state.BlockState":
                "public class BlockState { public final net.minecraft.world.level.block.Block block=new net.minecraft.world.level.block.Block(); public Object m_60734_() {return block;} }",
            "net.minecraft.util.RandomSource":
                "public class RandomSource { public int roll; public int m_188503_(int bound) { if(bound!=4) throw new AssertionError(\"Wrong probability\");return roll;} }",
            "net.minecraft.world.level.Level":
                "public class Level { public static boolean seasonMismatch=true,controlled=true; public boolean client; public final net.minecraft.util.RandomSource random=new net.minecraft.util.RandomSource(); public Object m_213780_() {return random;} public boolean m_5776_() {return client;} }",
            "com.teamtea.eclipticseasons.api.EclipticSeasonsApi":
                # Mirrors Ecliptic Seasons: a public interface whose instance is a package-private anonymous class.
                "public interface EclipticSeasonsApi { boolean isSeasonEnabled(net.minecraft.world.level.Level l); String getSeason(net.minecraft.world.level.Level l); String getSolarTerm(net.minecraft.world.level.Level l); static EclipticSeasonsApi getInstance(){return com.teamtea.eclipticseasons.api.util.EclipticUtil.INSTANCE;} }",
            "com.teamtea.eclipticseasons.api.util.EclipticUtil":
                "public class EclipticUtil { public static final com.teamtea.eclipticseasons.api.EclipticSeasonsApi INSTANCE = new com.teamtea.eclipticseasons.api.EclipticSeasonsApi() { public boolean isSeasonEnabled(net.minecraft.world.level.Level l){return true;} public String getSeason(net.minecraft.world.level.Level l){return \"WINTER\";} public String getSolarTerm(net.minecraft.world.level.Level l){return \"GREATER_COLD\";} }; }",
            "com.teamtea.eclipticseasons.common.item.info.GrowthInfoResolver":
                "public class GrowthInfoResolver { public static Report resolve(net.minecraft.world.level.Level l, net.minecraft.core.BlockPos p, net.minecraft.world.level.block.state.BlockState s) {return l.controlled?new Report():null;} public static class Report {public boolean needsSeasonCore(){return net.minecraft.world.level.Level.seasonMismatch;} public float growChance(){return 0;} public boolean humidityMismatch(){return false;} public int greenhouseLevel(){return 3;} } }",
            "com.teamtea.eclipticseasons.common.core.crop.CropGrowthHandler":
                "public class CropGrowthHandler { public static java.util.List<Object> appendInfo(net.minecraft.world.level.Level l,net.minecraft.world.level.block.state.BlockState s){return java.util.List.of(net.minecraft.network.chat.Component.m_237113_(\"Preferred seasons: SUMMER\"));} }",
        })
        work = SOURCE / (".test-" + uuid.uuid4().hex)
        work.mkdir()
        try:
            files = []
            for name, body in stubs.items():
                path = work / (name.replace(".", "/") + ".java")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("package " + name.rsplit(".", 1)[0] + "; " + body)
                files.append(str(path))
            self.run_checked(["java", "-m", "jdk.compiler/com.sun.tools.javac.Main",
                              "-cp", str(JADE), "-d", str(work), *files,
                              str(SOURCE / "src/serverfixes/jadeseasons/Compat.java"),
                              str(SOURCE / "BehaviorTest.java")])
            self.run_checked(["java", "-cp", os.pathsep.join([str(work), str(JADE)]), "BehaviorTest"])
        finally:
            shutil.rmtree(work)


if __name__ == "__main__":
    unittest.main()
