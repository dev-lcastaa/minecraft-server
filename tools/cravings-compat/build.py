from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
JAR_NAME = "cravings-compat-1.20.1-1.0.0.jar"


def build():
    entries = [SOURCE / "pack.mcmeta"]
    entries.extend(path for folder in ("META-INF", "coremods")
                   for path in (SOURCE / folder).rglob("*") if path.is_file())
    server_jar = ROOT / "mods" / JAR_NAME
    with ZipFile(server_jar, "w", compression=ZIP_DEFLATED) as jar:
        for path in sorted(entries):
            info = ZipInfo(path.relative_to(SOURCE).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            jar.writestr(info, path.read_bytes())
    (ROOT / "client-config/mods" / JAR_NAME).write_bytes(server_jar.read_bytes())
    for name in ("server_scripts/craving_foods.js",):
        path = Path("kubejs") / name
        target = ROOT / "client-config" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / "server-config" / path).read_bytes())
    print(f"Built {JAR_NAME} and synchronized singleplayer scripts")


if __name__ == "__main__":
    build()
