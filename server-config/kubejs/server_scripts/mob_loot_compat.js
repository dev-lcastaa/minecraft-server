var $MobLootRegistries = Java.loadClass('net.minecraftforge.registries.ForgeRegistries')
var $MobLootTagKey = Java.loadClass('net.minecraft.tags.TagKey')
var $MobLootRegistriesKeys = Java.loadClass('net.minecraft.core.registries.Registries')
var $MobLootLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
var $MobLootMobType = Java.loadClass('net.minecraft.world.entity.MobType')
var $MobLootPlayer = Java.loadClass('net.minecraft.world.entity.player.Player')
var $MobLootItemEntity = Java.loadClass('net.minecraft.world.entity.item.ItemEntity')
var $MobLootArrows = Java.loadClass('net.mehvahdjukaar.supplementaries.common.items.loot.RandomArrowFunction')
var mobLootTags = {}
var mobLootMissing = {}

// KubeJS's EntityKJS.kjs$getType() shadows vanilla Entity.getType() and returns the id string.
function mobLootEntityType(entity) {
  return $MobLootRegistries.ENTITY_TYPES.getValue(new $MobLootLocation(String(entity.getType())))
}

function mobLootTagged(entity, id) {
  if (!mobLootTags[id]) mobLootTags[id] = $MobLootTagKey.create(
    $MobLootRegistriesKeys.ENTITY_TYPE, new $MobLootLocation(id))
  return mobLootEntityType(entity).is(mobLootTags[id])
}

function mobLootAncestors(entity) {
  var names = []
  for (var type = entity.getClass(); type !== null; type = type.getSuperclass()) {
    names.push(String(type.getName()))
    type.getInterfaces().forEach(face => names.push(String(face.getName())))
  }
  return names
}

function mobLootBloodType(entity) {
  var id = String(entity.getType())
  var names = mobLootAncestors(entity)
  var mobType = String(entity.getMobType())
  if (mobLootTagged(entity, 'mob_loot_compat:bloodless') ||
      names.indexOf('net.minecraft.world.entity.monster.AbstractSkeleton') >= 0 ||
      names.indexOf('net.minecraft.world.entity.animal.AbstractGolem') >= 0 ||
      names.indexOf('net.minecraft.world.entity.decoration.ArmorStand') >= 0 ||
      names.indexOf('net.minecraft.world.entity.monster.Blaze') >= 0 ||
      names.indexOf('net.minecraft.world.entity.monster.Ghast') >= 0) return -1
  var categories = ['primary', 'winged', 'wide', 'humanoid', 'aquatic']
  for (var n = 0; n < categories.length; n++) {
    if (mobLootTagged(entity, 'mob_loot_compat:blood_' + categories[n])) return n
  }
  // Preserve the mod's explicitly authored blood lore, including its zombie and phantom exceptions.
  if (mobLootTagged(entity, 'sons_of_sins:is_humanoid')) return 3
  if (mobLootTagged(entity, 'sons_of_sins:is_large')) return 2
  if (mobLootTagged(entity, 'sons_of_sins:has_wing')) return 1
  if (id === 'sons_of_sins:nibbler') return 4
  if (mobType === String($MobLootMobType.UNDEAD)) {
    if (names.indexOf('net.minecraft.world.entity.monster.Zombie') >= 0) return 3
    return -1
  }
  if (mobType === String($MobLootMobType.WATER) ||
      names.indexOf('net.minecraft.world.entity.animal.WaterAnimal') >= 0) return 4
  if (mobType === String($MobLootMobType.ILLAGER)) return 3
  if (names.indexOf('net.minecraft.world.entity.animal.FlyingAnimal') >= 0 ||
      names.indexOf('net.minecraft.world.entity.ambient.Bat') >= 0) return 1
  var humanoids = ['AbstractVillager', 'AbstractIllager', 'AbstractPiglin', 'EnderMan', 'Zombie']
  for (var h = 0; h < humanoids.length; h++) {
    if (names.indexOf('net.minecraft.world.entity.monster.' + humanoids[h]) >= 0 ||
        names.indexOf('net.minecraft.world.entity.npc.' + humanoids[h]) >= 0) return 3
  }
  if (names.indexOf('net.minecraft.world.entity.monster.piglin.AbstractPiglin') >= 0) return 3
  if (names.indexOf('net.minecraft.world.entity.animal.horse.AbstractHorse') >= 0) return 2
  if (names.indexOf('net.minecraft.world.entity.animal.Animal') >= 0) {
    return mobLootEntityType(entity).getWidth() >= 1.4 ? 2 : 0
  }
  if (mobType === String($MobLootMobType.ARTHROPOD) ||
      names.indexOf('net.minecraft.world.entity.monster.Creeper') >= 0 ||
      names.indexOf('net.minecraft.world.entity.monster.Slime') >= 0 ||
      names.indexOf('net.minecraft.world.entity.monster.Shulker') >= 0 ||
      names.indexOf('net.minecraft.world.entity.monster.warden.Warden') >= 0) return 0
  if (!mobLootMissing[id]) {
    mobLootMissing[id] = true
    console.warn('Mob loot compatibility: unclassified blood excluded: ' + id +
      ' (' + String(entity.getClass().getName()) + ')')
  }
  return -2
}

global.mobLootCompatDrops = event => {
  var entity = event.getEntity()
  if (entity.level.isClientSide()) return
  var id = String(entity.getType())
  var names = mobLootAncestors(entity)
  var drops = event.getDrops()
  if (names.indexOf('net.minecraft.world.entity.monster.AbstractSkeleton') >= 0) {
    var iterator = drops.iterator()
    while (iterator.hasNext()) {
      if (String(iterator.next().getItem().id) === 'supplementaries:quiver') iterator.remove()
    }
    // One independent 1% roll per player-killed skeleton; Looting never participates.
    if (event.isRecentlyHit() && entity.getRandom().nextFloat() < 0.01) {
      var quiver = $MobLootArrows.createRandomQuiver(entity.getRandom(), 0.0)
      drops.add(new $MobLootItemEntity(entity.level, entity.x, entity.y, entity.z, quiver))
    }
  }
  // KubeJS remaps DamageSource's attacker methods to these names.
  var source = event.getSource()
  var killer = source.getActual()
  if (!(killer instanceof $MobLootPlayer) ||
      source.getImmediate() !== killer ||
      String(killer.mainHandItem.id) !== 'sons_of_sins:sickle_of_struggle') return
  var blood = mobLootBloodType(entity)
  if (blood < 0) return
  var inventory = killer.inventory
  var slot = inventory.find(Ingredient.of('minecraft:glass_bottle'))
  if (slot < 0) return
  inventory.extractItem(slot, 1, false)
  var bottle = Item.of('sons_of_sins:bottle_of_blood', '{originEntityCapaity:' + blood + '.0d}')
  drops.add(new $MobLootItemEntity(entity.level, entity.x, entity.y, entity.z, bottle))
}

ServerEvents.loaded(event => {
  var level = event.server.getOverworld()
  var counted = {eligible: 0, bloodless: 0, missing: 0, nonliving: 0, failed: 0}
  var living = Java.loadClass('net.minecraft.world.entity.LivingEntity')
  $MobLootRegistries.ENTITY_TYPES.getValues().forEach(type => {
    try {
      var entity = type.create(level)
      if (!(entity instanceof living)) { counted.nonliving++; return }
      var blood = mobLootBloodType(entity)
      if (blood >= 0) counted.eligible++
      else if (blood === -1) counted.bloodless++
      else counted.missing++
    } catch (error) {
      counted.failed++
      console.warn('Mob loot compatibility: cannot audit ' +
        String($MobLootRegistries.ENTITY_TYPES.getKey(type)) + ': ' + error)
    }
  })
  console.info('Mob loot compatibility registry coverage: ' + JSON.stringify(counted))
})
