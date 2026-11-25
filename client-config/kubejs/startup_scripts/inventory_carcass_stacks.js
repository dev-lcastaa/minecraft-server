// Butcher's Delight's raw, placed, skinned, hanging/processed and roasted animal carcasses.
// This changes item limits at registration, not inventory contents or item NBT.
ItemEvents.modification(event => {
  event.modify(/^butchersdelight:(dead|hooked|hoked|roasted)/, item => {
    item.maxStackSize = 16;
  });
});
