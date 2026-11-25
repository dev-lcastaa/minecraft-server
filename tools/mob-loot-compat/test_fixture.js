const fs = require('fs')
const vm = require('vm')
const assert = require('assert')
const root = process.argv[2]
const classes = {}
class Player {}
class ItemEntity { constructor(level, x, y, z, item) { this.item = item } getItem() { return this.item } }
classes['net.minecraftforge.registries.ForgeRegistries'] = {
  ENTITY_TYPES: { getKey: type => type.id, getValues: () => [] }
}
classes['net.minecraft.tags.TagKey'] = { create: (registry, location) => location.id }
classes['net.minecraft.core.registries.Registries'] = { ENTITY_TYPE: 'entities' }
classes['net.minecraft.resources.ResourceLocation'] = class { constructor(id) { this.id = id } }
classes['net.minecraft.world.entity.MobType'] = {
  UNDEAD: 'undead', WATER: 'water', ARTHROPOD: 'arthropod', ILLAGER: 'illager'
}
classes['net.minecraft.world.entity.player.Player'] = Player
classes['net.minecraft.world.entity.item.ItemEntity'] = ItemEntity
classes['net.mehvahdjukaar.supplementaries.common.items.loot.RandomArrowFunction'] = {
  createRandomQuiver: () => ({id: 'supplementaries:quiver', arrows: 'minecraft:arrow'})
}
const warnings = []
const messages = []
classes['net.minecraft.world.entity.LivingEntity'] = class {
  static [Symbol.hasInstance](object) { return !!object && typeof object.getMobType === 'function' }
}
const context = {
  Java: {loadClass: name => classes[name]}, global: {},
  console: {warn: message => warnings.push(message), info: message => messages.push(message)},
  Ingredient: {of: id => id},
  Item: {of: (id, nbt) => ({id, nbt})},
  ServerEvents: {loaded: callback => context.loaded = callback},
  ForgeEvents: {onEvent: (name, callback) => context.callback = callback}
}
vm.createContext(context)
for (const scope of ['startup_scripts', 'server_scripts']) {
  vm.runInContext(fs.readFileSync(`${root}/server-config/kubejs/${scope}/mob_loot_compat.js`, 'utf8'), context)
}
function entity(id, ancestors, tags = [], mob = 'normal', roll = 0.9) {
  const types = ancestors.map(name => ({
    getName: () => name, getInterfaces: () => [], getSuperclass: () => null
  }))
  types.forEach((type, i) => type.getSuperclass = () => types[i + 1] || null)
  const type = {id, is: tag => tags.includes(tag), getWidth: () => 0.6}
  return {
    level: {isClientSide: () => false}, x: 0, y: 0, z: 0,
    getClass: () => types[0], getType: () => type, getMobType: () => mob,
    getRandom: () => ({nextFloat: () => roll})
  }
}
function killer(tool, bottles = 1) {
  const player = new Player()
  player.mainHandItem = {id: tool}
  player.inventory = {
    bottles, find: () => player.inventory.bottles > 0 ? 0 : -1,
    extractItem: () => player.inventory.bottles--
  }
  return player
}
function death(mob, player, direct = player, looting = 0, oldDrops = []) {
  const drops = oldDrops.map(item => new ItemEntity(null, 0, 0, 0, item))
  const list = {
    add: item => drops.push(item),
    iterator: () => {
      let index = 0
      return {hasNext: () => index < drops.length, next: () => drops[index++],
        remove: () => drops.splice(--index, 1)}
    }
  }
  context.callback({
    getEntity: () => mob, getDrops: () => list, isRecentlyHit: () => !!player,
    getLootingLevel: () => looting,
    getSource: () => ({getEntity: () => player, getDirectEntity: () => direct})
  })
  return drops.map(drop => drop.item)
}
const bat = entity('fangs_n_claws:evil_bat', ['example.Bat'], ['mob_loot_compat:blood_winged'])
for (const tool of ['farmersdelight:iron_knife', 'sons_of_sins:butcher_cleaver', 'minecraft:diamond_sword']) {
  const player = killer(tool)
  assert.deepEqual(death(bat, player), [])
  assert.equal(player.inventory.bottles, 1)
}
const sickle = 'sons_of_sins:sickle_of_struggle'
for (const [category, code] of [['primary', 0], ['winged', 1], ['wide', 2], ['humanoid', 3], ['aquatic', 4]]) {
  const mob = entity('example:mob', ['example.Mob'], [`mob_loot_compat:blood_${category}`])
  const player = killer(sickle)
  const drops = death(mob, player)
  assert.equal(drops.length, 1)
  assert.equal(drops[0].id, 'sons_of_sins:bottle_of_blood')
  assert.equal(drops[0].nbt, `{originEntityCapaity:${code}.0d}`)
  assert.equal(player.inventory.bottles, 0)
}
assert.equal(death(bat, killer(sickle, 0)).length, 0)
assert.equal(death(bat, killer(sickle), {}).length, 0)
const construct = entity('example:golem', ['net.minecraft.world.entity.animal.AbstractGolem'])
assert.equal(death(construct, killer(sickle)).length, 0)
const undead = entity('example:undead', ['example.Undead'], [], 'undead')
assert.equal(death(undead, killer(sickle)).length, 0)
const unknown = entity('example:unclassified', ['example.Ambiguous'])
assert.equal(death(unknown, killer(sickle)).length, 0)
assert.equal(death(unknown, killer(sickle)).length, 0)
assert.equal(warnings.length, 1)
const animal = entity('example:animal', ['example.Animal', 'net.minecraft.world.entity.animal.Animal'])
assert.equal(death(animal, killer(sickle))[0].nbt, '{originEntityCapaity:0.0d}')
const fish = entity('example:fish', ['example.Fish'], [], 'water')
assert.equal(death(fish, killer(sickle))[0].nbt, '{originEntityCapaity:4.0d}')
const zombie = entity('example:zombie', ['example.Zombie', 'net.minecraft.world.entity.monster.Zombie'], [], 'undead')
assert.equal(death(zombie, killer(sickle))[0].nbt, '{originEntityCapaity:3.0d}')
for (const type of ['decoration.ArmorStand', 'monster.Blaze', 'monster.Ghast']) {
  const mob = entity('minecraft:test', ['net.minecraft.world.entity.' + type])
  assert.equal(context.mobLootBloodType(mob), -1)
}
const warden = entity('minecraft:warden', ['net.minecraft.world.entity.monster.warden.Warden'])
assert.equal(context.mobLootBloodType(warden), 0)
for (const looting of [0, 3, 100]) {
  for (const roll of [0, 0.009999, 0.01, 0.9]) {
    const skeleton = entity('minecraft:skeleton', ['net.minecraft.world.entity.monster.AbstractSkeleton'], [], 'undead', roll)
    const result = death(skeleton, killer(sickle), undefined, looting,
      [{id: 'supplementaries:quiver', arrows: 'unobtainable:arrow'}, {id: 'minecraft:bone'}])
    assert.equal(result.filter(item => item.id === 'supplementaries:quiver').length, roll < 0.01 ? 1 : 0)
    assert.equal(result.filter(item => item.id === 'minecraft:bone').length, 1)
    assert.equal(result.filter(item => item.id === 'sons_of_sins:bottle_of_blood').length, 0)
    for (const item of result.filter(item => item.id === 'supplementaries:quiver')) {
      assert.equal(item.arrows, 'minecraft:arrow')
    }
  }
}
classes['net.minecraftforge.registries.ForgeRegistries'].ENTITY_TYPES.getValues = () => [
  {create: () => animal}, {create: () => construct}, {create: () => unknown},
  {create: () => null}, {id: 'example:broken_constructor', create: () => {throw Error('broken')}}
]
context.loaded({server: {overworld: () => ({})}})
assert.ok(messages.some(message => message.endsWith(
  '{"eligible":1,"bloodless":1,"missing":1,"nonliving":1,"failed":1}')))
assert.ok(warnings.some(message => message.includes('cannot audit example:broken_constructor')))
const coverage = JSON.parse(fs.readFileSync(`${root}/tools/mob-loot-compat/blood_coverage.json`, 'utf8'))
const categoryTags = {}
for (const category of ['primary', 'winged', 'wide', 'humanoid', 'aquatic', 'bloodless']) {
  const tag = category === 'bloodless' ? 'bloodless' : 'blood_' + category
  const data = JSON.parse(fs.readFileSync(
    `${root}/server-config/new-world/datapacks/mob-loot-compat/data/mob_loot_compat/tags/entity_types/${tag}.json`, 'utf8'))
  for (const value of data.values) {
    categoryTags[value.id] = 'mob_loot_compat:' + tag
  }
}
const codes = {primary: 0, winged: 1, wide: 2, humanoid: 3, aquatic: 4, adaptive_animal: 0, bloodless: -1}
const types = {f_21640_: 'normal', f_21641_: 'undead', f_21642_: 'arthropod', f_21643_: 'illager', f_21644_: 'water'}
let eligible = 0, excluded = 0
for (const [id, row] of Object.entries(coverage)) {
  const tags = row.native_tags.map(tag => 'sons_of_sins:' + tag)
  if (categoryTags[id]) tags.push(categoryTags[id])
  const mob = entity(id, row.ancestors, tags, types[row.native_mob_type] || 'normal')
  const actual = context.mobLootBloodType(mob)
  assert.equal(actual, codes[row.category], `${id}: ${row.basis}`)
  if (actual >= 0) eligible++
  else excluded++
}
const registered = JSON.parse(fs.readFileSync(`${root}/tools/mob-loot-compat/verified_entities.json`, 'utf8'))
assert.equal(eligible + excluded, Object.keys(registered).length)
assert.equal(Object.keys(coverage).length, Object.keys(registered).length)
assert.ok(!warnings.some(message => message.includes('unclassified blood excluded:') &&
  Object.keys(coverage).some(id => message.includes(id))))
console.log(`Manifest coverage passed: ${eligible} eligible + ${excluded} excluded = ${Object.keys(coverage).length}; 0 unknown`)
console.log('Mob loot gameplay fixtures passed')
