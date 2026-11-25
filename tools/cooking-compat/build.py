#!/usr/bin/env python3
"""Build the cooking overlay from the installed jars, without editing shared files."""
from copy import deepcopy
from collections import defaultdict
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "server-config/new-world/datapacks/cooking-compat"


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def catalog():
    recipes = {}
    for path in sorted((ROOT / "mods").glob("*.jar")):
        with ZipFile(path) as jar:
            for name in sorted(jar.namelist()):
                parts = name.split("/")
                if len(parts) < 4 or parts[0] != "data" or parts[2] != "recipes" or not name.endswith(".json"):
                    continue
                try:
                    data = json.loads(jar.read(name))
                except (ValueError, UnicodeDecodeError):
                    continue
                ident = parts[1] + ":" + "/".join(parts[3:])[:-5]
                if data.get("type") == "forge:conditional":
                    # Preserve the original enable/mod/tag conditions on the
                    # actual serializer rather than registering a wrapper.
                    if len(data.get("recipes", [])) != 1:
                        continue
                    wrapped = data["recipes"][0]
                    data = deepcopy(wrapped["recipe"])
                    data["conditions"] = wrapped["conditions"]
                recipes[ident] = data
    return recipes


def ingredients(recipe):
    if recipe["type"] == "minecraft:crafting_shaped":
        return [deepcopy(recipe["key"][char]) for row in recipe["pattern"] for char in row if char != " "]
    return deepcopy(recipe["ingredients"])


def cutting_audit():
    definitions = []
    tags = defaultdict(list)
    known = set()
    for path in sorted((ROOT / "mods").glob("*.jar")):
        with ZipFile(path) as jar:
            for name in jar.namelist():
                if name.startswith("assets/") and name.endswith("/lang/en_us.json"):
                    for key in json.loads(jar.read(name)):
                        parts = key.split(".")
                        if len(parts) == 3 and parts[0] in ("item", "block") and parts[1] != "minecraft":
                            known.add(parts[1] + ":" + parts[2])
                parts = name.split("/")
                if not name.endswith(".json") or len(parts) < 4 or parts[0] != "data":
                    continue
                if parts[2:4] == ["tags", "items"]:
                    data = json.loads(jar.read(name))
                    ident = parts[1] + ":" + "/".join(parts[4:])[:-5]
                    if data.get("replace"):
                        tags[ident] = []
                    tags[ident].extend(data["values"])
                if parts[2] == "recipes":
                    try:
                        data = json.loads(jar.read(name))
                    except ValueError:
                        continue
                    for recipe in [data] + [r.get("recipe", {}) for r in data.get("recipes", [])]:
                        if recipe.get("type") == "farmersdelight:cutting":
                            definitions.append({"source": name, "recipe": recipe})
    vanilla_saplings = {
        "minecraft:" + name for name in
        ("oak_sapling", "spruce_sapling", "birch_sapling", "jungle_sapling",
         "acacia_sapling", "dark_oak_sapling", "cherry_sapling", "mangrove_propagule")
    }
    tags["minecraft:saplings"].extend(sorted(vanilla_saplings))
    known.update(vanilla_saplings | {"minecraft:charcoal", "minecraft:chorus_fruit"})

    def expand(value, seen=None):
        seen = set() if seen is None else seen
        if isinstance(value, list):
            return set().union(*(expand(v, seen) for v in value)) if value else set()
        if isinstance(value, dict):
            if "item" in value:
                return {value["item"]}
            if "id" in value:
                return expand(value["id"], seen)
            if "tag" in value:
                return expand("#" + value["tag"], seen)
            return set()
        if isinstance(value, str):
            if not value.startswith("#"):
                return {value}
            ident = value[1:]
            if ident in seen:
                return set()
            return expand(tags.get(ident, []), seen | {ident})
        return set()

    covered = set().union(*(expand(d["recipe"]["ingredients"]) for d in definitions))
    return definitions, known, covered, expand


def build():
    originals = catalog()
    replacements = {}
    removals = []
    fluids = {}
    provenance = {}
    juice_items = set()
    monster_items = set()
    items = {}
    native_cutting, known_items, covered_cutting, expand_ingredient = cutting_audit()
    candidate_audit = {}

    def add(ident, data, source=None):
        replacements[ident] = data
        if source:
            provenance[ident] = source

    def tag(ident, values):
        namespace, name = ident.split(":")
        dump(PACK / f"data/{namespace}/tags/items/{name}.json", {"replace": False, "values": values})

    raw = ["oceanic_delight:squid_tentacles", "oceanic_delight:glow_squid_tentacles", "miners_delight:tentacles"]
    cooked = ["oceanic_delight:grilled_squid_tentacles", "miners_delight:baked_tentacles"]
    tag("cooking_compat:raw_tentacles", raw)
    tag("cooking_compat:cooked_tentacles", cooked)
    tag("forge:tentacles", ["miners_delight:tentacles"])
    tag("forge:foods/tentacles", raw[:2] + cooked[:1])
    # Do not broaden the native smelting inputs: that creates two competing
    # furnace recipes for the same raw item.
    for ident, data in originals.items():
        if ident.split(":")[0] not in ("oceanic_delight", "miners_delight", "minersdelight"):
            continue
        if data.get("type") not in ("minecraft:crafting_shaped", "minecraft:crafting_shapeless", "farmersdelight:cooking"):
            continue

        def exchange(value):
            if isinstance(value, list):
                return [exchange(v) for v in value]
            if isinstance(value, dict):
                if value.get("item") in raw:
                    return {"tag": "cooking_compat:raw_tentacles"}
                if value.get("item") in cooked:
                    return {"tag": "cooking_compat:cooked_tentacles"}
                return {key: exchange(val) for key, val in value.items()}
            return value

        updated = deepcopy(data)
        for field in ("ingredients", "key"):
            if field in updated:
                updated[field] = exchange(updated[field])
        if updated != data:
            result = updated.get("result", {})
            if isinstance(result, dict) and isinstance(result.get("item"), str):
                result_id = result["item"]
                if result_id.split(":")[0] != ident.split(":")[0]:
                    condition = {"type": "forge:item_exists", "item": result_id}
                    conditions = updated.setdefault("conditions", [])
                    if condition not in conditions:
                        conditions.append(condition)
            add(ident, updated, ident)

    def cutting(name, ingredient, output, count):
        add("cooking_compat:cutting/" + name, {
            "type": "farmersdelight:cutting", "ingredients": [ingredient],
            "tool": {"tag": "forge:tools/knives"},
            "result": [{"item": output, "count": count}],
        })

    # String -> wool uses four string; two wool -> three carpets. These
    # deliberately lossy yields cannot multiply string via crafting loops.
    cutting("cobweb", {"item": "minecraft:cobweb"}, "minecraft:string", 1)
    cutting("wool", {"tag": "minecraft:wool"}, "minecraft:string", 2)
    cutting("carpet", {"tag": "minecraft:wool_carpets"}, "minecraft:string", 1)
    cutting("flax", {"item": "supplementaries:flax"}, "minecraft:string", 1)
    cutting("rope", {"item": "supplementaries:rope"}, "minecraft:string", 1)
    # Mirror shipped raw butchering yields after cooking, with no extra bone
    # rolls and no second recipe for already-covered raw meat.
    thermal = defaultdict(set)
    for recipe in originals.values():
        if recipe.get("type") in ("minecraft:smelting", "minecraft:smoking", "minecraft:campfire_cooking"):
            ingredient = recipe.get("ingredient", {})
            if isinstance(ingredient, dict) and "item" in ingredient and isinstance(recipe.get("result"), str):
                thermal[ingredient["item"]].add(recipe["result"])
    meat_outputs = {
        "minecraft:beef": "minecraft:cooked_beef",
        "minecraft:porkchop": "minecraft:cooked_porkchop",
        "minecraft:mutton": "minecraft:cooked_mutton",
        "minecraft:chicken": "minecraft:cooked_chicken",
        "minecraft:rabbit": "minecraft:cooked_rabbit",
        "minecraft:cod": "minecraft:cooked_cod",
        "minecraft:salmon": "minecraft:cooked_salmon",
        "farmersdelight:minced_beef": "farmersdelight:cooked_minced_beef",
        "farmersdelight:bacon": "farmersdelight:cooked_bacon",
        "farmersdelight:chicken_cuts": "farmersdelight:cooked_chicken_cuts",
        "farmersdelight:cod_slice": "farmersdelight:cooked_cod_slice",
        "farmersdelight:salmon_slice": "farmersdelight:cooked_salmon_slice",
    }
    cooked_meats = {}
    for native in native_cutting:
        recipe = native["recipe"]
        meat = [result for result in recipe["result"] if result.get("item") in meat_outputs]
        if len(meat) != 1:
            continue
        result = meat[0]
        for raw in expand_ingredient(recipe["ingredients"]):
            for cooked_meat in thermal[raw] - covered_cutting:
                if cooked_meat in known_items:
                    cooked_meats[cooked_meat] = (meat_outputs[result["item"]], result.get("count", 1))
    for meat, (output, count) in cooked_meats.items():
        cutting(meat.split(":")[1], {"item": meat}, output, count)
    candidate_audit["cooked_meat_gaps"] = sorted(cooked_meats)

    plantable = (expand_ingredient({"tag": "minecraft:saplings"}) & known_items) - covered_cutting
    saplings = sorted(item for item in plantable if item.endswith("_sapling") or item == "minecraft:mangrove_propagule")
    tag("cooking_compat:unprocessed_saplings", [{"id": item, "required": False} for item in saplings])
    cutting("saplings", {"tag": "cooking_compat:unprocessed_saplings"}, "minecraft:stick", 1)
    candidate_audit["saplings_added"] = saplings
    candidate_audit["tree_seeds_not_woody_saplings"] = sorted(plantable - set(saplings))
    candidate_audit["saplings_already_covered"] = sorted(expand_ingredient({"tag": "minecraft:saplings"}) & covered_cutting)

    # Audit every existing one-input dye craft, not just a chosen flower list.
    # Subtract all native cutting inputs, including arrays and recursively
    # resolved tags. Ambiguous fruits/materials with conflicting dye recipes
    # are deliberately not assigned an arbitrary cutting output.
    dyes = defaultdict(set)
    dye_sources = {}
    for source, recipe in originals.items():
        if recipe.get("type") not in ("minecraft:crafting_shaped", "minecraft:crafting_shapeless"):
            continue
        output = recipe.get("result", {})
        if not isinstance(output, dict) or not output.get("item", "").endswith("_dye"):
            continue
        inputs = ingredients(recipe)
        if len(inputs) == 1:
            for item in (expand_ingredient(inputs) & known_items) - covered_cutting:
                dyes[item].add((output["item"], output.get("count", 1)))
                dye_sources.setdefault(item, (source, recipe.get("conditions")))
    candidate_audit["dye_processing_added"] = {}
    candidate_audit["ambiguous_dyes_not_added"] = {}
    for item, outputs in sorted(dyes.items()):
        if len(outputs) != 1:
            candidate_audit["ambiguous_dyes_not_added"][item] = sorted(outputs)
            continue
        output, count = next(iter(outputs))
        name = item.replace(":", "_") + "_dye"
        cutting(name, {"item": item}, output, count)
        source, conditions = dye_sources[item]
        ident = "cooking_compat:cutting/" + name
        provenance[ident] = source
        if conditions:
            replacements[ident]["conditions"] = deepcopy(conditions)
        candidate_audit["dye_processing_added"][item] = {"item": output, "count": count}

    non_food = {"chorus_crate", "chorus_fruit_from_crate", "endstone_stove", "shulker_bowl"}
    for ident, recipe in originals.items():
        if not ident.startswith("endersdelight:"):
            continue
        kind = recipe.get("type")
        if kind == "farmersdelight:cooking":
            updated = deepcopy(recipe)
            updated["type"] = "dungeonsdelight:monster_cooking"
            add(ident, updated, ident)
            monster_items.add(recipe["result"]["item"])
        elif kind in ("minecraft:crafting_shaped", "minecraft:crafting_shapeless"):
            name = ident.split(":")[1]
            if name in non_food or name == "chorus_juice":
                continue
            inputs = ingredients(recipe)
            updated = {
                "type": "dungeonsdelight:monster_cooking", "ingredients": inputs,
                "result": deepcopy(recipe["result"]), "cookingtime": 200,
                "experience": 1.0, "recipe_book_tab": "meals",
            }
            if {"item": "endersdelight:shulker_bowl"} in inputs:
                inputs.remove({"item": "endersdelight:shulker_bowl"})
                updated["container"] = {"item": "endersdelight:shulker_bowl"}
            if len(inputs) > 6:
                if name != "chorus_pie":
                    raise ValueError(f"unhandled monster pot capacity: {ident}")
                # The original pie requires nine ingredients, while the
                # Monster Pot has six slots. Both steps remain Monster Pot
                # recipes and consume every original ingredient exactly once.
                mix = "kubejs:chorus_pie_filling"
                items[mix] = "Chorus Pie Filling"
                first = inputs[:6]
                updated["ingredients"] = [{"item": mix}] + inputs[6:]
                add("cooking_compat:monster_cooking/chorus_pie_filling", {
                    "type": "dungeonsdelight:monster_cooking", "ingredients": first,
                    "result": {"item": mix}, "cookingtime": 200,
                    "experience": 0, "recipe_book_tab": "misc",
                }, ident)
            add(ident, updated, ident)
            monster_items.add(recipe["result"]["item"])

    # Kettle recipes only accept two item ingredients and fluid outputs.
    # Private, unbottleable intermediate fluids preserve larger recipes'
    # ingredient multiplicities without pretending Ingredient.count works.
    for ident, recipe in originals.items():
        result = recipe.get("result", {})
        if not isinstance(result, dict) or "juice" not in result.get("item", ""):
            continue
        if recipe.get("type") not in ("minecraft:crafting_shaped", "minecraft:crafting_shapeless", "farmersdelight:cooking"):
            continue
        juice_items.add(result["item"])
        inputs = ingredients(recipe)
        container = deepcopy(recipe.get("container", {"item": "minecraft:glass_bottle"}))
        inputs = [i for i in inputs if i != {"item": container["item"]}]
        if not inputs:
            raise ValueError(f"juice has no brewing ingredients: {ident}")
        servings = result.get("count", 1)
        # processBrewing keeps the entire tank's volume, regardless of the
        # recipe's declared result amount, while consuming ingredients once.
        # Require a full 1000 mB tank and divide it into the original yield;
        # 250 mB bases would otherwise quadruple a one-serving recipe.
        volume = 1000
        if volume % servings:
            raise ValueError(f"juice yield cannot divide kettle tank: {ident}")
        stem = ident.replace(":", "_").replace("/", "_")
        base = "minecraft:water"
        for index in range(0, len(inputs), 2):
            last = index + 2 >= len(inputs)
            fluid = "kubejs:juice_" + stem + ("_ready" if last else f"_stage_{index // 2 + 1}")
            fluids[fluid] = (result["item"].split(":")[1].replace("_", " ").title()
                             + ("" if last else " (Brewing)"))
            brew = {
                "type": "farmersrespite:brewing",
                "base": {"fluid": base, "count": volume},
                "result": {"fluid": fluid, "count": volume},
                "ingredients": inputs[index:index + 2],
                "brewingtime": recipe.get("cookingtime", 200),
                "experience": recipe.get("experience", 0.35) if last else 0,
            }
            if "conditions" in recipe:
                brew["conditions"] = deepcopy(recipe["conditions"])
            stage_id = ident if index == 0 else "cooking_compat:brewing/" + stem + f"_{index // 2 + 1}"
            add(stage_id, brew, ident)
            base = fluid
        # Batch output (e.g. four aloe juices) is poured one container at a
        # time. Never return four filled bottles for one empty bottle.
        pour_output = deepcopy(result)
        pour_output["count"] = 1
        pour = {
            "type": "farmersrespite:kettle_pouring", "fluid": base, "amount": volume // servings,
            "container": container, "output": pour_output,
        }
        if "conditions" in recipe:
            pour["conditions"] = deepcopy(recipe["conditions"])
        add("cooking_compat:pouring/" + stem, pour, ident)

    for recipe in originals.values():
        outputs = recipe.get("results", []) + [recipe.get("result", {}), recipe.get("output", {})]
        for output in outputs:
            item = output.get("item", "") if isinstance(output, dict) else ""
            if "juice" in item and not item.startswith("farmersrespite:"):
                juice_items.add(item)

    # Existing Delightful/Farmer's Respite brewing and pouring already use
    # the real kettle serializers and remain intact. Remove non-kettle
    # integrations by exact ID, never replaceInput/replaceOutput.
    for ident, recipe in originals.items():
        outputs = recipe.get("results", []) + [recipe.get("result", {}), recipe.get("output", {})]
        if any(isinstance(o, dict) and o.get("item") in juice_items for o in outputs):
            if ident not in replacements and recipe.get("type") not in ("farmersrespite:brewing", "farmersrespite:kettle_pouring"):
                removals.append(ident)

    dump(PACK / "pack.mcmeta", {"pack": {"pack_format": 15, "description": "Cross-mod cutting, kettle juices and Ender Monster Pot recipes"}})
    for path in (PACK / "data").glob("*/recipes/**/*.json"):
        parts = path.relative_to(PACK / "data").parts
        ident = parts[0] + ":" + "/".join(parts[2:])[:-5]
        if ident not in replacements:
            path.unlink()
    for ident, recipe in replacements.items():
        namespace, name = ident.split(":")
        dump(PACK / f"data/{namespace}/recipes/{name}.json", recipe)
    script = (
        "// Generated by tools/cooking-compat/build.py from installed recipes.\n"
        "// Remove/re-add by ID: KubeJS 2001.6.5 can skip schema-less replacements.\n"
        "const COOKING_COMPAT_RECIPES = " + json.dumps(replacements, indent=2, sort_keys=True) + "\n"
        "const COOKING_COMPAT_REMOVALS = " + json.dumps(sorted(removals)) + "\n"
        + Path(__file__).with_name("recipe_runtime.js").read_text()
    )
    startup = (
        "// Generated by tools/cooking-compat/build.py. Restart both sides after installing.\n"
        "// No buckets or placeable blocks: intermediate brews cannot bypass the kettle.\n"
        "const COOKING_COMPAT_FLUIDS = " + json.dumps(fluids, indent=2, sort_keys=True) + "\n"
        "StartupEvents.registry('fluid', event => {\n"
        "  Object.keys(COOKING_COMPAT_FLUIDS).forEach(id => {\n"
        "    event.create(id).displayName(COOKING_COMPAT_FLUIDS[id]).thinTexture(0xAB6699).noBucket().noBlock()\n"
        "  })\n"
        "})\n"
        "StartupEvents.registry('item', event => {\n"
        "  event.create('kubejs:chorus_pie_filling').displayName('Chorus Pie Filling').texture('endersdelight:item/chorus_pie')\n"
        "})\n"
    )
    tooltip = (
        "// Generated by tools/cooking-compat/build.py.\n"
        "ItemEvents.tooltip(event => {\n"
        "  event.add(" + json.dumps(sorted(juice_items)) + ", Text.gray(\"Brew in Farmer's Respite's Kettle; fill with water before each batch.\"))\n"
        "  event.add(" + json.dumps(sorted(monster_items)) + ", Text.darkPurple(\"Prepared in Dungeons Delight's Monster Pot.\"))\n"
        "  event.add('kubejs:chorus_pie_filling', Text.darkPurple('Monster Pot: add two sugar and one pie crust to finish.'))\n"
        "})\n"
    )
    for base in [ROOT / "server-config/kubejs", ROOT / "client-config/kubejs"]:
        for name, content in [("server_scripts/cooking_compat.js", script), ("startup_scripts/cooking_compat.js", startup),
                              ("client_scripts/cooking_compat_tooltips.js", tooltip)]:
            path = base / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    dump(ROOT / "tools/cooking-compat/manifest.json", {
        "sources": provenance, "removals": sorted(removals),
        "juice_items": sorted(juice_items), "monster_items": sorted(monster_items),
        "fluids": fluids, "items": items, "recipe_count": len(replacements),
        "cutting_audit": {
            "native_definition_count": len(native_cutting),
            "native_distinct_source_count": len({d["source"] for d in native_cutting}),
            "native_expanded_ingredient_count": len(covered_cutting),
            **candidate_audit,
        },
    })
    print(f"Built {len(replacements)} recipes, {len(fluids)} fluids; {len(juice_items)} juices, {len(monster_items)} Monster Pot foods.")


if __name__ == "__main__":
    build()
