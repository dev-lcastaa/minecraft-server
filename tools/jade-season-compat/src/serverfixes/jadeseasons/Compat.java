package serverfixes.jadeseasons;

import com.teamtea.eclipticseasons.api.EclipticSeasonsApi;
import com.teamtea.eclipticseasons.api.constant.biome.Humidity;
import com.teamtea.eclipticseasons.api.constant.solar.Season;
import com.teamtea.eclipticseasons.api.constant.solar.SolarTerm;
import com.teamtea.eclipticseasons.api.data.climate.AgroClimaticZone;
import com.teamtea.eclipticseasons.api.data.crop.CropGrowControl;
import com.teamtea.eclipticseasons.api.data.crop.GrowParameter;
import com.teamtea.eclipticseasons.common.core.SolarHolders;
import com.teamtea.eclipticseasons.common.core.crop.CropGrowthHandler;
import com.teamtea.eclipticseasons.common.core.solar.SolarDataManager;
import com.teamtea.eclipticseasons.common.item.GrowthDetectorItem;
import com.teamtea.eclipticseasons.config.CommonConfig;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.BonemealableBlock;
import net.minecraft.world.level.block.CropBlock;
import net.minecraft.world.level.block.FungusBlock;
import net.minecraft.world.level.block.MushroomBlock;
import net.minecraft.world.level.block.SaplingBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraftforge.common.IPlantable;
import net.minecraftforge.common.util.FakePlayer;
import net.minecraftforge.event.entity.player.BonemealEvent;
import net.minecraftforge.eventbus.api.Event;
import net.minecraftforge.fml.common.Mod;

/** Season-aware bonemeal and Growth Detector reports for Ecliptic Seasons. */
@Mod("jade_season_compat")
public final class Compat {
    public static final float OUT_OF_SEASON_BONEMEAL = 0.25F;
    // Ecliptic's own "liked season" threshold (CropGrowthHandler.getLikeSeasonsInTemperate).
    static final float IN_SEASON_THRESHOLD = 0.4F;

    /** Seasonal state of one plant at one position; {@code null} from {@link #season} means no Ecliptic rule. */
    public record SeasonState(boolean inSeason, boolean greenhouse, List<Season> liked) { }

    public static SeasonState season(Level level, BlockPos pos, BlockState state) {
        if (!EclipticSeasonsApi.getInstance().isSeasonEnabled(level) || !CommonConfig.Crop.enableCrop.get()) return null;
        Map<Holder<AgroClimaticZone>, CropGrowControl> controls = CropGrowthHandler.getControlMap(state.m_60734_());
        if (controls == null) return null;
        Holder<Biome> biome = CropGrowthHandler.getCropBiome(level, pos);
        Holder<AgroClimaticZone> climate = CropGrowthHandler.getclimateTypeHolder(biome);
        if (climate == null) return null;
        Holder<AgroClimaticZone> fallback = CropGrowthHandler.getDefaultAgroClimaticZoneHolder(level);
        CropGrowControl control = CropGrowthHandler.getCropGrowControl(controls, climate);
        CropGrowControl fallbackControl = CropGrowthHandler.getCropGrowControl(controls, fallback);
        if (control == null && fallbackControl == null) return null;
        SolarTerm term = EclipticSeasonsApi.getInstance().getSolarTerm(level);
        // Same parameter Ecliptic uses for this biome's climate zone and the current solar term.
        GrowParameter parameter = CropGrowthHandler.getSeasonGrowParameter(state, control, fallbackControl, term, climate);
        List<Season> liked = CropGrowthHandler.getLikeSeasonsInTemperate(state, controls, fallback);
        boolean greenhouse = CropGrowthHandler.getGreenHouseProvider(level, pos, state, controls, fallback) != null
            && CropGrowthHandler.isInRoom(level, pos, state, (control != null ? control : fallbackControl).notGreenHouse());
        return new SeasonState(inSeason(parameter == null ? null : parameter.grow_chance(), greenhouse), greenhouse, liked);
    }

    /** A crop is in season when this solar term's chance clears Ecliptic's liked threshold, or a season core covers it. */
    public static boolean inSeason(Float seasonGrowChance, boolean greenhouse) {
        return seasonGrowChance == null || seasonGrowChance > IN_SEASON_THRESHOLD || greenhouse;
    }

    /** Probability that the season gate lets bonemeal through; {@code 1} when the plant has no seasonal rule. */
    public static float bonemealGate(SeasonState season) {
        return season == null || season.inSeason() ? 1.0F : OUT_OF_SEASON_BONEMEAL;
    }

    /** The block's own vanilla isBonemealSuccess odds, which apply after the season gate. */
    public static float nativeBonemealChance(Block block) {
        if (block instanceof SaplingBlock) return 0.45F;
        if (block instanceof MushroomBlock || block instanceof FungusBlock) return 0.4F;
        return 1.0F;
    }

    // Replaces Ecliptic's BonemealEvent handler: in season bonemeal behaves normally, out of season it passes 25%.
    public static boolean bonemeal(BonemealEvent event) {
        Level level = event.getLevel();
        if (level.m_5776_() || !CommonConfig.Crop.restrictBoneMeal.get()) return false;
        if (event.getEntity() != null && event.getEntity().m_7500_()) return false;
        if (event.getResult() != Event.Result.DEFAULT) return false;
        BlockState state = event.getBlock();
        BlockPos pos = event.getPos();
        if (!(state.m_60734_() instanceof BonemealableBlock block) || !block.m_7370_(level, pos, state, false)) return false;
        SeasonState season = season(level, pos, state);
        if (season == null) return false;
        if (level.m_213780_().m_188501_() < bonemealGate(season)) {
            // Ecliptic would otherwise re-roll the season for the growth this bonemeal triggers (e.g. sapling -> tree).
            SolarDataManager data = SolarHolders.getSaveData(level);
            if (data != null) data.addSkipNextCheck(pos, state);
            return true;
        }
        if (CommonConfig.Crop.boneMealConsumeOnFailure.get()) event.setResult(Event.Result.ALLOW);
        else event.setCanceled(true);
        if (event.getEntity() instanceof ServerPlayer player && !(player instanceof FakePlayer))
            player.m_5661_(Component.m_237113_("Out of season: bonemeal failed ("
                + percent(OUT_OF_SEASON_BONEMEAL) + " chance)").m_130940_(ChatFormatting.GOLD), true);
        return true;
    }

    static boolean isSapling(Block block) {
        return block instanceof SaplingBlock || name(block).contains("sapling") || name(block).contains("propagule");
    }

    static String name(Block block) {
        return block.getClass().getName().toLowerCase(Locale.ROOT) + " " + block.m_7705_().toLowerCase(Locale.ROOT);
    }

    public static boolean isPlantable(Block block) {
        return block instanceof IPlantable || block instanceof BonemealableBlock || isSapling(block)
            || CropGrowthHandler.getControlMap(block) != null;
    }

    // Growth Detector right-click on any plantable: server-built chat report. Returns null to run the original item.
    public static InteractionResult detect(UseOnContext context) {
        Level level = context.m_43725_();
        Player player = context.m_43723_();
        if (level.m_5776_() || player == null) return null;
        BlockPos pos = context.m_8083_();
        BlockState state = level.m_8055_(pos);
        if (state.m_60795_() || !isPlantable(state.m_60734_())) return null;
        MutableComponent message = Component.m_237113_("Growth Detector: ").m_130940_(ChatFormatting.GREEN)
            .m_7220_(state.m_60734_().m_49954_().m_6881_().m_130940_(ChatFormatting.WHITE));
        for (Component line : report(level, pos, state)) message.m_130946_("\n").m_7220_(line);
        player.m_213846_(message);
        return InteractionResult.CONSUME;
    }

    static MutableComponent line(String label, String value, ChatFormatting color) {
        return Component.m_237113_(label + ": ").m_130940_(ChatFormatting.GRAY)
            .m_7220_(Component.m_237113_(value).m_130940_(color));
    }

    static String percent(float chance) {
        return Math.round(chance * 100) + "%";
    }

    static String seasons(List<Season> seasons) {
        List<String> names = new ArrayList<>();
        for (Season season : seasons) names.add(title(season.getName()));
        return String.join(", ", names);
    }

    static String title(String raw) {
        String text = raw.replace('_', ' ').toLowerCase(Locale.ROOT);
        return text.isEmpty() ? text : Character.toUpperCase(text.charAt(0)) + text.substring(1);
    }

    public static List<Component> report(Level level, BlockPos pos, BlockState state) {
        List<Component> lines = new ArrayList<>();
        Block block = state.m_60734_();
        boolean sapling = isSapling(block);
        boolean enabled = EclipticSeasonsApi.getInstance().isSeasonEnabled(level);
        SeasonState season = season(level, pos, state);

        lines.add(line("Type", sapling ? "Sapling (grows into a tree)"
            : block instanceof CropBlock ? "Crop" : "Plant", ChatFormatting.WHITE));
        if (enabled) {
            Season now = EclipticSeasonsApi.getInstance().getSeasonSignal(level, pos);
            SolarTerm term = EclipticSeasonsApi.getInstance().getSolarTerm(level);
            lines.add(line("Season", title(now.getName()) + " (" + title(term.name()) + ")", ChatFormatting.WHITE));
        }
        if (season == null) {
            lines.add(line("In season", "Yes - no seasonal rule, grows all year", ChatFormatting.GREEN));
        } else {
            String liked = season.liked().isEmpty() ? "" : " - grows in " + seasons(season.liked());
            lines.add(line("In season", (season.inSeason()
                ? (season.greenhouse() ? "Yes (greenhouse)" : "Yes") : "No") + liked,
                season.inSeason() ? ChatFormatting.GREEN : ChatFormatting.RED));
        }

        float growth = 0.0F;
        for (int i = 0; i < 100; i++) growth += GrowthDetectorItem.getGrowChance(level, pos, state);
        growth /= 100.0F;
        int light = level.m_45524_(pos, 0);
        boolean dark = (sapling || block instanceof CropBlock) && light < 9;
        lines.add(line("Growth chance", percent(growth) + " of normal speed"
            + (dark ? " (too dark: light " + light + ", needs 9+)" : ""),
            growth <= 0.0F || dark ? ChatFormatting.RED : growth < 0.5F ? ChatFormatting.GOLD : ChatFormatting.GREEN));

        if (block instanceof BonemealableBlock bonemealable && bonemealable.m_7370_(level, pos, state, false)) {
            float gate = CommonConfig.Crop.restrictBoneMeal.get() ? bonemealGate(season) : 1.0F;
            float chance = gate * nativeBonemealChance(block);
            String detail = gate < 1.0F ? " (out of season " + percent(gate) + " gate"
                + (nativeBonemealChance(block) < 1.0F ? " x " + percent(nativeBonemealChance(block)) + " plant chance" : "") + ")"
                : nativeBonemealChance(block) < 1.0F ? " (plant's own chance per use)" : "";
            lines.add(line("Bonemeal success", percent(chance) + detail,
                chance >= 1.0F ? ChatFormatting.GREEN : chance >= 0.4F ? ChatFormatting.GOLD : ChatFormatting.RED));
        } else {
            lines.add(line("Bonemeal success", "No effect (fully grown or not bonemealable)", ChatFormatting.GRAY));
        }

        if (sapling) {
            boolean grows = growth > 0.0F && !dark;
            lines.add(line("Sapling growth", grows ? "Can grow into a tree now (needs clear space above)"
                : "Cannot grow into a tree right now", grows ? ChatFormatting.GREEN : ChatFormatting.RED));
            for (String hint : saplingHints(String.valueOf(state))) lines.add(Component.m_237113_(" - " + hint).m_130940_(ChatFormatting.GRAY));
        } else {
            lines.add(line("Sapling growth", "Not a sapling - regular crop/plant growth only", ChatFormatting.GRAY));
        }

        if (enabled && level instanceof ServerLevel server) {
            Humidity humidity = EclipticSeasonsApi.getInstance().getAdjustedHumidity(server, pos);
            String value = title(humidity.getName()) + (humidity == Humidity.HUMID ? " (humid)" : " (not humid)");
            Map<Holder<AgroClimaticZone>, CropGrowControl> controls = CropGrowthHandler.getControlMap(block);
            if (controls != null) {
                List<Humidity> liked = CropGrowthHandler.getLikeHumidityInTemperate(state, controls,
                    CropGrowthHandler.getDefaultAgroClimaticZoneHolder(level));
                if (!liked.isEmpty()) {
                    List<String> names = new ArrayList<>();
                    for (Humidity h : liked) names.add(title(h.getName()));
                    value += " - prefers " + String.join(", ", names);
                }
            }
            if (!CommonConfig.Crop.enableCropHumidityControl.get()) value += "; does not affect growth on this server";
            lines.add(line("Humidity", value, humidity == Humidity.HUMID ? ChatFormatting.AQUA : ChatFormatting.WHITE));
        }
        return lines;
    }

    public static List<String> saplingHints(String state) {
        if (state.contains("minecraft:dark_oak_sapling")) return List.of(
            "Requires 2x2 dark oak saplings (same species, same Y)",
            "Clear overhead and side space for a variable-height trunk and wide canopy",
            "First growth/bonemeal advances stage 0 -> 1; a later attempt grows the tree",
            "Light >=9 for natural growth; bonemeal cannot bypass space/2x2 checks");
        if (state.contains("minecraft:spruce_sapling") || state.contains("minecraft:jungle_sapling")) return List.of(
            "1x1 normal tree; 2x2 same-species saplings for a mega tree",
            "Mega trees need large clear volume; no fixed height guarantees growth",
            "First growth/bonemeal advances stage 0 -> 1; other saplings need not be stage 1",
            "Light >=9 for natural growth; bonemeal cannot bypass space checks");
        if (state.contains("dynamictrees:")) return List.of(
            "Dynamic Trees uses its own species/soil/space growth; vanilla 2x2 rules do not apply");
        if (state.contains("sapling")) return List.of(
            "Growth rules are species-specific; do not assume modded saplings accept 2x2",
            "Check soil, light, overhead/side clearance, and season");
        return List.of();
    }
}
