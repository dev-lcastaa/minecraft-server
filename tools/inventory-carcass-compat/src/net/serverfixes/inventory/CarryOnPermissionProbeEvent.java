package net.serverfixes.inventory;

import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraftforge.event.level.BlockEvent;

public final class CarryOnPermissionProbeEvent extends BlockEvent.BreakEvent {
    public CarryOnPermissionProbeEvent(Level level, BlockPos pos, BlockState state, Player player) {
        super(level, pos, state, player);
    }
}
