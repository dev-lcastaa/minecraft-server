ForgeEvents.onEvent('net.minecraftforge.event.entity.living.LivingDropsEvent', event => {
  if (global.mobLootCompatDrops) global.mobLootCompatDrops(event)
})
