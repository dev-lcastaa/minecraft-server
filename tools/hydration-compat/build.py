import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import uuid
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
JAR_NAME = "hydration-compat-1.20.1-1.0.0.jar"
DATAPACK = ROOT / "server-config/new-world/datapacks/water-compat"
MOD_JARS = ("farmersrespite-1.20.1-2.1.2.jar", "FarmersDelight-1.20.1-1.3.4.jar")


def classpath():
    """Real SRG Minecraft/Forge classes (see jade-season-compat) plus the kettle's mods; None if unavailable."""
    spec = importlib.util.spec_from_file_location("season_build", ROOT / "tools/jade-season-compat/build.py")
    season = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(season)
    base = season.classpath()
    return None if base is None else os.pathsep.join([base, *(str(ROOT / "mods" / jar) for jar in MOD_JARS)])


def compile_to(classes, *extra):
    cp = classpath()
    if cp is None:
        raise SystemExit("Forge 1.20.1 SRG libraries not found; set MC_LIBRARIES")
    subprocess.run(["java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "-source", "17", "-target", "17",
                    "-proc:none", "-nowarn", "-cp", cp, "-d", str(classes),
                    *map(str, (SOURCE / "src").rglob("*.java")), *map(str, extra)], check=True, cwd=ROOT)


def build():
    work = SOURCE / (".build-" + uuid.uuid4().hex)
    work.mkdir()
    try:
        compile_to(work)
        entries = [SOURCE / "pack.mcmeta"]
        entries += [path for folder in ("META-INF", "coremods")
                    for path in (SOURCE / folder).rglob("*") if path.is_file()]
        target = ROOT / "mods" / JAR_NAME
        contents = {path.relative_to(SOURCE).as_posix(): path.read_bytes() for path in entries}
        contents.update({path.relative_to(DATAPACK).as_posix(): path.read_bytes()
                         for path in (DATAPACK / "data").rglob("*") if path.is_file()})
        contents.update({path.relative_to(work).as_posix(): path.read_bytes()
                         for path in (work / "serverfixes").rglob("*.class")})
        with ZipFile(target, "w", compression=ZIP_DEFLATED) as jar:
            for name, data in sorted(contents.items()):
                info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                jar.writestr(info, data)
    finally:
        shutil.rmtree(work)
    (ROOT / "client-config/mods" / JAR_NAME).write_bytes(target.read_bytes())
    for name in ("startup_scripts/hydration_hooks.js", "server_scripts/hydration_recipes.js"):
        relative = Path("kubejs") / name
        client = ROOT / "client-config" / relative
        client.parent.mkdir(parents=True, exist_ok=True)
        client.write_bytes((ROOT / "server-config" / relative).read_bytes())
    print("Built hydration compatibility and mirrored client scripts")


if __name__ == "__main__":
    build()
