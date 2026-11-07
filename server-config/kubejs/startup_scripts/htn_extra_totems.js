// Applies Hardcore Totem Nerf (HTN) post-totem penalties to modded totems that
// bypass vanilla's LivingEntity#checkTotemDeathProtection return path.
//
// HTN only hooks HEAD/RETURN of checkTotemDeathProtection. More Totems cancels that
// method at HEAD with setReturnValue(true), so HTN's RETURN hook (penalties, cooldown
// start, max-health loss) never runs. HTN's HEAD pre-check is applied before More
// Totems' HEAD hooks, so an active cooldown still blocks More Totems totems.
// Fangs & Claws' Totem of Frost uses LivingDamageEvent and bypasses HTN completely.
//
// Detection: when a player takes damage that would be lethal (or, for Totem of Frost,
// drop them to <= 25% max health) while holding a listed totem, check one tick later
// whether that totem was consumed and the player is alive, then call HTN's handler.
const $PostTotemHandler = Java.loadClass('dev.spagurder.htn.PostTotemHandler')
const $ServerPlayer = Java.loadClass('net.minecraft.server.level.ServerPlayer')

const LETHAL_TOTEMS = [
  'moretotems:explosive_totem_of_undying',
  'moretotems:stinging_totem_of_undying',
  'moretotems:teleporting_totem_of_undying',
  'moretotems:ghastly_totem_of_undying',
  'moretotems:skeletal_totem_of_undying',
  'moretotems:tentacled_totem_of_undying',
  'moretotems:rotting_totem_of_undying'
]
// Set to false to leave Totem of Frost un-nerfed.
const INCLUDE_TOTEM_OF_FROST = true
const FROST_TOTEM = 'fangs_n_claws:totem_of_frost'

const pending = {}

function handSnapshot(stack) {
  return { id: String(stack.id), count: stack.count }
}

function consumed(before, stack) {
  const now = String(stack.id) === before.id ? stack.count : 0
  return now === before.count - 1
}

ForgeEvents.onEvent('net.minecraftforge.event.entity.living.LivingDamageEvent', event => {
  const player = event.entity
  if (!(player instanceof $ServerPlayer)) return

  const uuid = String(player.stringUUID)
  if (pending[uuid]) return

  const health = player.health
  const lethal = event.amount >= health
  const frostRange = health - event.amount <= player.maxHealth * 0.25

  const hands = [handSnapshot(player.mainHandItem), handSnapshot(player.offhandItem)]
  const watched = hands.map(h =>
    (lethal && LETHAL_TOTEMS.indexOf(h.id) >= 0) ||
    (INCLUDE_TOTEM_OF_FROST && frostRange && h.id === FROST_TOTEM))
  if (!watched[0] && !watched[1]) return

  pending[uuid] = true
  player.server.scheduleInTicks(1, () => {
    delete pending[uuid]
    if (!player.isAlive() || player.isRemoved()) return
    const used = (watched[0] && consumed(hands[0], player.mainHandItem)) ||
      (watched[1] && consumed(hands[1], player.offhandItem))
    if (!used) return
    try {
      $PostTotemHandler.handlePostTotem(player)
    } catch (e) {
      console.error('HTN extra-totem compat failed for ' + player.username + ': ' + e)
    }
  })
})

// Unusual End's Void Totem (and its linked variant, same item) saves players from the
// End void from the inventory tick and then puts the item on cooldown. Treat the
// cooldown starting while in the End as a totem use.
const VOID_TOTEM = 'unusualend:void_totem'
const voidCooldown = {}
let voidTotemItem = null

ForgeEvents.onEvent('net.minecraftforge.event.TickEvent$PlayerTickEvent', event => {
  if (String(event.phase) !== 'END' || !event.side.isServer()) return
  const player = event.player
  const uuid = String(player.stringUUID)
  if (String(player.level.dimension).indexOf('minecraft:the_end') < 0) {
    delete voidCooldown[uuid]
    return
  }
  if (voidTotemItem === null) voidTotemItem = Item.of(VOID_TOTEM).item
  const onCooldown = player.cooldowns.isOnCooldown(voidTotemItem)
  const previous = voidCooldown[uuid]
  voidCooldown[uuid] = onCooldown
  // First tick in the End only records state, so entering with an active cooldown is ignored.
  if (previous === undefined || previous || !onCooldown || !player.isAlive()) return
  try {
    $PostTotemHandler.handlePostTotem(player)
  } catch (e) {
    console.error('HTN void-totem compat failed for ' + player.username + ': ' + e)
  }
})
