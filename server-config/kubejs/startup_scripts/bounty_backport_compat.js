ForgeEvents.onEvent('net.minecraftforge.event.village.VillagerTradesEvent', event => {
  const Registries = Java.loadClass('net.minecraftforge.registries.ForgeRegistries');
  const Listing = Java.loadClass('net.minecraftforge.common.BasicItemListing');
  if (String(Registries.VILLAGER_PROFESSIONS.getKey(event.getType())) !== 'minecraft:farmer') return;
  // Append listings; never clear or replace vanilla or another mod's offers.
  ['minecraft:egg', 'backported_animal_variants:blue_egg',
    'backported_animal_variants:brown_egg'].forEach(id => {
    event.getTrades().get(2).add(new Listing(
      Item.of('16x ' + id), Item.of('minecraft:emerald'), 12, 5, 0.05
    ));
  });
});
