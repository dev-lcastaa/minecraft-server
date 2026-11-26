// Thirst copies its drink/food maps into static fields once, when ThirstHelper initialises.
// Startup scripts run before items are registered and configs load, so loading it here would
// freeze every modded drink as minecraft:air. Only load it from event handlers.
let HydrationThirst = null;
function hydrationThirst() {
  if (HydrationThirst === null) HydrationThirst = Java.loadClass('dev.ghen.thirst.api.ThirstHelper');
  return HydrationThirst;
}
const HydrationUseAnim = Java.loadClass('net.minecraft.world.item.UseAnim');
let HydrationBrewingBefore = null;
const HydrationForge = Java.loadClass('net.minecraftforge.common.MinecraftForge');
const HydrationPriority = Java.loadClass('net.minecraftforge.eventbus.api.EventPriority');
const HydrationMath = Java.loadClass('dev.ghen.thirst.foundation.util.MathHelper');
const HydrationClipFluid = Java.loadClass('net.minecraft.world.level.ClipContext$Fluid');
const HydrationBowl = Java.loadClass('doggytalents.common.block.FoodBowlBlock');
const HydrationBath = Java.loadClass('doggytalents.common.block.DogBathBlock');
const HydrationPotion = Java.loadClass('net.minecraft.world.item.PotionItem');

function hydrationPreparedDrink(stack) {
  return !stack.isEmpty() && (hydrationThirst().isDrink(stack) || stack.getUseAnimation() === HydrationUseAnim.DRINK);
}

ForgeEvents.onEvent('net.minecraftforge.event.entity.player.PlayerEvent$ItemCraftedEvent', event => {
  const stack = event.getCrafting();
  if (hydrationPreparedDrink(stack)) stack.getOrCreateTag().putInt('Purity', 3);
});

HydrationForge.EVENT_BUS.addListener(HydrationPriority.HIGHEST, false,
  Java.loadClass('net.minecraftforge.event.brewing.PotionBrewEvent$Pre'), event => {
    HydrationBrewingBefore = [event.getItem(0).copy(), event.getItem(1).copy(), event.getItem(2).copy()];
  });
HydrationForge.EVENT_BUS.addListener(HydrationPriority.LOWEST, false,
  Java.loadClass('net.minecraftforge.event.brewing.PotionBrewEvent$Post'), event => {
    const before = HydrationBrewingBefore;
    HydrationBrewingBefore = null;
    for (let slot = 0; slot < 3; slot++) {
      var result = event.getItem(slot);
      if (result.isEmpty() || !(hydrationPreparedDrink(result) || result.getItem() instanceof HydrationPotion)) continue;
      // Rhino binds const/let inside loop bodies once, so per-slot values must use var.
      // Vanilla mixing can replace the entire stack: merge old custom data, but let new Potion/effects win.
      // KubeJS remaps vanilla ItemStack getTag/setTag to getNbt/setNbt; getTag()/hasTag() do not exist in JS.
      if (before !== null && before[slot].getNbt() !== null) {
        var tag = before[slot].getNbt().copy();
        if (result.getNbt() !== null) tag.merge(result.getNbt());
        result.setNbt(tag);
      }
      result.getOrCreateTag().putInt('Purity', 3);
    }
  });

function hydrationDogWater(block) {
  return block instanceof HydrationBowl || block instanceof HydrationBath;
}

// Doggy Talents' dog bath hands out water bottles from its own use() method, before any item use.
HydrationForge.EVENT_BUS.addListener(HydrationPriority.HIGHEST, false,
  Java.loadClass('net.minecraftforge.event.entity.player.PlayerInteractEvent$RightClickBlock'), event => {
    if (event.getItemStack().id !== 'minecraft:glass_bottle') return;
    if (hydrationDogWater(event.getLevel().getBlockState(event.getPos()).getBlock())) event.setCanceled(true);
  });

// Block both vanilla and Thirst's running-water path (waterlogged bowls/baths) before either consumes a glass bottle.
HydrationForge.EVENT_BUS.addListener(HydrationPriority.HIGHEST, false,
  Java.loadClass('net.minecraftforge.event.entity.player.PlayerInteractEvent$RightClickItem'), event => {
    if (event.getItemStack().id !== 'minecraft:glass_bottle') return;
    const player = event.getEntity();
    const level = event.getLevel();
    const hit = HydrationMath.getPlayerPOVHitResult(level, player, HydrationClipFluid.ANY);
    if (hydrationDogWater(level.getBlockState(hit.getBlockPos()).getBlock())) event.setCanceled(true);
  });
