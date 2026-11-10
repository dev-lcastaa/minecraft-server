const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const root = process.argv[2];
const categories = ['sweet', 'healthy', 'meaty', 'fishy', 'gross', 'fancy', 'hearty', 'raw'];
const configured = {
  sweet: ['minecraft:cookie'],
  fishy: ['minecraft:cod'],
  raw: ['minecraft:cod'],
  meaty: ['minecraft:cooked_beef'],
  hearty: ['minecraft:rabbit_stew']
};
const fd = {fishy: ['farmersdelight:fish_stew'], hearty: ['farmersdelight:fish_stew'],
  raw: ['farmersdelight:cod_slice']};
const config = {CFG_FD_toggle: {get: () => true}};
categories.forEach(category => {
  config['CFG_' + category + '_foods'] = {get: () => configured[category] || []};
  config['CFG_FD_' + category + '_foods'] = {get: () => fd[category] || []};
});
function food(nutrition, meat = false) {
  return {getNutrition: () => nutrition, isMeat: () => meat};
}
const items = {
  'minecraft:cookie': food(2),
  'minecraft:cod': food(2, true),
  'minecraft:cooked_beef': food(8, true),
  'minecraft:rabbit_stew': food(10),
  'supplementaries:candy': food(2),
  'supplementaries:pancake': null,
  'farmersdelight:fish_stew': food(12),
  'farmersdelight:cod_slice': food(1),
  'miners_delight:fish_stew_cup': food(6),
  'new_mod:vegetable_soup': food(8),
  'new_mod:spider_stew': food(8),
  'new_mod:golden_truffle_platter': food(12),
  'new_mod:chocolate_pudding': food(10),
  'new_mod:hidden_food': food(3),
  'new_mod:unusual_animation_food': food(6),
  'new_mod:raw_trout': food(3),
  'new_mod:milk': null,
  'minecraft:potion': null,
  'new_mod:warped_potion': null,
  'minecraft:cake': null,
  'new_mod:pie': null,
  'minecraft:stone': null
};
const placeable = new Set(['minecraft:cake', 'new_mod:pie', 'supplementaries:pancake']);
let tagHandler;
let loaded;
let tooltip;
let tick;
const tags = {};
const logs = [];
const stacks = {};
Object.keys(items).forEach(id => {
  stacks[id] = {
    id, isEmpty: () => false,
    getUseAnimation: () => id.endsWith(':milk') || id.includes('potion') ? 'DRINK' : 'EAT',
    item: {
      id, isEdible: () => items[id] !== null,
      getFoodProperties: () => items[id]
    }
  };
});
let craving = 'Fishy';
let main = stacks['minecraft:stone'];
let offhand = main;
const chimes = [];
const context = {
  global: {lunchBasketPlaceableFood: item => placeable.has(item.id)},
  Java: {loadClass: name => {
    if (name.endsWith('ConfigFileFoods')) return {SERVER: config};
    if (name.endsWith('CravingsModVariables')) return {PLAYER_VARIABLES: 'capability'};
    if (name.endsWith('ForgeRegistries')) return {SOUND_EVENTS: {getValue: location => {
      assert.equal(location.id, 'minecraft:block.amethyst_block.resonate');
      return location.id;
    }}};
    if (name.endsWith('ResourceLocation')) return function(id) { this.id = id; };
    throw Error(name);
  }},
  ServerEvents: {
    tags: (type, callback) => { assert.equal(type, 'item'); tagHandler = callback; },
    loaded: callback => { loaded = callback; }
  },
  ItemEvents: {
    tooltip: callback => callback({addAdvancedToAll: handler => { tooltip = handler; }})
  },
  Item: {getTypeList: () => Object.keys(items), of: id => stacks[id]},
  Ingredient: {of: tag => ({
    test: stack => (tags[tag.slice(1)] || []).includes(stack.id),
    itemIds: {
      forEach: callback => (tags[tag.slice(1)] || []).forEach(callback),
      size: () => (tags[tag.slice(1)] || []).length
    }
  })},
  Client: {player: {
    getUUID: () => 'player-one',
    getCapability: () => ({orElse: () => ({current_craving: craving})}),
    getMainHandItem: () => main,
    getOffhandItem: () => offhand,
    playSound: (sound, volume, pitch) => { chimes.push(sound); assert.equal(volume, 1); assert.equal(pitch, 1); }
  }},
  ClientEvents: {tick: callback => { tick = callback; }},
  Text: {translate: (...values) => ({values, green() { return this; }, gray() { return this; }})},
  console: {info: message => logs.push(message), warn: message => logs.push(message)}
};
vm.createContext(context);
function run(path) { vm.runInContext(fs.readFileSync(root + '/' + path, 'utf8'), context); }
run('server-config/kubejs/server_scripts/craving_foods.js');
function reload() {
  Object.keys(tags).forEach(tag => delete tags[tag]);
  tagHandler({add: (tag, ids) => { tags[tag] = Array.from(ids); }});
  loaded();
}
reload();
const edible = Object.keys(items).filter(id => !['minecraft:stone', 'minecraft:potion', 'new_mod:warped_potion'].includes(id));
assert.deepEqual([...tags['cravings:foods']].sort(), edible.sort());
assert.ok(tags['cravings:sweet'].includes('supplementaries:candy'));
assert.ok(tags['cravings:hearty'].includes('supplementaries:pancake'));
assert.ok(tags['cravings:big_meal'].includes('supplementaries:pancake'));
assert.ok(tags['cravings:simple_food'].includes('minecraft:cod'));
assert.ok(tags['cravings:big_meal'].includes('farmersdelight:fish_stew'));
assert.ok(tags['cravings:regular_food'].includes('minecraft:cooked_beef'));
assert.ok(tags['cravings:regular_food'].includes('miners_delight:fish_stew_cup'));
assert.ok(tags['cravings:fishy'].includes('farmersdelight:cod_slice'));
assert.ok(!tags['cravings:meaty'].includes('new_mod:raw_trout'));
for (const id of edible) {
  assert.ok(categories.some(category => tags['cravings:' + category].includes(id)), id);
  assert.equal(['simple_food', 'regular_food', 'big_meal'].filter(tier => tags['cravings:' + tier].includes(id)).length, 1);
}
assert.ok(tags['cravings:gross'].includes('new_mod:spider_stew'));
assert.ok(tags['cravings:fancy'].includes('new_mod:golden_truffle_platter'));
assert.ok(tags['cravings:sweet'].includes('new_mod:chocolate_pudding'));
assert.ok(tags['cravings:raw'].includes('new_mod:raw_trout'));
assert.ok(logs.some(message => message.includes('uncategorized') && message.includes('hidden_food')));
const first = JSON.stringify(tags);
reload();
assert.equal(JSON.stringify(tags), first);
tags['cravings:foods'] = tags['cravings:foods'].filter(id => id !== 'new_mod:hidden_food');
assert.throws(loaded, /not in food tag/);
reload();
tags['cravings:regular_food'].push('minecraft:cod');
assert.throws(loaded, /coverage validation failed/);
reload();
tags['cravings:foods'] = [];
assert.throws(loaded, /empty food registry/);
reload();
run('client-config/kubejs/client_scripts/craving_feedback.js');
function hover(id) {
  const lines = [];
  tooltip(stacks[id], false, {add: line => lines.push(line)});
  return lines;
}
tick();
main = stacks['minecraft:cod'];
tick();
assert.equal(chimes.length, 1);
for (let i = 0; i < 100; i++) tick();
assert.equal(chimes.length, 1, 'Holding a food must not ring every tick');
assert.equal(hover('farmersdelight:fish_stew').length, 2);
assert.equal(chimes.length, 2);
for (let i = 0; i < 100; i++) { hover('farmersdelight:fish_stew'); tick(); }
assert.equal(chimes.length, 2, 'Stationary hover must not repeat');
hover('minecraft:stone');
hover('minecraft:cod');
assert.equal(chimes.length, 3);
hover('farmersdelight:fish_stew');
assert.equal(chimes.length, 3, 'Shared cooldown applies to hover and held notifications');
craving = 'None';
assert.equal(hover('minecraft:cod').length, 0);
for (let i = 0; i < 41; i++) tick();
craving = 'Sweet';
main = stacks['minecraft:stone'];
offhand = stacks['supplementaries:candy'];
tick();
assert.equal(chimes.length, 4, 'Offhand matching food must ring');
craving = 'Raw';
assert.equal(hover('minecraft:cod').length, 1, 'Raw should not advertise a buff-duration multiplier');
context.Client.player = null;
tick();
assert.equal(hover('minecraft:cod').length, 0, 'Disconnected and menu tooltips must not ring');
console.log('Craving registry and client feedback fixtures passed');
