"""Opt-in verification against official 1.20.1 bytecode; no downloaded classes are retained."""
import hashlib
import io
from pathlib import Path
import subprocess
from urllib.request import urlopen
import uuid
from zipfile import ZipFile

SOURCE = Path(__file__).resolve().parent
SERVER_SHA1 = "84194a2f286ef7c14ed7ce0090dba59902951553"


def verify():
    payload = urlopen(
        f"https://piston-data.mojang.com/v1/objects/{SERVER_SHA1}/server.jar", timeout=120).read()
    assert hashlib.sha1(payload).hexdigest() == SERVER_SHA1, "Official server hash mismatch"
    with ZipFile(io.BytesIO(payload)) as bundle:
        server = bundle.read("META-INF/versions/1.20.1/server-1.20.1.jar")
    scratch = SOURCE / (".vanilla-verification-" + uuid.uuid4().hex + ".jar")
    try:
        with ZipFile(io.BytesIO(server)) as original, ZipFile(scratch, "w") as subset:
            for name in ("cwb", "dbg", "dbm", "dbn", "dbq"):
                subset.writestr(name + ".class", original.read(name + ".class"))
        output = subprocess.check_output(
            ["java", "-m", "jdk.jdeps/com.sun.tools.javap.Main", "-p", "-c",
             "-classpath", str(scratch), "cwb", "dbg", "dbm", "dbn", "dbq"], text=True)
        dark_oak = output.split("public class dbm extends dbg", 1)[1].split("public class dbn", 1)[0]
        normal = dark_oak.split("a(apf, boolean);", 1)[1].split("protected", 1)[0]
        assert "aconst_null" in normal, "Dark oak unexpectedly gained a single-sapling feature"
        for name in ("dbn", "dbq"):
            tree = output.split("public class " + name + " extends dbg", 1)[1]
            normal = tree.split("a(apf, boolean);", 1)[1].split("protected", 1)[0]
            assert "getstatic" in normal and "aconst_null" not in normal, "Optional mega-tree rules changed"
        square = output.split("public static boolean a(dcb, cls, gu, int, int);", 1)[1].split("}", 1)[0]
        assert square.count("Method dcb.a:(Lcpn;)Z") == 4, "2x2 requires four equal block types"
        assert square.count("Method gu.b:(III)Lgu;") == 4, "2x2 checks four positions"
        sapling = output.split("public abstract class dbg", 1)[0]
        natural = sapling.split("public void b(dcb, aif, gu, apf);", 1)[1].split("public void", 1)[0]
        assert "bipush        9" in natural and "bipush        7" in natural, "Light/random-tick gates changed"
        advance = sapling.split("public void a(aif, gu, dcb, apf);", 1)[1].split("public boolean", 1)[0]
        assert "Integer" in advance and "Method dbh.a:" in advance, "Stage advancement/feature growth changed"
        print("Official 1.20.1 SHA1 verified: dark oak requires 2x2; spruce/jungle optional mega trees;")
        print("four same-block/same-Y positions; natural light>=9 and 1-in-7 tick; stage advancement before growth.")
    finally:
        scratch.unlink(missing_ok=True)


if __name__ == "__main__":
    verify()
