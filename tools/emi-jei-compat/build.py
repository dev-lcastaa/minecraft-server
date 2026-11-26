"""Package the EMI/JEI bridge coremod; client-only, mirrored to client-config/mods."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
JAR_NAME = "emi-jei-compat-1.20.1-1.0.0.jar"


def build():
    files = [SOURCE / "pack.mcmeta", *(p for d in ("META-INF", "coremods") for p in (SOURCE / d).rglob("*") if p.is_file())]
    target = ROOT / "client-config/mods" / JAR_NAME
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as jar:
        for path in sorted(files):
            info = ZipInfo(path.relative_to(SOURCE).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            jar.writestr(info, path.read_bytes())
    print(f"Built {target.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
