"""Compile against the real SRG-named Minecraft/Forge and installed Ecliptic Seasons classes.

Set MC_LIBRARIES to a Forge 1.20.1-47.4.28 libraries folder (defaults to the Modrinth App's).
Nothing from the compile classpath is packaged.
"""
import os
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
FORGE = "1.20.1-47.4.28"
MINECRAFT = "1.20.1-20230612.114412"
LIBRARIES = Path(os.environ.get("MC_LIBRARIES", Path.home() / ".local/share/ModrinthApp/meta/libraries"))


def classpath():
    """Patched Forge classes must shadow the vanilla SRG jar; returns None when libraries are unavailable."""
    forge = LIBRARIES / "net/minecraftforge/forge" / FORGE
    first = [forge / f"forge-{FORGE}-client.jar",
             LIBRARIES / "net/minecraft/client" / MINECRAFT / f"client-{MINECRAFT}-srg.jar",
             forge / f"forge-{FORGE}-universal.jar"]
    if not all(p.is_file() for p in first):
        return None
    rest = sorted(p for p in LIBRARIES.rglob("*.jar") if p not in first and "net/minecraftforge/forge/" not in p.as_posix()
                  and "net/minecraft/client/" not in p.as_posix())
    seasons, = (ROOT / "mods").glob("Ecliptic-Seasons-1.20.1-forge-0.15.5-all.jar")
    return os.pathsep.join(map(str, [*first, *rest, seasons]))


def compile_to(classes, *extra):
    cp = classpath()
    if cp is None:
        raise SystemExit(f"Forge {FORGE} libraries not found under {LIBRARIES}; set MC_LIBRARIES")
    subprocess.run(["java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "-source", "17", "-target", "17",
                    "-proc:none", "-nowarn", "-cp", cp, "-d", str(classes),
                    *map(str, (SOURCE / "src").rglob("*.java")), *map(str, extra)], check=True, cwd=ROOT)


def build():
    work = SOURCE / (".build-" + uuid.uuid4().hex)
    work.mkdir()
    try:
        classes = work / "classes"
        classes.mkdir()
        compile_to(classes)
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
