import json
from pathlib import Path
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "server-config/new-world/datapacks/loot-compat"


class LootCompatTest(unittest.TestCase):
    def test_pack_format(self):
        metadata = json.loads((PACK / "pack.mcmeta").read_text())
        self.assertEqual(metadata["pack"]["pack_format"], 15)

    def test_only_schema_changes(self):
        paths = sorted((PACK / "data").rglob("*.json"))
        self.assertEqual(len(paths), 2)
        with ZipFile(ROOT / "mods/forge-dungeonsdelight-1.20.1-1.3.1.jar") as mod:
            registration = json.loads(
                mod.read("data/forge/loot_modifiers/global_loot_modifiers.json")
            )["entries"]
            for path in paths:
                with self.subTest(path=path):
                    relative = path.relative_to(PACK).as_posix()
                    original = json.loads(mod.read(relative))
                    original["lootTable"] = original.pop("table")
                    override = json.loads(path.read_text())
                    self.assertEqual(override, original)
                    modifier_id = "dungeonsdelight:" + path.relative_to(
                        PACK / "data/dungeonsdelight/loot_modifiers"
                    ).with_suffix("").as_posix()
                    self.assertIn(modifier_id, registration)

    def test_image_includes_pack_for_config_sync(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn(
            "COPY server-config/new-world/datapacks/ /config/new-world/datapacks/",
            dockerfile,
        )
        self.assertIn("level-name=new-world", (ROOT / "server.properties").read_text())


if __name__ == "__main__":
    unittest.main()
