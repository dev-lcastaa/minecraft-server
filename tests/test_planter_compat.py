import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tomllib
import unittest
import uuid
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/planter-compat"
JAR_NAME = "planter-compat-1.20.1-1.0.0.jar"
JAR = ROOT / "mods" / JAR_NAME
SUPPLEMENTARIES = ROOT / "mods/supplementaries-1.20-3.1.44-forge.jar"
FARMERS_DELIGHT = ROOT / "mods/FarmersDelight-1.20.1-1.3.4.jar"
NETHERS_DELIGHT = ROOT / "mods/MyNethersDelight-1.20.1-1.10.4-backport.1.jar"
COLONY_TAG = "data/farmersdelight/tags/blocks/mushroom_colony_growable_on.json"
LIBRARIES = Path(os.environ.get("PLANTER_FORGE_LIBRARIES",
                                Path.home() / ".local/share/ModrinthApp/meta/libraries"))

BEHAVIOR_STUBS = {
    "net.minecraft.core.BlockPos":
        "public record BlockPos(int x, int y, int z) { public BlockPos m_7495_() {return new BlockPos(x, y - 1, z);} }",
    "net.minecraft.resources.ResourceLocation":
        "public class ResourceLocation { final String id; public ResourceLocation(String a,String b) {id=a+\":\"+b;} public String toString() {return id;} }",
    "net.minecraft.resources.ResourceKey": "public class ResourceKey<T> {}",
    "net.minecraft.core.Registry": "public interface Registry<T> {}",
    "net.minecraft.core.registries.Registries":
        "public class Registries { public static final net.minecraft.resources.ResourceKey<net.minecraft.core.Registry<net.minecraft.world.level.block.Block>> f_256747_ = new net.minecraft.resources.ResourceKey<>(); }",
    "net.minecraft.tags.TagKey":
        "public class TagKey<T> { public final String id; TagKey(String id) {this.id=id;} public static <T> TagKey<T> m_203882_(net.minecraft.resources.ResourceKey<? extends net.minecraft.core.Registry<T>> k, net.minecraft.resources.ResourceLocation l) {return new TagKey<>(l.toString());} }",
    "net.minecraft.world.level.LevelReader":
        "public interface LevelReader { net.minecraft.world.level.block.state.BlockState m_8055_(net.minecraft.core.BlockPos p); }",
    "net.minecraft.world.level.Level":
        "public class Level implements LevelReader { public final java.util.Map<net.minecraft.core.BlockPos, net.minecraft.world.level.block.state.BlockState> states = new java.util.HashMap<>();"
        " public net.minecraft.world.level.block.state.BlockState m_8055_(net.minecraft.core.BlockPos p) {return states.getOrDefault(p, net.minecraft.world.level.block.Blocks.f_50016_.m_49966_());}"
        " public boolean m_46597_(net.minecraft.core.BlockPos p, net.minecraft.world.level.block.state.BlockState s) {states.put(p, s); return true;} }",
    "net.minecraft.world.level.block.Block":
        "public class Block { public final java.util.Set<String> tags = new java.util.HashSet<>(); public boolean survives = true;"
        " private final net.minecraft.world.level.block.state.BlockState state = new net.minecraft.world.level.block.state.BlockState(this);"
        " public final net.minecraft.world.level.block.state.BlockState m_49966_() {return state;} }",
    "net.minecraft.world.level.block.Blocks":
        "public class Blocks { public static final Block f_50016_ = new Block(), f_50691_ = new Block(), f_50700_ = new Block(), f_50072_ = new Block(); }",
    "net.minecraft.world.level.block.BonemealableBlock": "public interface BonemealableBlock {}",
    "net.minecraft.world.level.block.GrowingPlantBlock": "public class GrowingPlantBlock extends Block {}",
    "net.minecraft.world.level.block.MultifaceBlock": "public class MultifaceBlock extends Block {}",
    "net.minecraft.world.level.block.state.properties.Property":
        "public class Property<T extends Comparable<T>> { final String name; public Property(String name) {this.name=name;} public String m_61708_() {return name;} }",
    "net.minecraft.world.level.block.state.BlockBehaviour":
        "public abstract class BlockBehaviour { public abstract static class BlockStateBase {"
        " protected final net.minecraft.world.level.block.Block block;"
        " protected final java.util.Map<net.minecraft.world.level.block.state.properties.Property<?>, Comparable<?>> values = new java.util.LinkedHashMap<>();"
        " protected BlockStateBase(net.minecraft.world.level.block.Block b) {block=b;}"
        " public net.minecraft.world.level.block.Block m_60734_() {return block;}"
        " public boolean m_204336_(net.minecraft.tags.TagKey<net.minecraft.world.level.block.Block> t) {return block.tags.contains(t.id);}"
        " public boolean m_60713_(net.minecraft.world.level.block.Block b) {return block==b;}"
        " public boolean m_60710_(net.minecraft.world.level.LevelReader l, net.minecraft.core.BlockPos p) {return block.survives;}"
        " public java.util.Collection<net.minecraft.world.level.block.state.properties.Property<?>> m_61147_() {return values.keySet();}"
        " @SuppressWarnings(\"unchecked\") public <T extends Comparable<T>> T m_61143_(net.minecraft.world.level.block.state.properties.Property<T> p) {return (T) values.get(p);} } }",
    "net.minecraft.world.level.block.state.BlockState":
        "public class BlockState extends BlockBehaviour.BlockStateBase { public BlockState(net.minecraft.world.level.block.Block b) {super(b);}"
        " public <T extends Comparable<T>> BlockState with(net.minecraft.world.level.block.state.properties.Property<T> p, T v) {BlockState s = new BlockState(block); s.values.putAll(values); s.values.put(p, v); return s;} }",
    "net.minecraftforge.common.IPlantable": "public interface IPlantable {}",
    "net.minecraftforge.registries.IForgeRegistry":
        "public interface IForgeRegistry<V> { V getValue(net.minecraft.resources.ResourceLocation key); }",
    "net.minecraftforge.registries.ForgeRegistries":
        "public class ForgeRegistries { public static final java.util.Map<String, net.minecraft.world.level.block.Block> VALUES = new java.util.HashMap<>();"
        " public static final IForgeRegistry<net.minecraft.world.level.block.Block> BLOCKS = key -> VALUES.getOrDefault(key.toString(), net.minecraft.world.level.block.Blocks.f_50016_); }",
    "net.minecraftforge.fml.common.Mod":
        "@java.lang.annotation.Retention(java.lang.annotation.RetentionPolicy.RUNTIME) public @interface Mod { String value(); }",
    "net.mehvahdjukaar.supplementaries.common.block.blocks.PlanterBlock":
        "public class PlanterBlock extends net.minecraft.world.level.block.Block {}",
}


def member_refs(data):
    """Field/method references (kind, owner, name, descriptor) from a class file's constant pool."""
    count = struct.unpack(">H", data[8:10])[0]
    pool, index, slot = [None] * count, 10, 1
    while slot < count:
        tag = data[index]
        index += 1
        if tag == 1:
            length = struct.unpack(">H", data[index:index + 2])[0]
            pool[slot] = data[index + 2:index + 2 + length].decode()
            index += 2 + length
        elif tag in (7, 8, 16, 19, 20):
            pool[slot] = struct.unpack(">H", data[index:index + 2])[0]
            index += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            pool[slot] = (tag,) + struct.unpack(">HH", data[index:index + 4])
            index += 4
        elif tag in (3, 4):
            index += 4
        elif tag in (5, 6):
            index += 8
            slot += 1
        elif tag == 15:
            index += 3
        else:
            raise ValueError(tag)
        slot += 1
    refs = set()
    for entry in pool:
        if isinstance(entry, tuple) and entry[0] in (9, 10, 11):
            name_type = pool[entry[2]]
            refs.add((entry[0], pool[pool[entry[1]]], pool[name_type[1]], pool[name_type[2]]))
    return refs


def tag_ids(data):
    return {value if isinstance(value, str) else value["id"] for value in json.loads(data)["values"]}


class PlanterCompatTest(unittest.TestCase):
    def run_checked(self, command):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def libraries(self, *patterns):
        found = []
        for pattern in patterns:
            matches = sorted(LIBRARIES.glob(pattern))
            if not matches:
                self.skipTest(f"Forge 1.20.1 libraries not found under {LIBRARIES} ({pattern}); "
                              "set PLANTER_FORGE_LIBRARIES to a launcher libraries folder")
            found.append(matches[-1])
        return found

    def test_artifact_matches_sources_and_is_mirrored_for_clients(self):
        self.assertEqual(JAR.read_bytes(), (ROOT / "client-config/mods" / JAR_NAME).read_bytes())
        with ZipFile(JAR) as jar:
            names = set(jar.namelist())
            for folder in ("META-INF", "coremods", "data"):
                for path in (SOURCE / folder).rglob("*"):
                    if path.is_file():
                        self.assertEqual(jar.read(path.relative_to(SOURCE).as_posix()), path.read_bytes(), path)
            self.assertEqual(jar.read("META-INF/compat-source.sha256").decode(), hashlib.sha256(
                (SOURCE / "src/serverfixes/plantercompat/Compat.java").read_bytes()).hexdigest())
            self.assertFalse(any(n.startswith(("net/", "com/", "vectorwing/")) for n in names), "stubs packaged")
            classes = [n for n in names if n.endswith(".class")]
            self.assertIn("serverfixes/plantercompat/Compat.class", classes)
            for name in classes:
                self.assertEqual(struct.unpack(">H", jar.read(name)[6:8])[0], 61, name)
            metadata = tomllib.loads(jar.read("META-INF/mods.toml").decode())
            self.assertEqual(metadata["mods"][0]["modId"], "planter_compat")
            dependencies = {d["modId"]: d for d in metadata["dependencies"]["planter_compat"]}
            self.assertTrue(dependencies["supplementaries"]["mandatory"])
            self.assertTrue(all(d["side"] == "BOTH" for d in dependencies.values()))
            self.assertEqual(json.loads(jar.read("META-INF/coremods.json")),
                             {"planter_compat": "coremods/planter_compat.js"})
        self.assertIn(f"mods/{JAR_NAME}", (ROOT / "client-config/README.md").read_text())

    def test_colony_growth_soil_includes_the_registered_planter(self):
        with ZipFile(SUPPLEMENTARIES) as jar:
            names = set(jar.namelist())
            # With Farmer's Delight installed, Supplementaries registers its rich planter as plain "planter".
            self.assertIn("assets/supplementaries/blockstates/planter.json", names)
            self.assertNotIn("assets/supplementaries/blockstates/planter_rich.json", names)
            installed = tag_ids(jar.read(COLONY_TAG))
        for mod in (FARMERS_DELIGHT, NETHERS_DELIGHT):
            with ZipFile(mod) as jar:
                installed |= tag_ids(jar.read(COLONY_TAG))
        self.assertIn("supplementaries:planter_rich", installed)
        self.assertNotIn("supplementaries:planter", installed)
        with ZipFile(JAR) as jar:
            self.assertEqual(tag_ids(jar.read(COLONY_TAG)), {"supplementaries:planter"})
            self.assertIn("#supplementaries:planters", tag_ids(jar.read("data/planter_compat/tags/blocks/planters.json")))
        with ZipFile(NETHERS_DELIGHT) as jar:
            registry = jar.read("com/soytutta/mynethersdelight/common/registry/MNDBlocks.class")
        helper = (SOURCE / "src/serverfixes/plantercompat/Compat.java").read_text()
        for colony in (b"crimson_fungus_colony", b"warped_fungus_colony"):
            self.assertIn(colony, registry)
            self.assertIn('"mynethersdelight", "%s"' % colony.decode(), helper)

    def test_helper_behavior(self):
        work = SOURCE / (".test-" + uuid.uuid4().hex)
        work.mkdir()
        try:
            files = []
            for name, body in BEHAVIOR_STUBS.items():
                path = work / "src" / (name.replace(".", "/") + ".java")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("package " + name.rsplit(".", 1)[0] + "; " + body)
                files.append(str(path))
            self.run_checked(["java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "-nowarn", "-d", str(work),
                              *files, str(SOURCE / "src/serverfixes/plantercompat/Compat.java"),
                              str(SOURCE / "BehaviorTest.java")])
            self.assertIn("Planter helper behavior tests passed",
                          self.run_checked(["java", "-cp", str(work), "BehaviorTest"]))
        finally:
            shutil.rmtree(work)

    def test_packaged_helper_links_against_real_forge_classes(self):
        forge, vanilla = self.libraries("net/minecraftforge/forge/1.20.1-*/forge-1.20.1-*-client.jar",
                                        "net/minecraft/client/1.20.1-*/client-1.20.1-*-srg.jar")
        classpath = [forge, vanilla] + [p for p in LIBRARIES.rglob("*.jar") if p not in (forge, vanilla)]
        work = SOURCE / (".test-" + uuid.uuid4().hex)
        work.mkdir()
        try:
            self.run_checked(["java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "-source", "17", "-target", "17",
                              "-nowarn", "-proc:none", "-cp", os.pathsep.join(map(str, classpath)), "-d", str(work),
                              str(SOURCE / "src/serverfixes/plantercompat/Compat.java")])
            with ZipFile(JAR) as jar:
                for name in ("Compat.class", "Compat$1.class"):
                    real = member_refs((work / "serverfixes/plantercompat" / name).read_bytes())
                    packaged = member_refs(jar.read("serverfixes/plantercompat/" + name))
                    self.assertEqual(packaged, real, f"stub-built {name} references differ from real SRG classes")
        finally:
            shutil.rmtree(work)

    def test_coremod_transforms_installed_bytecode(self):
        forge, nashorn = self.libraries("net/minecraftforge/forge/1.20.1-*/forge-1.20.1-*-client.jar",
                                        "org/openjdk/nashorn/nashorn-core/15.*/nashorn-core-*.jar")
        asm = [self.libraries(f"org/ow2/asm/{part}/9.*/{part}-9.*.jar")[0]
               for part in ("asm", "asm-tree", "asm-analysis", "asm-commons", "asm-util")]
        output = self.run_checked([
            "java", "-cp", os.pathsep.join(map(str, [nashorn, *asm])), str(SOURCE / "BytecodeTest.java"),
            str(SOURCE / "coremods/planter_compat.js"), str(forge), str(FARMERS_DELIGHT),
            str(ROOT / "mods/ColdSweat-2.4.5.jar"), str(ROOT / "mods/Oh-The-Biomes-Weve-Gone-Forge-1.8.2.jar"),
            str(JAR), str(SUPPLEMENTARIES)])
        self.assertIn("Planter coremod bytecode tests passed", output)


if __name__ == "__main__":
    unittest.main()
