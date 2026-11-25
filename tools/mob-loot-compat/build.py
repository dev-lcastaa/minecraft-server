import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
PACK = ROOT / "server-config/new-world/datapacks/mob-loot-compat"
JAR_NAME = "mob-loot-compat-1.20.1-1.0.0.jar"


def encoded(data):
    return (json.dumps(data, indent=2) + "\n").encode()


def resources():
    result = {}
    categories = json.loads((SOURCE / "classifications.json").read_text())
    for category, ids in json.loads((SOURCE / "audited_extensions.json").read_text()).items():
        categories[category].extend(ids)
    for category, ids in categories.items():
        tag = "bloodless" if category == "bloodless" else f"blood_{category}"
        result[f"data/mob_loot_compat/tags/entity_types/{tag}.json"] = encoded({
            "replace": True, "values": [{"id": id, "required": False} for id in sorted(ids)]
        })
    result["data/forge/loot_modifiers/global_loot_modifiers.json"] = encoded({
        "replace": False,
        "entries": ["mob_loot_compat:evil_bat_wings", "mob_loot_compat:zombie_food"]
    })
    for modifier, entity, table in (
        ("evil_bat_wings", "fangs_n_claws:evil_bat", "evil_bat_wings"),
        ("zombie_food", "minecraft:zombie", "zombie_food"),
    ):
        result[f"data/mob_loot_compat/loot_modifiers/{modifier}.json"] = encoded({
            "type": "farmersdelight:add_loot_table",
            "conditions": [
                {"condition": "minecraft:killed_by_player"},
                {"condition": "minecraft:entity_properties", "entity": "this",
                 "predicate": {"type": entity}}
            ],
            "lootTable": f"mob_loot_compat:{table}"
        })
    result["data/mob_loot_compat/loot_tables/evil_bat_wings.json"] = encoded({
        "type": "minecraft:entity", "pools": [{
            "rolls": 1, "entries": [{"type": "minecraft:item", "name": "miners_delight:bat_wing",
                                   "functions": [{"function": "minecraft:set_count",
                                                  "count": {"type": "minecraft:uniform", "min": 1, "max": 2}}]}]
        }]
    })
    result["data/mob_loot_compat/loot_tables/zombie_food.json"] = encoded({
        "type": "minecraft:entity", "pools": [{
            "rolls": 1, "conditions": [{"condition": "minecraft:random_chance", "chance": 0.05}],
            "entries": [{"type": "minecraft:item", "name": f"farmersdelight:{item}", "weight": 1}
                        for item in ("cabbage", "tomato", "onion", "rice", "cabbage_seeds", "tomato_seeds")]
        }]
    })
    return result


def build():
    data = resources()
    PACK.mkdir(parents=True, exist_ok=True)
    (PACK / "pack.mcmeta").write_bytes(encoded({
        "pack": {"pack_format": 15, "description": "Mob loot compatibility: blood categories and additive food drops"}
    }))
    # The JAR registers modifiers once; this world datapack supplies the editable tables/tags.
    for name, content in data.items():
        if name == "data/forge/loot_modifiers/global_loot_modifiers.json":
            continue
        target = PACK / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    entries = {"pack.mcmeta": (SOURCE / "pack.mcmeta").read_bytes(), **data}
    for folder in ("META-INF", "coremods"):
        entries.update({p.relative_to(SOURCE).as_posix(): p.read_bytes()
                        for p in (SOURCE / folder).rglob("*") if p.is_file()})
    jar = ROOT / "mods" / JAR_NAME
    with ZipFile(jar, "w", ZIP_DEFLATED) as archive:
        for name, content in sorted(entries.items()):
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    (ROOT / "client-config/mods" / JAR_NAME).write_bytes(jar.read_bytes())
    for scope in ("server_scripts", "startup_scripts"):
        relative = Path("kubejs") / scope / "mob_loot_compat.js"
        target = ROOT / "client-config" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / "server-config" / relative).read_bytes())
    print(f"Built {JAR_NAME}, world datapack, and mirrored client scripts")


if __name__ == "__main__":
    build()
