var $CravingVariables = Java.loadClass('net.dyrohc.cravings.network.CravingsModVariables')
var $CravingSounds = Java.loadClass('net.minecraftforge.registries.ForgeRegistries')
var $CravingLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
var cravingChime = $CravingSounds.SOUND_EVENTS.getValue(new $CravingLocation('minecraft:block.amethyst_block.resonate'))
var cravingFeedbackTick = 0
var cravingLastChime = -40
var cravingHeldKey = ''
var cravingHoverKey = ''
var cravingHoverTick = -2
var cravingFeedbackPlayer = null

function cravingCurrent() {
  if (!Client.player) return 'None'
  var variables = Client.player.getCapability($CravingVariables.PLAYER_VARIABLES).orElse(null)
  if (variables === null) throw new Error('Cravings feedback: player capability is missing')
  return String(variables.current_craving)
}

function cravingMatchingKey(stack, craving) {
  if (!stack || stack.isEmpty() || craving === 'None') return ''
  return Ingredient.of('#cravings:' + craving.toLowerCase()).test(stack) ? craving + ':' + stack.id : ''
}

function cravingNotify(key) {
  if (key && cravingFeedbackTick - cravingLastChime >= 40) {
    Client.player.playSound(cravingChime, 1, 1)
    cravingLastChime = cravingFeedbackTick
  }
}

ClientEvents.tick(() => {
  cravingFeedbackTick++
  var playerId = Client.player ? String(Client.player.getUUID()) : null
  if (playerId !== cravingFeedbackPlayer) {
    cravingFeedbackPlayer = playerId
    cravingLastChime = -40
    cravingHeldKey = ''
    cravingHoverKey = ''
  }
  if (!Client.player) return
  if (cravingFeedbackTick - cravingHoverTick > 2) cravingHoverKey = ''
  var craving = cravingCurrent()
  var key = cravingMatchingKey(Client.player.getMainHandItem(), craving) ||
    cravingMatchingKey(Client.player.getOffhandItem(), craving)
  if (key !== cravingHeldKey) {
    cravingHeldKey = key
    cravingNotify(key)
  }
})

ItemEvents.tooltip(event => {
  event.addAdvancedToAll((stack, advanced, lines) => {
    var craving = cravingCurrent()
    var key = cravingMatchingKey(stack, craving)
    cravingHoverTick = cravingFeedbackTick
    if (key !== cravingHoverKey) {
      cravingHoverKey = key
      cravingNotify(key)
    }
    if (!key) return
    lines.add(Text.translate('serverfixes.craving.matches', Text.translate('serverfixes.craving.' + craving.toLowerCase())).green())
    if (craving !== 'Raw') {
      var multiplier = Ingredient.of('#cravings:big_meal').test(stack) ? 2 :
        Ingredient.of('#cravings:simple_food').test(stack) ? 0.5 : 1
      lines.add(Text.translate('serverfixes.craving.duration', String(multiplier)).gray())
    }
  })
})
