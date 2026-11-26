import java.util.Map;
import net.mehvahdjukaar.supplementaries.common.block.blocks.PlanterBlock;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.*;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraftforge.common.IPlantable;
import net.minecraftforge.registries.ForgeRegistries;
import serverfixes.plantercompat.Compat;

/** Runs the real compiled helper against small behavioral Minecraft stand-ins. */
class BehaviorTest {
    static class Crop extends Block implements IPlantable {}
    static class Sapling extends Block implements IPlantable {}
    static class BambooSapling extends Block implements BonemealableBlock {}
    static class Cocoa extends Block implements BonemealableBlock {}
    static class Vines extends GrowingPlantBlock implements BonemealableBlock {}
    static class Lichen extends MultifaceBlock implements BonemealableBlock {}

    static final BlockPos PLANT = new BlockPos(0, 65, 0);
    static final BlockPos SOIL = new BlockPos(0, 64, 0);

    static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    static boolean on(Block soil, BlockState plant) {
        Level level = new Level();
        level.states.put(SOIL, soil.m_49966_());
        return Compat.survivesOnPlanter(plant, level, PLANT);
    }

    public static void main(String[] args) {
        Block planter = new PlanterBlock();
        Block stone = new Block();
        check(on(planter, new Crop().m_49966_()), "Modded crop with custom mayPlaceOn rejected on planter");
        check(!on(stone, new Crop().m_49966_()), "Plant forced to survive away from planters");
        check(on(planter, new Sapling().m_49966_()), "Sapling rejected on planter");
        check(on(planter, new BambooSapling().m_49966_()), "Bonemealable floor plant (bamboo) rejected");
        check(!on(planter, new Block().m_49966_()), "Non-plant block affected");

        Property<Boolean> hanging = new Property<>("hanging");
        BlockState hangingPropagule = new Sapling().m_49966_().with(hanging, true);
        check(!on(planter, hangingPropagule), "Hanging plant kept alive by a planter below it");
        check(on(planter, new Sapling().m_49966_().with(hanging, false)), "Standing propagule rejected");
        Property<String> facing = new Property<>("facing");
        check(!on(planter, new Cocoa().m_49966_().with(facing, "north")), "Wall-attached cocoa kept alive");
        check(on(planter, new Crop().m_49966_().with(facing, "north")), "Plantable with facing (attached stem) rejected");
        check(!on(planter, new Vines().m_49966_()), "Hanging vines kept alive by planter");
        check(!on(planter, new Lichen().m_49966_()), "Glow lichen kept alive by planter");

        Block excluded = new Crop();
        excluded.tags.add("planter_compat:not_planter_plants");
        check(!on(planter, excluded.m_49966_()), "Exclusion tag ignored");
        Block listed = new Block();
        listed.tags.add("planter_compat:planter_plants");
        check(on(planter, listed.m_49966_().with(facing, "up")), "Inclusion tag ignored");
        Block taggedPlanter = new Block();
        taggedPlanter.tags.add("planter_compat:planters");
        check(on(taggedPlanter, new Crop().m_49966_()), "Tagged planter-like soil ignored");

        Block crimsonColony = new Block();
        Block warpedColony = new Block();
        ForgeRegistries.VALUES.putAll(Map.of(
            "mynethersdelight:crimson_fungus_colony", crimsonColony,
            "mynethersdelight:warped_fungus_colony", warpedColony));
        Level level = new Level();
        check(Compat.convertFungus(Blocks.f_50700_.m_49966_(), PLANT, level), "Crimson fungus not converted");
        check(level.states.get(PLANT).m_60734_() == crimsonColony, "Crimson fungus became the wrong block");
        check(Compat.convertFungus(Blocks.f_50691_.m_49966_(), PLANT, level), "Warped fungus not converted");
        check(level.states.get(PLANT).m_60734_() == warpedColony, "Warped fungus became the wrong block");
        level.states.clear();
        check(!Compat.convertFungus(Blocks.f_50072_.m_49966_(), PLANT, level), "Brown mushroom hijacked from Farmer's Delight");
        warpedColony.survives = false;
        check(!Compat.convertFungus(Blocks.f_50691_.m_49966_(), PLANT, level), "Converted into a colony that cannot survive");
        check(level.states.isEmpty(), "Unsurvivable conversion changed the world");
        ForgeRegistries.VALUES.clear();
        check(!Compat.convertFungus(Blocks.f_50700_.m_49966_(), PLANT, level), "Converted without My Nether's Delight");
        System.out.println("Planter helper behavior tests passed");
    }
}
