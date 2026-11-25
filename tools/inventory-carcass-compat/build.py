from pathlib import Path
import shutil
import subprocess
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
JAR_NAME = "inventory-carcass-compat-1.20.1-1.0.0.jar"
SCRIPT = Path("kubejs/startup_scripts/inventory_carcass_stacks.js")


def build():
    work = SOURCE / (".build-" + uuid4().hex)
    work.mkdir()
    try:
        api = {
            "net.minecraft.core.BlockPos": "public class BlockPos {}",
            "net.minecraft.world.entity.player.Player": "public class Player {}",
            "net.minecraft.world.level.Level": "public class Level {}",
            "net.minecraft.world.level.block.state.BlockState": "public class BlockState {}",
            "net.minecraftforge.event.level.BlockEvent": """
                public class BlockEvent {
                    public static class BreakEvent {
                        public BreakEvent(net.minecraft.world.level.Level level,
                            net.minecraft.core.BlockPos pos,
                            net.minecraft.world.level.block.state.BlockState state,
                            net.minecraft.world.entity.player.Player player) {}
                    }
                }
            """,
        }
        sources = []
        for name, body in api.items():
            path = work / (name.replace(".", "/") + ".java")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("package " + name.rsplit(".", 1)[0] + ";\n" + body)
            sources.append(str(path))
        sources.extend(str(path) for path in (SOURCE / "src").rglob("*.java"))
        compiler = ["java", "-m", "jdk.compiler/com.sun.tools.javac.Main"]
        output = ["-d", str(work), *sources]
        result = subprocess.run(
            [*compiler, "--release", "17", *output], cwd=ROOT, capture_output=True, text=True,
        )
        if result.returncode and "release version 17 not supported" in result.stderr:
            # The local reduced Java 25 runtime lacks ct.sym; this helper uses only our API stubs.
            print("No Java 17 ct.sym; compiling the constructor-only helper with source/target 17")
            subprocess.run(
                [*compiler, "-source", "17", "-target", "17", *output], cwd=ROOT, check=True,
            )
        elif result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        entries = {Path("pack.mcmeta"): (SOURCE / "pack.mcmeta").read_bytes()}
        for folder in ("META-INF", "coremods"):
            entries.update({
                path.relative_to(SOURCE): path.read_bytes()
                for path in (SOURCE / folder).rglob("*") if path.is_file()
            })
        helper = Path("net/serverfixes/inventory/CarryOnPermissionProbeEvent.class")
        entries[helper] = (work / helper).read_bytes()
        server = ROOT / "mods" / JAR_NAME
        with ZipFile(server, "w", compression=ZIP_DEFLATED) as jar:
            for path, content in sorted(entries.items()):
                info = ZipInfo(path.as_posix(), (1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                jar.writestr(info, content)
        client = ROOT / "client-config/mods" / JAR_NAME
        client.parent.mkdir(parents=True, exist_ok=True)
        client.write_bytes(server.read_bytes())
        overlay = ROOT / "client-config" / SCRIPT
        overlay.parent.mkdir(parents=True, exist_ok=True)
        overlay.write_bytes((ROOT / "server-config" / SCRIPT).read_bytes())
        print(f"Built {JAR_NAME}; mirrored add-on and startup script")
    finally:
        shutil.rmtree(work)


if __name__ == "__main__":
    build()
