import dev.latvian.mods.rhino.Context;
import dev.latvian.mods.rhino.NativeJavaClass;
import dev.latvian.mods.rhino.ScriptableObject;
import dev.latvian.mods.rhino.util.RemapForJS;
import dev.latvian.mods.rhino.util.RemapPrefixForJS;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

public class HydrationHooksRhinoTest {
    public static class Bowl {}
    public static class PotionItem {}

    public static final class Tag {
        public final Map<String, Object> values = new HashMap<>();
        public Tag copy() { Tag tag = new Tag(); tag.values.putAll(values); return tag; }
        public void merge(Tag other) { values.putAll(other.values); }
        public void putInt(String key, int value) { values.put(key, value); }
        public Object get(String key) { return values.get(key); }
    }

    // Same shape as KubeJS's ItemStackKJS: kjs$hasTag(item tag) claims `hasTag`, and
    // vanilla ItemStack.hasTag() is only reachable as m_41782_ on the server.
    @RemapPrefixForJS("kjs$")
    public interface ItemStackKJS {
        default boolean kjs$hasTag(String itemTag) { return false; }
    }

    public static final class Stack implements ItemStackKJS {
        public final String id;
        public final boolean drink;
        private final Object item;
        private Tag tag;
        Stack(String id, boolean drink, Object item) { this.id = id; this.drink = drink; this.item = item; }
        public boolean isEmpty() { return id.equals("minecraft:air"); }
        public String getUseAnimation() { return "NONE"; }
        public Object getItem() { return item; }
        // KubeJS's ItemStackMixin renames these SRG methods, so getTag/setTag/hasTag never exist in JS.
        @RemapForJS("hasNBT") public boolean m_41782_() { return tag != null; }
        @RemapForJS("getNbt") public Tag m_41783_() { return tag; }
        @RemapForJS("setNbt") public void m_41751_(Tag tag) { this.tag = tag; }
        public Tag getOrCreateTag() { if (tag == null) tag = new Tag(); return tag; }
        public Stack copy() { Stack copy = new Stack(id, drink, item); if (tag != null) copy.tag = tag.copy(); return copy; }
    }

    public static final class State {
        private final Object block;
        State(Object block) { this.block = block; }
        public Object getBlock() { return block; }
    }

    public static final class Level {
        private final Object block;
        Level(Object block) { this.block = block; }
        public State getBlockState(Object pos) { return new State(block); }
    }

    // Same shape as KubeJS's EntityKJS. On the crashing client the vanilla
    // Entity.level() method stayed under its SRG name, so the kjs$getLevel bean
    // property claimed `level` and `player.level()` threw "not a function".
    @RemapPrefixForJS("kjs$")
    public interface EntityKJS {
        Object self();
        default Object kjs$getLevel() { return ((Player) self()).level; }
    }

    public static final class Player implements EntityKJS {
        final Level level;
        Player(Level level) { this.level = level; }
        public Object self() { return this; }
        public Object m_9236_() { return level; }
    }

    public static final class RightClickItem {
        private final Stack stack;
        private final Player player;
        public boolean canceled;
        RightClickItem(Stack stack, Player player) { this.stack = stack; this.player = player; }
        public Stack getItemStack() { return stack; }
        public Player getEntity() { return player; }
        public Level getLevel() { return player.level; }
        public void setCanceled(boolean value) { canceled = value; }
    }

    public static final class Brew {
        private final Stack[] slots;
        Brew(Stack[] slots) { this.slots = slots; }
        public Stack getItem(int slot) { return slots[slot]; }
    }

    public static final class Crafted {
        private final Stack stack;
        Crafted(Stack stack) { this.stack = stack; }
        public Stack getCrafting() { return stack; }
    }

    public static final class Factory {
        public final Object bowl = new Bowl();
        public final Object potion = new PotionItem();
        public Stack stack(String id, boolean drink, Object item) { return new Stack(id, drink, item); }
        public Player player(Object block) { return new Player(new Level(block)); }
        public RightClickItem click(Stack stack, Player player) { return new RightClickItem(stack, player); }
        public Brew brew(Stack a, Stack b, Stack c) { return new Brew(new Stack[]{a, b, c}); }
        public Crafted crafted(Stack stack) { return new Crafted(stack); }
    }

    public static void main(String[] args) throws Exception {
        Context context = Context.enter();
        ScriptableObject scope = context.initStandardObjects();
        ScriptableObject.putProperty(scope, "make", Context.javaToJS(context, new Factory(), scope), context);
        ScriptableObject.putProperty(scope, "BowlClass", new NativeJavaClass(context, scope, Bowl.class), context);
        ScriptableObject.putProperty(scope, "PotionClass", new NativeJavaClass(context, scope, PotionItem.class), context);
        context.evaluateString(scope, """
            var listeners = {};
            var classes = {
              'dev.ghen.thirst.api.ThirstHelper': {isDrink: function(stack) { return stack.drink; }},
              'net.minecraft.world.item.UseAnim': {DRINK: 'DRINK'},
              'net.minecraftforge.common.MinecraftForge': {EVENT_BUS: {
                addListener: function(priority, cancelled, type, fn) { listeners[type] = fn; }
              }},
              'net.minecraftforge.eventbus.api.EventPriority': {HIGHEST: 'HIGHEST', LOWEST: 'LOWEST'},
              'dev.ghen.thirst.foundation.util.MathHelper': {
                getPlayerPOVHitResult: function(level, player, mode) {
                  return {getBlockPos: function() { return 'pos'; }};
                }
              },
              'net.minecraft.world.level.ClipContext$Fluid': {ANY: 'ANY'},
              'doggytalents.common.block.FoodBowlBlock': BowlClass,
              'net.minecraft.world.item.PotionItem': PotionClass
            };
            var Java = {loadClass: function(name) {
              return name.indexOf('net.minecraftforge.event.') === 0 ? name : classes[name];
            }};
            var ForgeEvents = {onEvent: function(name, fn) { listeners[name] = fn; }};
            """, "hydration-fixture-setup", 1, null);
        context.evaluateString(scope, Files.readString(Path.of(args[0])), args[0], 1, null);
        context.evaluateString(scope, """
            var shadowed = make.player(make.bowl);
            if (typeof shadowed.level === 'function') throw Error('Fixture did not reproduce KubeJS level shadowing');
            var reproduced = false;
            try { shadowed.level(); } catch (e) { reproduced = String(e).indexOf('not a function') !== -1; }
            if (!reproduced) throw Error('Fixture did not reproduce the client crash');
            var probe = make.stack('minecraft:potion', false, make.potion);
            if (typeof probe.getTag === 'function' || typeof probe.setTag === 'function')
              throw Error('Fixture exposes getTag/setTag, which KubeJS remaps to getNbt/setNbt');

            var click = 'net.minecraftforge.event.entity.player.PlayerInteractEvent$RightClickItem';
            var cases = [[make.bowl, 'minecraft:glass_bottle', true], [{}, 'minecraft:glass_bottle', false],
                         [make.bowl, 'minecraft:water_bucket', false]];
            cases.forEach(function(c) {
              var event = make.click(make.stack(c[1], false, null), make.player(c[0]));
              listeners[click](event);
              if (event.canceled !== c[2]) throw Error('Unexpected bowl result for ' + c[1]);
            });

            var drink = make.stack('farmersrespite:green_tea', true, null);
            listeners['net.minecraftforge.event.entity.player.PlayerEvent$ItemCraftedEvent'](make.crafted(drink));
            if (drink.getNbt().get('Purity') != 3) throw Error('Crafted drink not purified');

            var named = make.stack('minecraft:potion', false, make.potion);
            named.getOrCreateTag().putInt('CustomData', 7);
            var air = make.stack('minecraft:air', false, null);
            var pre = make.brew(named, air, make.stack('minecraft:potion', false, make.potion));
            listeners['net.minecraftforge.event.brewing.PotionBrewEvent$Pre'](pre);
            var brewed = make.stack('minecraft:potion', false, make.potion);
            var post = make.brew(brewed, air, make.stack('minecraft:potion', false, make.potion));
            listeners['net.minecraftforge.event.brewing.PotionBrewEvent$Post'](post);
            if (brewed.getNbt().get('Purity') != 3 || brewed.getNbt().get('CustomData') != 7 ||
                post.getItem(2).getNbt().get('Purity') != 3 || air.getNbt() !== null) {
              throw Error('Brewing purity or tag preservation failed');
            }
            """, "hydration-fixture-assertions", 1, null);
        System.out.println("Rhino hydration hooks passed");
    }
}
