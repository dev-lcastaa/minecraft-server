ServerEvents.loaded(event => {
  const Registries = Java.loadClass('net.minecraftforge.registries.ForgeRegistries')
  const Growth = Java.loadClass('com.teamtea.eclipticseasons.common.core.crop.CropGrowthHandler')
  const Plant = Java.loadClass('net.minecraftforge.common.IPlantable')
  const Bonemealable = Java.loadClass('net.minecraft.world.level.block.BonemealableBlock')
  let configured = 0
  const uncovered = []
  Registries.BLOCKS.getValues().forEach(block => {
    if (!(block instanceof Plant) && !(block instanceof Bonemealable)) return
    if (Growth.getControlMap(block) != null) configured++
    else uncovered.push(String(Registries.BLOCKS.getKey(block)))
  })
  console.info('[Jade Seasons] Native Ecliptic control maps: ' + configured +
    ' growth-capable blocks; ' + uncovered.length + ' without configured rules.')
  if (uncovered.length) console.info('[Jade Seasons] No seasonal rule configured (not assigned arbitrary seasons): ' +
    uncovered.sort().join(', '))
})
