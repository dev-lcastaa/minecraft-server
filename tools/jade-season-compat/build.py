"""Compile against installed Jade APIs; compile-only Minecraft stubs are never packaged."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import uuid
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
JAR_NAME = "jade-season-compat-1.20.1-1.0.0.jar"
SCRIPT = Path("kubejs/server_scripts/jade_season_audit.js")

STUBS = {
    "net.minecraft.nbt.CompoundTag": "public class CompoundTag { public void m_128359_(String k,String v) {} public void m_128405_(String k,int v) {} public String m_128461_(String k) {return \"\";} }",
    "net.minecraft.network.chat.Component": "public interface Component { static MutableComponent m_237113_(String s) {return null;} }",
    "net.minecraft.network.chat.MutableComponent": "public class MutableComponent implements Component {}",
    "net.minecraft.resources.ResourceLocation": "public class ResourceLocation { public ResourceLocation(String a,String b) {} }",
    "net.minecraft.world.level.block.Block": "public class Block {}",
    "net.minecraft.world.level.block.entity.BlockEntity": "public class BlockEntity {}",
    "net.minecraft.world.level.block.state.BlockState": "public class BlockState {}",
    "net.minecraft.world.entity.Entity": "public class Entity {}",
    "net.minecraft.world.entity.player.Player": "public class Player extends net.minecraft.world.entity.Entity {}",
    "net.minecraft.world.level.Level": "public class Level {}",
    "net.minecraft.core.BlockPos": "public class BlockPos {}",
    "net.minecraft.world.phys.HitResult": "public class HitResult {}",
    "net.minecraft.world.phys.BlockHitResult": "public class BlockHitResult extends HitResult {}",
    "net.minecraft.world.phys.EntityHitResult": "public class EntityHitResult extends HitResult {}",
    "net.minecraft.world.item.ItemStack": "public class ItemStack {}",
    "net.minecraftforge.fml.common.Mod": "@java.lang.annotation.Retention(java.lang.annotation.RetentionPolicy.RUNTIME) public @interface Mod { String value(); }",
}

def build():
    work = SOURCE / (".build-" + uuid.uuid4().hex)
    work.mkdir()
    try:
        files = []
        for name, body in STUBS.items():
            path = work / "stubs" / (name.replace(".", "/") + ".java")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("package " + name.rsplit(".", 1)[0] + "; " + body + "\n")
            files.append(str(path))
        classes = work / "classes"
        classes.mkdir(exist_ok=True)
        jade, = (ROOT / "mods").glob("Jade-1.20.1-Forge-11.13.3.jar")
        subprocess.run(["java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "-source", "17", "-target", "17",
                        "-cp", str(jade), "-d", str(classes), *files,
                        *map(str, (SOURCE / "src").rglob("*.java"))], check=True, cwd=ROOT)
        entries = {p.relative_to(SOURCE).as_posix(): p.read_bytes()
                   for folder in ("META-INF", "coremods", "assets", "data")
                   for p in (SOURCE / folder).rglob("*") if p.is_file()}
        entries["pack.mcmeta"] = (SOURCE / "pack.mcmeta").read_bytes()
        entries["META-INF/compat-source.sha256"] = hashlib.sha256(
            (SOURCE / "src/serverfixes/jadeseasons/Compat.java").read_bytes()).hexdigest().encode()
        entries.update({p.relative_to(classes).as_posix(): p.read_bytes()
                        for p in (classes / "serverfixes").rglob("*.class")})
        artifact = work / JAR_NAME
        with ZipFile(artifact, "w", compression=ZIP_DEFLATED) as jar:
            for name, data in sorted(entries.items()):
                info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                jar.writestr(info, data)
        destination = ROOT / "mods" / JAR_NAME
        artifact.replace(destination)
        client = ROOT / "client-config/mods" / JAR_NAME
        client.parent.mkdir(parents=True, exist_ok=True)
        client_artifact = work / ("client-" + JAR_NAME)
        client_artifact.write_bytes(destination.read_bytes())
        client_artifact.replace(client)
        client_script = ROOT / "client-config" / SCRIPT
        client_script.parent.mkdir(parents=True, exist_ok=True)
        script_artifact = work / SCRIPT.name
        script_artifact.write_bytes((ROOT / "server-config" / SCRIPT).read_bytes())
        script_artifact.replace(client_script)
        print(f"Built and mirrored {JAR_NAME}")
    finally:
        shutil.rmtree(work)

if __name__ == "__main__":
    build()
