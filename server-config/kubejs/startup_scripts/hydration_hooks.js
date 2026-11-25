const HydrationThirst = Java.loadClass('dev.ghen.thirst.api.ThirstHelper');
const HydrationUseAnim = Java.loadClass('net.minecraft.world.item.UseAnim');
let HydrationBrewingBefore = null;
const HydrationForge = Java.loadClass('net.minecraftforge.common.MinecraftForge');
const HydrationPriority = Java.loadClass('net.minecraftforge.eventbus.api.EventPriority');
const HydrationMath = Java.loadClass('dev.ghen.thirst.foundation.util.MathHelper');
const HydrationClipFluid = Java.loadClass('net.minecraft.world.level.ClipContext$Fluid');
const HydrationBowl = Java.loadClass('doggytalents.common.block.FoodBowlBlock');
const HydrationPotion = Java.loadClass('net.minecraft.world.item.PotionItem');

function hydrationPreparedDrink(stack) {
  return !stack.isEmpty() && (HydrationThirst.isDrink(stack) || stack.getUseAnimation() === HydrationUseAnim.DRINK);
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
      const result = event.getItem(slot);
      if (result.isEmpty() || !(hydrationPreparedDrink(result) || result.getItem() instanceof HydrationPotion)) continue;
      // Vanilla mixing can replace the entire stack: merge old custom data, but let new Potion/effects win.
      if (before !== null && before[slot].hasTag()) {
        const tag = before[slot].getTag().copy();
        if (result.hasTag()) tag.merge(result.getTag());
        result.setTag(tag);
      }
      result.getOrCreateTag().putInt('Purity', 3);
    }
  });

// Block both vanilla and Thirst's running-water path before either consumes a glass bottle.
HydrationForge.EVENT_BUS.addListener(HydrationPriority.HIGHEST, false,
  Java.loadClass('net.minecraftforge.event.entity.player.PlayerInteractEvent$RightClickItem'), event => {
    if (event.getItemStack().id !== 'minecraft:glass_bottle') return;
    const player = event.getEntity();
    const level = player.level();
    const hit = HydrationMath.getPlayerPOVHitResult(level, player, HydrationClipFluid.ANY);
    if (level.getBlockState(hit.getBlockPos()).getBlock() instanceof HydrationBowl) event.setCanceled(true);
  });
