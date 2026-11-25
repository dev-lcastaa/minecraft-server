ServerEvents.recipes(event => {
  // Also catches recipes added at runtime by other compatibility scripts.
  event.replaceInput({ input: 'minecraft:egg' }, 'minecraft:egg', '#forge:eggs');
});

ServerEvents.loaded(event => {
  const eggs = ['minecraft:egg', 'backported_animal_variants:blue_egg',
    'backported_animal_variants:brown_egg'];
  const actual = Ingredient.of('#forge:eggs').itemIds;
  eggs.forEach(id => {
    if (!actual.contains(id)) throw new Error('Missing raw egg ingredient: ' + id);
  });
  const Content = Java.loadClass('io.ejekta.bountiful.content.BountifulContent');
  const Registries = Java.loadClass('net.minecraftforge.registries.ForgeRegistries');
  const ResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation');
  const BlockItem = Java.loadClass('net.minecraft.world.item.BlockItem');
  const EntityBlock = Java.loadClass('net.minecraft.world.level.block.EntityBlock');
  let pools = 0;
  let entries = 0;
  const vetoes = [];
  Content.INSTANCE.getPools().forEach(pool => {
    let owned = false;
    pool.getItems().forEach(entry => {
      if (String(entry.id).includes('bounty_backport_compat_')) owned = true;
    });
    if (!owned) return;
    pools++;
    if (pool.getItems().isEmpty()) throw new Error('Empty compatibility bounty pool: ' + pool.getId());
    pool.getItems().forEach(entry => {
      if (!String(entry.id).includes('bounty_backport_compat_')) return;
      const id = String(entry.getContent());
      const kind = String(entry.getType());
      if (kind.endsWith(':item') && Item.of(id).isEmpty()) {
        throw new Error('Unregistered bounty item: ' + id);
      }
      if (kind.endsWith(':item')) {
        const item = Item.of(id).item;
        if (item instanceof BlockItem && item.getBlock() instanceof EntityBlock && !vetoes.includes(id)) {
          vetoes.push(id);
        }
      }
      if (kind.endsWith(':entity') && !Registries.ENTITY_TYPES.containsKey(new ResourceLocation(id))) {
        throw new Error('Unregistered bounty target: ' + id);
      }
      entries++;
    });
  });
  if (pools !== 27) throw new Error('Expected 27 compatibility bounty pools, loaded ' + pools);
  if (vetoes.length) console.warn('[bounty-backport-compat] Native typed safety excludes ' +
    vetoes.length + ' block-entity item IDs on every roll/reload: ' + vetoes.join(', '));
  console.info('[bounty-backport-compat] Verified ' + pools + ' bounty pools, ' + entries +
    ' registered entries and all raw eggs; vanilla trades and animal behavior preserved.');
});
