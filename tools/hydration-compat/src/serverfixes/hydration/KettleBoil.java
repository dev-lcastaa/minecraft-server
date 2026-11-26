package serverfixes.hydration;

import java.util.Map;
import java.util.WeakHashMap;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.Fluids;
import net.minecraftforge.fluids.FluidStack;
import umpaz.farmersrespite.common.block.entity.KettleBlockEntity;

/**
 * Farmer's Respite only brews when an ingredient slot holds an item, so plain water never boiled.
 * A heated kettle with empty ingredient slots now boils its water to Thirst's Purity 3.
 */
public final class KettleBoil {
    /** Matches the brewingtime of water_compat:kettle_water, which EMI/JEI show as the boil step. */
    public static final int BOIL_TICKS = 200;
    public static final int PURIFIED = 3;
    static final Map<KettleBlockEntity, Integer> PROGRESS = new WeakHashMap<>();

    private KettleBoil() { }

    public static boolean shouldBoil(boolean water, int amount, int purity, boolean heated, boolean ingredientsEmpty) {
        return water && amount > 0 && purity < PURIFIED && heated && ingredientsEmpty;
    }

    static int purity(FluidStack fluid) {
        return fluid.hasTag() && fluid.getTag().m_128441_("Purity") ? fluid.getTag().m_128451_("Purity") : -1;
    }

    public static void tick(Level level, BlockPos pos, BlockState state, KettleBlockEntity kettle) {
        if (level.m_5776_()) return;
        FluidStack fluid = kettle.getFluidTank().getFluid();
        boolean idle = kettle.getInventory().getStackInSlot(0).m_41619_()
            && kettle.getInventory().getStackInSlot(1).m_41619_();
        if (!shouldBoil(!fluid.isEmpty() && fluid.getFluid().m_6212_(Fluids.f_76193_), fluid.getAmount(),
                purity(fluid), kettle.isHeated(level, pos), idle)) {
            PROGRESS.remove(kettle);
            return;
        }
        int ticks = PROGRESS.merge(kettle, 1, Integer::sum);
        if (ticks < BOIL_TICKS) return;
        PROGRESS.remove(kettle);
        fluid.getOrCreateTag().m_128405_("Purity", PURIFIED);
        kettle.m_6596_();
        level.m_7260_(pos, state, state, 3);
    }
}
