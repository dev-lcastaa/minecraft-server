import collections
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "server-config/new-world/datapacks/cooking-compat"
BUILD = ROOT / "tools/cooking-compat/build.py"
SPEC = importlib.util.spec_from_file_location("cooking_builder", BUILD)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def load_recipes():
    recipes = {}
    for path in (PACK / "data").glob("*/recipes/**/*.json"):
        parts = path.relative_to(PACK / "data").parts
        recipes[parts[0] + ":" + "/".join(parts[2:])[:-5]] = json.loads(path.read_text())
    return recipes


def tag(name):
    namespace, path = name.split(":")
    return json.loads((PACK / f"data/{namespace}/tags/items/{path}.json").read_text())


class CookingCompatTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipes = load_recipes()
        cls.originals = BUILDER.catalog()
        cls.manifest = json.loads((ROOT / "tools/cooking-compat/manifest.json").read_text())

    def test_pack_and_generated_overlay(self):
        self.assertEqual(json.loads((PACK / "pack.mcmeta").read_text())["pack"]["pack_format"], 15)
        self.assertEqual(len(self.recipes), self.manifest["recipe_count"])
        for name in ("server_scripts/cooking_compat.js", "startup_scripts/cooking_compat.js",
                     "client_scripts/cooking_compat_tooltips.js"):
            self.assertEqual((ROOT / "server-config/kubejs" / name).read_bytes(),
                             (ROOT / "client-config/kubejs" / name).read_bytes())
        script = (ROOT / "server-config/kubejs/server_scripts/cooking_compat.js").read_text()
        self.assertNotIn("replaceInput", script)
        self.assertNotIn("replaceOutput", script)

    def test_schema_limits_and_private_fluid_registration(self):
        fluids = self.manifest["fluids"]
        for ident, recipe in self.recipes.items():
            with self.subTest(id=ident):
                kind = recipe["type"]
                if kind == "farmersrespite:brewing":
                    self.assertGreater(len(recipe["ingredients"]), 0)
                    self.assertLessEqual(len(recipe["ingredients"]), 2)
                    self.assertIn("brewingtime", recipe)
                    self.assertNotIn("cookingtime", recipe)
                    self.assertIn(recipe["result"]["fluid"], fluids)
                    self.assertEqual(recipe["base"]["count"], recipe["result"]["count"])
                    self.assertEqual(recipe["base"]["count"], 1000)
                    self.assertTrue(recipe["base"]["fluid"] == "minecraft:water"
                                    or recipe["base"]["fluid"] in fluids)
                elif kind == "farmersrespite:kettle_pouring":
                    self.assertIn(recipe["fluid"], fluids)
                    self.assertIn(recipe["amount"], (250, 1000))
                    self.assertEqual(recipe["output"]["count"], 1)
                    self.assertTrue(recipe["fluid"].endswith("_ready"))
                elif kind == "dungeonsdelight:monster_cooking":
                    self.assertLessEqual(len(recipe["ingredients"]), 6)
        startup = (ROOT / "server-config/kubejs/startup_scripts/cooking_compat.js").read_text()
        self.assertIn(".noBucket().noBlock()", startup)

    def test_kettle_chains_preserve_all_ingredients_yield_and_conditions(self):
        for ident, original in self.originals.items():
            if original.get("type") not in ("minecraft:crafting_shaped", "minecraft:crafting_shapeless", "farmersdelight:cooking"):
                continue
            result = original.get("result", {})
            if not isinstance(result, dict) or "juice" not in result.get("item", ""):
                continue
            with self.subTest(id=ident):
                actual = self.recipes[ident]
                self.assertEqual(actual["type"], "farmersrespite:brewing")
                container = original.get("container", {"item": "minecraft:glass_bottle"})
                expected = [i for i in BUILDER.ingredients(original) if i != {"item": container["item"]}]
                consumed = []
                while True:
                    self.assertEqual(actual.get("conditions"), original.get("conditions"))
                    consumed.extend(actual["ingredients"])
                    fluid = actual["result"]["fluid"]
                    if fluid.endswith("_ready"):
                        break
                    next_steps = [r for r in self.recipes.values()
                                  if r["type"] == "farmersrespite:brewing"
                                  and r["base"]["fluid"] == fluid]
                    self.assertEqual(len(next_steps), 1)
                    actual = next_steps[0]
                self.assertEqual(consumed, expected)
                pouring = [r for r in self.recipes.values()
                           if r["type"] == "farmersrespite:kettle_pouring" and r["fluid"] == fluid]
                self.assertEqual(len(pouring), 1)
                pour = pouring[0]
                self.assertEqual(pour["container"], container)
                expected_result = deepcopy(result)
                expected_result["count"] = 1
                self.assertEqual(pour["output"], expected_result)
                self.assertEqual(actual["result"]["count"] // pour["amount"], result.get("count", 1))
                self.assertEqual(pour.get("conditions"), original.get("conditions"))

    def test_all_non_kettle_juice_producers_replaced_or_removed(self):
        juices = set(self.manifest["juice_items"])
        for ident, recipe in self.originals.items():
            outputs = recipe.get("results", []) + [recipe.get("result", {}), recipe.get("output", {})]
            if any(isinstance(o, dict) and o.get("item") in juices for o in outputs):
                if recipe.get("type") in ("farmersrespite:brewing", "farmersrespite:kettle_pouring"):
                    continue
                with self.subTest(id=ident):
                    self.assertTrue(ident in self.manifest["removals"]
                                    or self.recipes.get(ident, {}).get("type") == "farmersrespite:brewing")
        self.assertIn("delightful:integration/create/filling/long_prickly_pear_juice",
                      self.manifest["removals"])
        # Existing native fluid recipes are not gratuitously deleted.
        self.assertNotIn("farmersrespite:brewing/melon_juice_from_water", self.recipes)
        self.assertNotIn("delightful:integration/farmersrespite/pouring/prickly_pear_juice",
                         self.manifest["removals"])

    def test_ender_food_output_and_containers_preserved_not_nonfood(self):
        untouched = {"chorus_crate", "chorus_fruit_from_crate", "shulker_bowl", "endstone_stove"}
        foods = []
        for ident, original in self.originals.items():
            if not ident.startswith("endersdelight:"):
                continue
            kind = original["type"]
            name = ident.split(":")[1]
            if kind not in ("farmersdelight:cooking", "minecraft:crafting_shaped", "minecraft:crafting_shapeless"):
                continue
            if name in untouched:
                self.assertNotIn(ident, self.recipes)
                continue
            if name == "chorus_juice":
                self.assertEqual(self.recipes[ident]["type"], "farmersrespite:brewing")
                continue
            foods.append(ident)
            updated = self.recipes[ident]
            self.assertEqual(updated["type"], "dungeonsdelight:monster_cooking")
            self.assertEqual(updated["result"], original["result"])
            if kind == "farmersdelight:cooking":
                expected = deepcopy(original)
                expected["type"] = "dungeonsdelight:monster_cooking"
                self.assertEqual(updated, expected)
            else:
                inputs = deepcopy(updated["ingredients"])
                if name == "chorus_pie":
                    self.assertEqual(inputs.pop(0), {"item": "kubejs:chorus_pie_filling"})
                    first = self.recipes["cooking_compat:monster_cooking/chorus_pie_filling"]
                    inputs = first["ingredients"] + inputs
                if updated.get("container"):
                    inputs.append(updated["container"])
                self.assertEqual(collections.Counter(map(json.dumps, inputs)),
                                 collections.Counter(map(json.dumps, BUILDER.ingredients(original))))
        self.assertEqual(len(foods), 16)

    def test_tentacles_cross_mod_raw_cooked_and_glow(self):
        raw = set(tag("cooking_compat:raw_tentacles")["values"])
        cooked = set(tag("cooking_compat:cooked_tentacles")["values"])
        self.assertEqual(raw, {"miners_delight:tentacles", "oceanic_delight:squid_tentacles",
                               "oceanic_delight:glow_squid_tentacles"})
        self.assertEqual(cooked, {"miners_delight:baked_tentacles", "oceanic_delight:grilled_squid_tentacles"})
        self.assertFalse(raw & cooked)
        self.assertIn("miners_delight:tentacles", tag("forge:tentacles")["values"])
        self.assertTrue({"oceanic_delight:squid_tentacles", "oceanic_delight:grilled_squid_tentacles"}
                        <= set(tag("forge:foods/tentacles")["values"]))
        for ident in ("oceanic_delight:seafood_skewer", "oceanic_delight:squid_and_pickles",
                      "miners_delight:tentacles_on_a_stick", "miners_delight:cave_hamburger"):
            self.assertIn("cooking_compat:cooked_tentacles", json.dumps(self.recipes[ident]))
            self.assertEqual(self.recipes[ident]["result"], self.originals[ident]["result"])
        self.assertIn("cooking_compat:raw_tentacles", json.dumps(self.recipes["oceanic_delight:glow_squid_stew"]))
        for ident in self.recipes:
            self.assertNotIn("tentacles_smelting", ident)
            self.assertNotIn("baked_tentacles_smoking", ident)
        calamari = self.recipes["miners_delight:calamari_roll"]
        self.assertIn({"type": "forge:item_exists", "item": "culturaldelights:calamari_roll"},
                      calamari["conditions"])

    def test_cutting_is_lossy_and_not_duplicate(self):
        cutting = {i: r for i, r in self.recipes.items() if r["type"] == "farmersdelight:cutting"}
        self.assertEqual(len(cutting), 38)
        for ident, recipe in cutting.items():
            self.assertEqual(recipe["tool"], {"tag": "forge:tools/knives"})
            for old in self.originals.values():
                if old.get("type") == "farmersdelight:cutting":
                    self.assertNotEqual(recipe["ingredients"], old["ingredients"], ident)
        wool = cutting["cooking_compat:cutting/wool"]["result"][0]["count"]
        carpet = cutting["cooking_compat:cutting/carpet"]["result"][0]["count"]
        self.assertLess(wool, 4)
        self.assertLessEqual(3 * carpet, 2 * wool)
        self.assertEqual(cutting["cooking_compat:cutting/cobweb"]["result"][0]["count"], 1)
        for material in ("flax", "rope"):
            self.assertEqual(cutting[f"cooking_compat:cutting/{material}"]["result"][0]["count"], 1)

    def test_all_audited_cutting_candidates_covered_without_native_overlap(self):
        definitions, known, native_covered, expand = BUILDER.cutting_audit()
        audit = self.manifest["cutting_audit"]
        self.assertEqual(len(definitions), 684)
        self.assertEqual(len({d["source"] for d in definitions}), 673)
        self.assertEqual(audit["native_definition_count"], len(definitions))
        self.assertEqual(len(audit["cooked_meat_gaps"]), 15)
        new_inputs = set()
        for recipe in self.recipes.values():
            if recipe["type"] != "farmersdelight:cutting":
                continue
            if recipe["ingredients"] == [{"tag": "cooking_compat:unprocessed_saplings"}]:
                values = tag("cooking_compat:unprocessed_saplings")["values"]
                inputs = {v["id"] for v in values}
                self.assertTrue(all(v["required"] is False for v in values))
            else:
                inputs = expand(recipe["ingredients"])
            self.assertFalse(inputs & native_covered)
            self.assertFalse(inputs & new_inputs)
            new_inputs.update(inputs)
        for field in ("cooked_meat_gaps", "saplings_added"):
            self.assertTrue(set(audit[field]) <= new_inputs)
        self.assertTrue(set(audit["dye_processing_added"]) <= new_inputs)
        self.assertEqual(len(audit["saplings_added"]), 58)
        self.assertTrue(all(item.endswith("_sapling") or item == "minecraft:mangrove_propagule"
                            for item in audit["saplings_added"]))
        self.assertFalse(set(audit["tree_seeds_not_woody_saplings"]) & new_inputs)
        self.assertIn("minecraft:oak_sapling", audit["saplings_already_covered"])
        self.assertIn("minecraft:dark_oak_sapling", audit["saplings_already_covered"])
        # One tag recipe covers every wool/carpet colour, not just white.
        self.assertEqual(self.recipes["cooking_compat:cutting/wool"]["ingredients"], [{"tag": "minecraft:wool"}])
        self.assertEqual(self.recipes["cooking_compat:cutting/carpet"]["ingredients"], [{"tag": "minecraft:wool_carpets"}])
        for item in audit["dye_processing_added"]:
            ident = "cooking_compat:cutting/" + item.replace(":", "_") + "_dye"
            source = self.manifest["sources"][ident]
            self.assertEqual(self.recipes[ident].get("conditions"), self.originals[source].get("conditions"))

    def test_juice_definition_census_has_no_unexplained_omissions(self):
        names = set()
        displays = set()
        for path in (ROOT / "mods").glob("*.jar"):
            with ZipFile(path) as jar:
                for name in jar.namelist():
                    if not name.startswith("assets/") or not name.endswith("/lang/en_us.json"):
                        continue
                    for key in json.loads(jar.read(name)):
                        parts = key.split(".")
                        if len(parts) == 3 and parts[0] in ("item", "block") and "juice" in parts[2]:
                            ident = parts[1] + ":" + parts[2]
                            names.add(ident)
                            if parts[1] == "displaydelight":
                                displays.add(ident)
                                model = json.loads(jar.read(f"assets/displaydelight/models/item/{parts[2]}.json"))
                                self.assertTrue(model["parent"].startswith("displaydelight:block/"))
        self.assertEqual(len(names), 19)
        self.assertEqual(len(displays), 8)
        self.assertEqual(names - displays - {"mbackrooms:juice", "farmersrespite:strong_melon_juice"},
                         set(self.manifest["juice_items"]))
        for recipe in self.originals.values():
            outputs = recipe.get("results", []) + [recipe.get("result", {}), recipe.get("output", {})]
            self.assertFalse(any(isinstance(o, dict) and o.get("item") == "mbackrooms:juice" for o in outputs))
        # Backrooms' plain food item has no source production recipe to
        # migrate; no invented ingredient/container recipe is introduced.
        self.assertFalse(any("mbackrooms:juice" in json.dumps(r) for r in self.recipes.values()))

    def test_new_crossmod_cutting_item_ids_are_in_installed_jars(self):
        known = set()
        for path in (ROOT / "mods").glob("*.jar"):
            with ZipFile(path) as jar:
                for name in jar.namelist():
                    if name.startswith("assets/") and name.endswith("/lang/en_us.json"):
                        for key in json.loads(jar.read(name)):
                            parts = key.split(".")
                            if len(parts) == 3 and parts[0] in ("item", "block"):
                                known.add(parts[1] + ":" + parts[2])
        for recipe in self.recipes.values():
            if recipe["type"] != "farmersdelight:cutting":
                continue
            for entry in recipe["ingredients"] + recipe["result"]:
                item = entry.get("item")
                if item and not item.startswith("minecraft:"):
                    self.assertIn(item, known)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for KubeJS callback fixtures")
    def test_kubejs_callbacks_execute_with_exact_ids_and_are_idempotent(self):
        fixture = r"""
const fs = require('fs'), vm = require('vm')
let recipes = new Map(), removed = [], registrations = {}, callback, missing = new Set(), warnings = []
let builder = {displayName(){return this},thinTexture(){return this},noBucket(){return this},noBlock(){return this},texture(){return this}}
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), {
  StartupEvents:{registry(type, cb){ cb({create(id){ registrations[id] = type; return builder }}) }}
})
vm.runInNewContext(fs.readFileSync(process.argv[2], 'utf8'), {
  ServerEvents:{recipes(cb){callback = cb}},
  Item:{of(id){return {isEmpty(){return missing.has(id)}}}},
  console:{warn(message){warnings.push(message)}}
})
let event = {remove(filter){if(!filter.id)throw Error('not ID based');removed.push(filter.id);recipes.delete(filter.id)},
  custom(value){return {id(id){recipes.set(id,value)}}}}
callback(event);let first = JSON.stringify([...recipes]);callback(event)
if (first !== JSON.stringify([...recipes])) throw Error('reload changed recipes')
const missingRecipes = {
  'miners_delight:calamari_roll':'culturaldelights:calamari_roll',
  'abnormals_delight:pickerelweed_juice':'upgrade_aquatic:pickerelweed',
  'delightful:food/prickly_pear_juice_from_cooked_prickly_pear':'ecologics:cooked_prickly_pear'
}
missing = new Set(Object.values(missingRecipes))
let preserved = new Map(Object.keys(missingRecipes).map(id => [id, 'original']))
let missingRemoved = []
callback({remove(filter){missingRemoved.push(filter.id);preserved.delete(filter.id)},
  custom(value){return {id(id){preserved.set(id,value)}}}})
for (const [id, item] of Object.entries(missingRecipes)) {
  if (preserved.get(id) !== 'original' || missingRemoved.includes(id)) throw Error('Missing recipe was replaced: ' + id)
  if (!warnings.some(w => w.includes(id) && w.includes(item))) throw Error('Missing warning: ' + id)
}
console.log(JSON.stringify({recipes:Object.fromEntries(recipes), registrations, removed}))
"""
        output = subprocess.check_output([
            "node", "-e", fixture,
            str(ROOT / "server-config/kubejs/startup_scripts/cooking_compat.js"),
            str(ROOT / "server-config/kubejs/server_scripts/cooking_compat.js"),
        ], text=True)
        result = json.loads(output)
        self.assertEqual(result["recipes"], self.recipes)
        for ident in self.manifest["fluids"]:
            self.assertEqual(result["registrations"][ident], "fluid")
        self.assertEqual(result["registrations"]["kubejs:chorus_pie_filling"], "item")
        for ident in self.recipes:
            self.assertIn(ident, result["removed"])
        for ident in self.manifest["removals"]:
            self.assertIn(ident, result["removed"])
        self.assertFalse(set(self.manifest["removals"]) & set(self.recipes))

    def test_actual_rhino_recipe_registry_guard(self):
        classpath = os.environ.get("COOKING_RHINO_TEST_CLASSPATH")
        if not classpath:
            self.skipTest("Set COOKING_RHINO_TEST_CLASSPATH to Gson and Commons Lang JARs")
        java = shutil.which("java")
        self.assertTrue(java, "Java is required for Rhino recipe verification")
        result = subprocess.run(
            [java, "-cp", str(ROOT / "mods/rhino-forge-2001.2.3-build.10.jar") + os.pathsep + classpath,
             str(ROOT / "tests/CookingCompatRhinoTest.java"),
             str(ROOT / "server-config/kubejs/server_scripts/cooking_compat.js")],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Rhino cooking registry guard passed", result.stdout)

    def test_installed_forge_item_exists_condition(self):
        jar = os.environ.get("FORGE_UNIVERSAL_JAR")
        if not jar:
            self.skipTest("Set FORGE_UNIVERSAL_JAR to the server's Forge universal JAR")
        java = shutil.which("java")
        self.assertTrue(java, "Java is required for Forge condition verification")
        def disassemble(name):
            return subprocess.check_output([
                java, "-m", "jdk.jdeps/com.sun.tools.javap.Main", "-c", "-p",
                "-classpath", jar, name,
            ], text=True)
        condition = disassemble("net.minecraftforge.common.crafting.conditions.ItemExistsCondition")
        self.assertIn("String item_exists", condition)
        self.assertIn("ForgeRegistries.ITEMS", condition)
        self.assertIn("IForgeRegistry.containsKey", condition)
        serializer = disassemble("net.minecraftforge.common.crafting.conditions.ItemExistsCondition$Serializer")
        self.assertIn("String item", serializer)
        helper = disassemble("net.minecraftforge.common.crafting.CraftingHelper")
        self.assertIn("ICondition.test", helper)

    @unittest.skipUnless(shutil.which("java"), "Java is required for serializer bytecode verification")
    def test_installed_serializer_contracts_not_guessed(self):
        def disassemble(jar, name):
            return subprocess.check_output([
                "java", "-m", "jdk.jdeps/com.sun.tools.javap.Main", "-c", "-p",
                "-classpath", str(ROOT / "mods" / jar), name,
            ], text=True)
        kettle = disassemble("farmersrespite-1.20.1-2.1.2.jar",
                             "umpaz.farmersrespite.common.crafting.KettleRecipe$Serializer")
        self.assertIn("Too many ingredients for brewing recipe! The max is 2", kettle)
        self.assertIn("String brewingtime", kettle)
        self.assertNotIn("String cookingtime", kettle)
        self.assertIn("String fluid", kettle)
        pouring = disassemble("farmersrespite-1.20.1-2.1.2.jar",
                              "umpaz.farmersrespite.common.crafting.KettlePouringRecipe$Serializer")
        self.assertIn("CraftingHelper.getItemStack", pouring)
        self.assertIn("String container", pouring)
        self.assertIn("String output", pouring)
        monster = disassemble("forge-dungeonsdelight-1.20.1-1.3.1.jar",
                              "net.yirmiri.dungeonsdelight.common.block.entity.container.MonsterPotRecipe$Serializer")
        self.assertIn("Too many ingredients for cooking recipe! The max is 6", monster)
        self.assertIn("CraftingHelper.getItemStack", monster)
        helper = disassemble("kubejs-forge-2001.6.5-build.26.jar",
                             "dev.latvian.mods.kubejs.platform.forge.RecipeForgeHelper")
        self.assertIn("CraftingHelper.processConditions", helper)
        tank = disassemble("farmersrespite-1.20.1-2.1.2.jar",
                           "umpaz.farmersrespite.common.block.entity.KettleBlockEntity")
        capacity = tank.split("private net.minecraftforge.fluids.capability.templates.FluidTank createFluidTank();")[1]
        self.assertIn("sipush        1000", capacity.split("private ", 1)[0])
        processing = tank.split("private boolean processBrewing(")[1].split("private ", 1)[0]
        # Output is a new FluidStack(recipe.getFluidOut(), tank.getFluidAmount()),
        # not the declared recipe amount. A 250mB base would amplify yield.
        self.assertIn("FluidTank.getFluidAmount:()I", processing)
        self.assertIn('FluidStack."<init>":(Lnet/minecraftforge/fluids/FluidStack;I)V', processing)


if __name__ == "__main__":
    unittest.main()
