// Hide Nether's Delight copies of items that My Nether's Delight also adds.
// Keep in sync with server_scripts/nethers_delight_unify.js and
// assets/emi/index/stacks/nethersdelight_duplicates.json.

const HIDDEN_NETHERS_DELIGHT_DUPLICATES = [
  'nethersdelight:crimson_fungus_colony',
  'nethersdelight:warped_fungus_colony',
  'nethersdelight:hoglin_hide',
  'nethersdelight:hoglin_loin',
  'nethersdelight:hoglin_trophy',
  'nethersdelight:raw_stuffed_hoglin',
  'nethersdelight:stuffed_hoglin',
  'nethersdelight:plate_of_stuffed_hoglin_ham',
  'nethersdelight:plate_of_stuffed_hoglin_snout',
  'nethersdelight:plate_of_stuffed_hoglin_roast',
  'nethersdelight:strider_slice',
  'nethersdelight:ground_strider'
]

JEIEvents.hideItems(event => {
  HIDDEN_NETHERS_DELIGHT_DUPLICATES.forEach(id => event.hide(id))
})
