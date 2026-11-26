package serverfixes.plantercompat;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.TagKey;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.BonemealableBlock;
import net.minecraft.world.level.block.GrowingPlantBlock;
import net.minecraft.world.level.block.MultifaceBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraftforge.common.IPlantable;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.registries.ForgeRegistries;

/** Runtime hooks installed by coremods/planter_compat.js; all Minecraft members are SRG names. */
@Mod("planter_compat")
public final class Compat {
    static final TagKey<Block> PLANTERS = tag("planters");
    static final TagKey<Block> PLANTS = tag("planter_plants");
    static final TagKey<Block> NOT_PLANTS = tag("not_planter_plants");
    static final ResourceLocation CRIMSON_COLONY = new ResourceLocation("mynethersdelight", "crimson_fungus_colony");
    static final ResourceLocation WARPED_COLONY = new ResourceLocation("mynethersdelight", "warped_fungus_colony");
    private static final String PLANTER_CLASS = "net.mehvahdjukaar.supplementaries.common.block.blocks.PlanterBlock";
    // Floor plants only: vines/lichen attach elsewhere, so a planter below must not keep them alive.
    private static final ClassValue<Boolean> PLANT_CLASS = new ClassValue<>() {
        @Override
        protected Boolean computeValue(Class<?> type) {
            return !GrowingPlantBlock.class.isAssignableFrom(type) && !MultifaceBlock.class.isAssignableFrom(type)
                && (IPlantable.class.isAssignableFrom(type) || BonemealableBlock.class.isAssignableFrom(type));
        }
    };
    private static volatile Class<?> planterClass;

    public Compat() {
    }

    private static TagKey<Block> tag(String path) {
        return TagKey.m_203882_(Registries.f_256747_, new ResourceLocation("planter_compat", path));
    }

    /** Head of BlockStateBase.canSurvive: any seed, sapling, flower or crop may stand on a planter. */
    public static boolean survivesOnPlanter(BlockBehaviour.BlockStateBase state, LevelReader level, BlockPos pos) {
        Block block = state.m_60734_();
        boolean listed = state.m_204336_(PLANTS);
        if (!listed && !PLANT_CLASS.get(block.getClass())) return false;
        if (state.m_204336_(NOT_PLANTS) || !isPlanter(level.m_8055_(pos.m_7495_()))) return false;
        boolean plantable = listed || block instanceof IPlantable;
        for (Property<?> property : state.m_61147_()) {
            String name = property.m_61708_();
            if (name.equals("hanging") && Boolean.TRUE.equals(value(state, property))) return false;
            // Bonemealable wall growths (cocoa, shelf fungi) depend on their side support, not the block below.
            if (!plantable && (name.equals("facing") || name.equals("face"))) return false;
        }
        return true;
    }

    /** Head of Farmer's Delight RichSoilBlock.convertMushroomToColony (rich soil and rich planters). */
    public static boolean convertFungus(BlockState state, BlockPos pos, Level level) {
        ResourceLocation id = state.m_60713_(Blocks.f_50700_) ? CRIMSON_COLONY
            : state.m_60713_(Blocks.f_50691_) ? WARPED_COLONY : null;
        if (id == null) return false;
        Block colony = ForgeRegistries.BLOCKS.getValue(id);
        if (colony == null || colony == Blocks.f_50016_) return false;
        BlockState target = colony.m_49966_();
        // Colonies keep Farmer's Delight's light rule off mushroom-growth soil; never convert into a broken block.
        if (!target.m_60710_(level, pos)) return false;
        return level.m_46597_(pos, target);
    }

    static boolean isPlanter(BlockState below) {
        if (below.m_204336_(PLANTERS)) return true;
        Class<?> type = planterClass;
        if (type == null) {
            try {
                type = Class.forName(PLANTER_CLASS, false, Compat.class.getClassLoader());
            } catch (ClassNotFoundException | LinkageError missing) {
                type = Void.class;
            }
            planterClass = type;
        }
        return type.isInstance(below.m_60734_());
    }

    private static <T extends Comparable<T>> T value(BlockBehaviour.BlockStateBase state, Property<T> property) {
        return state.m_61143_(property);
    }
}
