from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
JAR_NAME = "lunch-basket-compat-1.20.1-1.0.0.jar"
SCRIPT = Path("kubejs/server_scripts/lunch_basket_foods.js")


def build():
    entries = [SOURCE / "pack.mcmeta"]
    entries.extend(
        path for folder in ("META-INF", "coremods", "data")
        for path in (SOURCE / folder).rglob("*") if path.is_file()
    )
    server_jar = ROOT / "mods" / JAR_NAME
    with ZipFile(server_jar, "w", compression=ZIP_DEFLATED) as jar:
        for path in sorted(entries):
            info = ZipInfo(path.relative_to(SOURCE).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            jar.writestr(info, path.read_bytes())
    client_jar = ROOT / "client-config/mods" / JAR_NAME
    client_jar.parent.mkdir(parents=True, exist_ok=True)
    client_jar.write_bytes(server_jar.read_bytes())
    client_script = ROOT / "client-config" / SCRIPT
    client_script.parent.mkdir(parents=True, exist_ok=True)
    client_script.write_bytes((ROOT / "server-config" / SCRIPT).read_bytes())
    print(f"Built {server_jar.name} and synchronized the client overlay")


if __name__ == "__main__":
    build()
