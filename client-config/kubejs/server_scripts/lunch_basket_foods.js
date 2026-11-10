var $LunchBasketBlockItem = Java.loadClass('net.minecraft.world.item.BlockItem')

var LUNCH_BASKET_FOOD_TAG = 'serverfixes:lunch_basket_foods'
var LUNCH_BASKET_FOOD_BLOCKS = [
  'net.minecraft.world.level.block.CakeBlock',
  'vectorwing.farmersdelight.common.block.FeastBlock',
  'vectorwing.farmersdelight.common.block.PieBlock',
  'net.mcreator.oceanicdelight.block.SpongeCakeBlock',
  'com.axedgaming.endersdelight.block.PieBlock',
  'com.soytutta.mynethersdelight.common.block.MagmaCakeBlock',
  'net.mehvahdjukaar.supplementaries.common.block.blocks.PancakeBlock',
  'com.jkvin114.displaydelight.block.FoodBlock',
  'com.jkvin114.displaydelight.block.SmallPlatedFoodBlock',
  'com.jkvin114.displaydelight.block.AbstractStackablePlatedFoodBlock'
]

function lunchBasketPlaceableFood(item) {
  if (!(item instanceof $LunchBasketBlockItem)) return false
  for (var type = item.getBlock().getClass(); type !== null; type = type.getSuperclass()) {
    if (LUNCH_BASKET_FOOD_BLOCKS.indexOf(String(type.getName())) >= 0) return true
  }
  return false
}

global.lunchBasketPlaceableFood = lunchBasketPlaceableFood

ServerEvents.tags('item', event => {
  var foods = []
  // Unlike Item.getList(), this includes items outside creative tabs and foods from newly added mods.
  Item.getTypeList().forEach(id => {
    var item = Item.of(id).item
    if (item.isEdible() || lunchBasketPlaceableFood(item)) foods.push(String(id))
  })
  event.add(LUNCH_BASKET_FOOD_TAG, foods)
  console.info('Lunch basket compatibility: registered ' + foods.length + ' foods and placeable meals')
})

ServerEvents.loaded(() => {
  var basket = Java.loadClass('net.mehvahdjukaar.supplementaries.common.items.LunchBoxItem')
  var foods = Ingredient.of('#' + LUNCH_BASKET_FOOD_TAG).itemIds
  var rejected = []
  foods.forEach(id => {
    if (!basket.canAcceptItem(Item.of(id))) rejected.push(String(id))
  })
  if (foods.size() === 0 || rejected.length > 0) {
    throw new Error('Lunch basket compatibility validation failed: ' +
      (foods.size() === 0 ? 'food tag is empty' : 'rejected ' + rejected.join(', ')))
  }
  console.info('Lunch basket compatibility: validated ' + foods.size() + ' food-tag items')
})
