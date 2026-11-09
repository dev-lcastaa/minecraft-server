import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/lunch-basket-compat"
JAR_NAME = "lunch-basket-compat-1.20.1-1.0.0.jar"
SCRIPT = Path("kubejs/server_scripts/lunch_basket_foods.js")


class LunchBasketCompatTest(unittest.TestCase):
    def test_built_jars_have_1_20_1_pack_metadata(self):
        for path in (ROOT / "mods" / JAR_NAME, ROOT / "client-config/mods" / JAR_NAME):
            with self.subTest(jar=path), ZipFile(path) as jar:
                metadata = json.loads(jar.read("pack.mcmeta"))
                self.assertEqual(metadata["pack"]["pack_format"], 15)
                self.assertEqual(metadata["pack"]["description"], "Lunch Basket Food Compatibility")

    def test_built_jars_match_sources_and_each_other(self):
        server = ROOT / "mods" / JAR_NAME
        self.assertEqual(server.read_bytes(), (ROOT / "client-config/mods" / JAR_NAME).read_bytes())
        with ZipFile(server) as jar:
            expected = {
                path.relative_to(SOURCE).as_posix(): path.read_bytes()
                for folder in ("META-INF", "coremods", "data")
                for path in (SOURCE / folder).rglob("*") if path.is_file()
            }
            expected["pack.mcmeta"] = (SOURCE / "pack.mcmeta").read_bytes()
            self.assertEqual(set(jar.namelist()), set(expected))
            for name, content in expected.items():
                self.assertEqual(jar.read(name), content, name)
            coremods = json.loads(jar.read("META-INF/coremods.json"))
            self.assertIn(coremods["lunch_basket_foods"], jar.namelist())
            tag = json.loads(jar.read("data/serverfixes/tags/items/lunch_basket_foods.json"))
            self.assertFalse(tag["replace"])
            self.assertEqual(
                {entry["id"] for entry in tag["values"]},
                {"#forge:foods", "#forge:cakes", "#farmersdelight:feasts", "#farmersdelight:pies"},
            )
            self.assertTrue(all(entry["required"] is False for entry in tag["values"]))

    def test_client_singleplayer_script_matches_server(self):
        self.assertEqual(
            (ROOT / "server-config" / SCRIPT).read_bytes(),
            (ROOT / "client-config" / SCRIPT).read_bytes(),
        )

    def test_registry_script_covers_hidden_future_and_placeable_foods(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is required to execute the KubeJS registry-script fixture")
        fixture = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function type(name, parent = null) {
  return {getName: () => name, getSuperclass: () => parent};
}
class BlockItem {
  constructor(blockType) { this.blockType = blockType; }
  getBlock() { return {getClass: () => this.blockType}; }
  isEdible() { return false; }
}
const ordinaryBlock = type('net.minecraft.world.level.block.Block');
const items = {
  'minecraft:apple': {isEdible: () => true},
  'butchersdelightfoods:raw_meat': {isEdible: () => true},
  'new_mod:hidden_food': {isEdible: () => true},
  'new_mod:unusual_animation_food': {isEdible: () => true},
  'minecraft:cake': new BlockItem(type('net.minecraft.world.level.block.CakeBlock', ordinaryBlock)),
  'new_mod:feast': new BlockItem(type('new_mod.Feast', type('vectorwing.farmersdelight.common.block.FeastBlock', ordinaryBlock))),
  'new_mod:pie': new BlockItem(type('new_mod.Pie', type('vectorwing.farmersdelight.common.block.PieBlock', ordinaryBlock))),
  'oceanicdelight:sponge_cake': new BlockItem(type('net.mcreator.oceanicdelight.block.SpongeCakeBlock', ordinaryBlock)),
  'endersdelight:pie': new BlockItem(type('com.axedgaming.endersdelight.block.PieBlock', ordinaryBlock)),
  'mynethersdelight:magma_cake': new BlockItem(type('com.soytutta.mynethersdelight.common.block.MagmaCakeBlock', ordinaryBlock)),
  'supplementaries:pancake': new BlockItem(type('net.mehvahdjukaar.supplementaries.common.block.blocks.PancakeBlock', ordinaryBlock)),
  'displaydelight:plated_food': new BlockItem(type('com.jkvin114.displaydelight.block.SmallPlatedFoodBlock', ordinaryBlock)),
  'minecraft:stone': new BlockItem(ordinaryBlock),
  'minecraft:diamond_sword': {isEdible: () => false},
  'supplementaries:lunch_basket': new BlockItem(type('net.mehvahdjukaar.supplementaries.common.block.blocks.LunchBoxBlock', ordinaryBlock)),
  'doggytalents:food_bowl': new BlockItem(type('doggytalents.common.block.FoodBowlBlock', ordinaryBlock))
};
let handler;
let loaded;
let tagged = [];
let rejectFood = false;
const messages = [];
const context = {
  Java: {loadClass: name => {
    if (name === 'net.mehvahdjukaar.supplementaries.common.items.LunchBoxItem') {
      return {canAcceptItem: stack => !rejectFood && tagged.includes(stack.id)};
    }
    assert.equal(name, 'net.minecraft.world.item.BlockItem');
    return BlockItem;
  }},
  ServerEvents: {tags: (registry, callback) => {
    assert.equal(registry, 'item');
    handler = callback;
  }, loaded: callback => { loaded = callback; }},
  Item: {
    getTypeList: () => Object.keys(items),
    getList: () => { throw Error('Creative-only enumeration misses hidden foods'); },
    of: id => ({id, item: items[id]})
  },
  Ingredient: {of: tag => {
    assert.equal(tag, '#serverfixes:lunch_basket_foods');
    return {itemIds: {forEach: callback => tagged.forEach(callback), size: () => tagged.length}};
  }},
  console: {info: message => messages.push(message)}
};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
for (let reload = 0; reload < 2; reload++) {
  const entries = [];
  handler({add: (tag, ids) => {
    assert.equal(tag, 'serverfixes:lunch_basket_foods');
    entries.push(...ids);
  }});
  const expected = Object.keys(items).filter(id => ![
    'minecraft:stone', 'minecraft:diamond_sword',
    'supplementaries:lunch_basket', 'doggytalents:food_bowl'
  ].includes(id));
  assert.deepEqual(entries.sort(), expected.sort());
  tagged = entries;
}
assert.equal(messages.length, 2);
assert.ok(messages.every(message => message.includes('12 foods')));
loaded();
assert.ok(messages[2].includes('validated 12 food-tag items'));
rejectFood = true;
assert.throws(loaded, /validation failed: rejected/);
tagged = [];
assert.throws(loaded, /food tag is empty/);
"""
        subprocess.run(
            [node, "-e", fixture, str(ROOT / "server-config" / SCRIPT)],
            check=True, cwd=ROOT, capture_output=True, text=True,
        )

    def test_actual_supplementaries_bytecode_transform(self):
        classpath = os.environ.get("LUNCH_BASKET_TEST_CLASSPATH")
        if not classpath:
            self.skipTest("Set LUNCH_BASKET_TEST_CLASSPATH to Nashorn and ASM JARs for bytecode execution")
        java = os.environ.get("JAVA", shutil.which("java"))
        self.assertTrue(java, "A JDK is required for the Java source-launcher integration test")
        jars = list((ROOT / "mods").glob("supplementaries-*.jar"))
        self.assertEqual(len(jars), 1)
        subprocess.run(
            [java, "-cp", classpath, str(ROOT / "tests/LunchBasketCoremodTest.java"),
             str(SOURCE / "coremods/lunch_basket_foods.js"), str(jars[0])],
            check=True, cwd=ROOT, capture_output=True, text=True,
        )


if __name__ == "__main__":
    unittest.main()
