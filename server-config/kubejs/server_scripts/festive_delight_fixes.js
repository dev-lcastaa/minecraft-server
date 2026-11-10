// Festive Delight's own right-click harvest (CinnamonRecoltProcedure) does not
// drop cinnamon on the dedicated server. Harvest the ripe bush here and cancel
// the click so Festive's NORMAL-priority Forge handler cannot drop a second time.

const CINNAMON_BUSH_RIPE = 'festive_delight:cinnamon_bushripe'
const CINNAMON_BUSH = 'festive_delight:cinnamon_bush'
const CINNAMON_DROP = 'festive_delight:cinnamon_sticks'

BlockEvents.rightClicked(CINNAMON_BUSH_RIPE, event => {
  if (event.hand != 'MAIN_HAND') return
  const block = event.block
  const level = block.level
  if (level.isClientSide()) return

  block.set(CINNAMON_BUSH)
  block.popItem(Item.of(CINNAMON_DROP, 1))
  const pitch = (0.8 + Math.random() * 0.4).toFixed(2)
  level.server.runCommandSilent(`execute in ${block.dimension} run playsound minecraft:block.sweet_berry_bush.pick_berries block @a ${block.x + 0.5} ${block.y + 0.5} ${block.z + 0.5} 1 ${pitch}`)
  event.player.swing(event.hand, true)
  event.cancel()
})
