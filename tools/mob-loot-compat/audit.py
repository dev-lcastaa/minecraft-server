import json
import os
from pathlib import Path
import subprocess
from zipfile import ZipFile


SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
BASES = {
    "net.minecraft.world.entity.animal.WaterAnimal": "aquatic",
    "net.minecraft.world.entity.animal.FlyingAnimal": "winged",
    "net.minecraft.world.entity.ambient.Bat": "winged",
    "net.minecraft.world.entity.animal.horse.AbstractHorse": "wide",
    "net.minecraft.world.entity.animal.Animal": "adaptive_animal",
    "net.minecraft.world.entity.monster.AbstractIllager": "humanoid",
    "net.minecraft.world.entity.monster.AbstractPiglin": "humanoid",
    "net.minecraft.world.entity.monster.piglin.AbstractPiglin": "humanoid",
    "net.minecraft.world.entity.npc.AbstractVillager": "humanoid",
    "net.minecraft.world.entity.monster.Zombie": "humanoid",
    "net.minecraft.world.entity.animal.AbstractGolem": "bloodless",
    "net.minecraft.world.entity.monster.AbstractSkeleton": "bloodless",
    "net.minecraft.world.entity.monster.Creeper": "primary",
}
VANILLA_BRIDGES = {
    "net.minecraft.world.entity.animal.Cow": ["net.minecraft.world.entity.animal.Animal"],
    "net.minecraft.world.entity.animal.Pig": ["net.minecraft.world.entity.animal.Animal"],
    "net.minecraft.world.entity.animal.Chicken": [
        "net.minecraft.world.entity.animal.Animal", "net.minecraft.world.entity.animal.FlyingAnimal"
    ],
    "net.minecraft.world.entity.animal.horse.AbstractHorse": ["net.minecraft.world.entity.animal.Animal"],
    "net.minecraft.world.entity.animal.IronGolem": ["net.minecraft.world.entity.animal.AbstractGolem"],
    "net.minecraft.world.entity.TamableAnimal": ["net.minecraft.world.entity.animal.Animal"],
    "net.minecraft.world.entity.animal.Bee": [
        "net.minecraft.world.entity.animal.Animal", "net.minecraft.world.entity.animal.FlyingAnimal"
    ],
    "net.minecraft.world.entity.animal.Wolf": ["net.minecraft.world.entity.animal.Animal"],
    "net.minecraft.world.entity.animal.camel.Camel": ["net.minecraft.world.entity.animal.Animal"],
    "net.minecraft.world.entity.monster.SpellcasterIllager": ["net.minecraft.world.entity.monster.AbstractIllager"],
    "net.minecraft.world.entity.monster.Skeleton": ["net.minecraft.world.entity.monster.AbstractSkeleton"],
    "net.minecraft.world.entity.monster.Stray": ["net.minecraft.world.entity.monster.AbstractSkeleton"],
    "net.minecraft.world.entity.monster.Husk": ["net.minecraft.world.entity.monster.Zombie"],
    "net.minecraft.world.entity.monster.ZombieVillager": ["net.minecraft.world.entity.monster.Zombie"],
    "net.minecraft.world.entity.animal.Rabbit": ["net.minecraft.world.entity.animal.Animal"],
    "net.minecraft.world.entity.animal.Sheep": ["net.minecraft.world.entity.animal.Animal"],
}


def audit():
    classpath = os.environ["MOB_LOOT_TEST_CLASSPATH"]
    result = subprocess.run(["java", "-cp", classpath, str(SOURCE / "RegistryAudit.java"), str(ROOT / "mods")],
                            cwd=ROOT, check=True, capture_output=True, text=True)
    lines = [line.split("\t") for line in result.stdout.splitlines()]
    hierarchy = {row[1]: (row[2], row[3].split(",") if row[3] else []) for row in lines if row[0] == "H"}
    mob_types = {row[1]: row[2] for row in lines if row[0] == "M"}
    strings = {row[1]: row[2:] for row in lines if row[0] == "S"}
    geometry = {row[1]: row[2].split(",") for row in lines if row[0] == "G"}
    renderers = [row for row in lines if row[0] == "V"]
    registrations = {(row[1], row[2], row[3], row[4]) for row in lines if row[0] == "R"}
    entities = json.loads((SOURCE / "verified_entities.json").read_text())
    discovered = set()
    for id, type, jar, registry in registrations:
        # GeckoLibMod.shouldRegisterExamples requires !FMLEnvironment.production.
        if registry == "software.bernie.example.registry.EntityRegistry":
            continue
        seen = set()
        while type in hierarchy and type not in seen:
            seen.add(type)
            type = hierarchy[type][0]
        if type.startswith("net.minecraft.world.entity.") and any(
            marker in type for marker in ("animal.", "monster.", "Mob", "Animal", "LivingEntity", "Ageable", "Ambient")
        ):
            discovered.add(id)
    if discovered != set(entities):
        raise ValueError("Constructor coverage mismatch: missing=" + str(sorted(discovered - set(entities))) +
                         ", stale=" + str(sorted(set(entities) - discovered)))
    explicit = {}
    for name in ("classifications.json", "audited_extensions.json"):
        for category, ids in json.loads((SOURCE / name).read_text()).items():
            for id in ids:
                if id in explicit:
                    raise ValueError("Duplicate classification: " + id)
                explicit[id] = category
    with ZipFile(ROOT / "mods/sons_of_sins-2.2.1-forge-1.20.1.jar") as jar:
        tags = {name.rsplit("/", 1)[-1][:-5]: json.loads(jar.read(name))["values"]
                for name in jar.namelist()
                if name.startswith("data/sons_of_sins/tags/entity_types/") and name.endswith(".json")}
    def expand(values):
        result = []
        for id in values:
            if id.startswith("#"):
                result.extend(expand(tags[id.split(":")[1]]))
            else:
                result.append(id if ":" in id else "minecraft:" + id)
        return result
    native_tags = {id: tag for tag in ("has_wing", "is_large", "is_humanoid") for id in expand(tags[tag])}
    native_categories = {"has_wing": "winged", "is_large": "wide", "is_humanoid": "humanoid"}
    coverage = {}
    for id, entity in sorted(entities.items()):
        if (id, entity["class"], entity["jar"], entity["registry"]) not in registrations:
            raise ValueError("Registry constructor binding changed: " + id)
        names = []
        type = entity["class"]
        while type in hierarchy:
            parent, interfaces = hierarchy[type]
            names.extend([type, *interfaces])
            type = parent
        names.extend([type, *VANILLA_BRIDGES.get(type, [])])
        mob_type = next((mob_types[name] for name in names if name in mob_types),
                        "f_21642_" if type == "net.minecraft.world.entity.monster.Silverfish" else "inherited_default")
        models = sorted({model for row in renderers if ("L" + entity["class"] + ";") in row[2]
                         for model in row[3].split(",")})
        if id in explicit:
            category, basis = explicit[id], "reviewed biological-equivalent anatomy/material exclusion"
        elif id in native_tags:
            category, basis = native_categories[native_tags[id]], "authored Sons of Sins entity tag"
        elif mob_type == "f_21644_":
            category, basis = "aquatic", "native MobType.WATER"
        elif mob_type == "f_21643_":
            category, basis = "humanoid", "native MobType.ILLAGER"
        elif mob_type == "f_21641_" and "net.minecraft.world.entity.monster.Zombie" not in names:
            category, basis = "bloodless", "native MobType.UNDEAD without authored blood exception"
        else:
            match = next(((base, category) for base, category in BASES.items() if base in names), None)
            if match:
                base, category = match
                basis = "inherited " + base
            elif mob_type == "f_21644_":
                category, basis = "aquatic", "native MobType.WATER"
            elif mob_type == "f_21642_":
                category, basis = "primary", "native MobType.ARTHROPOD"
            elif mob_type == "f_21641_":
                category, basis = "bloodless", "native MobType.UNDEAD without authored blood exception"
            elif type == "net.minecraft.world.entity.monster.Silverfish":
                category, basis = "primary", "inherited vanilla arthropod"
            else:
                raise ValueError("Unclassified constructor: " + id)
        with ZipFile(ROOT / "mods" / entity["jar"]) as jar:
            language_path = "assets/" + id.split(":")[0] + "/lang/en_us.json"
            language = json.loads(jar.read(language_path)) if language_path in jar.namelist() else {}
            label = language.get("entity." + id.replace(":", "."), id)
        coverage[id] = {
            "category": category, "eligible": category != "bloodless", "basis": basis,
            "entity_label": label, "ancestors": names, "native_mob_type": mob_type,
            "native_tags": [native_tags[id]] if id in native_tags else [],
            "native_strings": strings.get(entity["class"], []),
            "models": {model: geometry.get(model, []) for model in models},
        }
    return coverage


if __name__ == "__main__":
    coverage = audit()
    (SOURCE / "blood_coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
    eligible = sum(row["eligible"] for row in coverage.values())
    print(f"Audited {len(coverage)} constructor bindings: {eligible} eligible, {len(coverage) - eligible} excluded, 0 unknown")
