// Nether's Delight and My Nether's Delight register the same foods/blocks under
// their own namespaces. My Nether's Delight is the canonical source: Nether's
// Delight recipes that only produce a duplicate are removed, recipes that still
// matter accept the MND item, and leftover ND items can be crafted 1:1 into MND.
// Loot-side duplicates are disabled in the modpack-fixes datapack.

const NETHERS_DELIGHT_DUPLICATES = {
  'nethersdelight:crimson_fungus_colony': 'mynethersdelight:crimson_fungus_colony',
  'nethersdelight:warped_fungus_colony': 'mynethersdelight:warped_fungus_colony',
  'nethersdelight:hoglin_hide': 'mynethersdelight:hoglin_hide',
  'nethersdelight:hoglin_loin': 'mynethersdelight:hoglin_loin',
  'nethersdelight:hoglin_trophy': 'mynethersdelight:hoglin_trophy',
  'nethersdelight:raw_stuffed_hoglin': 'mynethersdelight:raw_stuffed_hoglin',
  'nethersdelight:stuffed_hoglin': 'mynethersdelight:roast_stuffed_hoglin',
  'nethersdelight:plate_of_stuffed_hoglin_ham': 'mynethersdelight:plate_of_stuffed_hoglin_ham',
  'nethersdelight:plate_of_stuffed_hoglin_snout': 'mynethersdelight:plate_of_stuffed_hoglin_snout',
  'nethersdelight:plate_of_stuffed_hoglin_roast': 'mynethersdelight:plate_of_stuffed_hoglin',
  'nethersdelight:strider_slice': 'mynethersdelight:strider_slice',
  'nethersdelight:ground_strider': 'mynethersdelight:minced_strider'
}

const NETHERS_DELIGHT_REDUNDANT_RECIPES = [
  'nethersdelight:cutting/crimson_fungus_colony',
  'nethersdelight:cutting/warped_fungus_colony',
  'nethersdelight:cutting/hoglin_hide',
  'nethersdelight:cutting/strider_slice',
  'nethersdelight:hoglin_trophy',
  'nethersdelight:raw_stuffed_hoglin',
  'farmersdelight:cooking/stuffed_hoglin'
]

global.nethersDelightDuplicates = NETHERS_DELIGHT_DUPLICATES

ServerEvents.tags('item', event => {
  // ND-only strider dishes (grilled strider, moss stew, nether skewer) use this tag.
  event.add('nethersdelight:raw_strider', ['mynethersdelight:strider_slice', 'mynethersdelight:minced_strider'])
})

ServerEvents.tags('block', event => {
  event.add('nethersdelight:soul_compost_activators', [
    'mynethersdelight:crimson_fungus_colony',
    'mynethersdelight:warped_fungus_colony'
  ])
})

ServerEvents.recipes(event => {
  NETHERS_DELIGHT_REDUNDANT_RECIPES.forEach(id => event.remove({ id: id }))

  event.replaceInput(
    { id: 'nethersdelight:soul_compost_from_hoglin_hide' },
    'nethersdelight:hoglin_hide',
    '#mynethersdelight:hoglin_hide'
  )
  // MND's cooked loin stands in for ND's sirloin, which now has no fresh source.
  event.replaceInput(
    { id: 'nethersdelight:warped_moldy_meat' },
    'nethersdelight:hoglin_sirloin',
    ['nethersdelight:hoglin_sirloin', 'mynethersdelight:cooked_loin']
  )

  Object.keys(NETHERS_DELIGHT_DUPLICATES).forEach(from => {
    event.shapeless(NETHERS_DELIGHT_DUPLICATES[from], [from])
      .id(`serverfixes:nethersdelight_unify/${from.split(':')[1]}`)
  })
})
