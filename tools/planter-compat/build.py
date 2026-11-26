"""Build planter-compat; compile-only Minecraft/Forge stubs (SRG names) are never packaged."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import uuid
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
JAR_NAME = "planter-compat-1.20.1-1.0.0.jar"
HELPER = SOURCE / "src/serverfixes/plantercompat/Compat.java"

# Signatures mirror Forge 1.20.1-47.x production (SRG) classes; tests/test_planter_compat.py
# recompiles the helper against the real jars and compares every member reference.
STUBS = {
    "net.minecraft.core.BlockPos": "public class BlockPos { public BlockPos m_7495_() {return this;} }",
    "net.minecraft.resources.ResourceLocation": "public class ResourceLocation { public ResourceLocation(String a,String b) {} }",
    "net.minecraft.resources.ResourceKey": "public class ResourceKey<T> {}",
    "net.minecraft.core.Registry": "public interface Registry<T> {}",
    "net.minecraft.core.registries.Registries":
        "public class Registries { public static final net.minecraft.resources.ResourceKey<net.minecraft.core.Registry<net.minecraft.world.level.block.Block>> f_256747_ = null; }",
    "net.minecraft.tags.TagKey":
        "public class TagKey<T> { public static <T> TagKey<T> m_203882_(net.minecraft.resources.ResourceKey<? extends net.minecraft.core.Registry<T>> k, net.minecraft.resources.ResourceLocation l) {return null;} }",
    "net.minecraft.world.level.LevelReader":
        "public interface LevelReader { net.minecraft.world.level.block.state.BlockState m_8055_(net.minecraft.core.BlockPos p); }",
    "net.minecraft.world.level.Level":
        "public abstract class Level implements LevelReader { public boolean m_46597_(net.minecraft.core.BlockPos p, net.minecraft.world.level.block.state.BlockState s) {return false;} }",
    "net.minecraft.world.level.block.Block":
        "public class Block { public final net.minecraft.world.level.block.state.BlockState m_49966_() {return null;} }",
    "net.minecraft.world.level.block.Blocks":
        "public class Blocks { public static final Block f_50016_ = null, f_50691_ = null, f_50700_ = null; }",
    "net.minecraft.world.level.block.BonemealableBlock": "public interface BonemealableBlock {}",
    "net.minecraft.world.level.block.GrowingPlantBlock": "public abstract class GrowingPlantBlock extends Block {}",
    "net.minecraft.world.level.block.MultifaceBlock": "public abstract class MultifaceBlock extends Block {}",
    "net.minecraft.world.level.block.state.properties.Property":
        "public abstract class Property<T extends Comparable<T>> { public String m_61708_() {return null;} }",
    "net.minecraft.world.level.block.state.BlockBehaviour":
        "public abstract class BlockBehaviour { public abstract static class BlockStateBase {"
        " public net.minecraft.world.level.block.Block m_60734_() {return null;}"
        " public boolean m_204336_(net.minecraft.tags.TagKey<net.minecraft.world.level.block.Block> t) {return false;}"
        " public boolean m_60713_(net.minecraft.world.level.block.Block b) {return false;}"
        " public boolean m_60710_(net.minecraft.world.level.LevelReader l, net.minecraft.core.BlockPos p) {return false;}"
        " public java.util.Collection<net.minecraft.world.level.block.state.properties.Property<?>> m_61147_() {return null;}"
        " public <T extends Comparable<T>> T m_61143_(net.minecraft.world.level.block.state.properties.Property<T> p) {return null;} } }",
    "net.minecraft.world.level.block.state.BlockState":
        "public class BlockState extends BlockBehaviour.BlockStateBase {}",
    "net.minecraftforge.common.IPlantable": "public interface IPlantable {}",
    "net.minecraftforge.registries.IForgeRegistry":
        "public interface IForgeRegistry<V> { V getValue(net.minecraft.resources.ResourceLocation key); }",
    "net.minecraftforge.registries.ForgeRegistries":
        "public class ForgeRegistries { public static final IForgeRegistry<net.minecraft.world.level.block.Block> BLOCKS = null; }",
    "net.minecraftforge.fml.common.Mod":
        "@java.lang.annotation.Retention(java.lang.annotation.RetentionPolicy.RUNTIME) public @interface Mod { String value(); }",
}


def write_stubs(folder, stubs):
    files = []
    for name, body in stubs.items():
        path = folder / (name.replace(".", "/") + ".java")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("package " + name.rsplit(".", 1)[0] + "; " + body + "\n")
        files.append(str(path))
    return files


def build():
    work = SOURCE / (".build-" + uuid.uuid4().hex)
    work.mkdir()
    try:
        files = write_stubs(work / "stubs", STUBS)
        classes = work / "classes"
        classes.mkdir()
        subprocess.run(["java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "-source", "17", "-target", "17", "-nowarn",
                        "-d", str(classes), *files, str(HELPER)], check=True, cwd=ROOT)
        entries = {p.relative_to(SOURCE).as_posix(): p.read_bytes()
                   for folder in ("META-INF", "coremods", "data")
                   for p in (SOURCE / folder).rglob("*") if p.is_file()}
        entries["pack.mcmeta"] = (SOURCE / "pack.mcmeta").read_bytes()
        entries["META-INF/compat-source.sha256"] = hashlib.sha256(HELPER.read_bytes()).hexdigest().encode()
        entries.update({p.relative_to(classes).as_posix(): p.read_bytes()
                        for p in (classes / "serverfixes").rglob("*.class")})
        artifact = work / JAR_NAME
        with ZipFile(artifact, "w", compression=ZIP_DEFLATED) as jar:
            for name, data in sorted(entries.items()):
                info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                jar.writestr(info, data)
        server = ROOT / "mods" / JAR_NAME
        client = ROOT / "client-config/mods" / JAR_NAME
        client.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, work / ("client-" + JAR_NAME))
        artifact.replace(server)
        (work / ("client-" + JAR_NAME)).replace(client)
        print(f"Built and mirrored {JAR_NAME}")
    finally:
        shutil.rmtree(work)


if __name__ == "__main__":
    build()
