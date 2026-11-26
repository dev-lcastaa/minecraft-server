const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = process.argv[2];
class Tag {
  constructor(data = {}) { this.data = structuredClone(data); }
  putInt(key, value) { this.data[key] = value; }
  getInt(key) { return this.data[key] || 0; }
  copy() { return new Tag(this.data); }
  merge(tag) { Object.assign(this.data, structuredClone(tag.data)); }
  toString() { return JSON.stringify(this.data); }
}
class Potion {}
class Bowl {}
class Bath {}
class Stack {
  constructor(id, animation = 'NONE', tag = null, registered = false, item = {}) {
    Object.assign(this, {id, animation, tag, registered, item, count: 1});
  }
  isEmpty() { return this.id === 'minecraft:air'; }
  getUseAnimation() { return this.animation; }
  getOrCreateTag() { return this.tag ||= new Tag(); }
  // KubeJS exposes vanilla getTag/setTag/hasTag only as getNbt/setNbt/hasNBT.
  hasNBT() { return this.tag !== null; }
  getNbt() { return this.tag; }
  setNbt(tag) { this.tag = tag; }
  getItem() { return this.item; }
  copy() { return new Stack(this.id, this.animation, this.tag?.copy() || null, this.registered, this.item); }
}
const events = {};
const classes = {
  'dev.ghen.thirst.api.ThirstHelper': {isDrink: stack => stack.registered},
  'net.minecraft.world.item.UseAnim': {DRINK: 'DRINK'},
  'net.minecraft.world.item.PotionItem': Potion,
  'doggytalents.common.block.FoodBowlBlock': Bowl,
  'doggytalents.common.block.DogBathBlock': Bath,
  'net.minecraftforge.eventbus.api.EventPriority': {HIGHEST: 'HIGHEST', LOWEST: 'LOWEST'},
  'net.minecraft.world.level.ClipContext$Fluid': {ANY: 'ANY'},
  'dev.ghen.thirst.foundation.util.MathHelper': {
    getPlayerPOVHitResult: level => ({getBlockPos: () => level.pos})
  },
  'net.minecraft.nbt.TagParser': {parseTag: value => new Tag(JSON.parse(value))}
};
const loadedClasses = [];
classes['net.minecraftforge.common.MinecraftForge'] = {
  EVENT_BUS: {addListener: (priority, receiveCanceled, name, callback) => {
    events[name] = callback;
    assert.equal(receiveCanceled, false);
    assert.equal(priority, name.endsWith('$Post') ? 'LOWEST' : 'HIGHEST');
  }}
};
const sandbox = {
  Java: {loadClass: name => {
    loadedClasses.push(name);
    return classes[name] || name;
  }},
  ForgeEvents: {onEvent: (name, callback) => {events[name] = callback;}},
  console,
  Item: {of: id => new Stack(id, id.includes('juice') || id === 'minecraft:potion' ? 'DRINK' : 'NONE')},
  ServerEvents: {recipes: callback => {events.recipes = callback;}}
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(root + '/server-config/kubejs/startup_scripts/hydration_hooks.js', 'utf8'), sandbox);
vm.runInContext(fs.readFileSync(root + '/server-config/kubejs/server_scripts/hydration_recipes.js', 'utf8'), sandbox);
assert.equal(loadedClasses.includes('java.lang.ThreadLocal'), false);

const before = new Stack('minecraft:potion', 'DRINK', new Tag({
  Potion: 'minecraft:water', CustomPotionEffects: [{Id: 1, Duration: 40}], display: {Name: 'Named drink'}, Purity: 0
}), false, new Potion());
const fuel = new Stack('minecraft:blaze_powder');
const brewed = new Stack('minecraft:splash_potion', 'NONE', new Tag({Potion: 'minecraft:healing'}), false, new Potion());
let slots = [before, new Stack('minecraft:air'), new Stack('other:juice', 'DRINK'), fuel, fuel];
events['net.minecraftforge.event.brewing.PotionBrewEvent$Pre']({getItem: slot => slots[slot]});
slots[0] = brewed;
events['net.minecraftforge.event.brewing.PotionBrewEvent$Post']({getItem: slot => slots[slot]});
assert.equal(brewed.getNbt().data.Potion, 'minecraft:healing');
assert.equal(brewed.getNbt().data.Purity, 3);
assert.deepEqual(brewed.getNbt().data.CustomPotionEffects, [{Id: 1, Duration: 40}]);
assert.equal(brewed.getNbt().data.display.Name, 'Named drink');
assert.equal(slots[2].getNbt().data.Purity, 3);
assert.equal(fuel.hasNBT(), false);
assert.equal(brewed.count, 1);

for (const stack of [new Stack('other:registered_drink', 'NONE', null, true), new Stack('other:drink', 'DRINK')]) {
  events['net.minecraftforge.event.entity.player.PlayerEvent$ItemCraftedEvent']({getCrafting: () => stack});
  assert.equal(stack.getNbt().data.Purity, 3);
}
const food = new Stack('minecraft:apple', 'EAT');
events['net.minecraftforge.event.entity.player.PlayerEvent$ItemCraftedEvent']({getCrafting: () => food});
assert.equal(food.hasNBT(), false);

for (const [block, item, expected] of [[new Bowl(), 'minecraft:glass_bottle', true],
  [new Bath(), 'minecraft:glass_bottle', true], [{}, 'minecraft:glass_bottle', false],
  [new Bowl(), 'minecraft:water_bucket', false], [new Bath(), 'minecraft:water_bucket', false]]) {
  for (const type of ['RightClickItem', 'RightClickBlock']) {
    let canceled = false;
    const level = {pos: {}, getBlockState: () => ({getBlock: () => block})};
    events['net.minecraftforge.event.entity.player.PlayerInteractEvent$' + type]({
      getItemStack: () => new Stack(item),
      getLevel: () => level,
      getPos: () => level.pos,
      // KubeJS's kjs$getLevel exposes `level` as a property, hiding vanilla level().
      getEntity: () => ({level}),
      setCanceled: value => {canceled = value;}
    });
    assert.equal(canceled, expected, type + ' ' + item);
  }
}
const recipeData = {
  type: 'create:mixing',
  ingredients: [{item: 'other:juice', nbt: {Purity: 0}}],
  results: [{item: 'other:juice', count: 2, nbt: {CustomPotionEffects: [{Id: 4}], display: {Name: 'Juice'}}},
    {item: 'minecraft:glass_bottle'}, {fluid: 'minecraft:water', amount: 500}]
};
const recipe = {
  serialize() {},
  json: {toString: () => JSON.stringify(recipeData)},
  merge: updates => Object.assign(recipeData, structuredClone(updates))
};
events.recipes({forEachRecipe: (filter, callback) => callback(recipe)});
const outputTag = JSON.parse(recipeData.results[0].nbt);
assert.equal(outputTag.Purity, 3);
assert.equal(outputTag.display.Name, 'Juice');
assert.equal(outputTag.CustomPotionEffects[0].Id, 4);
assert.equal(recipeData.results[0].count, 2);
assert.equal(recipeData.ingredients[0].nbt.Purity, 0);
assert.deepEqual(recipeData.results[1], {item: 'minecraft:glass_bottle'});
assert.deepEqual(recipeData.results[2], {fluid: 'minecraft:water', amount: 500});
const untouched = {type: 'farmersrespite:kettle_pouring', output: {
  item: 'other:juice', nbt: '{"Purity":3,"display":{"Name":"Keep exact serialized tag"}}'
}};
let merges = 0;
events.recipes({forEachRecipe: (filter, callback) => callback({
  serialize() {}, json: {toString: () => JSON.stringify(untouched)}, merge() {merges++;}
})});
assert.equal(merges, 0);
assert.equal(untouched.output.nbt, '{"Purity":3,"display":{"Name":"Keep exact serialized tag"}}');
const conditional = {type: 'forge:conditional', recipes: [{
  conditions: [{type: 'forge:mod_loaded', modid: 'delightful'}],
  recipe: {type: 'minecraft:crafting_shapeless', ingredients: [{item: 'minecraft:glass_bottle'}],
    result: {item: 'other:juice', nbt: {display: {Name: 'Conditional juice'}}}}
}]};
events.recipes({forEachRecipe: (filter, callback) => callback({
  serialize() {}, json: {toString: () => JSON.stringify(conditional)},
  merge: updated => Object.assign(conditional, structuredClone(updated))
})});
assert.equal(JSON.parse(conditional.recipes[0].recipe.result.nbt).Purity, 3);
assert.equal(JSON.parse(conditional.recipes[0].recipe.result.nbt).display.Name, 'Conditional juice');
assert.equal(conditional.recipes[0].conditions[0].modid, 'delightful');
const serializedStack = {type: 'toughasnails:water_purifying', result: {
  id: 'minecraft:potion', Count: 1, tag: {Potion: 'minecraft:water', display: {Name: 'Old tag'}}
}};
events.recipes({forEachRecipe: (filter, callback) => callback({
  serialize() {}, json: {toString: () => JSON.stringify(serializedStack)},
  merge: updated => Object.assign(serializedStack, structuredClone(updated))
})});
assert.equal(serializedStack.result.tag.Purity, 3);
assert.equal(serializedStack.result.tag.display.Name, 'Old tag');
assert.equal(serializedStack.result.Count, 1);
console.log('Hydration recipe, effects, container, brewing and bowl fixtures passed');
