var $CravingFoodConfig = Java.loadClass('net.dyrohc.cravings.ConfigFileFoods')
var CRAVING_CATEGORIES = ['sweet', 'healthy', 'meaty', 'fishy', 'gross', 'fancy', 'hearty', 'raw']
var CRAVING_BIG_DISH = /stew|soup|pasta|noodle|curry|paella|risotto|stroganoff|lasagna|platter|feast|stuffed|shepherd|steak_and|steak_with|breakfast|sinigang|ghoulash|ossobuco|rubaboo|salmagundi|terrine/
var CRAVING_SIMPLE_FOOD = /cookie|candy|gummy|berries|berry$|popsicle|^raw_|_raw$|uncooked|^minced_|^dried_|^apple$|^carrot$|^potato$|^beetroot$|^cod$|^salmon$|^tropical_fish$|^pufferfish$/

function cravingFoodRules(id, food, configured) {
  var path = id.split(':')[1]
  var categories = configured.slice()
  var nutrition = food ? food.getNutrition() : 0
  var fishy = /fish|cod|salmon|trout|perch|pike|tuna|shrimp|prawn|crab|lobster|squid|tentacle|calamari|caviar|roe|sushi/.test(path)
  var rawName = /^raw_|_raw$|uncooked|^minced_/.test(path)
  if (id === 'supplementaries:candy' && categories.indexOf('sweet') < 0) categories.push('sweet')
  if (id === 'supplementaries:pancake' && categories.indexOf('hearty') < 0) categories.push('hearty')
  if (categories.length === 0) {
    if (/cookie|candy|gummy|chocolate|cocoa|cake|pie|ice_cream|milkshake|pudding|muffin|sweet|berries|fruit|apple|melon|honey|jam|sugar|marshmallow/.test(path)) categories.push('sweet')
    if (/rotten|poison|spider|insect|arthropod|silverfish|maggot|eyeball|slime|flesh|mold|moss|bat_wing/.test(path)) categories.push('gross')
    if (/golden|enchanted|caviar|truffle|deluxe|royal/.test(path)) categories.push('fancy')
    if (/salad|vegetable|carrot|potato|beetroot|cabbage|tomato|onion|kelp|rice|mushroom|nut|acorn|tea|juice|milk/.test(path)) categories.push('healthy')
    if (food && food.isMeat() && !rawName && !fishy) categories.push('meaty')
    if (rawName) categories.push('raw')
    if (CRAVING_BIG_DISH.test(path) || /bread|sandwich|burger|wrap|pancake/.test(path)) categories.push('hearty')
  }
  if (fishy && categories.indexOf('fishy') < 0) categories.push('fishy')
  var fallback = categories.length === 0
  if (fallback) categories.push(nutrition >= 6 ? 'hearty' : 'healthy')
  var raw = categories.indexOf('raw') >= 0 && !CRAVING_BIG_DISH.test(path)
  var cup = /_cup$/.test(path)
  var big = id === 'supplementaries:pancake' ||
    (!raw && !cup && (CRAVING_BIG_DISH.test(path) ||
      (nutrition >= 10 && !/^(cooked|smoked|roasted)_/.test(path))))
  var simple = !big && !cup && (raw || CRAVING_SIMPLE_FOOD.test(path) || nutrition <= 4)
  return {categories: categories, tier: big ? 'big_meal' : simple ? 'simple_food' : 'regular_food', fallback: fallback}
}

function cravingConsumable(stack) {
  var id = String(stack.id)
  // Potions cleanse the palate rather than acting as a meal, including modded potions.
  var drink = String(stack.getUseAnimation()) === 'DRINK' && !/potion|^cravings:/.test(id)
  return stack.item.isEdible() || global.lunchBasketPlaceableFood(stack.item) || drink
}

ServerEvents.tags('item', event => {
  var config = $CravingFoodConfig.SERVER
  var configured = {}
  CRAVING_CATEGORIES.forEach(category => {
    var lists = [config['CFG_' + category + '_foods'].get()]
    if (config.CFG_FD_toggle.get()) lists.push(config['CFG_FD_' + category + '_foods'].get())
    lists.forEach(list => list.forEach(id => {
      id = String(id)
      if (!configured[id]) configured[id] = []
      if (configured[id].indexOf(category) < 0) configured[id].push(category)
    }))
  })
  var foods = []
  var fallback = []
  var tags = {big_meal: [], simple_food: [], regular_food: []}
  CRAVING_CATEGORIES.forEach(category => { tags[category] = [] })
  Item.getTypeList().forEach(value => {
    var id = String(value)
    var stack = Item.of(id)
    var item = stack.item
    if (!cravingConsumable(stack) && !configured[id]) return
    var rules = cravingFoodRules(id, item.getFoodProperties(), configured[id] || [])
    foods.push(id)
    rules.categories.forEach(category => tags[category].push(id))
    tags[rules.tier].push(id)
    if (rules.fallback) fallback.push(id)
  })
  event.add('cravings:foods', foods)
  Object.keys(tags).forEach(tag => event.add('cravings:' + tag, tags[tag]))
  if (fallback.length > 0) console.warn('Cravings: assigned uncategorized foods by nutrition: ' + fallback.join(', '))
  console.info('Cravings: categorized ' + foods.length + ' foods; simple=' + tags.simple_food.length +
    ', regular=' + tags.regular_food.length + ', big=' + tags.big_meal.length)
})

ServerEvents.loaded(() => {
  var missing = []
  var foods = Ingredient.of('#cravings:foods').itemIds
  var categories = CRAVING_CATEGORIES.map(category => Ingredient.of('#cravings:' + category))
  var tiers = ['simple_food', 'regular_food', 'big_meal'].map(tier => Ingredient.of('#cravings:' + tier))
  var foodTag = Ingredient.of('#cravings:foods')
  Item.getTypeList().forEach(id => {
    var stack = Item.of(id)
    if (cravingConsumable(stack) && !foodTag.test(stack)) missing.push(String(id) + ' (not in food tag)')
  })
  foods.forEach(id => {
    var stack = Item.of(id)
    if (!categories.some(category => category.test(stack)) ||
        tiers.filter(tier => tier.test(stack)).length !== 1) missing.push(String(id))
  })
  if (foods.size() === 0 || missing.length > 0) {
    throw new Error('Cravings coverage validation failed: ' +
      (foods.size() === 0 ? 'empty food registry' : missing.join(', ')))
  }
  console.info('Cravings: validated categories and one duration tier for all ' + foods.size() + ' foods')
})
