import serverfixes.jadeseasons.Compat;

class BehaviorTest {
    public enum Result { DEFAULT, ALLOW, DENY }
    public static class Event {
        public Result result = Result.DEFAULT;
        public final net.minecraft.world.level.Level level = new net.minecraft.world.level.Level();
        public final net.minecraft.world.level.block.state.BlockState state = new net.minecraft.world.level.block.state.BlockState();
        public Object getLevel() { return level; }
        public Object getBlock() { return state; }
        public Object getPos() { return new net.minecraft.core.BlockPos(); }
        public Result getResult() { return result; }
        public void setResult(Result result) { this.result = result; }
    }
    public static void main(String[] args) {
        int allowed = 0, failures = 0, grown = 0, consumed = 0;
        for (int roll = 0; roll < 4; roll++) {
            Event event = new Event();
            event.level.random.roll = roll;
            if (!Compat.bonemeal(event)) throw new AssertionError("Out-of-season crop not handled");
            if (event.result == Result.DEFAULT) allowed++;
            if (event.result == Result.ALLOW) failures++;
            // Model Forge's post-event dispatch: DEFAULT runs a fertile crop's native growth;
            // ALLOW consumes the item without invoking that growth routine.
            if (event.result == Result.DEFAULT) {
                event.state.block.fertileGrowth();
                grown += event.state.block.age;
            }
            if (event.result == Result.DEFAULT || event.result == Result.ALLOW) consumed++;
        }
        if (allowed != 1 || failures != 3) throw new AssertionError("Expected exact 25% success /75% consume-only");
        if (grown != 1 || consumed != 4)
            throw new AssertionError("Fertile out-of-season crop must actually grow on its successful roll; all four attempts consume");
        Event suitable = new Event();
        net.minecraft.world.level.Level.seasonMismatch = false;
        if (Compat.bonemeal(suitable)) throw new AssertionError("Suitable/greenhouse crop must preserve native handler");
        net.minecraft.world.level.Level.seasonMismatch = true;
        Event denied = new Event(); denied.result = Result.DENY;
        if (Compat.bonemeal(denied)) throw new AssertionError("Other mod's denial must not be overridden");
        Event invalid = new Event(); invalid.state.block.valid = false;
        if (Compat.bonemeal(invalid)) throw new AssertionError("Mature/invalid crop must not consume bonemeal");
        net.minecraft.world.level.Level.controlled = false;
        if (Compat.bonemeal(new Event())) throw new AssertionError("Unconfigured plant must preserve native behavior");
        net.minecraft.world.level.Level.controlled = true;
        Event client = new Event(); client.level.client = true;
        if (Compat.bonemeal(client)) throw new AssertionError("Client must not roll");
        net.minecraft.nbt.CompoundTag tag = new net.minecraft.nbt.CompoundTag();
        Event hover = new Event();
        snownee.jade.api.BlockAccessor accessor = (snownee.jade.api.BlockAccessor) java.lang.reflect.Proxy.newProxyInstance(
            BehaviorTest.class.getClassLoader(), new Class<?>[]{snownee.jade.api.BlockAccessor.class},
            (proxy, method, values) -> switch (method.getName()) {
                case "getLevel" -> hover.level;
                case "getBlockState" -> hover.state;
                case "getBlock" -> hover.state.block;
                case "getPosition" -> new net.minecraft.core.BlockPos();
                case "getServerData" -> tag;
                case "getBlockEntity" -> null;
                default -> null;
            });
        final int[] sent = {0};
        if (!Compat.request(accessor)) throw new AssertionError("Crop without block entity never requested");
        if (!Compat.sync(accessor, data -> sent[0]++)) throw new AssertionError("No-block-entity sync not handled");
        if (sent[0] != 1 || !tag.m_128461_("jade_season_compat").contains("25%"))
            throw new AssertionError("Missing synced season/bonemeal tooltip");
        if (!tag.m_128461_("jade_season_compat_preferences").contains("SUMMER"))
            throw new AssertionError("Native crop preference component was not synced");
        if (tag.m_128451_("x") != 11 || tag.m_128451_("y") != 64 || tag.m_128451_("z") != -7)
            throw new AssertionError("Jade packet position keys missing");
        net.minecraft.world.level.Level.controlled = false;
        Compat.sync(accessor, data -> {});
        if (!tag.m_128461_("jade_season_compat").contains("No Ecliptic seasonal growth rule configured"))
            throw new AssertionError("Unconfigured plant displayed invented seasons");
        net.minecraft.world.level.Level.controlled = true;
        net.minecraft.world.entity.Entity entity = new net.minecraft.world.entity.TamableAnimal();
        snownee.jade.api.EntityAccessor entityAccessor = (snownee.jade.api.EntityAccessor) java.lang.reflect.Proxy.newProxyInstance(
            BehaviorTest.class.getClassLoader(), new Class<?>[]{snownee.jade.api.EntityAccessor.class},
            (proxy, method, values) -> switch (method.getName()) {
                case "getLevel" -> hover.level;
                case "getEntity" -> entity;
                default -> null;
            });
        try {
            var constructor = Class.forName("serverfixes.jadeseasons.Compat$EntityDetails").getDeclaredConstructor();
            constructor.setAccessible(true);
            @SuppressWarnings("unchecked")
            var provider = (snownee.jade.api.IServerDataProvider<snownee.jade.api.EntityAccessor>) constructor.newInstance();
            provider.appendServerData(tag, entityAccessor);
        } catch (ReflectiveOperationException e) { throw new AssertionError(e); }
        String details = tag.m_128461_("jade_season_compat_entity");
        if (!details.contains("Health: 8.0/20.0") || !details.contains("Armor: 3")
            || !details.contains("Grows up in: 2s") || !details.contains("Tamed"))
            throw new AssertionError("Advanced entity details missing: " + details);
        if (Compat.saplingHints("Block{minecraft:dark_oak_sapling}").stream().noneMatch(s -> s.contains("Requires 2x2")))
            throw new AssertionError("Dark oak requirement missing");
        if (Compat.saplingHints("Block{minecraft:jungle_sapling}").stream().noneMatch(s -> s.contains("1x1 normal")))
            throw new AssertionError("Jungle optional mega requirement missing");
        if (Compat.saplingHints("Block{dynamictrees:oak_sapling}").stream().noneMatch(s -> s.contains("do not apply")))
            throw new AssertionError("Dynamic tree warning missing");
        if (Compat.saplingHints("Block{other:maple_sapling}").stream().noneMatch(s -> s.contains("do not assume")))
            throw new AssertionError("Modded sapling rules invented");
        System.out.println("Verified four RNG outcomes, greenhouse/unconfigured/mature/client/denial preservation, server sync, sapling hints");
    }
}
