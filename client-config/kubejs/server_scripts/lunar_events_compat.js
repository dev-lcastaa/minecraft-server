// Gameplay for lunar_events_compat moons that the Enhanced Celestials 2 datapack format
// cannot express. Spawn lists, spawn rates, effects, drops and visuals live in the
// lunar-events-compat world datapack; this script only reads the current lunar event.
var $LunarEC = null
try {
  $LunarEC = Java.loadClass('dev.corgitaco.enhancedcelestials2core.EnhancedCelestials')
} catch (err) {
  console.warn('Lunar events compat: Enhanced Celestials 2 is missing, script disabled: ' + err)
}
var $LunarZombie = Java.loadClass('net.minecraft.world.entity.monster.Zombie')
var $LunarEnemy = Java.loadClass('net.minecraft.world.entity.monster.Enemy')
var $LunarMob = Java.loadClass('net.minecraft.world.entity.Mob')
var $LunarAgeable = Java.loadClass('net.minecraft.world.entity.AgeableMob')
var $LunarShulker = Java.loadClass('net.minecraft.world.entity.monster.Shulker')
var $LunarOwnable = Java.loadClass('net.minecraft.world.entity.OwnableEntity')
var $LunarNeutral = Java.loadClass('net.minecraft.world.entity.NeutralMob')
var $LunarGolem = Java.loadClass('net.minecraft.world.entity.animal.AbstractGolem')
var $LunarIronGolem = Java.loadClass('net.minecraft.world.entity.animal.IronGolem')
var $LunarRanged = Java.loadClass('net.minecraft.world.entity.monster.RangedAttackMob')
var $LunarCreeper = Java.loadClass('net.minecraft.world.entity.monster.Creeper')
var $LunarAttributes = Java.loadClass('net.minecraft.world.entity.ai.attributes.Attributes')
var $LunarModifier = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier')
var $LunarOperation = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier$Operation')
var $LunarUUID = Java.loadClass('java.util.UUID')

var LUNAR_NS = 'lunar_events_compat:'
var LUNAR_PEACEFUL = {
  'lunar_events_compat:peaceful_moon': true,
  'enhancedcelestials2defaultlunarevents:harvest_moon': true,
  'enhancedcelestials2defaultlunarevents:super_harvest_moon': true,
  'enhancedcelestials2defaultlunarevents:blue_moon': true,
  'enhancedcelestials2defaultlunarevents:super_blue_moon': true
}
var LUNAR_HORDE_ZOMBIES = {
  'minecraft:zombie': true, 'minecraft:husk': true, 'minecraft:drowned': true,
  'minecraft:zombie_villager': true, 'dungeonsdelight:rotten_zombie': true,
  'rottencreatures:burned': true, 'rottencreatures:frostbitten': true,
  'rottencreatures:swampy': true, 'rottencreatures:undead_miner': true,
  'rottencreatures:mummy': true, 'rottencreatures:zap': true, 'graveyard:ghoul': true
}
var LUNAR_BLOCKED_TAG = 'lunar_events_compat.blocked_spawn'
var LUNAR_SHULKER_TAG = 'lunar_events_compat.ender_moon_shulker'
var LUNAR_HEALTH_ID = $LunarUUID.fromString('5d1c7a52-5f0e-4a8e-9a43-6f2b0c1e7a01')
var LUNAR_ARMOR_ID = $LunarUUID.fromString('5d1c7a52-5f0e-4a8e-9a43-6f2b0c1e7a02')
var LUNAR_TOUGHNESS_ID = $LunarUUID.fromString('5d1c7a52-5f0e-4a8e-9a43-6f2b0c1e7a03')
var LUNAR_PULSE_TICKS = 80
var lunarEventCache = {}
var lunarBlockedPending = 0
var lunarShulkers = []

// Cached for one second per dimension; spawn checks call this often.
function lunarEventId(level) {
  if ($LunarEC === null || level === null) return null
  var dimension = String(level.getDimension())
  var time = Number(level.getGameTime())
  var cached = lunarEventCache[dimension]
  if (cached && time >= cached.time && time - cached.time < 20) return cached.id
  var id = null
  var forecast = $LunarEC.lunarForecastWorldData(level)
  if (forecast.isPresent()) {
    var key = forecast.get().currentLunarEventHolder().unwrapKey()
    if (key.isPresent()) id = String(key.get().location())
  }
  lunarEventCache[dimension] = { time: time, id: id }
  return id
}

function lunarTypeId(entity) {
  var id = entity.getEncodeId()
  return id === null ? '' : String(id)
}

function lunarAddModifier(entity, attribute, uuid, name, amount, operation) {
  var instance = entity.getAttribute(attribute)
  if (instance === null || instance.getModifier(uuid) !== null) return
  instance.addPermanentModifier(new $LunarModifier(uuid, name, amount, operation))
}

function lunarBuffHordeZombie(entity) {
  lunarAddModifier(entity, $LunarAttributes.MAX_HEALTH, LUNAR_HEALTH_ID,
    'Horde Moon health', 1.0, $LunarOperation.MULTIPLY_BASE)
  lunarAddModifier(entity, $LunarAttributes.ARMOR, LUNAR_ARMOR_ID,
    'Horde Moon armor', 6.0, $LunarOperation.ADDITION)
  lunarAddModifier(entity, $LunarAttributes.ARMOR_TOUGHNESS, LUNAR_TOUGHNESS_ID,
    'Horde Moon toughness', 2.0, $LunarOperation.ADDITION)
  entity.setHealth(entity.getMaxHealth())
}

function lunarBlockSpawn(entity) {
  entity.addTag(LUNAR_BLOCKED_TAG)
  lunarBlockedPending++
}

EntityEvents.checkSpawn(event => {
  var entity = event.getEntity()
  if (!(entity instanceof $LunarMob)) return
  var moon = lunarEventId(event.getLevel())
  if (moon === null) return
  var spawnType = String(event.getType())

  if (LUNAR_PEACEFUL[moon]) {
    // Natural spawning is already capped at zero; this also stops phantoms, patrols and
    // mods that spawn hostiles through their own natural spawners.
    if (entity instanceof $LunarEnemy && (spawnType === 'NATURAL' || spawnType === 'PATROL')) {
      lunarBlockSpawn(entity)
    }
    return
  }
  if (moon.indexOf(LUNAR_NS) !== 0) return

  if (moon === 'lunar_events_compat:horde_moon') {
    if ((entity instanceof $LunarZombie || LUNAR_HORDE_ZOMBIES[lunarTypeId(entity)]) &&
        spawnType !== 'COMMAND' && spawnType !== 'SPAWN_EGG') {
      lunarBuffHordeZombie(entity)
    }
  } else if (moon === 'lunar_events_compat:baby_horde_moon') {
    if ((spawnType === 'NATURAL' || spawnType === 'REINFORCEMENT' || spawnType === 'EVENT') &&
        (entity instanceof $LunarEnemy || entity instanceof $LunarAgeable) && Math.random() < 0.85) {
      // Mob#setBaby is a no-op for mobs without a baby form.
      entity.setBaby(true)
    }
  } else if (moon === 'lunar_events_compat:ender_moon') {
    if (entity instanceof $LunarShulker && spawnType === 'NATURAL') {
      // Vanilla has no shulker spawn placement, so keep them out of lit areas.
      if (event.getLevel().getMaxLocalRawBrightness(entity.blockPosition()) > 7) {
        lunarBlockSpawn(entity)
      } else {
        entity.addTag(LUNAR_SHULKER_TAG)
        lunarShulkers.push(entity)
      }
    }
  }
})

EntityEvents.spawned(event => {
  if (lunarBlockedPending <= 0) return
  var entity = event.getEntity()
  if (!entity.getTags().contains(LUNAR_BLOCKED_TAG)) return
  lunarBlockedPending--
  event.cancel()
})

// Shulkers do not despawn, so ender-moon shulkers leave with the moon.
EntityEvents.spawned('minecraft:shulker', event => {
  var entity = event.getEntity()
  if (entity.getTags().contains(LUNAR_SHULKER_TAG) &&
      lunarEventId(event.getLevel()) !== 'lunar_events_compat:ender_moon') {
    event.cancel()
  }
})

function lunarCanFight(mob) {
  if (!mob.isAlive() || mob.isNoAi()) return false
  if (mob instanceof $LunarOwnable && mob.getOwnerUUID() !== null) return false
  if (mob instanceof $LunarGolem && !(mob instanceof $LunarIronGolem && !mob.isPlayerCreated())) return false
  return mob instanceof $LunarRanged || mob instanceof $LunarCreeper ||
    mob.getAttributes().hasAttribute($LunarAttributes.ATTACK_DAMAGE)
}

// Returns the player, another mob, or null; Rhino may wrap one Java object twice, so
// identity is compared through entity ids.
function lunarPickVictim(mob, mobs, player) {
  var nearPlayer = player.isAlive() && !player.isCreative() && !player.isSpectator() &&
    mob.distanceToSqr(player) < 256
  if (nearPlayer && (!(mob instanceof $LunarEnemy) || Math.random() < 0.5)) return player
  var own = lunarTypeId(mob)
  var start = Math.floor(Math.random() * mobs.size())
  for (var n = 0; n < mobs.size(); n++) {
    var other = mobs.get((start + n) % mobs.size())
    if (other.getId() !== mob.getId() && other.isAlive() && lunarTypeId(other) !== own &&
        mob.canAttack(other)) return other
  }
  return nearPlayer ? player : null
}

// Every mob near a player that can fight picks a fight with another mob or the player.
function lunarChaosPulse(player) {
  var mobs = player.getLevel().getEntitiesOfClass($LunarMob, player.getBoundingBox().inflate(24))
  var limit = Math.min(mobs.size(), 48)
  for (var i = 0; i < limit; i++) {
    var mob = mobs.get(i)
    var target = mob.getTarget()
    if ((target !== null && target.isAlive()) || !lunarCanFight(mob)) continue
    var victim = lunarPickVictim(mob, mobs, player)
    if (victim === null) continue
    mob.setTarget(victim)
    if (mob instanceof $LunarNeutral && victim.getId() === player.getId()) {
      mob.setPersistentAngerTarget(player.getUUID())
      mob.startPersistentAngerTimer()
    }
  }
}

function lunarCleanupShulkers() {
  var kept = []
  for (var i = 0; i < lunarShulkers.length; i++) {
    var shulker = lunarShulkers[i]
    if (!shulker.isAlive()) continue
    if (lunarEventId(shulker.getLevel()) === 'lunar_events_compat:ender_moon') kept.push(shulker)
    else shulker.discard()
  }
  lunarShulkers = kept
}

ServerEvents.tick(event => {
  var server = event.getServer()
  if ($LunarEC === null || server.getTickCount() % LUNAR_PULSE_TICKS !== 0) return
  if (lunarShulkers.length > 0) lunarCleanupShulkers()
  var players = server.getPlayers()
  for (var p = 0; p < players.size(); p++) {
    var player = players.get(p)
    if (player.isSpectator()) continue
    if (lunarEventId(player.getLevel()) === 'lunar_events_compat:chaos_moon') lunarChaosPulse(player)
  }
})
