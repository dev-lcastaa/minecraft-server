// Adds generated gray stat lines to every item, because most mods ship no descriptive tooltips:
// - breakable items (tools, weapons, armor, shields, bows, ...): durability, enchantability,
//   armor/toughness, mining level/speed for diggers and the repair material;
// - every other item: food values, fuel value, block hardness/blast resistance/light and stack size.
// All lines are read from the item's own data, so they stay accurate for every mod.
var $TieredItem = Java.loadClass('net.minecraft.world.item.TieredItem');
var $DiggerItem = Java.loadClass('net.minecraft.world.item.DiggerItem');
var $ArmorItem = Java.loadClass('net.minecraft.world.item.ArmorItem');
var $BlockItem = Java.loadClass('net.minecraft.world.item.BlockItem');
var $ForgeHooks = Java.loadClass('net.minecraftforge.common.ForgeHooks');

var STAT_LEVEL_NAMES = ['Wood/Gold', 'Stone', 'Iron', 'Diamond', 'Netherite'];
var statCache = {};

function statRepairName(ingredient) {
  if (!ingredient || ingredient.isEmpty()) return null;
  var first = ingredient.getFirst();
  if (!first || first.isEmpty()) return null;
  return String(first.getHoverName().getString());
}

function statFormat(value) {
  return (Math.round(value * 10) / 10).toFixed(1);
}

function statTrim(value) {
  return String(Math.round(value * 10) / 10);
}

function statGearLines(item) {
  var lines = [];
  var repair = null;
  var enchantability = item.getEnchantmentValue();
  if (item instanceof $TieredItem) {
    var tier = item.getTier();
    repair = statRepairName(tier.getRepairIngredient());
    if (item instanceof $DiggerItem) {
      var level = tier.getLevel();
      var levelName = level >= 0 && level < STAT_LEVEL_NAMES.length ? STAT_LEVEL_NAMES[level] : 'Level ' + level;
      lines.push('Mining level: ' + levelName + ' \u00b7 Mining speed: ' + statFormat(tier.getSpeed()));
    }
  } else if (item instanceof $ArmorItem) {
    var armorLine = 'Armor: ' + item.getDefense();
    var toughness = item.getToughness();
    if (toughness > 0) armorLine += ' \u00b7 Toughness: ' + statFormat(toughness);
    lines.push(armorLine);
    repair = statRepairName(item.getMaterial().getRepairIngredient());
  }
  if (enchantability > 0) lines.push('Enchantability: ' + enchantability);
  if (repair) lines.push('Repair material: ' + repair);
  return lines;
}

function statItemLines(stack, item) {
  var lines = [];
  if (item.isEdible()) {
    var food = item.getFoodProperties();
    var nutrition = food ? food.getNutrition() : 0;
    if (nutrition > 0) {
      lines.push('Food: ' + nutrition + ' hunger \u00b7 ' +
        statFormat(nutrition * food.getSaturationModifier() * 2) + ' saturation');
    }
  }
  var burn = 0;
  try {
    burn = $ForgeHooks.getBurnTime(stack, null);
  } catch (e) {
    burn = 0;
  }
  if (burn > 0) lines.push('Fuel: smelts ' + statTrim(burn / 200) + ' items');
  if (item instanceof $BlockItem) {
    var block = item.getBlock();
    var hardness = block.defaultDestroyTime();
    var blockLine = hardness < 0 ? 'Unbreakable' : 'Hardness: ' + statFormat(hardness);
    blockLine += ' \u00b7 Blast resistance: ' + statFormat(block.getExplosionResistance());
    lines.push(blockLine);
    try {
      var light = block.defaultBlockState().getLightEmission();
      if (light > 0) lines.push('Light level: ' + light);
    } catch (e) {
      // Some modded blocks compute light from world context only.
    }
  }
  lines.push('Stacks to ' + stack.getMaxStackSize());
  return lines;
}

// Lines that only depend on the item type, cached per item id.
function statStaticLines(stack, item, breakable) {
  var lines = [];
  try {
    if (breakable) lines = statGearLines(item);
  } catch (e) {
    lines = [];
  }
  if (stack.isDamageableItem()) return lines;
  // Unbreakable gear gets the generic item lines too, so every item shows something.
  try {
    return lines.concat(statItemLines(stack, item));
  } catch (e) {
    return lines.length > 0 ? lines : ['Stacks to ' + stack.getMaxStackSize()];
  }
}

function statLines(stack, advanced) {
  if (stack.isEmpty()) return [];
  var item = stack.getItem();
  var breakable = stack.isDamageableItem() || item instanceof $TieredItem || item instanceof $ArmorItem;
  var id = String(stack.id);
  if (!(id in statCache)) statCache[id] = statStaticLines(stack, item, breakable);
  var lines = [];
  // Vanilla already prints durability in advanced (F3+H) tooltips.
  if (stack.isDamageableItem() && !advanced) {
    var max = stack.getMaxDamage();
    lines.push('Durability: ' + (max - stack.getDamageValue()) + ' / ' + max);
  }
  return lines.concat(statCache[id]);
}

ItemEvents.tooltip(function (event) {
  event.addAdvancedToAll(function (stack, advanced, text) {
    // KubeJS 6 passes a boolean here; newer builds pass a TooltipFlag.
    var isAdvanced = advanced === true || (advanced && typeof advanced.isAdvanced === 'function' && advanced.isAdvanced());
    var lines = statLines(stack, !!isAdvanced);
    for (var i = 0; i < lines.length; i++) text.add(Text.gray(lines[i]));
  });
});
