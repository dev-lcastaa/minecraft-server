import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.jar.JarFile;
import javax.tools.ToolProvider;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory;

class BytecodeTest {
    static Path root, work;
    static final String BI = "dev/fallingcloud/betterinventory/";
    static final String BD = "net/mcreator/butchersdelight/procedures/";
    static final String EVENT = "net/minecraftforge/event/level/BlockEvent$BreakEvent";
    static final List<String> PROCEDURES = List.of("HookedchickenBlock", "HookedcowBlock",
        "Hookedgoatblock", "HookedhoglinBlock", "Hookedllamablock", "HookedpigBlock",
        "HookedsheepBlock", "RackcowBlock", "RackgoatBlock", "RackhoglinBlock", "RacksheepBlock");

    public static void main(String[] args) throws Exception {
        root = Path.of(args[0]);
        work = root.resolve("tools/inventory-carcass-compat/.bytecode-test-" + UUID.randomUUID());
        Files.createDirectory(work);
        try {
            prepareInventory();
            prepareStubs();
            var sources = new ArrayList<String>(List.of("-source", "17", "-target", "17",
                "-classpath", work + System.getProperty("path.separator") +
                    root.resolve("mods/betterinventory-forge-1.20.1-2.1.0.jar"),
                "-d", work.toString()));
            try (var files = Files.walk(work)) {
                files.filter(p -> p.toString().endsWith(".java")).forEach(p -> sources.add(p.toString()));
            }
            if (ToolProvider.getSystemJavaCompiler().run(null, null, null,
                    sources.toArray(String[]::new)) != 0) throw new AssertionError("Fixture compilation failed");
            prepareClear();
            try (var loader = new URLClassLoader(new java.net.URL[]{work.toUri().toURL()},
                    BytecodeTest.class.getClassLoader())) {
                Thread.currentThread().setContextClassLoader(loader);
                var engine = new NashornScriptEngineFactory().getScriptEngine(
                    new String[]{"--language=es6"}, loader);
                engine.eval(Files.readString(root.resolve(
                    "tools/inventory-carcass-compat/coremods/inventory_carcass.js")));
                engine.eval("var patches = initializeCoreMod()");
                var slot = read("betterinventory-forge-1.20.1-2.1.0.jar",
                    BI + "inv/handler/SlotItemHandler");
                keep(slot, "<init>", "<clinit>", "getItemHandler", "m_7993_", "m_5852_", "m_6201_");
                save(copyRenamed(slot, "test/OriginalSlot"));
                engine.put("clazz", slot);
                engine.eval("patches.inventory_slot_dirty.transformer(clazz)");
                save(slot);
                engine.put("clazz", slot);
                try {
                    engine.eval("patches.inventory_slot_dirty.transformer(clazz)");
                    throw new AssertionError("Repeated transform must fail rather than add duplicate methods");
                } catch (javax.script.ScriptException expected) {
                    if (!expected.getMessage().contains("now implements")) throw expected;
                }
                prepareCarry(engine);
                loader.loadClass("test.Scenarios").getMethod("run").invoke(null);
                System.out.println("inventory/carcass bytecode cases passed");
            }
        } finally {
            try (var paths = Files.walk(work)) {
                for (Path p : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(p);
            }
        }
    }

    static void prepareClear() throws Exception {
        var shell = new ClassNode();
        new ClassReader(Files.readAllBytes(work.resolve("test/PageClear.class"))).accept(shell, 0);
        var tab = read("betterinventory-forge-1.20.1-2.1.0.jar", BI + "menu/TabStorage");
        keep(tab, "m_6211_");
        var clear = tab.methods.get(0);
        for (var insn : clear.instructions) {
            if (insn instanceof MethodInsnNode m && m.owner.equals(tab.name)) m.owner = shell.name;
        }
        shell.methods.removeIf(m -> m.name.equals("m_6211_"));
        shell.methods.add(clear);
        save(shell);
    }

    static void prepareInventory() throws Exception {
        for (String name : List.of("inv/handler/ItemStackHandler", "inv/BigStackHandler",
                "inv/ComponentBackedHandler", "data/StoredItems", "data/StoredItems$Entry", "data/ItemNbt")) {
            var node = read("betterinventory-forge-1.20.1-2.1.0.jar", BI + name);
            if (name.equals("inv/BigStackHandler")) {
                node.methods.removeIf(m -> m.name.equals("fromUpgrade") || m.name.equals("lambda$fromUpgrade$0"));
            }
            save(node);
        }
        var loadout = read("betterinventory-forge-1.20.1-2.1.0.jar", BI + "inv/PlayerLoadout");
        keep(loadout, "migratePageSlot", "migrateContents", "lambda$pageStore$5");
        loadout.fields.removeIf(f -> !f.name.equals("dirty"));
        loadout.interfaces.clear();
        var constructor = new MethodNode(Opcodes.ACC_PUBLIC, "<init>", "()V", null, null);
        constructor.instructions.add(new VarInsnNode(Opcodes.ALOAD, 0));
        constructor.instructions.add(new MethodInsnNode(Opcodes.INVOKESPECIAL,
            "java/lang/Object", "<init>", "()V", false));
        constructor.instructions.add(new InsnNode(Opcodes.RETURN));
        loadout.methods.add(constructor);
        save(loadout);
        var sync = read("betterinventory-forge-1.20.1-2.1.0.jar", BI + "logic/SyncService");
        requireCall(sync, "syncNow", "serializeNBT");
        requireCall(sync, "syncNow", "sendToPlayer");
        requireCall(sync, "applyClientSync", "deserializeNBT");
        var page = read("betterinventory-forge-1.20.1-2.1.0.jar", BI + "menu/BackpackMenu$PageView");
        save(page);
    }

    static void prepareCarry(javax.script.ScriptEngine engine) throws Exception {
        var carry = read("carryon-forge-1.20.1-2.1.2.7.jar", "tschipp/carryon/events/CommonEvents");
        keep(carry, "lambda$onBlockClick$0");
        carry.methods.get(0).access = Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC;
        save(copyRenamed(carry, "test/OriginalCarry"));
        engine.put("method", carry.methods.get(0));
        engine.eval("patches.carry_permission_probe.transformer(method)");
        save(copyRenamed(carry, "test/PatchedCarry"));
        for (String prefix : PROCEDURES) {
            var proc = read("Butchersdelight beta 1.20.1 2.1.0.jar",
                BD + prefix + "DestroyedByPlayerProcedure");
            keep(proc, "onBlockBreak");
            for (var insn : proc.methods.get(0).instructions) {
                if (insn instanceof MethodInsnNode call && call.name.equals("execute")) {
                    call.owner = "test/Harvest";
                }
            }
            engine.put("method", proc.methods.get(0));
            engine.eval("patches.carcass_probe_" + prefix + ".transformer(method)");
            save(proc);
        }
        try (var jar = new JarFile(root.resolve("mods/inventory-carcass-compat-1.20.1-1.0.0.jar").toFile())) {
            String name = "net/serverfixes/inventory/CarryOnPermissionProbeEvent.class";
            Path output = work.resolve(name);
            Files.createDirectories(output.getParent());
            Files.write(output, jar.getInputStream(jar.getJarEntry(name)).readAllBytes());
        }
    }

    static void prepareStubs() throws Exception {
        source("net.minecraftforge.coremod.api.ASMAPI",
            "public class ASMAPI { public static String mapMethod(String n) { return n; } }");
        source("net.minecraft.nbt.Tag", "public interface Tag {}");
        source("net.minecraft.nbt.CompoundTag", """
            public class CompoundTag implements Tag {
                private final java.util.Map<String,Object> values = new java.util.HashMap<>();
                public void m_128405_(String key, int value) { values.put(key, value); }
                public int m_128451_(String key) { return (Integer)values.getOrDefault(key, 0); }
                public boolean m_128425_(String key, int type) { return values.containsKey(key); }
                public Tag m_128365_(String key, Tag value) { return (Tag)values.put(key, value); }
                public Tag m_128423_(String key) { return (Tag)values.get(key); }
                public ListTag m_128437_(String key, int type) {
                    return (ListTag)values.getOrDefault(key, new ListTag());
                }
                public void remove(String key) { values.remove(key); }
            }
            """);
        source("net.minecraft.nbt.ListTag", """
            public class ListTag extends java.util.ArrayList<Object> implements Tag {
                public CompoundTag m_128728_(int i) { return (CompoundTag)get(i); }
            }
            """);
        source("net.minecraft.core.NonNullList", """
            public class NonNullList<E> extends java.util.ArrayList<E> {
                public static <E> NonNullList<E> m_122780_(int size, E empty) {
                    NonNullList<E> list = new NonNullList<>();
                    for (int i=0; i<size; i++) list.add(empty);
                    return list;
                }
            }
            """);
        source("net.minecraft.world.item.Item", "public class Item {}");
        source("net.minecraft.world.item.Items", """
            public class Items { public static final Item f_41852_ = new Item(); }
            """);
        source("net.minecraft.world.item.ItemStack", """
            public class ItemStack {
                public static final ItemStack f_41583_ = new ItemStack(0, 0);
                private int count;
                public final int identity;
                public final Item item;
                private final net.minecraft.nbt.CompoundTag tag = new net.minecraft.nbt.CompoundTag();
                public ItemStack(int id, int count) {
                    identity = id; this.count = count;
                    item = id == 0 ? Items.f_41852_ : new Item();
                }
                public boolean m_41619_() { return count <= 0 || identity == 0; }
                public int m_41613_() { return count; }
                public void m_41764_(int count) { this.count = count; }
                public int m_41741_() { return 64; }
                public Item m_41720_() { return item; }
                public ItemStack m_41777_() { return new ItemStack(identity, count); }
                public ItemStack m_255036_(int count) { return new ItemStack(identity, count); }
                public static boolean m_150942_(ItemStack a, ItemStack b) { return a.identity == b.identity; }
                public net.minecraft.nbt.CompoundTag m_41783_() { return tag; }
                public net.minecraft.nbt.CompoundTag m_41784_() { return tag; }
                public void m_41749_(String key) { tag.remove(key); }
                public net.minecraft.nbt.CompoundTag m_41739_(net.minecraft.nbt.CompoundTag nbt) {
                    nbt.m_128405_("id", identity); nbt.m_128405_("Count", count); return nbt;
                }
                public static ItemStack m_41712_(net.minecraft.nbt.CompoundTag nbt) {
                    return new ItemStack(nbt.m_128451_("id"), nbt.m_128451_("Count"));
                }
            }
            """);
        source("net.minecraft.world.Container", "public interface Container {}");
        source("net.minecraft.world.SimpleContainer", """
            public class SimpleContainer implements Container { public SimpleContainer(int size) {} }
            """);
        source("net.minecraft.world.inventory.Slot", """
            public class Slot {
                public Slot(net.minecraft.world.Container c, int i, int x, int y) {}
                public void m_6654_() {}
            }
            """);
        source("dev.fallingcloud.betterinventory.menu.slots.BackgroundSlot", """
            public class BackgroundSlot extends net.minecraft.world.inventory.Slot {
                public BackgroundSlot(net.minecraft.world.Container c, int i, int x, int y) { super(c,i,x,y); }
            }
            """);
        source("dev.fallingcloud.betterinventory.inv.handler.IItemHandler", """
            public interface IItemHandler {
                int getSlots();
                net.minecraft.world.item.ItemStack getStackInSlot(int slot);
                net.minecraft.world.item.ItemStack insertItem(int slot, net.minecraft.world.item.ItemStack stack, boolean simulate);
                net.minecraft.world.item.ItemStack extractItem(int slot, int count, boolean simulate);
                int getSlotLimit(int slot);
                boolean isItemValid(int slot, net.minecraft.world.item.ItemStack stack);
            }
            """);
        source("dev.fallingcloud.betterinventory.inv.handler.IItemHandlerModifiable", """
            public interface IItemHandlerModifiable extends IItemHandler {
                void setStackInSlot(int slot, net.minecraft.world.item.ItemStack stack);
            }
            """);
        source("dev.fallingcloud.betterinventory.logic.StackUpgradeService", """
            public class StackUpgradeService {
                public static boolean active() { return false; }
                public static int scaledCap(net.minecraft.world.item.ItemStack stack, int cap) { return cap; }
            }
            """);
        source("dev.fallingcloud.betterinventory.data.ItemData", """
            public class ItemData<T> {
                private Object lastTag, lastValue;
                public T getOrDefault(net.minecraft.world.item.ItemStack host, T fallback) {
                    Object tag = host.m_41783_().m_128423_("contents");
                    if (tag == null) return fallback;
                    if (tag != lastTag) {
                        lastTag = tag;
                        lastValue = StoredItems.fromNbt((net.minecraft.nbt.Tag)tag);
                    }
                    return (T)lastValue;
                }
                public void set(net.minecraft.world.item.ItemStack host, T value) {
                    var tag = ((StoredItems)value).toNbt();
                    host.m_41784_().m_128365_("contents", tag);
                    lastTag = tag; lastValue = value;
                }
                public void remove(net.minecraft.world.item.ItemStack host) { host.m_41749_("contents"); }
            }
            """);
        source("dev.fallingcloud.betterinventory.registry.ModComponents", """
            public class ModComponents {
                public static final dev.fallingcloud.betterinventory.data.ItemData<dev.fallingcloud.betterinventory.data.StoredItems>
                    BACKPACK_CONTENTS = new dev.fallingcloud.betterinventory.data.ItemData<>();
            }
            """);
        source("dev.fallingcloud.betterinventory.menu.BackpackMenu", """
            public class BackpackMenu {
                public dev.fallingcloud.betterinventory.inv.ComponentBackedHandler storageHandler;
                public int base;
                public int pageBase() { return base; }
                public dev.fallingcloud.betterinventory.inv.handler.IItemHandlerModifiable view() {
                    try {
                        var c = Class.forName(getClass().getName() + "$PageView").getDeclaredConstructor(getClass());
                        c.setAccessible(true);
                        return (dev.fallingcloud.betterinventory.inv.handler.IItemHandlerModifiable)c.newInstance(this);
                    } catch (ReflectiveOperationException e) { throw new AssertionError(e); }
                }
            }
            """);
        source("net.minecraft.core.BlockPos", """
            public class BlockPos {
                public int m_123341_() { return 1; }
                public int m_123342_() { return 2; }
                public int m_123343_() { return 3; }
            }
            """);
        source("net.minecraft.world.level.LevelAccessor", "public interface LevelAccessor {}");
        source("net.minecraft.world.level.Level", "public class Level implements LevelAccessor {}");
        source("net.minecraft.world.level.block.state.BlockState", "public class BlockState {}");
        source("net.minecraft.world.entity.player.Player", "public class Player {}");
        source("net.minecraftforge.eventbus.api.Event", "public class Event {}");
        source("net.minecraftforge.event.level.BlockEvent", """
            public class BlockEvent {
                public static class BreakEvent extends net.minecraftforge.eventbus.api.Event {
                    private final net.minecraft.world.level.Level level;
                    private final net.minecraft.core.BlockPos pos;
                    public boolean canceled;
                    public BreakEvent(net.minecraft.world.level.Level level, net.minecraft.core.BlockPos pos,
                            net.minecraft.world.level.block.state.BlockState state,
                            net.minecraft.world.entity.player.Player player) { this.level=level; this.pos=pos; }
                    public net.minecraft.world.level.LevelAccessor getLevel() { return level; }
                    public net.minecraft.core.BlockPos getPos() { return pos; }
                    public boolean isCanceled() { return canceled; }
                }
            }
            """);
        source("net.minecraftforge.eventbus.api.IEventBus", "public interface IEventBus { boolean post(Event event); }");
        source("net.minecraftforge.common.MinecraftForge", """
            public class MinecraftForge {
                public static boolean deny;
                public static int permissionChecks;
                public static final net.minecraftforge.eventbus.api.IEventBus EVENT_BUS = event -> {
                    permissionChecks++;
                    for (String name : test.Harvest.procedures) {
                        try {
                            Class.forName("net.mcreator.butchersdelight.procedures." + name +
                                "DestroyedByPlayerProcedure").getMethod("onBlockBreak",
                                net.minecraftforge.event.level.BlockEvent.BreakEvent.class).invoke(null, event);
                        } catch (ReflectiveOperationException e) { throw new AssertionError(e); }
                    }
                    ((net.minecraftforge.event.level.BlockEvent.BreakEvent)event).canceled = deny;
                    return deny;
                };
            }
            """);
        source("test.Harvest", """
            public class Harvest {
                public static int calls;
                public static final String[] procedures = {"HookedchickenBlock","HookedcowBlock",
                    "Hookedgoatblock","HookedhoglinBlock","Hookedllamablock","HookedpigBlock",
                    "HookedsheepBlock","RackcowBlock","RackgoatBlock","RackhoglinBlock","RacksheepBlock"};
                public static void execute(net.minecraftforge.eventbus.api.Event e,
                    net.minecraft.world.level.LevelAccessor level, double x, double y, double z) { calls++; }
            }
            """);
        source("test.PageClear", """
            public class PageClear {
                private final dev.fallingcloud.betterinventory.inv.ComponentBackedHandler handler;
                private final int base;
                public PageClear(dev.fallingcloud.betterinventory.inv.ComponentBackedHandler handler, int base) {
                    this.handler = handler; this.base = base;
                }
                public void m_6836_(int slot, net.minecraft.world.item.ItemStack stack) {
                    handler.setStackInSlot(base + slot, stack);
                }
                public void m_6211_() {}
            }
            """);
        source("test.Scenarios", SCENARIOS);
    }

    static ClassNode read(String jarName, String name) throws Exception {
        try (var jar = new JarFile(root.resolve("mods/" + jarName).toFile())) {
            var entry = jar.getJarEntry(name + ".class");
            if (entry == null) throw new AssertionError("Installed target missing: " + name);
            var node = new ClassNode();
            new ClassReader(jar.getInputStream(entry)).accept(node, 0);
            return node;
        }
    }
    static void keep(ClassNode node, String... names) {
        var allowed = Set.of(names);
        node.methods.removeIf(m -> !allowed.contains(m.name));
        for (String name : names) {
            if (node.methods.stream().noneMatch(m -> m.name.equals(name))) {
                throw new AssertionError(node.name + " missing target " + name);
            }
        }
    }
    static void requireCall(ClassNode node, String method, String call) {
        var target = node.methods.stream().filter(m -> m.name.equals(method)).findFirst().orElseThrow();
        for (var insn : target.instructions) {
            if (insn instanceof MethodInsnNode m && m.name.equals(call)) return;
        }
        throw new AssertionError("Native server-authoritative sync path changed: " + method + "/" + call);
    }
    static ClassNode copyRenamed(ClassNode original, String name) {
        var clone = new ClassNode();
        original.accept(clone);
        String before = clone.name;
        clone.name = name;
        for (var method : clone.methods) {
            for (var insn : method.instructions) {
                if (insn instanceof FieldInsnNode f && f.owner.equals(before)) f.owner = name;
                if (insn instanceof MethodInsnNode m && m.owner.equals(before)) m.owner = name;
            }
        }
        return clone;
    }
    static void save(ClassNode node) throws Exception {
        var writer = new ClassWriter(ClassWriter.COMPUTE_MAXS | ClassWriter.COMPUTE_FRAMES) {
            @Override protected String getCommonSuperClass(String a, String b) { return "java/lang/Object"; }
        };
        node.accept(writer);
        Path path = work.resolve(node.name + ".class");
        Files.createDirectories(path.getParent());
        Files.write(path, writer.toByteArray());
    }
    static void source(String name, String body) throws Exception {
        Path path = work.resolve(name.replace('.', '/') + ".java");
        Files.createDirectories(path.getParent());
        Files.writeString(path, "package " + name.substring(0, name.lastIndexOf('.')) + ";\n" + body);
    }

    static final String SCENARIOS = """
        public class Scenarios {
            static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
            public static void run() throws Exception {
                carry();
                inventory();
                migration();
            }
            static void carry() throws Exception {
                var signature = new Class<?>[]{net.minecraft.world.level.Level.class,
                    net.minecraft.world.entity.player.Player.class,
                    net.minecraft.world.level.block.state.BlockState.class, net.minecraft.core.BlockPos.class};
                var arguments = new Object[]{new net.minecraft.world.level.Level(),
                    new net.minecraft.world.entity.player.Player(),
                    new net.minecraft.world.level.block.state.BlockState(), new net.minecraft.core.BlockPos()};
                var original = Class.forName("test.OriginalCarry").getMethod("lambda$onBlockClick$0", signature);
                var patched = Class.forName("test.PatchedCarry").getMethod("lambda$onBlockClick$0", signature);
                check((Boolean)original.invoke(null, arguments), "Original permitted pickup");
                check(Harvest.calls == 11, "Original permission probe erroneously fires all harvest callbacks");
                Harvest.calls = 0;
                for (int i=0; i<50; i++) check((Boolean)patched.invoke(null, arguments), "Pickup UX retained");
                check(Harvest.calls == 0, "Pickup must not harvest carcass loot");
                net.minecraftforge.common.MinecraftForge.deny = true;
                check(!(Boolean)patched.invoke(null, arguments), "Permission denial retained");
                check(Harvest.calls == 0, "Canceled probe cannot harvest");
                check(net.minecraftforge.common.MinecraftForge.permissionChecks == 52, "Every probe reaches Forge event bus");
                net.minecraftforge.common.MinecraftForge.deny = false;
                var real = new net.minecraftforge.event.level.BlockEvent.BreakEvent(
                    (net.minecraft.world.level.Level)arguments[0], (net.minecraft.core.BlockPos)arguments[3],
                    (net.minecraft.world.level.block.state.BlockState)arguments[2],
                    (net.minecraft.world.entity.player.Player)arguments[1]);
                net.minecraftforge.common.MinecraftForge.EVENT_BUS.post(real);
                check(Harvest.calls == 11, "Genuine block harvest unchanged");
            }
            static void inventory() throws Exception {
                var component = dev.fallingcloud.betterinventory.registry.ModComponents.BACKPACK_CONTENTS;
                var host = new net.minecraft.world.item.ItemStack(999,1);
                var handler = new dev.fallingcloud.betterinventory.inv.ComponentBackedHandler(host,component,360,()->64);
                final int[] dirty = {0};
                var loadout = new dev.fallingcloud.betterinventory.inv.PlayerLoadout();
                var notify = loadout.getClass().getDeclaredMethod("lambda$pageStore$5");
                notify.setAccessible(true);
                handler.setChangeListener(()->{
                    dirty[0]++;
                    try { notify.invoke(loadout); } catch (Exception e) { throw new AssertionError(e); }
                });
                var menu = new dev.fallingcloud.betterinventory.menu.BackpackMenu();
                menu.storageHandler = handler;
                menu.base = 72;
                var view = menu.view();
                var api = dev.fallingcloud.betterinventory.inv.handler.IItemHandler.class;
                var oldSlot = Class.forName("test.OriginalSlot").getConstructor(api,int.class,int.class,int.class)
                    .newInstance(view,3,0,0);
                handler.setStackInSlot(75,new net.minecraft.world.item.ItemStack(7,40));
                handler.getStackInSlot(75).m_41764_(25);
                oldSlot.getClass().getMethod("m_6654_").invoke(oldSlot);
                var stale = new dev.fallingcloud.betterinventory.inv.ComponentBackedHandler(host,component,360,()->64);
                check(stale.getStackInSlot(75).m_41613_()==40,"Reproduced original phantom old count after reload");
                var slot = Class.forName("dev.fallingcloud.betterinventory.inv.handler.SlotItemHandler")
                    .getConstructor(api,int.class,int.class,int.class).newInstance(view,3,0,0);
                int previous = dirty[0];
                loadout.dirty = false;
                slot.getClass().getMethod("m_6654_").invoke(slot);
                check(dirty[0]>previous,"Native server sync dirty listener notified");
                check(loadout.dirty,"Actual installed pageStore listener marks loadout dirty for server sync");
                var reopened = new dev.fallingcloud.betterinventory.inv.ComponentBackedHandler(host,component,360,()->64);
                check(reopened.getStackInSlot(75).m_41613_()==25,"Partial shift-click persisted via real PageView");
                var simulated = reopened.extractItem(75,10,true);
                check(simulated.m_41613_()==10 && reopened.getStackInSlot(75).m_41613_()==25,"Simulation nonmutating");
                check(reopened.extractItem(75,10,false).m_41613_()==10,"Extraction succeeds");
                check(handler.getStackInSlot(75).m_41613_()==15,"Multiple handlers refresh authoritative host");
                handler.setStackInSlot(359,new net.minecraft.world.item.ItemStack(8,1000));
                handler.getStackInSlot(75).m_41764_(0);
                slot.getClass().getMethod("m_6654_").invoke(slot);
                var saved = dev.fallingcloud.betterinventory.data.StoredItems.fromNbt(
                    component.getOrDefault(host,dev.fallingcloud.betterinventory.data.StoredItems.EMPTY).toNbt());
                check(saved.unpack(360).get(75).m_41619_(),"Removed stack never resurrected");
                check(saved.unpack(360).get(359).m_41613_()==1000,"Other pages and large counts preserved");

                slot.getClass().getMethod("m_5852_",net.minecraft.world.item.ItemStack.class)
                    .invoke(slot,new net.minecraft.world.item.ItemStack(7,50));
                checkCount(host,75,50,"Native slot set persists");
                var removed = (net.minecraft.world.item.ItemStack)slot.getClass().getMethod("m_6201_",int.class)
                    .invoke(slot,20);
                check(removed.m_41613_()==20,"Native slot removal returns requested amount");
                checkCount(host,75,30,"Native partial removal persists");
                var mutable = (net.minecraft.world.item.ItemStack)slot.getClass().getMethod("m_7993_").invoke(slot);
                mutable.m_41764_(45);
                slot.getClass().getMethod("m_6654_").invoke(slot);
                checkCount(host,75,45,"Direct stack grow followed by native setChanged persists");
                mutable = (net.minecraft.world.item.ItemStack)slot.getClass().getMethod("m_7993_").invoke(slot);
                mutable.m_41764_(2);
                slot.getClass().getMethod("m_6654_").invoke(slot);
                checkCount(host,75,2,"Direct stack shrink followed by native setChanged persists");
                slot.getClass().getMethod("m_6201_",int.class).invoke(slot,64);
                checkCount(host,75,0,"Native full removal persists without ghost restoration");
                slot.getClass().getMethod("m_5852_",net.minecraft.world.item.ItemStack.class)
                    .invoke(slot,new net.minecraft.world.item.ItemStack(7,12));
                slot.getClass().getMethod("m_5852_",net.minecraft.world.item.ItemStack.class)
                    .invoke(slot,net.minecraft.world.item.ItemStack.f_41583_);
                checkCount(host,75,0,"Native slot clear/set EMPTY persists");
                for (int i=144;i<216;i++) handler.setStackInSlot(i,new net.minecraft.world.item.ItemStack(7,i));
                new PageClear(handler,144).m_6211_();
                for (int i=144;i<216;i++) checkCount(host,i,0,"Actual native clear visits every slot");
                checkCount(host,359,1000,"Native clear preserves unrelated pages");

                Object readOnly = java.lang.reflect.Proxy.newProxyInstance(api.getClassLoader(),
                    new Class<?>[]{api},(proxy,method,args)->method.invoke(view,args));
                var readOnlySlot = slot.getClass().getConstructor(api,int.class,int.class,int.class)
                    .newInstance(readOnly,3,0,0);
                previous = dirty[0];
                readOnlySlot.getClass().getMethod("m_6654_").invoke(readOnlySlot);
                check(dirty[0]==previous,"Read-only handlers are not cast, mutated, or rejected");
            }
            static void checkCount(net.minecraft.world.item.ItemStack host, int slot, int count, String message) {
                var reopened = new dev.fallingcloud.betterinventory.inv.ComponentBackedHandler(host,
                    dev.fallingcloud.betterinventory.registry.ModComponents.BACKPACK_CONTENTS,360,()->64);
                check(reopened.getStackInSlot(slot).m_41613_()==count,message);
            }
            static void migration() {
                var component = dev.fallingcloud.betterinventory.registry.ModComponents.BACKPACK_CONTENTS;
                var entries = new java.util.ArrayList<dev.fallingcloud.betterinventory.data.StoredItems.Entry>();
                for (int i=0;i<180;i++) entries.add(new dev.fallingcloud.betterinventory.data.StoredItems.Entry(
                    i,new net.minecraft.world.item.ItemStack(i+1, i+300)));
                var legacy = new dev.fallingcloud.betterinventory.data.StoredItems(180,java.util.List.copyOf(entries));
                var serialized = dev.fallingcloud.betterinventory.data.StoredItems.fromNbt(legacy.toNbt());
                var migrated = dev.fallingcloud.betterinventory.inv.PlayerLoadout.migrateContents(serialized);
                check(migrated.size()==360 && migrated.entries().size()==180,"All legacy serialized entries retained");
                var unpacked = migrated.unpack(360);
                for(int i=0;i<180;i++) {
                    var stack = unpacked.get((i/45)*72+i%45);
                    check(stack.identity==i+1 && stack.m_41613_()==i+300,"Legacy slot and count preserved");
                }
                check(dev.fallingcloud.betterinventory.inv.PlayerLoadout.migrateContents(migrated)==migrated,
                    "Migration idempotent");
                var host = new net.minecraft.world.item.ItemStack(999,1);
                component.set(host,serialized);
                var handler = new dev.fallingcloud.betterinventory.inv.ComponentBackedHandler(host,component,360,()->64);
                check(handler.getStackInSlot(260).identity==180,"Actual refresh migrates legacy host");
                check(component.getOrDefault(host,legacy).size()==360,"Migration persisted on host");
                var after = dev.fallingcloud.betterinventory.data.StoredItems.fromNbt(
                    component.getOrDefault(host,legacy).toNbt());
                check(after.entries().size()==180,"NBT save/reload has no data deletion");
            }
        }
        """;
}
