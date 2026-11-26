"""Generate the lunar-events-compat datapack, client language files and the server gameplay mod jar.

Run with `python3 tools/lunar-events-compat/build.py`; the generated files are committed.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
PACK = ROOT / "server-config/new-world/datapacks/lunar-events-compat"
CLIENT_ASSETS = ROOT / "client-config/kubejs/assets"
JAR_NAME = "lunar-events-compat-1.20.1-1.0.0.jar"
API_JARS = ("Enhanced-Celestials-2-Core-Forge-1.20.1-1.0.3.4.jar", "Data_Anchor-forge-1.20.1-1.0.0.24.jar",
            "Corgilib-Forge-1.20.1-4.0.3.6.jar")
NS = "lunar_events_compat"
DEFAULTS = "enhancedcelestials2defaultlunarevents"
CORE = "enhancedcelestials2core"
ALL_PHASES = list(range(8))

# Default Lunar Events that also become peaceful (no natural hostile spawns or village sieges).
PEACEFUL_DEFAULTS = ("harvest_moon", "super_harvest_moon", "blue_moon", "super_blue_moon")

# Minecraft drops the rest of a spawner list after an unknown entity (and logs it), so
# vanilla entries always come before the optional modded ones.
HORDE_ZOMBIES = [
    ("minecraft:zombie", 400, 2, 4), ("minecraft:husk", 100, 2, 4),
    ("minecraft:drowned", 60, 1, 3), ("minecraft:zombie_villager", 40, 1, 2),
    ("dungeonsdelight:rotten_zombie", 25, 1, 3), ("rottencreatures:burned", 15, 1, 2),
    ("rottencreatures:frostbitten", 15, 1, 2), ("rottencreatures:swampy", 15, 1, 2),
    ("rottencreatures:undead_miner", 15, 1, 2), ("rottencreatures:mummy", 10, 1, 1),
    ("rottencreatures:zap", 10, 1, 2), ("graveyard:ghoul", 20, 1, 2),
]
BABY_ZOMBIES = [
    ("minecraft:zombie", 300, 2, 4), ("minecraft:husk", 60, 1, 3),
    ("minecraft:drowned", 40, 1, 3), ("minecraft:zombie_villager", 40, 1, 2),
    ("dungeonsdelight:rotten_zombie", 20, 1, 2), ("rottencreatures:burned", 10, 1, 2),
    ("rottencreatures:frostbitten", 10, 1, 2), ("rottencreatures:swampy", 10, 1, 2),
    ("rottencreatures:undead_miner", 10, 1, 2), ("rottencreatures:zap", 10, 1, 2),
]
SUPER_HORDE = [
    ("minecraft:zombie", 100, 2, 4), ("minecraft:skeleton", 100, 2, 4),
    ("minecraft:spider", 100, 2, 4), ("minecraft:creeper", 80, 1, 3),
    ("minecraft:witch", 20, 1, 1), ("minecraft:enderman", 20, 1, 2),
    ("minecraft:husk", 20, 1, 3), ("minecraft:stray", 20, 1, 3),
    ("minecraft:zombie_villager", 20, 1, 2), ("minecraft:pillager", 10, 1, 2),
    ("minecraft:vindicator", 5, 1, 1),
    ("fangs_n_claws:goblin", 15, 1, 3), ("fangs_n_claws:dart_goblin", 10, 1, 2),
    ("fangs_n_claws:ghost", 8, 1, 1), ("fangs_n_claws:scorpion", 10, 1, 2),
    ("fangs_n_claws:ogre", 4, 1, 1), ("fangs_n_claws:werewolf", 4, 1, 1),
    ("graveyard:ghoul", 15, 1, 2), ("graveyard:revenant", 15, 1, 2),
    ("graveyard:skeleton_creeper", 10, 1, 1), ("graveyard:wraith", 5, 1, 1),
    ("rottencreatures:burned", 10, 1, 2), ("rottencreatures:frostbitten", 10, 1, 2),
    ("rottencreatures:swampy", 10, 1, 2), ("rottencreatures:undead_miner", 10, 1, 2),
    ("rottencreatures:mummy", 6, 1, 1), ("rottencreatures:zap", 6, 1, 1),
    ("dungeonsdelight:rotten_zombie", 15, 1, 2),
    ("illagerinvasion:basher", 5, 1, 1), ("illagerinvasion:provoker", 5, 1, 1),
    ("takesapillage:legioner", 5, 1, 1), ("takesapillage:archer", 5, 1, 1),
    ("takesapillage:skirmisher", 5, 1, 1),
    ("friendsandfoes:iceologer", 3, 1, 1), ("friendsandfoes:illusioner", 3, 1, 1),
    ("quark:forgotten", 4, 1, 1),
    ("mutantmonsters:mutant_zombie", 1, 1, 1), ("mutantmonsters:mutant_skeleton", 1, 1, 1),
    ("mutantmonsters:mutant_creeper", 1, 1, 1),
]
ENDER = [
    ("minecraft:enderman", 400, 1, 4), ("minecraft:endermite", 60, 1, 3),
    ("minecraft:shulker", 2, 1, 1),
    ("unusualend:undead_enderling", 20, 1, 2), ("unusualend:ender_blob", 10, 1, 2),
    ("endergetic:charger_eetle", 10, 1, 2), ("endergetic:glider_eetle", 6, 1, 1),
    ("alexsmobs:enderiophage", 10, 1, 3), ("mutantmonsters:mutant_enderman", 1, 1, 1),
]
SPIDERS = [
    ("minecraft:spider", 400, 2, 4), ("minecraft:cave_spider", 150, 2, 4),
    ("minecraft:silverfish", 60, 2, 4),
    ("fangs_n_claws:scorpion", 25, 1, 2), ("fangs_n_claws:desert_scorpion", 15, 1, 2),
    ("fangs_n_claws:frost_scorpion", 15, 1, 2), ("fangs_n_claws:nether_scorpion", 8, 1, 2),
]

PLAYER = {"type": "corgilib:is_type", "id": "minecraft:player"}
HORDE_FILTER = {"type": "corgilib:is_type_tag", "tag": f"#{NS}:horde_zombies"}
NO_SLEEP = {"condition": {"type": "corgilib:any"}}


def effect(filter, effect_id, amplifier, duration):
    return {"filter": filter, "mob_effect": {
        "ambient": True, "amplifier": amplifier, "duration_in_ticks": duration,
        "effect": effect_id, "show_icon": False, "visible": False}}


def spawn_settings(entries):
    return {"spawn_settings": {"spawners": {"monster": [
        {"type": id, "weight": weight, "minCount": low, "maxCount": high}
        for id, weight, low, high in entries]}, "spawn_costs": {}}}


EVENTS = {
    "peaceful_moon": {
        "sky": "fff1cc", "moon": "ffffff", "size": 30.0, "name": "55ff55", "style": "green",
        "sound": "blue_moon", "weight": 6, "min_nights": 10, "phases": ALL_PHASES,
        "modifiers": {
            "spawn_category_multiplier": {"multipliers": {"monster": 0.0}},
            "village_siege_probability": {"probability": 0.0},
        },
        "title": "Peaceful Moon",
        "rise": "The \"Peaceful Moon\" rises... The night is too bright for monsters.",
        "set": "The \"Peaceful Moon\" sets... Monsters stir once more.",
    },
    "horde_moon": {
        "sky": "7a9e5a", "moon": "4f7a2a", "size": 25.0, "name": "00aa00", "style": "dark_green",
        "sound": "blood_moon", "weight": 5, "min_nights": 12, "phases": ALL_PHASES,
        "modifiers": {
            "spawn_category_multiplier": {"multipliers": {"monster": 3.0}},
            "disable_biome_spawn_settings": {},
            "mob_spawn_settings": spawn_settings(HORDE_ZOMBIES),
            "mob_effects": {"effects": [
                effect(HORDE_FILTER, "minecraft:strength", 0, 100),
                effect(HORDE_FILTER, "minecraft:speed", 0, 100),
            ]},
            "force_surface_spawning": {},
            "block_sleeping": NO_SLEEP,
            "village_siege_probability": {"probability": 0.75},
            "mob_spawn_distances": {"distances": {"monster": 64}},
        },
        "title": "Horde Moon",
        "rise": "The \"Horde Moon\" rises... A rotting horde shambles out of the dark.",
        "set": "The \"Horde Moon\" sets... The horde begins to burn.",
    },
    "super_horde_moon": {
        "sky": "a33a3a", "moon": "7a1f1f", "size": 40.0, "name": "aa0000", "style": "dark_red",
        "sound": "blood_moon", "weight": 4, "min_nights": 20, "phases": [0],
        "modifiers": {
            "spawn_category_multiplier": {"multipliers": {"monster": 5.0}},
            "mob_spawn_settings": spawn_settings(SUPER_HORDE),
            "force_surface_spawning": {},
            "block_sleeping": NO_SLEEP,
            "village_siege_probability": {"probability": 1.0},
            "mob_spawn_distances": {"distances": {"monster": 64}},
        },
        "title": "Super Horde Moon",
        "rise": "The \"Super Horde Moon\" rises... Every monster in the land answers its call!",
        "set": "The \"Super Horde Moon\" sets... The great horde scatters.",
    },
    "baby_horde_moon": {
        "sky": "ffb3d9", "moon": "ff99cc", "size": 12.0, "name": "ff55ff", "style": "light_purple",
        "sound": "blood_moon", "weight": 4, "min_nights": 12, "phases": ALL_PHASES,
        "modifiers": {
            "spawn_category_multiplier": {"multipliers": {"monster": 2.5}},
            "mob_spawn_settings": spawn_settings(BABY_ZOMBIES),
            "force_surface_spawning": {},
            "block_sleeping": NO_SLEEP,
        },
        "title": "Baby Horde Moon",
        "rise": "The \"Baby Horde Moon\" rises... Tiny footsteps patter in the dark.",
        "set": "The \"Baby Horde Moon\" sets... The little ones run out of energy.",
    },
    "miners_moon": {
        "sky": "c9a66b", "moon": "b87333", "size": 22.0, "name": "ffaa00", "style": "gold",
        "sound": "harvest_moon", "weight": 5, "min_nights": 10, "phases": ALL_PHASES,
        "modifiers": {
            "spawn_category_multiplier": {"multipliers": {"monster": 1.5}},
            "mob_effects": {"effects": [
                effect(PLAYER, "minecraft:haste", 1, 100),
                effect(PLAYER, "minecraft:night_vision", 0, 300),
            ]},
            # Redstone needs two or more so placed redstone wire cannot be duplicated.
            "block_item_drop": {"settings": {"drop_enhancer": [
                {"minimum_count": 1, "multipliers": {
                    "#forge:raw_materials": 2.0, "#forge:gems": 2.0, "minecraft:coal": 2.0}},
                {"minimum_count": 2, "multipliers": {"minecraft:redstone": 2.0}},
            ]}},
        },
        "title": "Miner's Moon",
        "rise": "The \"Miner's Moon\" rises... Ores glitter and the caves grow restless.",
        "set": "The \"Miner's Moon\" sets... The veins grow dull again.",
    },
    "black_moon": {
        "sky": "202020", "moon": "111111", "size": 25.0, "name": "555555", "style": "dark_gray",
        "sound": "blood_moon", "weight": 7, "min_nights": 16, "phases": [3, 4, 5],
        "modifiers": {
            "mob_effects": {"effects": [effect(PLAYER, "minecraft:blindness", 0, 100)]},
            "block_sleeping": NO_SLEEP,
        },
        "title": "Black Moon",
        "rise": "The \"Black Moon\" rises... Darkness swallows your sight.",
        "set": "The \"Black Moon\" sets... Your eyes adjust to the light.",
    },
    "ender_moon": {
        "sky": "b366ff", "moon": "cc66ff", "size": 28.0, "name": "aa00aa", "style": "dark_purple",
        "sound": "blue_moon", "weight": 4, "min_nights": 12, "phases": ALL_PHASES,
        "modifiers": {
            "spawn_category_multiplier": {"multipliers": {"monster": 2.5}},
            "mob_spawn_settings": spawn_settings(ENDER),
            "block_sleeping": NO_SLEEP,
        },
        "title": "Ender Moon",
        "rise": "The \"Ender Moon\" rises... The End bleeds into the Overworld.",
        "set": "The \"Ender Moon\" sets... The void recedes.",
    },
    "spider_moon": {
        "sky": "a0522d", "moon": "5c3317", "size": 25.0, "name": "ff5555", "style": "red",
        "sound": "blood_moon", "weight": 4, "min_nights": 12, "phases": ALL_PHASES,
        "modifiers": {
            "spawn_category_multiplier": {"multipliers": {"monster": 3.0}},
            "mob_spawn_settings": spawn_settings(SPIDERS),
            "force_surface_spawning": {},
            "block_sleeping": NO_SLEEP,
        },
        "title": "Spider Moon",
        "rise": "The \"Spider Moon\" rises... Countless legs skitter in the dark.",
        "set": "The \"Spider Moon\" sets... The webs fall silent.",
    },
    "chaos_moon": {
        "sky": "ff6600", "moon": "ff3300", "size": 30.0, "name": "ffff55", "style": "yellow",
        "sound": "blood_moon", "weight": 3, "min_nights": 16, "phases": ALL_PHASES,
        # A crowded, mixed population so the lunar_events_compat mod has plenty of mobs to set on each other.
        "modifiers": {
            "spawn_category_multiplier": {"multipliers": {"monster": 4.0, "creature": 2.0}},
            "mob_spawn_settings": spawn_settings(SUPER_HORDE),
            "force_surface_spawning": {},
            "block_sleeping": NO_SLEEP,
            "mob_spawn_distances": {"distances": {"monster": 48}},
        },
        "title": "Chaos Moon",
        "rise": "The \"Chaos Moon\" rises... Every creature turns on every other!",
        "set": "The \"Chaos Moon\" sets... An uneasy peace returns.",
    },
}

DEFAULT_RISE = {
    "blue_moon": "The \"Blue Moon\" rises... You feel lucky!",
    "harvest_moon": "The \"Harvest Moon\" rises... Your crops provide a better harvest.",
    "super_blue_moon": "The \"Super Blue Moon\" rises... You feel very lucky!",
    "super_harvest_moon": "The \"Super Harvest Moon\" rises... Your crops provide an exceptional harvest.",
}


def encoded(data):
    return (json.dumps(data, indent=2) + "\n").encode()


def modifier_settings(name, event):
    # Same order as the Default Lunar Events: presentation first, then gameplay.
    return {
        "sky_light_color": {"color": event["sky"]},
        "moon_texture_color": {"color": event["moon"]},
        "moon_size": {"moon_size": event["size"]},
        "sound_track": {"sound_track": {"sound_id": f"{DEFAULTS}:{event['sound']}"}},
        "text_components": {"components": {
            "end_notification": {"type": "CHAT", "component": {
                "key": f"{NS}.notification.{name}.set"}},
            "start_notification": {"type": "CHAT", "component": {
                "key": f"{NS}.notification.{name}.rise",
                "style": {"color": event["style"], "font": "minecraft:default"}}},
        }},
        "name_color": {"color": event["name"]},
        **event["modifiers"],
    }


def probability(event_id, event):
    return {
        "dimensions": {"minecraft:overworld": {"priority": 0, "spawn_requirements": {
            "rules": [
                {"type": f"{CORE}:min_nights_between",
                 "settings": {"min_nights": event["min_nights"]}},
                {"type": f"{CORE}:valid_moon_phase",
                 "settings": {"valid_moon_phases": event["phases"]}},
            ],
            "weight": event["weight"],
        }}},
        "lunar_event": event_id,
    }


def default_event_modifiers(name):
    jars = sorted((ROOT / "mods").glob("Enhanced-Celestials-2-Default-Lunar-Events-*.jar"))
    if len(jars) != 1:
        raise SystemExit(f"Expected one Default Lunar Events jar, found {jars}")
    with ZipFile(jars[0]) as jar:
        return json.loads(jar.read(f"data/{DEFAULTS}/{CORE}/lunar/event/{name}.json"))["modifiers"]


def resources():
    lunar = f"data/{NS}/{CORE}/lunar"
    files = {
        "pack.mcmeta": encoded({"pack": {
            "pack_format": 15,
            "description": "Enhanced Celestials 2 compat: nine extra lunar events and peaceful Harvest/Blue Moons",
        }}),
        f"data/{NS}/tags/entity_types/horde_zombies.json": encoded({"replace": False, "values": [
            id if id.startswith("minecraft:") else {"id": id, "required": False}
            for id in sorted({id for id, *_ in HORDE_ZOMBIES})]}),
    }
    lang = {}
    for name, event in EVENTS.items():
        modifiers = []
        for kind, settings in modifier_settings(name, event).items():
            modifiers.append(f"{NS}:{name}_{kind}")
            files[f"{lunar}/event_modifier/{name}_{kind}.json"] = encoded(
                {"type": f"{CORE}:{kind}", "settings": settings})
        files[f"{lunar}/event/{name}.json"] = encoded({"modifiers": modifiers})
        files[f"{lunar}/event_probability/{name}.json"] = encoded(probability(f"{NS}:{name}", event))
        lang[f"lunar.event.{NS}.{name}"] = event["title"]
        lang[f"{NS}.notification.{name}.rise"] = event["rise"]
        lang[f"{NS}.notification.{name}.set"] = event["set"]

    # Overrides keep every original Harvest/Blue Moon modifier and add the Peaceful Moon's.
    for name in PEACEFUL_DEFAULTS:
        files[f"data/{DEFAULTS}/{CORE}/lunar/event/{name}.json"] = encoded({
            "modifiers": default_event_modifiers(name) + [
                f"{NS}:peaceful_moon_spawn_category_multiplier",
                f"{NS}:peaceful_moon_village_siege_probability",
            ]})
    client = {
        f"{NS}/lang/en_us.json": encoded(dict(sorted(lang.items()))),
        f"{DEFAULTS}/lang/en_us.json": encoded({
            f"{DEFAULTS}.notification.{name}.rise": text + " Monsters keep their distance tonight."
            for name, text in sorted(DEFAULT_RISE.items())}),
    }
    return files, client


def classpath():
    """Real SRG Minecraft/Forge (see jade-season-compat) plus Enhanced Celestials; None when unavailable."""
    spec = importlib.util.spec_from_file_location("season_build", ROOT / "tools/jade-season-compat/build.py")
    season = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(season)
    base = season.classpath()
    return None if base is None else os.pathsep.join([base, *(str(ROOT / "mods" / jar) for jar in API_JARS)])


def compile_to(classes, *extra):
    cp = classpath()
    if cp is None:
        raise SystemExit("Forge 1.20.1 SRG libraries not found; set MC_LIBRARIES")
    subprocess.run(["java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "-source", "17", "-target", "17",
                    "-proc:none", "-nowarn", "-cp", cp, "-d", str(classes),
                    *map(str, (SOURCE / "src").rglob("*.java")), *map(str, extra)], check=True, cwd=ROOT)


def build_jar():
    work = SOURCE / (".build-" + uuid.uuid4().hex)
    work.mkdir()
    try:
        compile_to(work)
        entries = {p.relative_to(SOURCE).as_posix(): p.read_bytes() for p in (SOURCE / "META-INF").rglob("*") if p.is_file()}
        entries["pack.mcmeta"] = (SOURCE / "pack.mcmeta").read_bytes()
        entries.update({p.relative_to(work).as_posix(): p.read_bytes() for p in (work / "serverfixes").rglob("*.class")})
        with ZipFile(ROOT / "mods" / JAR_NAME, "w", compression=ZIP_DEFLATED) as jar:
            for name, data in sorted(entries.items()):
                info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                jar.writestr(info, data)
    finally:
        shutil.rmtree(work)
    # Mirrored like every *_compat add-on; on clients it only matters for singleplayer worlds.
    (ROOT / "client-config/mods" / JAR_NAME).write_bytes((ROOT / "mods" / JAR_NAME).read_bytes())


def build():
    build_jar()
    files, client = resources()
    for base, entries in ((PACK, files), (CLIENT_ASSETS, client)):
        for relative, content in entries.items():
            path = base / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)


if __name__ == "__main__":
    build()
