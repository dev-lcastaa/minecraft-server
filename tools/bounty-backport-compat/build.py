"""Build additive pools from acquisition evidence, not the creative item inventory."""
import json
import gzip
import re
import struct
import tomllib
import zlib
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[1]
PACK = ROOT / "server-config/new-world/datapacks/bounty-backport-compat"
JAR_NAME = "bounty-backport-compat-1.20.1-1.0.0.jar"
EGGS = ["minecraft:egg", "backported_animal_variants:blue_egg",
        "backported_animal_variants:brown_egg"]
ANIMALS = {f"minecraft:{animal}": [
    f"backported_animal_variants:{temperature}_{animal}" for temperature in ("cold", "warm")
] for animal in ("chicken", "cow", "pig")}
DECREES = ("armorer", "butcher", "cleric", "farmer", "fisherman", "fletcher",
           "inventor", "leatherer", "librarian", "mapper", "shepherd", "toolsmith")
TOKENS = {
    "armorer": {"helmet", "chestplate", "leggings", "boots", "shield", "armor"},
    "butcher": {"meat", "beef", "porkchop", "chicken", "bacon", "sausage", "ham", "egg", "milk", "mutton", "rabbit", "bison", "kangaroo", "moose", "duck", "venison", "loin", "ribs"},
    "cleric": {"amethyst", "quartz", "pearl", "dust", "crystal", "glowstone", "eye", "heart"},
    "farmer": {"egg", "milk", "seed", "seeds", "wheat", "beetroot", "honey", "fruit", "melon", "pumpkin", "bread", "pie", "cake", "cookie", "rice", "tomato", "cabbage", "onion", "potato", "carrot", "apple", "berry", "berries", "tea", "coffee", "juice", "dough", "salad", "soup", "stew", "sandwich", "burger", "toast", "roll", "dumpling", "pasta", "noodles", "omelette", "pancake", "curry", "pizza", "burrito", "taco", "muffin", "ice", "cream", "jelly"},
    "fisherman": {"fish", "cod", "salmon", "tuna", "catfish", "shrimp", "crab", "squid", "fishing", "perch", "pike", "roe", "lobster", "trilocaris", "lanternfish", "tripodfish", "canoe", "raft", "sailboat"},
    "fletcher": {"arrow", "bow", "crossbow", "feather"},
    "inventor": {"ingot", "nugget", "wire", "circuit", "gear", "plate", "alloy", "redstone"},
    "leatherer": {"leather", "hide", "belt", "saddle", "horse", "backpack"},
    "librarian": {"book", "paper", "tome", "codex", "ink", "candle", "disc", "music"},
    "mapper": {"compass", "map", "rope", "spyglass", "lantern", "canoe", "raft", "sailboat"},
    "shepherd": {"wool", "dye", "string", "yarn", "carpet", "cloth"},
    "toolsmith": {"pickaxe", "axe", "shovel", "hoe", "hammer", "knife", "sickle", "cleaver"},
}
FORBIDDEN = re.compile(
    r"(?:^|_)(?:creative|spawn|spawner|command|debug|barrier|bedrock|portal|"
    r"decree|bounty|kettle|stove|station|cabinet|drawer|"
    r"machine|reactor|generator|tank|carcass|corpse|"
    r"blood)(?:_|$)"
)
UNOBTAINABLE = re.compile(r"(?:^|_)(?:creative|spawn|spawner|command|debug|barrier|bedrock)(?:_|$)")
STATEFUL = re.compile(
    r"(?:^|_)(?:chest|barrel|shulker|crate|sack|backpack|bag|pouch|tool_belt|"
    r"furnace|smoker|brewing|enchanting|workbench|crafter|crafting|"
    r"crusher|grinder|sawmill|millstone|press|mixer|pump|hopper|"
    r"engine|kiln|incubator|brewer|infuser|smelter|centrifuge|"
    r"condenser|compressor|controller|turbine|teleporter|"
    r"sign|banner|head|skull|clock|bed|loom|stonecutter|grindstone|anvil|lectern|binder)(?:_|$)"
)
VANILLA_FORBIDDEN = {"minecraft:air", "minecraft:dragon_egg", "minecraft:enchanted_book",
                     "minecraft:filled_map", "minecraft:knowledge_book", "minecraft:elytra",
                     "minecraft:potion", "minecraft:splash_potion", "minecraft:lingering_potion",
                     "minecraft:tipped_arrow", "minecraft:written_book", "minecraft:suspicious_stew",
                     "minecraft:firework_rocket", "minecraft:firework_star"}
VANILLA_ADMIN = {"minecraft:light", "minecraft:structure_void", "minecraft:structure_block",
                 "minecraft:jigsaw", "minecraft:debug_stick", "minecraft:end_portal_frame"}
VANILLA_NON_SUPPLY_ROOTS = {"minecraft:budding_amethyst", "minecraft:reinforced_deepslate",
                           "minecraft:petrified_oak_slab", "minecraft:chorus_plant",
                           "minecraft:frogspawn", "minecraft:dirt_path", "minecraft:farmland"}
OUTPUT_KEYS = {"result", "results", "output", "outputs", "outputItem", "output_item",
               "primaryOutput", "secondaryOutput", "secondary_output", "byproducts", "container"}
VANILLA_TAGS = {
    "minecraft:planks", "minecraft:logs", "minecraft:logs_that_burn", "minecraft:saplings",
    "minecraft:wool", "minecraft:wool_carpets", "minecraft:flowers", "minecraft:small_flowers",
    "minecraft:fishes", "minecraft:coals", "minecraft:stone_crafting_materials",
    "forge:ingots/iron", "forge:ingots/gold", "forge:ingots/copper",
    "forge:nuggets/iron", "forge:nuggets/gold", "forge:gems/diamond",
    "forge:gems/emerald", "forge:gems/amethyst", "forge:gems/quartz",
    "forge:dusts/redstone", "forge:dusts/glowstone", "forge:rods/wooden",
    "forge:string", "forge:leather", "forge:bones", "forge:feathers", "forge:gunpowder",
    "forge:eggs", "forge:milk", "forge:milk/milk", "forge:milk_bucket",
    "forge:bread", "forge:cooked_beef", "forge:cooked_pork", "forge:cooked_chicken",
    "forge:crops/wheat", "forge:crops/carrot", "forge:crops/potato", "forge:crops/beetroot",
}
EXACT_CATEGORY = {
    "naturescompass:naturescompass": "mapper",
    "butchersdelightfoods:beefribs": "butcher",
    "butchersdelightfoods:beeftenderloin": "butcher",
    "butchersdelightfoods:cookedbeefribs": "butcher",
    "butchersdelightfoods:coockedbeeftenderloin": "butcher",
    "butchersdelight:cleaver": "toolsmith",
}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def quark_flags(config):
    flags = {}
    normalize = lambda name: name.lower().replace(" ", "_")
    for category, section in config.items():
        if category in ("general", "categories") or not isinstance(section, dict):
            continue
        enabled = config.get("categories", {}).get(category, True)
        for name, value in section.items():
            if isinstance(value, bool):
                flags[normalize(name)] = enabled and value
        for module, settings in section.items():
            if isinstance(settings, dict) and module in flags:
                for name, value in settings.items():
                    if name.startswith("Enable ") and isinstance(value, bool):
                        flags[normalize(name[7:])] = flags[module] and value
    # Verified ConfigFlagManager bindings in the installed MoreStoneVariantsModule.
    for name in ("granite", "diorite", "andesite", "calcite", "dripstone", "tuff",
                 "limestone", "jasper", "shale", "myalite"):
        flags[name] = flags.get("more_stone_variants", False)
    if "glow_berry_sack" in flags:
        flags["glowberry_sack"] = flags["glow_berry_sack"]
    return flags


def item_id(value):
    if isinstance(value, str):
        return value if ":" in value else f"minecraft:{value}"
    if isinstance(value, dict):
        return item_id(value.get("item", value.get("id"))) if value.get("item", value.get("id")) else None
    return None


def recipe_outputs(recipe):
    outputs = []
    for key in ("result", "results", "output", "outputs", "primaryOutput", "secondaryOutput"):
        value = recipe.get(key, [])
        outputs.extend(value if isinstance(value, list) else [value])
    return [v for v in outputs if not isinstance(v, dict) or
            v.get("chance", 1) > 0 and v.get("count", 1) > 0]


def recipe_inputs(recipe):
    if "ingredients" in recipe:
        return recipe["ingredients"]
    if "key" in recipe:
        return list(recipe["key"].values())
    return [recipe[k] for k in ("ingredient", "input", "itemInput", "primaryInput",
                                "secondaryInput", "base", "addition", "template") if k in recipe]


def input_references(value):
    if isinstance(value, list):
        return sorted(set(v for entry in value for v in input_references(entry)))
    if isinstance(value, str):
        return [item_id(value)]
    if not isinstance(value, dict):
        return []
    if "item" in value:
        identity = item_id(value["item"])
        return [identity] if identity else []
    if "tag" in value:
        identity = item_id(value["tag"])
        return ["#" + identity] if identity else []
    return sorted(set(v for entry in value.values() for v in input_references(entry)))


def has_field(value, fields):
    if isinstance(value, list):
        return any(has_field(v, fields) for v in value)
    return isinstance(value, dict) and (bool(value.keys() & fields) or
                                       any(has_field(v, fields) for v in value.values()))


def candidate_sources(data, mods):
    sources = defaultdict(list)
    non_item_outputs = []
    for name, (jar, value) in data.items():
        if "/recipes/" in name and "/advancements/" not in name:
            branches = value.get("recipes", []) if value.get("type") == "forge:conditional" else [{"recipe": value}]
            for branch in branches:
                recipe = branch.get("recipe", {})
                active = bool(conditions_met(branch, mods) and conditions_met(recipe, mods))
                inputs = recipe_inputs(recipe)
                for output in recipe_outputs(recipe):
                    identity = item_id(output)
                    if identity:
                        sources[identity].append({
                            "source": f"{jar}!{name}", "kind": "recipe", "type": recipe.get("type"),
                            "active": active, "references": input_references(inputs),
                            "nbt": has_field(inputs, {"nbt"}) or has_field(output, {"nbt"}),
                            "fluid_or_chemical": has_field(recipe, {"fluid", "gas", "chemical", "fluidInput",
                                                                    "gasInput", "chemicalInput", "fluid_input"}),
                        })
                    elif isinstance(output, dict) and output:
                        non_item_outputs.append({"source": f"{jar}!{name}", "output": output,
                                                 "reason": "Private fluid/chemical output is not an item bounty"})
        elif "/loot_tables/" in name:
            def visit(node, inherited=()):
                if isinstance(node, list):
                    for child in node:
                        visit(child, inherited)
                elif isinstance(node, dict):
                    functions = (*inherited, *node.get("functions", []))
                    if node.get("type") in ("item", "minecraft:item") and node.get("name"):
                        sources[item_id(node["name"])].append({
                            "source": f"{jar}!{name}", "kind": "loot",
                            "functions": sorted({f.get("function", "") for f in functions}),
                        })
                    for child in node.values():
                        visit(child, functions)
            visit(value)
    return dict(sources), non_item_outputs


def class_header(bytecode):
    """Read the actual superclass/interfaces; no renderer/model-name type guessing."""
    offset, count = 10, struct.unpack_from(">H", bytecode, 8)[0]
    constants = [None]
    while len(constants) < count:
        tag = bytecode[offset]
        offset += 1
        if tag == 1:
            size = struct.unpack_from(">H", bytecode, offset)[0]
            offset += 2
            constants.append(bytecode[offset:offset + size].decode("utf-8", "replace"))
            offset += size
        elif tag in (7, 8, 16, 19, 20):
            constants.append(struct.unpack_from(">H", bytecode, offset)[0])
            offset += 2
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            constants.append(None)
            offset += 4
        elif tag in (5, 6):
            constants.extend((None, None))
            offset += 8
        elif tag == 15:
            constants.append(None)
            offset += 3
        else:
            raise ValueError(f"Unknown constant-pool tag {tag}")
    _, identity, parent, interfaces = struct.unpack_from(">HHHH", bytecode, offset)
    return (constants[constants[identity]],
            constants[constants[parent]] if parent else None,
            [constants[constants[struct.unpack_from(">H", bytecode, offset + 8 + 2 * i)[0]]]
             for i in range(interfaces)])


def block_types(classes):
    headers, aliases = {}, defaultdict(list)
    for path, (jar, bytecode) in classes.items():
        if "/block/" not in path and not path.endswith("Block.class"):
            continue
        identity, parent, interfaces = class_header(bytecode)
        headers[identity] = (parent, interfaces)
        tail = identity.rsplit("/", 1)[1]
        if "$" not in tail:
            aliases[re.sub(r"[^a-z0-9]", "", re.sub(r"Block$", "", tail).lower())].append((identity, jar))
    return headers, aliases


def is_stateful_block(identity, headers, seen=frozenset()):
    if identity in seen:
        return False
    if identity in {"net/minecraft/world/level/block/EntityBlock",
                    "net/minecraft/world/level/block/BaseEntityBlock",
                    "net/minecraft/world/level/block/ChestBlock",
                    "net/minecraft/world/level/block/BarrelBlock",
                    "net/minecraft/world/level/block/AbstractFurnaceBlock",
                    "net/minecraft/world/level/block/SignBlock",
                    "net/minecraft/world/level/block/BannerBlock",
                    "net/minecraft/world/level/block/BedBlock"}:
        return True
    parent, interfaces = headers.get(identity, (None, []))
    return any(is_stateful_block(v, headers, seen | {identity}) for v in [parent, *interfaces] if v)


def exclusion_reason(identity, blocks, headers, aliases, namespace_jars=None):
    tail = identity.split(":")[1]
    words = set(tail.split("_"))
    if identity in VANILLA_FORBIDDEN:
        return "NBT_VARIANT_OR_UNIQUE", "The bare item ID cannot represent required NBT, map/potion contents or unique progression"
    if identity in VANILLA_ADMIN or UNOBTAINABLE.search(tail):
        return "CREATIVE_OR_ADMIN", "Creative/admin-only or spawn-egg content is not a survival supply objective"
    if words & {"incomplete", "unfinished", "transitional"}:
        return "PRIVATE_PROCESS_INTERMEDIATE", "Transitional fabrication items carry private process state rather than ordinary supplies"
    if identity.startswith("ad_astra:") and (tail.endswith("_rocket") or tail == "rover"):
        return "PRIVATE_FLUID_VEHICLE", "Verified VehicleItem implements BotariumFluidItem; its fuel/container state is not represented by a bare item bounty"
    if identity in blocks and identity.startswith("butchersdelight:"):
        return "CARCASS_OR_BUTCHERY_STATION", "Butchery carcass/workstation blocks are not ordinary edible meat supplies"
    if identity == "the_bumblezone:bee_cannon" or words & {"quiver", "bundle", "satchel", "backpack", "bag", "pouch", "wallet"} or any(
        v in tail for v in ("lunch_basket", "lunch_box", "lunchbox", "tool_belt", "toolbelt")
    ):
        return "CONTAINER_OR_CONFIGURED_BLOCK", "Inventory-bearing items may contain private stacks/NBT that bounty consumption must preserve"
    if FORBIDDEN.search(tail):
        return "STATION_OR_STATEFUL_RESOURCE", "Workstation, bounty economy item, carcass, biological/NBT-sensitive or unique trophy"
    if tail.endswith(("cooking_pot", "copper_pot", "monster_pot", "cutting_board",
                      "crafting_table", "smithing_table", "enchanting_table", "enchantment_table",
                      "binding_table", "arcane_table", "alchemy_table", "bounty_board")):
        return "STATION_OR_STATEFUL_RESOURCE", "Identified cooking/cutting/crafting workstation, not ordinary supplies"
    vanilla_station = identity.startswith("minecraft:") and tail in {
        "loom", "stonecutter", "grindstone", "anvil", "chipped_anvil", "damaged_anvil",
        "lectern", "beacon", "conduit", "chest", "barrel", "hopper", "dispenser", "dropper",
        "crafting_table", "smithing_table", "enchanting_table",
        "brewing_stand", "furnace", "smoker", "blast_furnace", "ender_chest",
    }
    if vanilla_station or STATEFUL.search(tail) and (
        identity in blocks or words & {"backpack", "bag", "pouch"} or "tool_belt" in tail
    ):
        return "CONTAINER_OR_CONFIGURED_BLOCK", "Inventory-bearing container or configured block state is not represented by a plain item ID"
    if identity in blocks:
        names = [name for name, jar in aliases.get(re.sub(r"[^a-z0-9]", "", tail.lower()), [])
                 if namespace_jars is None or jar in namespace_jars.get(identity.split(":")[0], [])]
        if any(is_stateful_block(n, headers) for n in names):
            return "BLOCK_ENTITY", "Actual block superclass/interface implements block-entity state"
    return None


def base_worth(identity):
    if identity in EGGS:
        return 50
    tag_values = {"minecraft:planks": 30, "minecraft:logs": 120, "minecraft:logs_that_burn": 120,
                  "minecraft:stone_crafting_materials": 25, "minecraft:saplings": 60,
                  "forge:eggs": 50, "forge:string": 80, "forge:leather": 200,
                  "forge:crops/wheat": 60}
    if identity in tag_values:
        return tag_values[identity]
    rare = {"minecraft:enchanted_golden_apple": 64000, "minecraft:totem_of_undying": 50000,
            "minecraft:nether_star": 128000, "minecraft:trident": 40000,
            "minecraft:dragon_breath": 10000, "minecraft:wither_skeleton_skull": 40000,
            "minecraft:heart_of_the_sea": 15000}
    ordinary = {"minecraft:stone": 25, "minecraft:cobblestone": 25, "minecraft:dirt": 15,
                "minecraft:sand": 20, "minecraft:gravel": 25, "minecraft:egg": 50,
                "minecraft:beef": 100, "minecraft:porkchop": 145, "minecraft:chicken": 70,
                "minecraft:string": 80, "minecraft:leather": 200, "minecraft:wheat": 60,
                "minecraft:ender_pearl": 1000, "minecraft:blaze_rod": 1000,
                "minecraft:blaze_powder": 500}
    if identity in rare or identity in ordinary:
        return rare.get(identity, ordinary.get(identity))
    words = set(re.split(r"[_/]", identity.split(":")[1]))
    values = {"netherite": 64000, "diamond": 10000, "emerald": 1000, "gold": 1000,
              "iron": 1000, "copper": 150, "steel": 1200, "silver": 800,
              "desh": 8000, "ostrum": 16000, "calorite": 32000, "quartz": 150,
              "amethyst": 150, "redstone": 100, "glowstone": 300, "obsidian": 500}
    value = max([values[word] for word in words if word in values] or [120])
    if words & values.keys():
        if "nugget" in words:
            value /= 9
        elif "block" in words:
            value *= 9
        elif words & {"chestplate", "chest"}:
            value *= 8
        elif "leggings" in words:
            value *= 7
        elif words & {"helmet", "head"}:
            value *= 5
        elif words & {"boots", "feet"}:
            value *= 4
    return value


def value_proofs(proofs, data):
    tags = {}
    for name, (_, value) in data.items():
        if "/tags/items/" in name:
            namespace, tail = name.split("/tags/items/")
            tags[namespace.split("/")[1] + ":" + tail[:-5]] = value.get("values", [])
    def ingredient_worth(value, seen=frozenset()):
        if isinstance(value, list):
            choices = [ingredient_worth(v, seen) for v in value]
            return min((v for v in choices if v is not None), default=None)
        if isinstance(value, str):
            return ingredient_worth({"item": value}, seen)
        if not isinstance(value, dict):
            return None
        if "ingredient" in value:
            worth = ingredient_worth(value["ingredient"], seen)
            amount = value.get("amount", value.get("count", 1))
            return worth * amount if worth is not None and isinstance(amount, (int, float)) else worth
        if "item" in value:
            identity = item_id(value["item"])
            if not identity or identity not in proofs and not identity.startswith("minecraft:"):
                return None
            return proofs.get(identity, {}).get("unitWorth", base_worth(identity)) * value.get("count", value.get("amount", 1))
        if "tag" in value:
            identity = item_id(value["tag"])
            if identity in seen:
                return None
            choices = []
            for v in tags.get(identity, []):
                v = v if isinstance(v, str) else v.get("id", "")
                choices.append({"tag": v[1:]} if v.startswith("#") else {"item": v})
            worth = ingredient_worth(choices, seen | {identity})
            if identity in VANILLA_TAGS:
                return min(worth, base_worth(identity)) if worth is not None else base_worth(identity)
            return worth
        return None
    for identity, proof in sorted(proofs.items(), key=lambda row: (row[1]["depth"], row[0])):
        worth = base_worth(identity)
        if proof.get("kind") == "recipe":
            ingredients = proof["ingredients"]
            prices = [ingredient_worth(v) for v in ingredients]
            count = proof.get("output_count", 1)
            if prices and all(v is not None for v in prices):
                worth = sum(prices) / max(count, 1)
        proof["unitWorth"] = round(max(worth, 1), 2)


def resources():
    """Read installed, enabled jars only; never read the user's root config overlays."""
    data, models, classes, mods, blocks = {}, {}, {}, {"minecraft", "forge"}, set()
    world_refs, model_sources = {}, defaultdict(list)
    namespace_jars = defaultdict(set)
    references = re.compile(rb"[a-z0-9_.-]+:[a-z0-9_./-]+")
    for path in sorted((ROOT / "mods").glob("*.jar")):
        if path.name.endswith("-compat-1.20.1-1.0.0.jar"):
            continue
        with ZipFile(path) as jar:
            for name in jar.namelist():
                if name.endswith(".class"):
                    bytecode = jar.read(name)
                    classes[name] = (path.name, bytecode)
                    if "worldgen" in name.lower() or "Feature" in name or "Biome" in name:
                        world_refs.update({v.decode(): f"{path.name}!{name}" for v in references.findall(bytecode)})
                elif name.endswith(".nbt") and "/structures/" in name:
                    payload = jar.read(name)
                    if payload.startswith(b"\x1f\x8b"):
                        try:
                            payload = gzip.decompress(payload)
                        except (EOFError, gzip.BadGzipFile, zlib.error):
                            continue
                    world_refs.update({v.decode(): f"{path.name}!{name}" for v in references.findall(payload)})
                elif name.endswith(".json") and name.startswith(("data/", "assets/")):
                    try:
                        value = json.loads(jar.read(name))
                    except (ValueError, UnicodeDecodeError):
                        continue
                    if name.startswith("assets/"):
                        namespace_jars[name.split("/")[1]].add(path.name)
                        if "/models/item/" in name:
                            parts = name.split("/models/item/")
                            identity = f"{parts[0].split('/')[1]}:{parts[1][:-5]}"
                            models[identity] = value
                            model_sources[identity].append(f"{path.name}!{name}")
                        if "/blockstates/" in name:
                            namespace, tail = name.split("/blockstates/")
                            blocks.add(f"{namespace.split('/')[1]}:{tail[:-5]}")
                    else:
                        if "/worldgen/" in name:
                            world_refs.update({v.decode(): f"{path.name}!{name}"
                                               for v in references.findall(json.dumps(value).encode())})
                        if name in data and ("/tags/" in name or name.endswith("global_loot_modifiers.json")) and not value.get("replace", False):
                            key = "entries" if name.endswith("global_loot_modifiers.json") else "values"
                            combined = data[name][1].get(key, []) + value.get(key, [])
                            value[key] = list({json.dumps(v, sort_keys=True): v for v in combined}.values())
                        data[name] = (path.name, value)
            if "META-INF/mods.toml" in jar.namelist():
                metadata = tomllib.loads(jar.read("META-INF/mods.toml").decode())
                mods.update(mod["modId"] for mod in metadata.get("mods", []))
    mods.update("__tag__" + name.split("/tags/items/")[0].split("/")[1] + ":" +
                name.split("/tags/items/")[1][:-5]
                for name, (_, value) in data.items() if "/tags/items/" in name and value.get("values"))
    mods.update("__item__" + identity for identity in models)
    quark = tomllib.loads((ROOT / "server-config/config/quark-common.toml").read_text())
    flags = quark_flags(quark)
    mods.update("__quark_known__" + name for name in flags)
    mods.update("__quark__" + name for name, enabled in flags.items() if enabled)
    disabled_items = {}
    for name, (_, recipe) in data.items():
        if "/recipes/" not in name or "/advancements/" in name:
            continue
        disabled_flags = [c["flag"] for c in recipe.get("conditions", [])
                          if c.get("type") == "quark:flag" and flags.get(c["flag"]) is False]
        if disabled_flags:
            disabled_items.update({item_id(output): f"Quark feature disabled: {', '.join(disabled_flags)}"
                                   for output in recipe_outputs(recipe)
                                   if item_id(output) and item_id(output).startswith("quark:")})
    data["__acquisition_world_refs__"] = ("installed jar placement resources", world_refs)
    data["__disabled_bounty_items__"] = ("authoritative server config and recipe flags", disabled_items)
    data["__namespace_jars__"] = ("asset namespace ownership", {k: sorted(v) for k, v in namespace_jars.items()})
    data["__item_model_sources__"] = ("item-model witnesses, not acquisition proofs", dict(model_sources))
    return data, models, classes, mods, blocks


def conditions_met(value, mods, condition=False):
    if isinstance(value, list):
        states = [conditions_met(v, mods, True) for v in value]
        return False if False in states else True if all(v is True for v in states) else None
    if not isinstance(value, dict):
        return True
    if not condition:
        return conditions_met(value.get("conditions", []), mods, True)
    kind = value.get("type", "")
    if kind in ("forge:mod_loaded", "neoforge:mod_loaded"):
        return value["modid"] in mods
    if kind == "forge:false":
        return False
    if kind == "forge:true":
        return True
    if kind == "forge:tag_empty":
        tag = item_id(value["tag"])
        return tag not in VANILLA_TAGS and "__tag__" + tag not in mods
    if kind == "forge:item_exists":
        if "item" not in value:
            return None
        identity = item_id(value["item"])
        return (identity.startswith("minecraft:") and identity not in VANILLA_FORBIDDEN or
                "__item__" + identity in mods)
    if kind == "quark:flag":
        return ("__quark__" + value["flag"] in mods
                if "__quark_known__" + value["flag"] in mods else None)
    if kind == "forge:not":
        state = conditions_met(value["value"], mods, True)
        return None if state is None else not state
    if kind == "forge:or":
        states = [conditions_met(v, mods, True) for v in value["values"]]
        return True if True in states else False if all(v is False for v in states) else None
    if kind == "forge:and":
        return conditions_met(value["values"], mods, True)
    if kind and kind not in ("forge:conditional", "delightful:enabled"):
        return None
    return conditions_met(value.get("conditions", []), mods)


def recipes(data, mods):
    for name, (jar, value) in sorted(data.items()):
        if "/recipes/" not in name or "/advancements/" in name or not conditions_met(value, mods):
            continue
        if value.get("type") == "forge:conditional":
            for branch in value.get("recipes", []):
                if conditions_met(branch, mods) and isinstance(branch.get("recipe"), dict):
                    yield name, jar, branch["recipe"]
                    break
        else:
            yield name, jar, value


def replace_egg(value, output=False):
    if isinstance(value, list):
        return [replace_egg(v, output) for v in value]
    if not isinstance(value, dict):
        return value
    if not output and value.get("item") == "minecraft:egg":
        return {**{k: replace_egg(v) for k, v in value.items() if k != "item"}, "tag": "forge:eggs"}
    return {k: replace_egg(v, output or k in OUTPUT_KEYS) for k, v in value.items()}


def acquisition(data, models, mods, classes):
    tags = {}
    for name, (_, value) in data.items():
        if "/tags/items/" in name:
            namespace, tail = name.split("/tags/items/")
            tags[f"{namespace.split('/')[1]}:{tail[:-5]}"] = value.get("values", [])
    proofs = {egg: {"source": "renewable chicken laying", "depth": 0} for egg in EGGS}
    world_refs = data.get("__acquisition_world_refs__", ("", {}))[1]
    namespace_jars = data.get("__namespace_jars__", ("", {}))[1]
    entity_headers, entity_aliases = {}, defaultdict(list)
    for path, (jar, bytecode) in classes.items():
        if "entit" not in path.lower() or any(v in path for v in ("Renderer", "Model", "Layer")):
            continue
        identity, parent, _ = class_header(bytecode)
        entity_headers[identity] = parent
        stem = re.sub(r"^Entity|Entity$", "", identity.rsplit("/", 1)[1])
        entity_aliases[re.sub(r"[^a-z0-9]", "", stem.lower())].append((identity, jar, path))
    def living(identity, seen=frozenset()):
        if not identity or identity in seen:
            return False
        if identity.startswith(("net/minecraft/world/entity/animal/", "net/minecraft/world/entity/monster/",
                                "net/minecraft/world/entity/npc/", "net/minecraft/world/entity/ambient/")) or identity in {
            "net/minecraft/world/entity/Mob", "net/minecraft/world/entity/LivingEntity",
            "net/minecraft/world/entity/PathfinderMob", "net/minecraft/world/entity/FlyingMob",
            "net/minecraft/world/entity/AgeableMob", "net/minecraft/world/entity/TamableAnimal"
        }:
            return True
        return living(entity_headers.get(identity), seen | {identity})
    entity_sources = {}
    reachable_tables = set()
    global_modifiers = set(data.get("data/forge/loot_modifiers/global_loot_modifiers.json", ("", {}))[1].get("entries", []))
    for name, (_, value) in data.items():
        if "/loot_tables/" in name:
            namespace, tail = name.split("/loot_tables/")
            namespace = namespace.split("/")[1]
            table_id = namespace + ":" + tail[:-5]
            if "/entities/" in name:
                matches = entity_aliases.get(re.sub(r"[^a-z0-9]", "", tail[len("entities/"):-5]), [])
                witness = next((f"{jar}!{path}" for identity, jar, path in matches
                                if jar in namespace_jars.get(namespace, []) and living(identity)), None)
                if witness or namespace == "minecraft":
                    reachable_tables.add(table_id)
                    entity_sources[table_id] = witness or "Minecraft 1.20.1 native entity loot dispatch"
            if table_id in world_refs:
                reachable_tables.add(table_id)
            if "/blocks/" in name:
                block_id = namespace + ":" + tail[len("blocks/"):-5]
                if block_id in world_refs:
                    reachable_tables.add(table_id)
    for _ in range(len(reachable_tables) + 1):
        before = len(reachable_tables)
        for name, (_, value) in data.items():
            if "/loot_tables/" not in name:
                continue
            namespace, tail = name.split("/loot_tables/")
            if namespace.split("/")[1] + ":" + tail[:-5] not in reachable_tables:
                continue
            def children(node):
                if isinstance(node, dict):
                    if node.get("type") in ("loot_table", "minecraft:loot_table"):
                        reachable_tables.add(node["name"])
                    for child in node.values():
                        children(child)
                elif isinstance(node, list):
                    for child in node:
                        children(child)
            children(value)
        if len(reachable_tables) == before:
            break
    native_meat = "net/mcreator/butchersdelightfoods/procedures/CustomDropsProcedure.class"
    if native_meat in classes:
        jar, bytecode = classes[native_meat]
        for candidate in re.findall(rb'summon item ~ ~ ~ \{Item:\{id:"([^"]+)"', bytecode):
            candidate = candidate.decode()
            if candidate in models and candidate.startswith("butchersdelightfoods:"):
                proofs[candidate] = {"source": f"{jar}!{native_meat}", "depth": 0}
    for name, (jar, value) in sorted(data.items()):
        if "/loot_modifiers/" in name:
            namespace, tail = name.split("/loot_modifiers/")
            modifier_id = namespace.split("/")[1] + ":" + tail[:-5]
            candidate = item_id(value.get("item"))
            possible = all(c.get("condition") != "minecraft:random_chance" or c.get("chance", 0) > 0
                           for c in value.get("conditions", []))
            if modifier_id in global_modifiers and value.get("type", "").endswith(":add_item") and candidate and (
                candidate in models or candidate.startswith("minecraft:")
            ) and possible:
                proofs.setdefault(candidate, {"source": f"{jar}!{name}", "depth": 0, "kind": "global_loot_modifier",
                                               "conditions": value.get("conditions", [])})
        if "/loot_tables/" not in name or not conditions_met(value, mods):
            continue
        namespace, tail = name.split("/loot_tables/")
        table_id = namespace.split("/")[1] + ":" + tail[:-5]
        if table_id not in reachable_tables:
            continue
        def visit(node, inherited_functions=()):
            if isinstance(node, list):
                for child in node:
                    visit(child, inherited_functions)
            elif isinstance(node, dict):
                for constraint in node.get("conditions", []):
                    kind = constraint.get("condition", constraint.get("type", ""))
                    if kind.startswith(("forge:", "quark:")) and not conditions_met(
                        {**constraint, "type": kind}, mods, True
                    ):
                        return
                    if kind == "minecraft:random_chance" and constraint.get("chance", 0) <= 0:
                        return
                functions = (*inherited_functions, *node.get("functions", []))
                for function in functions:
                    if function.get("function") in ("minecraft:set_count", "set_count"):
                        count = function.get("count", 1)
                        maximum = count.get("max", 1) if isinstance(count, dict) else count
                        if isinstance(maximum, (int, float)) and maximum <= 0:
                            return
                candidate = node.get("name") if node.get("type") in ("minecraft:item", "item") else None
                if candidate and (candidate in models or candidate.startswith("minecraft:")) and not UNOBTAINABLE.search(candidate.split(":")[1]):
                    words = set(candidate.split(":")[1].split("_"))
                    if candidate.startswith("quark:") and "crab" in words and "__quark__crabs" not in mods:
                        return
                    safe_functions = {"minecraft:set_count", "minecraft:looting_enchant",
                                      "minecraft:furnace_smelt", "set_count", "looting_enchant",
                                      "furnace_smelt"}
                    if candidate not in VANILLA_FORBIDDEN and all(
                        f.get("function") in safe_functions for f in functions
                    ):
                        proofs.setdefault(candidate, {"source": f"{jar}!{name}", "depth": 0,
                                                      "kind": "loot", "functions": list(functions),
                                                      "loot_table": table_id,
                                                      "entity_class_source": entity_sources.get(table_id),
                                                      "placement_source": world_refs.get(table_id, world_refs.get(
                                                          namespace.split("/")[1] + ":" + tail[len("blocks/"):-5]
                                                      )) if "/blocks/" in name else world_refs.get(table_id),
                                                      "conditions": node.get("conditions", [])})
                for child in node.values():
                    visit(child, functions)
        visit(value)

    def ingredient_depth(value, seen=frozenset()):
        if isinstance(value, list):
            depths = [ingredient_depth(v, seen) for v in value]
            viable = [d for d in depths if d is not None]
            return min(viable) if viable else None
        if isinstance(value, str):
            return ingredient_depth({"item": value}, seen)
        if not isinstance(value, dict) or "nbt" in value or value.get("type") in ("forge:nbt", "forge:partial_nbt"):
            return None
        if "ingredient" in value:
            return ingredient_depth(value["ingredient"], seen)
        if "item" in value:
            candidate = item_id(value["item"])
            if candidate in VANILLA_FORBIDDEN or candidate in VANILLA_ADMIN or UNOBTAINABLE.search(candidate.split(":")[1]):
                return None
            if candidate in data.get("__disabled_bounty_items__", ("", {}))[1]:
                return None
            if candidate in VANILLA_NON_SUPPLY_ROOTS or candidate.startswith("minecraft:infested_"):
                return proofs.get(candidate, {}).get("depth")
            if candidate.startswith("minecraft:"):
                return 0
            return proofs.get(candidate, {}).get("depth")
        if "tag" in value:
            tag = item_id(value["tag"])
            if tag in VANILLA_TAGS:
                return 0
            if tag in seen:
                return None
            choices = []
            for entry in tags.get(tag, []):
                entry = entry if isinstance(entry, str) else entry.get("id", "")
                choices.append({"tag": entry[1:]} if entry.startswith("#") else {"item": entry})
            return ingredient_depth(choices, seen | {tag})
        return None

    active_recipes = list(recipes(data, mods))
    for _ in range(len(active_recipes) + 1):
        changed = False
        for name, jar, recipe in active_recipes:
            kind = recipe.get("type", "")
            supported = (kind.startswith(("minecraft:", "farmersdelight:", "dungeonsdelight:")) or
                         kind in {"crafting_shaped", "crafting_shapeless", "create:pressing",
                                  "create:milling", "create:crushing", "create:mixing", "create:compacting",
                                  "create:cutting", "create:deploying", "create:splashing", "create:haunting",
                                  "create:mechanical_crafting", "ad_astra:compressing", "ad_astra:alloying",
                                  "ad_astra:nasa_workbench", "valhelsia_structures:axe_crafting",
                                  "graveyard:ossuary_carving", "mekanism:crushing",
                                  "mekanism:enriching", "mekanism:smelting", "mekanism:combining",
                                  "mekanism:sawing", "immersiveengineering:crusher",
                                  "immersiveengineering:metal_press", "immersiveengineering:sawmill"})
            if not supported or any(k in recipe for k in ("fluidInput", "gasInput", "chemicalInput",
                                                          "fluid", "fluid_input", "gas", "chemical")):
                continue
            inputs = recipe_inputs(recipe)
            if not inputs:
                continue
            depths = [ingredient_depth(v) for v in inputs]
            for output in recipe_outputs(recipe):
                result = item_id(output)
                if not result or (result not in models and not result.startswith("minecraft:")) or result in proofs or result in VANILLA_ADMIN or UNOBTAINABLE.search(result.split(":")[1]):
                    continue
                nbt_result = isinstance(output, dict) and output.get("nbt")
                if all(d is not None for d in depths) and not nbt_result and result not in VANILLA_FORBIDDEN:
                    cost_inputs = [recipe["key"][c] for row in recipe["pattern"] for c in row if c != " "] if (
                        "key" in recipe and "pattern" in recipe
                    ) else inputs
                    proofs[result] = {"source": f"{jar}!{name}", "depth": 1 + max(depths),
                                      "kind": "recipe", "type": kind, "ingredients": cost_inputs,
                                      "output_count": output.get("count", 1) if isinstance(output, dict) else 1}
                    changed = True
        if not changed:
            break
    return proofs


def entry(candidate, decree, reward=False, proof=None):
    words = set(candidate.split(":")[1].split("_"))
    equipment = decree in ("armorer", "toolsmith", "mapper", "leatherer", "librarian", "supplies")
    worth = 1800 if equipment else 120
    rarity, reputation = ("UNCOMMON" if equipment else "COMMON"), 0
    if "diamond" in candidate or "osseous" in candidate or "netherite" in candidate:
        worth = 80000 if "netherite" in candidate else 16000
        rarity, reputation = "EPIC", 20
    elif any(token in candidate for token in ("space", "hazmat", "desh", "steel", "royal_jelly")):
        worth = 8000 if equipment else 1000
        rarity, reputation = "RARE", 10
    elif decree == "inventor":
        worth = 900 if "ingot" in candidate or "plate" in candidate else 250
    if proof:
        worth = proof.get("unitWorth", worth)
        if worth >= 50000:
            rarity, reputation = "EPIC", max(reputation, 20)
        elif worth >= 12000:
            rarity, reputation = "RARE", max(reputation, 10)
        if proof.get("type", "").startswith(("create:", "mekanism:", "immersiveengineering:", "ad_astra:")):
            rarity, reputation = "RARE", max(reputation, 10)
        if proof.get("kind") == "loot" and "/chests/" in proof["source"] and not words & TOKENS["farmer"]:
            rarity, reputation = "RARE", max(reputation, 10)
    if words & {"calorite", "ostrum", "antimatter", "pellet", "uranium", "polonium", "plutonium"}:
        rarity, reputation = "EPIC", max(reputation, 20)
    building_supply = decree == "supplies" and proof and proof.get("block_item") and worth < 12000
    maximum = (8 if reward else 32) if building_supply else 1 if equipment or worth >= 12000 else (4 if reward else 8)
    minimum = 2 if maximum > 1 else 1
    if candidate in EGGS:
        minimum, maximum = (2, 8) if reward else (8, 32)
    result = {
        "type": "item", "content": candidate, "amount": {"min": minimum,
        "max": maximum}, "unitWorth": worth,
        "weightMult": 0.1, "rarity": rarity, "timeMult": 3.0,
    }
    if reputation:
        result["repRequired"] = reputation
    return result


def build():
    data, models, classes, mods, blocks = resources()
    proofs = acquisition(data, models, mods, classes)
    value_proofs(proofs, data)
    headers, aliases = block_types(classes)
    generated, evidence, counts, exclusions, applicable = {}, {}, {}, {}, {}
    choices = defaultdict(list)
    for candidate, proof in sorted(proofs.items()):
        proof["block_item"] = candidate in blocks
        disabled = data["__disabled_bounty_items__"][1].get(candidate)
        reason = ("CONFIG_DISABLED", disabled) if disabled else exclusion_reason(
            candidate, blocks, headers, aliases, data["__namespace_jars__"][1]
        )
        if reason:
            exclusions[candidate] = {"code": reason[0], "reason": reason[1],
                                     "proven": True, "source": proof["source"]}
            continue
        words = set(candidate.split(":")[1].split("_"))
        categories = [decree for decree in DECREES if words & TOKENS[decree] or
                      EXACT_CATEGORY.get(candidate) == decree]
        if candidate in blocks:
            categories = [decree for decree in categories if
                          decree == "shepherd" and words & {"wool", "carpet"} or
                          decree == "librarian" and "candle" in words]
        if "inventor" in categories and words & {"armor", "horse"}:
            categories.remove("inventor")
        if "farmer" in categories and words == {"ice", "shard"}:
            categories.remove("farmer")
        if not categories:
            categories = ["supplies"]
        for category in categories:
            choices[category].append(candidate)
        evidence[candidate] = proof
        applicable[candidate] = list(DECREES) if categories == ["supplies"] else categories
    def emit(name, value):
        generated[name] = value
    for name, (_, value) in data.items():
        if "/tags/items/" in name and "minecraft:egg" in [
            v if isinstance(v, str) else v.get("id") for v in value.get("values", [])
        ]:
            emit(name, {"replace": False, "values": EGGS[1:]})
        if "/tags/entity_types/" in name:
            animals = []
            for v in value.get("values", []):
                animals.extend(ANIMALS.get(v if isinstance(v, str) else v.get("id"), []))
            if animals:
                emit(name, {"replace": False, "values": sorted(set(animals))})
    emit("data/forge/tags/items/eggs.json", {"replace": False, "values": EGGS})
    emit("data/compat_farmersdelight/tags/items/eggs.json", {"replace": False, "values": EGGS})
    egg_recipes = []
    for name, jar, recipe in recipes(data, mods):
        changed = replace_egg(recipe)
        if changed != recipe:
            emit(name, changed)
            egg_recipes.append({"recipe": name, "jar": jar, "type": recipe["type"]})
    for recipe_type, suffix in (("farmersdelight:cooking", "cooking_pot"),
                                 ("dungeonsdelight:monster_cooking", "monster_pot")):
        emit(f"data/bounty_backport_compat/recipes/egg_in_{suffix}.json", {
            "type": recipe_type, "ingredients": [{"tag": "forge:eggs"}],
            "result": {"item": "farmersdelight:fried_egg"}, "cookingtime": 100,
            "experience": 0.1, "recipe_book_tab": "misc",
        })
    for decree in (*DECREES, "supplies"):
        selected = choices[decree]
        for reward in (False, True):
            suffix = "rews" if reward else "objs"
            pool = f"compat_{decree}_{suffix}"
            content = {f"bounty_backport_compat_{pool}_{c.replace(':', '_').replace('/', '_')}":
                       entry(c, decree, reward, proofs[c]) for c in selected}
            emit(f"data/bounty_backport_compat/bounty_pools/compat/{pool}.json",
                 {"replace": False, "weightMult": min(0.25, 25.0 / max(len(selected), 1)) if decree == "supplies" else 1.0,
                  "content": content})
        if decree in DECREES:
            emit(f"data/bounty_backport_compat/bounty_decrees/compat/{decree}.json", {
                "replace": False, "objectives": [f"compat_{decree}_objs", "compat_hunts_objs", "compat_supplies_objs"],
                "rewards": [f"compat_{decree}_rews", "compat_supplies_rews"],
            })
        counts[decree] = len(selected)
    # This jar shipped a NeoForge-only biome modifier directory on Forge. Its
    # SpawnSetup registers placement predicates, not biome spawns.
    hunts = {}
    for entity in ("goblin", "dart_goblin"):
        identity = f"fangs_n_claws:{entity}"
        class_name = f"net/raptorzizi/fangs_n_claws/entity/{entity}/{'Goblin' if entity == 'goblin' else 'DartGoblin'}Entity.class"
        if class_name not in classes or b"net/minecraft/world/entity/monster/Monster" not in classes[class_name][1]:
            raise ValueError(f"Missing verified hostile entity class for {identity}")
        emit(f"data/bounty_backport_compat/forge/biome_modifier/{entity}_spawns.json", {
            "type": "forge:add_spawns", "biomes": "#minecraft:is_overworld",
            "spawners": {"type": identity, "weight": 8 if entity == "goblin" else 4,
                         "minCount": 1, "maxCount": 2},
        })
        hunts["bounty_backport_compat_" + entity] = {"type": "entity", "content": identity, "amount": {"min": 1, "max": 3},
                         "unitWorth": 450, "weightMult": 0.15, "timeMult": 12.0,
                         "rarity": "UNCOMMON"}
    emit("data/bounty_backport_compat/bounty_pools/compat/compat_hunts_objs.json",
         {"replace": False, "content": hunts})
    for root in (SOURCE, PACK):
        for path in (root / "data").rglob("*.json"):
            if path.relative_to(root).as_posix() not in generated:
                path.unlink()
    for name, value in sorted(generated.items()):
        write_json(SOURCE / name, value)
        write_json(PACK / name, value)
    (PACK / "pack.mcmeta").write_bytes((SOURCE / "pack.mcmeta").read_bytes())
    selected_mods = sorted({candidate.split(":")[0] for candidate in evidence})
    recipe_mods = sorted({item_id(output).split(":")[0] for _, _, r in recipes(data, mods)
                          for output in recipe_outputs(r) if item_id(output) in models and
                          not item_id(output).startswith("minecraft:")})
    source_index, non_item_outputs = candidate_sources(data, mods)
    for identity, sources in data["__item_model_sources__"][1].items():
        source_index.setdefault(identity, []).extend({"kind": "item_model", "source": source} for source in sources)
    for identity, proof in proofs.items():
        if not any(v["source"] == proof["source"] for v in source_index.get(identity, [])):
            source_index.setdefault(identity, []).append({"source": proof["source"], "kind": proof.get("kind", "native behavior")})
    for identity in sorted(i for i in source_index if i and i not in evidence and i not in exclusions):
        reason = exclusion_reason(identity, blocks, headers, aliases, data["__namespace_jars__"][1])
        disabled = data["__disabled_bounty_items__"][1].get(identity)
        sources = source_index[identity]
        recipe_sources = [v for v in sources if v["kind"] == "recipe"]
        active = [v for v in recipe_sources if v["active"]]
        if disabled:
            reason = ("CONFIG_DISABLED", disabled)
        elif identity not in models and not identity.startswith("minecraft:"):
            reason = ("NO_INSTALLED_REGISTRATION_WITNESS", "No installed item-model/registration witness; commonly an absent optional integration")
        elif recipe_sources and not active and not reason:
            reason = ("INACTIVE_OR_UNRESOLVED_CONDITION", "Inactive or unsupported recipe conditions; no acquisition proof")
        elif active and all(v["nbt"] for v in active) and not reason:
            reason = ("REQUIRES_NBT_STATE", "Every active recipe requires or produces NBT state not represented by a bare item bounty")
        elif active and all(v["fluid_or_chemical"] for v in active) and not reason:
            reason = ("UNPROVEN_FLUID_OR_CHEMICAL_CHAIN", "All active routes require fluid/gas/chemical acquisition not verified by the item-only graph")
        elif all(v["kind"] == "item_model" for v in sources) and not reason:
            reason = ("NO_SUPPORTED_ACQUISITION_EVIDENCE", "Item model exists, but no supported recipe, reachable plain-item loot or inspected native acquisition behavior proves obtainability")
        elif not recipe_sources and not reason:
            reason = ("UNPROVEN_LOOT_REACHABILITY_OR_STATE", "Loot table has no verified placement/living-entity witness or applies unsupported state-changing loot functions")
        elif not reason:
            reason = ("UNPROVEN_INPUT_OR_SERIALIZER", "No complete ingredient closure or supported item-only serializer; inspect the recorded input IDs/tags")
        exclusions[identity] = {"code": reason[0], "reason": reason[1], "proven": False,
                                "sources": [v["source"] for v in sources],
                                "input_references": sorted({v for route in active for v in route.get("references", [])})}
    missing_proven = sorted(set(proofs) - set(evidence) - set(exclusions))
    if missing_proven:
        raise ValueError(f"Unaccounted acquisition-proven candidates: {missing_proven}")
    write_json(SOURCE / "coverage.json", {
        "decrees": {d: counts[d] for d in DECREES}, "shared_supply_items": counts["supplies"],
        "selected_items": evidence, "applicable_decrees": applicable,
        "covered_item_namespaces": selected_mods,
        "recipe_namespaces_without_safe_candidates": sorted(set(recipe_mods) - set(selected_mods)),
        "excluded_recipe_items": exclusions,
        "candidate_sources": source_index,
        "non_item_recipe_outputs": non_item_outputs,
        "audit": {"proven_candidates": len(proofs), "covered_proven_candidates": len(evidence),
                  "candidate_items": len(source_index), "non_item_recipe_outputs": len(non_item_outputs),
                  "explicitly_excluded_proven_candidates": sum(v["proven"] for v in exclusions.values()),
                  "unaccounted_proven_candidates": missing_proven,
                  "exclusion_categories": dict(sorted(Counter(v["code"] for v in exclusions.values()).items())),
                  "proven_exclusion_categories": dict(sorted(Counter(v["code"] for v in exclusions.values() if v["proven"]).items())),
                  "baseline": {"selected_items": 197, "graph_proven_mod_candidates": 2760,
                               "uncovered_graph_proven_mod_candidates": 2563,
                               "diversity_cap_exclusions": 243, "unclassified_exclusions": 344,
                               "exclusion_categories": {"inactive_or_unknown_condition": 910,
                                                        "creative_station_unique_nbt_name": 340,
                                                        "all_block_items": 3564,
                                                        "unproven_inputs_or_serializer": 897,
                                                        "diversity_cap": 243, "unclassified": 344},
                               "proven_gap_breakdown": {"block_items": 1805, "unclassified": 344,
                                                       "diversity_cap": 243, "loot_only_absent_from_audit": 129,
                                                       "inactive_recipe_but_other_acquisition_evidence": 42}}},
        "egg_recipes": egg_recipes, "kill_entities": [v["content"] for v in hunts.values()],
        "policy": "Every acquisition-proven item is mapped to all applicable profession pools or shared delivery pools available to all twelve decrees, unless explicitly excluded for creative/admin, disabled content, station/container/NBT or unique progression. No diversity cap or unclassified-item exclusion. Item models are acquisition-audit candidates, never obtainability proofs. Loot requires placement/living-class evidence; complete spawn/config/world reachability and procedural-only acquisition are not claimed. Native registry/block-entity checks still apply.",
        "runtime_safety": "Native PoolEntry.isValid vetoes bounty_backport_compat-marked BlockItem/EntityBlock entries on every roll/reload. KubeJS verifies registrations and reports any typed runtime exclusions. Unrelated native/addon bounty entries are unchanged.",
    })
    entries = [SOURCE / "pack.mcmeta", *(SOURCE / "META-INF").glob("*")]
    entries.extend((SOURCE / "coremods").glob("*.js"))
    entries.extend(path for path in (SOURCE / "data").rglob("*") if path.is_file())
    server_jar = ROOT / "mods" / JAR_NAME
    with ZipFile(server_jar, "w", ZIP_DEFLATED) as jar:
        for path in sorted(entries):
            info = ZipInfo(path.relative_to(SOURCE).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            jar.writestr(info, path.read_bytes())
    (ROOT / "client-config/mods" / JAR_NAME).write_bytes(server_jar.read_bytes())
    for folder in ("server_scripts", "startup_scripts"):
        script = Path(f"kubejs/{folder}/bounty_backport_compat.js")
        destination = ROOT / "client-config" / script
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / "server-config" / script).read_bytes())
    config = Path("config/bountiful/bountiful.json")
    (ROOT / "client-config" / config).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "client-config" / config).write_bytes((ROOT / "server-config" / config).read_bytes())
    print(f"Bounties: {counts}; {len(evidence)} items across {len(selected_mods)} namespaces; "
          f"{len(egg_recipes)} egg recipes; {len(hunts)} obtainable hunts")


if __name__ == "__main__":
    build()
