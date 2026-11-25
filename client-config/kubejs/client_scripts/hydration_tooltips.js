ItemEvents.tooltip(event => {
  event.add('farmersdelight:cooking_pot', Text.gray('Heat ordinary water bottles to purify; supply an empty glass bottle for serving.'));
  event.add('farmersrespite:kettle', Text.gray('Heat water or brew drinks to fully purify. Native fluid amounts and bottle costs apply.'));
  event.add('minecraft:glass_bottle', Text.gray('Dog water bowls cannot refill bottles. Named or effect-bearing potions are not pot ingredients.'));
});
