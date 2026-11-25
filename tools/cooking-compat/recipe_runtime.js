function cookingMissingIngredient(ingredient) {
  if (Array.isArray(ingredient)) {
    var missing = null
    for (var alternative of ingredient) {
      var item = cookingMissingIngredient(alternative)
      if (item === null) return null
      if (missing === null) missing = item
    }
    return missing
  }
  if (ingredient && typeof ingredient.item === 'string' && Item.of(ingredient.item).isEmpty()) {
    return ingredient.item
  }
  return null
}

function cookingMissingRecipeItem(recipe) {
  var inputs = (recipe.ingredients || []).concat(recipe.ingredient ? [recipe.ingredient] : [])
  if (recipe.key) Object.keys(recipe.key).forEach(key => inputs.push(recipe.key[key]))
  if (recipe.input) inputs.push(recipe.input)
  for (var ingredient of inputs) {
    var missing = cookingMissingIngredient(ingredient)
    if (missing !== null) return missing
  }
  for (var field of ['result', 'results', 'output', 'outputs', 'container']) {
    var value = recipe[field]
    for (var output of Array.isArray(value) ? value : [value]) {
      var missing = cookingMissingIngredient(output)
      if (missing !== null) return missing
    }
  }
  return null
}

ServerEvents.recipes(event => {
  COOKING_COMPAT_REMOVALS.forEach(id => event.remove({ id: id }))
  Object.keys(COOKING_COMPAT_RECIPES).forEach(id => {
    var recipe = COOKING_COMPAT_RECIPES[id]
    var missing = cookingMissingRecipeItem(recipe)
    if (missing !== null) {
      console.warn('[cooking-compat] Skipped ' + id + ': unregistered item ' + missing)
      return
    }
    event.remove({ id: id })
    event.custom(recipe).id(id)
  })
})
