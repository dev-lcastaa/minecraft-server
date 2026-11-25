from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
JAR_NAME = "hydration-compat-1.20.1-1.0.0.jar"
DATAPACK = ROOT / "server-config/new-world/datapacks/water-compat"


def build():
    entries = [SOURCE / "pack.mcmeta"]
    entries += [path for folder in ("META-INF", "coremods")
                for path in (SOURCE / folder).rglob("*") if path.is_file()]
    target = ROOT / "mods" / JAR_NAME
    contents = {path.relative_to(SOURCE).as_posix(): path.read_bytes() for path in entries}
    contents.update({path.relative_to(DATAPACK).as_posix(): path.read_bytes()
                     for path in (DATAPACK / "data").rglob("*") if path.is_file()})
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as jar:
        for name, data in sorted(contents.items()):
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            jar.writestr(info, data)
    (ROOT / "client-config/mods" / JAR_NAME).write_bytes(target.read_bytes())
    for name in ("startup_scripts/hydration_hooks.js", "server_scripts/hydration_recipes.js"):
        relative = Path("kubejs") / name
        client = ROOT / "client-config" / relative
        client.parent.mkdir(parents=True, exist_ok=True)
        client.write_bytes((ROOT / "server-config" / relative).read_bytes())
    print("Built hydration compatibility and mirrored client scripts")


if __name__ == "__main__":
    build()
