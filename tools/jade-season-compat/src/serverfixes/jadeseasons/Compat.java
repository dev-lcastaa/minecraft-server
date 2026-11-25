package serverfixes.jadeseasons;

import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.ArrayDeque;
import java.util.List;
import java.util.function.Consumer;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.fml.common.Mod;
import snownee.jade.api.*;
import snownee.jade.api.config.IPluginConfig;

@Mod("jade_season_compat")
@WailaPlugin("jade_season_compat")
public final class Compat implements IWailaPlugin {
    static final ResourceLocation UID = new ResourceLocation("jade_season_compat", "details");
    static final String KEY = "jade_season_compat";
    static final String API = "com.teamtea.eclipticseasons.api.EclipticSeasonsApi";
    static final String RESOLVER = "com.teamtea.eclipticseasons.common.item.info.GrowthInfoResolver";

    public static Object call(Object target, String name, Object... args) {
        Class<?> type = target instanceof Class<?> c ? c : target.getClass();
        for (Method method : type.getMethods()) {
            if (!method.getName().equals(name) || method.getParameterCount() != args.length) continue;
            Class<?>[] parameters = method.getParameterTypes();
            boolean matches = true;
            for (int i = 0; i < args.length; i++) {
                if (args[i] != null && !parameters[i].isInstance(args[i]) && !parameters[i].isPrimitive()) matches = false;
            }
            if (!matches) continue;
            try {
                return accessible(method).invoke(target instanceof Class<?> ? null : target, args);
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException(type.getName() + "." + name, e);
            }
        }
        throw new IllegalStateException("Missing API: " + type.getName() + "." + name);
    }

    // Public methods on non-public implementations (e.g. Ecliptic's anonymous EclipticUtil$1)
    // can only be invoked through the public supertype that declares them.
    static Method accessible(Method method) {
        if (Modifier.isPublic(method.getDeclaringClass().getModifiers())) return method;
        ArrayDeque<Class<?>> pending = new ArrayDeque<>(List.of(method.getDeclaringClass()));
        while (!pending.isEmpty()) {
            Class<?> candidate = pending.poll();
            if (Modifier.isPublic(candidate.getModifiers())) {
                try { return candidate.getMethod(method.getName(), method.getParameterTypes()); }
                catch (NoSuchMethodException ignored) { }
            }
            if (candidate.getSuperclass() != null) pending.add(candidate.getSuperclass());
            pending.addAll(List.of(candidate.getInterfaces()));
        }
        return method;
    }

    static Class<?> type(String name) {
        try { return Class.forName(name); }
        catch (ClassNotFoundException e) { throw new IllegalStateException("Required Ecliptic Seasons API missing", e); }
    }

    static Object field(String owner, String name) {
        try { return type(owner).getField(name).get(null); }
        catch (ReflectiveOperationException e) { throw new IllegalStateException(owner + "." + name, e); }
    }

    static Object api() { return call(type(API), "getInstance"); }
    static boolean enabled(Object level) { return (Boolean) call(api(), "isSeasonEnabled", level); }
    static Object growth(Object level, Object pos, Object state) {
        return call(type(RESOLVER), "resolve", level, pos, state);
    }
    static boolean cropBonemeal(Object block) {
        return type("net.minecraft.world.level.block.BonemealableBlock").isInstance(block)
            && !type("net.minecraft.world.level.block.SaplingBlock").isInstance(block)
            && !block.getClass().getSimpleName().toLowerCase(java.util.Locale.ROOT).contains("sapling");
    }

    public static boolean request(BlockAccessor accessor) {
        return enabled(accessor.getLevel());
    }

    // Jade 11 only requests/sends block-entity NBT; crops need the same validated packet path.
    public static boolean sync(BlockAccessor accessor, Consumer<CompoundTag> sender) {
        if (!enabled(accessor.getLevel())) return false;
        CompoundTag tag = accessor.getServerData();
        String info = season(accessor.getLevel());
        Object report = growth(accessor.getLevel(), accessor.getPosition(), accessor.getBlockState());
        if (report != null) {
            info += "\nLocal growth: " + Math.round(((Number) call(report, "growChance")).floatValue()) + "%";
            info += (Boolean) call(report, "needsSeasonCore")
                ? (cropBonemeal(accessor.getBlock())
                    ? "\nOut of season: crop bonemeal 25% chance (consumed)"
                    : "\nOut of season: native plant growth restrictions")
                : "\nSeason/greenhouse conditions satisfied";
            if ((Boolean) call(report, "humidityMismatch")) info += "\nHumidity mismatch";
            info += "\nGreenhouse level: " + call(report, "greenhouseLevel");
        } else {
            info += "\nNo Ecliptic seasonal growth rule configured";
        }
        tag.m_128359_(KEY, info);
        StringBuilder preferences = new StringBuilder();
        for (Object component : (List<?>) call(type("com.teamtea.eclipticseasons.common.core.crop.CropGrowthHandler"),
                "appendInfo", accessor.getLevel(), accessor.getBlockState())) {
            if (preferences.length() > 0) preferences.append('\n');
            preferences.append(call(type("net.minecraft.network.chat.Component$Serializer"), "m_130703_", component));
        }
        tag.m_128359_(KEY + "_preferences", preferences.toString());
        if (accessor.getBlockEntity() != null &&
            !((List<?>) call(field("snownee.jade.impl.WailaCommonRegistration", "INSTANCE"),
                "getBlockNBTProviders", accessor.getBlockEntity())).isEmpty()) return false;
        Object pos = accessor.getPosition();
        tag.m_128405_("x", ((Number) call(pos, "m_123341_")).intValue());
        tag.m_128405_("y", ((Number) call(pos, "m_123342_")).intValue());
        tag.m_128405_("z", ((Number) call(pos, "m_123343_")).intValue());
        sender.accept(tag);
        return true;
    }

    static String season(Object level) {
        return "Season: " + call(api(), "getSeason", level) + " | Solar term: " + call(api(), "getSolarTerm", level);
    }

    public static boolean bonemeal(Object event) {
        Object level = call(event, "getLevel");
        if (!enabled(level) || (Boolean) call(level, "m_5776_")) return false;
        Object state = call(event, "getBlock");
        Object pos = call(event, "getPos");
        Object report = growth(level, pos, state);
        if (report == null || !(Boolean) call(report, "needsSeasonCore")) return false;
        Object block = call(state, "m_60734_");
        if (!cropBonemeal(block)) return false;
        if (!(Boolean) call(block, "m_7370_", level, pos, state, false)) return false;
        Object result = call(event, "getResult");
        if (!result.toString().equals("DEFAULT")) return false;
        Object random = call(level, "m_213780_");
        boolean success = ((Number) call(random, "m_188503_", 4)).intValue() == 0;
        if (!success) {
            Object allow = java.lang.Enum.valueOf(result.getClass().asSubclass(Enum.class), "ALLOW");
            // Forge ALLOW consumes one bonemeal but skips performBonemeal. DEFAULT continues vanilla growth.
            call(event, "setResult", allow);
        }
        return true;
    }

    @Override public void register(IWailaCommonRegistration registration) {
        registration.registerEntityDataProvider(new EntityDetails(), net.minecraft.world.entity.Entity.class);
    }
    @Override public void registerClient(IWailaClientRegistration registration) {
        registration.registerBlockComponent(new BlockDetails(), net.minecraft.world.level.block.Block.class);
        registration.registerEntityComponent(new EntityDetails(), net.minecraft.world.entity.Entity.class);
    }

    static void lines(ITooltip tooltip, CompoundTag tag) {
        String text = tag.m_128461_(KEY);
        if (!text.isEmpty()) for (String line : text.split("\n")) tooltip.add(Component.m_237113_(line));
    }

    static final class BlockDetails implements IBlockComponentProvider {
        @Override public ResourceLocation getUid() { return UID; }
        @Override public void appendTooltip(ITooltip tooltip, BlockAccessor accessor, IPluginConfig config) {
            lines(tooltip, accessor.getServerData());
            if (!accessor.showDetails()) return;
            for (String json : accessor.getServerData().m_128461_(KEY + "_preferences").split("\n"))
                if (!json.isEmpty()) tooltip.add((Component) call(type("net.minecraft.network.chat.Component$Serializer"), "m_130691_", json));
            tooltip.add(Component.m_237113_(accessor.getBlockState().toString()));
            String state = accessor.getBlockState().toString();
            for (String hint : saplingHints(state)) tooltip.add(Component.m_237113_(hint));
        }
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
            "Check soil, light, overhead/side clearance, and season/humidity");
        return List.of();
    }

    static final class EntityDetails implements IEntityComponentProvider, IServerDataProvider<EntityAccessor> {
        @Override public ResourceLocation getUid() { return UID; }
        @Override public void appendServerData(CompoundTag tag, EntityAccessor accessor) {
            if (enabled(accessor.getLevel())) tag.m_128359_(KEY, season(accessor.getLevel()));
            Object entity = accessor.getEntity();
            String details = call(entity, "m_6095_").toString();
            if (type("net.minecraft.world.entity.LivingEntity").isInstance(entity)) {
                details += "\nHealth: " + call(entity, "m_21223_") + "/" + call(entity, "m_21233_");
                details += "\nArmor: " + call(entity, "m_21230_");
            }
            if (type("net.minecraft.world.entity.AgeableMob").isInstance(entity)) {
                int age = ((Number) call(entity, "m_146764_")).intValue();
                details += age < 0 ? "\nGrows up in: " + (-age / 20) + "s"
                    : age > 0 ? "\nBreeding cooldown: " + (age / 20) + "s" : "\nAdult; age cooldown ready";
            }
            if (type("net.minecraft.world.entity.TamableAnimal").isInstance(entity))
                details += (Boolean) call(entity, "m_21824_") ? "\nTamed" : "\nUntamed";
            tag.m_128359_(KEY + "_entity", details);
        }
        @Override public void appendTooltip(ITooltip tooltip, EntityAccessor accessor, IPluginConfig config) {
            lines(tooltip, accessor.getServerData());
            if (accessor.showDetails()) for (String line : accessor.getServerData().m_128461_(KEY + "_entity").split("\n"))
                if (!line.isEmpty()) tooltip.add(Component.m_237113_(line));
        }
    }
}
