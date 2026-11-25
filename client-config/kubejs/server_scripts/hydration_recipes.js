// priority: -1000
const HydrationRecipeThirst = Java.loadClass('dev.ghen.thirst.api.ThirstHelper');
const HydrationRecipeUseAnim = Java.loadClass('net.minecraft.world.item.UseAnim');
const HydrationTagParser = Java.loadClass('net.minecraft.nbt.TagParser');

ServerEvents.recipes(event => {
  let purified = 0;
  let alreadyPure = 0;
  const drinks = {};
  const serializers = {};
  const unsupported = [];
  event.forEachRecipe({}, recipe => {
    recipe.serialize();
    const json = JSON.parse(recipe.json.toString());
    let changed = false;
    function output(value, type) {
      const id = typeof value === 'string' ? value : value && (value.item || value.id);
      if (!id) return value;
      const stack = Item.of(id);
      if (stack.isEmpty() || !(HydrationRecipeThirst.isDrink(stack) ||
          stack.getUseAnimation() === HydrationRecipeUseAnim.DRINK)) return value;
      drinks[id] = true;
      serializers[type] = (serializers[type] || 0) + 1;
      if (typeof value === 'string') {
        if (type !== 'minecraft:smelting' && type !== 'minecraft:campfire_cooking' &&
            type !== 'minecraft:crafting_shaped' && type !== 'minecraft:crafting_shapeless') {
          unsupported.push(recipe.getId() + ' [' + type + '] string output ' + id);
          return value;
        }
        value = {item: value};
      }
      const tagKey = value.item ? 'nbt' : 'tag';
      const tag = HydrationTagParser.parseTag(typeof value[tagKey] === 'string' ?
        value[tagKey] : JSON.stringify(value[tagKey] || {}));
      if (tag.getInt('Purity') === 3) {
        alreadyPure++;
        return value;
      }
      tag.putInt('Purity', 3);
      value[tagKey] = tagKey === 'tag' && typeof value.tag !== 'string' ?
        Object.assign({}, value.tag || {}, {Purity: 3}) : tag.toString();
      purified++;
      changed = true;
      return value;
    }
    function prepare(data) {
      // Only output fields and conditional recipe bodies, never ingredients or container returns.
      if (data.result) data.result = output(data.result, data.type);
      if (data.output) data.output = output(data.output, data.type);
      if (Array.isArray(data.results)) data.results = data.results.map(value => output(value, data.type));
      if (data.type === 'forge:conditional' && Array.isArray(data.recipes))
        data.recipes.forEach(branch => {
          if (!branch.recipe) {
            console.warn('[Hydration] Conditional branch has no recipe body; unchanged: ' + recipe.getId());
            return;
          }
          prepare(branch.recipe);
        });
    }
    prepare(json);
    if (changed) recipe.merge(json);
  });
  console.info('[Hydration] Prepared outputs changed=' + purified + ', alreadyPure=' + alreadyPure +
    ', uniqueDrinks=' + Object.keys(drinks).length + ', unsupported=' + unsupported.length +
    ', serializers=' + JSON.stringify(serializers));
  unsupported.forEach(value => console.warn('[Hydration] Unsupported prepared drink: ' + value));
});
