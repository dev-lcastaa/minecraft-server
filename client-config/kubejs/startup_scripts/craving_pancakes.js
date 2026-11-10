ItemEvents.modification(event => {
  event.modify('supplementaries:pancake', item => {
    // Match one placed pancake; placement, toppings and jukebox use remain available.
    item.foodProperties = food => {
      food.hunger(1)
      food.saturation(0.1)
    }
  })
})
