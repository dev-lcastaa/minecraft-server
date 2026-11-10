ItemEvents.modification(event => {
  event.modify('supplementaries:pancake', item => {
    // Match one placed pancake; placement, toppings and jukebox use remain available.
    // Call the method: Rhino exposes `foodProperties` as a read-only FoodProperties bean.
    item.setFoodProperties(food => {
      food.hunger(1)
      food.saturation(0.1)
    })
  })
})
