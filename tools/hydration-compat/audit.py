"""Report declared drink outputs, including conditional bodies; not a live registry audit."""
import json
from pathlib import Path
import tomllib
from zipfile import ZipFile
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]


def audit():
    config = tomllib.loads((ROOT / "server-config/config/thirst/item_settings.toml").read_text())
    drinks = {entry[0] for entry in config["Drinks"]["drinks"]}
    seen, covered, conditional_drinks = set(), set(), set()
    serializers, shapes = Counter(), Counter()
    malformed, unsupported = [], []
    total = 0

    def recipe(data, location, conditional=False):
        nonlocal total
        if not isinstance(data, dict):
            return
        if data.get("type") == "forge:conditional":
            for branch in data["recipes"]:
                if "recipe" not in branch:
                    malformed.append({"location": location, "error": "Conditional branch has no recipe body"})
                    continue
                recipe(branch["recipe"], location, True)
        for key in ("result", "output", "results"):
            values = data.get(key)
            for value in values if isinstance(values, list) else [values]:
                ident = value if isinstance(value, str) else value.get("item", value.get("id")) if isinstance(value, dict) else None
                if ident not in drinks:
                    continue
                total += 1
                seen.add(ident)
                if conditional:
                    conditional_drinks.add(ident)
                typ = data.get("type", "<missing>")
                serializers[typ] += 1
                shape = "string" if isinstance(value, str) else "item" if "item" in value else "id/tag"
                shapes[shape] += 1
                supported = shape != "string" or typ in {
                    "minecraft:smelting", "minecraft:campfire_cooking",
                    "minecraft:crafting_shaped", "minecraft:crafting_shapeless",
                }
                if supported:
                    covered.add(ident)
                else:
                    unsupported.append({"location": location, "type": typ, "item": ident, "shape": shape})

    for path in sorted((ROOT / "mods").glob("*.jar")):
        if path.name.endswith("-compat-1.20.1-1.0.0.jar"):
            continue
        with ZipFile(path) as jar:
            for name in sorted(jar.namelist()):
                if "/recipes/" not in name or not name.endswith(".json"):
                    continue
                try:
                    data = json.loads(jar.read(name))
                except json.JSONDecodeError as exc:
                    malformed.append({"location": f"{path.name}:{name}", "error": str(exc)})
                    continue
                recipe(data, f"{path.name}:{name}")
    return {
        "scope": "Vendor recipe catalog, including potentially inactive conditional recipes; excludes generated compatibility jars",
        "configured_drink_ids": len(drinks),
        "drink_ids_with_declared_recipes": len(seen),
        "drink_ids_with_supported_output_shapes": len(covered),
        "declared_drink_outputs": total,
        "conditional_drink_ids": len(conditional_drinks),
        "serializers": dict(sorted(serializers.items())),
        "output_shapes": dict(sorted(shapes.items())),
        "unsupported_output_shapes": unsupported,
        "configured_drinks_without_declared_recipe": sorted(drinks - seen),
        "malformed_vendor_json": malformed,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
