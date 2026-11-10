import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Map;
import java.util.jar.JarFile;
import javax.tools.ToolProvider;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.analysis.Analyzer;
import org.objectweb.asm.tree.analysis.BasicVerifier;
import org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory;
import org.openjdk.nashorn.api.scripting.ScriptObjectMirror;

class CravingsCoremodTest {
    public static void main(String[] args) throws Exception {
        Path directory = Files.createTempDirectory("cravings-bytecode-test-");
        try {
            fixtures(directory);
            try (var loader = new URLClassLoader(new java.net.URL[]{directory.toUri().toURL()},
                    CravingsCoremodTest.class.getClassLoader())) {
                var engine = new NashornScriptEngineFactory().getScriptEngine(new String[]{"--language=es6"}, loader);
                engine.eval(Files.readString(Path.of(args[0])));
                var transforms = (ScriptObjectMirror)engine.eval("var transforms = initializeCoreMod(); transforms");
                ClassNode helpers = null;
                int durationCalls = 0;
                int placedCalls = 0;
                for (String key : transforms.keySet()) {
                    var transform = (ScriptObjectMirror)transforms.get(key);
                    var target = (ScriptObjectMirror)transform.get("target");
                    boolean isClass = target.get("type").equals("CLASS");
                    String name = (String)target.get(isClass ? "name" : "class");
                    ClassNode node = readClass(Path.of(args[1]), directory, name);
                    engine.put("testKey", key);
                    if (isClass) {
                        engine.put("testNode", node);
                        engine.eval("transforms[testKey].transformer(testNode)");
                    } else {
                        var matches = node.methods.stream().filter(method ->
                            method.name.equals(target.get("methodName")) &&
                            method.desc.equals(target.get("methodDesc"))).toList();
                        if (matches.size() != 1) throw new AssertionError("Method target changed: " + name);
                        engine.put("testMethod", matches.get(0));
                        engine.eval("transforms[testKey].transformer(testMethod)");
                    }
                    for (MethodNode method : node.methods) {
                        if ((method.access & (Opcodes.ACC_ABSTRACT | Opcodes.ACC_NATIVE)) != 0) continue;
                        method.maxStack += 16;
                        new Analyzer<>(new BasicVerifier()).analyze(node.name, method);
                        for (var instruction : method.instructions) {
                            if (instruction instanceof MethodInsnNode call) {
                                if (call.name.equals("serverfixes$scaleDuration")) {
                                    durationCalls++;
                                    var load = call.getPrevious();
                                    if (!(load instanceof org.objectweb.asm.tree.VarInsnNode local) || local.var != 7) {
                                        throw new AssertionError("Reward must use the consuming player");
                                    }
                                    if (!(load.getPrevious() instanceof org.objectweb.asm.tree.FieldInsnNode field) ||
                                            !field.name.endsWith("_duration") || field.name.equals("bonus_duration")) {
                                        throw new AssertionError("Only the base reward duration may be scaled");
                                    }
                                }
                                if (call.name.equals("onItemUseFinish")) placedCalls++;
                            }
                        }
                    }
                    if (name.endsWith(".EatingCheckProcedure")) helpers = node;
                }
                if (durationCalls != 15 || placedCalls != 5) {
                    throw new AssertionError("Expected 15 duration paths and 5 placed-food paths, got " +
                        durationCalls + "/" + placedCalls);
                }
                if (transforms.containsKey("RawDuration")) throw new AssertionError("Raw Nausea must be unchanged");
                if (helpers == null) throw new AssertionError("Food helpers missing");
                saveHelpers(directory, helpers);
                Class<?> helperClass = loader.loadClass("net.dyrohc.cravings.procedures.EatingCheckProcedure");
                Class<?> entity = loader.loadClass("net.minecraft.world.entity.Entity");
                var scale = helperClass.getMethod("serverfixes$scaleDuration", double.class, entity);
                var constructor = entity.getConstructor(String.class);
                for (String id : new String[]{"simple", "regular", "big"}) {
                    double multiplier = id.equals("simple") ? 0.5 : id.equals("big") ? 2 : 1;
                    for (double base : new double[]{0, 6000, 1200}) {
                        double actual = (double)scale.invoke(null, base, constructor.newInstance(id));
                        if (actual != base * multiplier) throw new AssertionError(id + ": " + actual);
                    }
                }
                Class<?> item = loader.loadClass("net.minecraft.world.item.Item");
                var food = helperClass.getMethod("serverfixes$isFood", item);
                var itemConstructor = item.getConstructor(String.class, boolean.class);
                for (var test : new Object[][]{
                    {"ordinary_food", true, true}, {"placed", false, true},
                    {"drink", false, true}, {"stone", false, false}
                }) {
                    if (!food.invoke(null, itemConstructor.newInstance(test[0], test[1])).equals(test[2])) {
                        throw new AssertionError("Food gate: " + test[0]);
                    }
                }
                System.out.println("Cravings installed-bytecode and duration tests passed: 15 reward/advancement paths, " +
                    "5 placed-food paths, 9 exact durations, 4 edible gates");
            }
        } finally {
            try (var paths = Files.walk(directory)) {
                for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(path);
            }
        }
    }

    private static ClassNode readClass(Path mods, Path directory, String name) throws Exception {
        ClassNode node = new ClassNode();
        String entry = name.replace('.', '/') + ".class";
        if (name.equals("net.minecraft.world.level.block.CakeBlock")) {
            new ClassReader(Files.readAllBytes(directory.resolve(entry))).accept(node, 0);
            return node;
        }
        try (var jars = Files.list(mods)) {
            for (Path path : jars.filter(path -> path.toString().endsWith(".jar")).toList()) {
                try (var jar = new JarFile(path.toFile())) {
                    var found = jar.getJarEntry(entry);
                    if (found != null) {
                        try (var stream = jar.getInputStream(found)) {
                            new ClassReader(stream).accept(node, 0);
                        }
                        return node;
                    }
                }
            }
        }
        throw new AssertionError("Installed class missing: " + name);
    }

    private static void saveHelpers(Path directory, ClassNode node) throws Exception {
        ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_FRAMES | ClassWriter.COMPUTE_MAXS);
        writer.visit(Opcodes.V17, Opcodes.ACC_PUBLIC, node.name, null, "java/lang/Object", null);
        for (MethodNode method : node.methods) {
            if (method.name.startsWith("serverfixes$")) method.accept(writer);
        }
        writer.visitEnd();
        Path target = directory.resolve(node.name + ".class");
        Files.createDirectories(target.getParent());
        Files.write(target, writer.toByteArray());
    }

    private static void fixtures(Path directory) throws Exception {
        var sources = new ArrayList<String>();
        sources.add("-source");
        sources.add("17");
        sources.add("-target");
        sources.add("17");
        Map<String, String> fixtures = Map.ofEntries(
            Map.entry("net.minecraftforge.coremod.api.ASMAPI", """
                public class ASMAPI {
                    public static String mapMethod(String name) { return name; }
                    public static String mapField(String name) { return name; }
                }
                """),
            Map.entry("net.minecraft.resources.ResourceLocation", """
                public class ResourceLocation {
                    public final String id;
                    public ResourceLocation(String id) { this.id = id; }
                }
                """),
            Map.entry("net.minecraft.tags.TagKey", """
                public class TagKey {
                    public final String id;
                    public TagKey(String id) { this.id = id; }
                }
                """),
            Map.entry("net.minecraft.world.level.ItemLike", "public interface ItemLike {}"),
            Map.entry("net.minecraft.world.item.Item", """
                public class Item implements net.minecraft.world.level.ItemLike {
                    public final String id;
                    public final boolean edible;
                    public Item(String id, boolean edible) { this.id = id; this.edible = edible; }
                    public boolean m_41472_() { return edible; }
                }
                """),
            Map.entry("net.minecraft.world.item.ItemStack", """
                public class ItemStack {
                    public final Item item;
                    public ItemStack(net.minecraft.world.level.ItemLike item) { this.item = (Item)item; }
                    public boolean m_204117_(net.minecraft.tags.TagKey tag) {
                        return switch (tag.id) {
                            case "cravings:simple_food" -> item.id.equals("simple");
                            case "cravings:big_meal" -> item.id.equals("big");
                            case "cravings:foods" -> item.id.equals("placed") || item.id.equals("drink");
                            default -> false;
                        };
                    }
                }
                """),
            Map.entry("net.minecraftforge.registries.IForgeRegistry", """
                public interface IForgeRegistry {
                    Object getValue(net.minecraft.resources.ResourceLocation location);
                    net.minecraftforge.registries.tags.ITagManager tags();
                }
                """),
            Map.entry("net.minecraftforge.registries.tags.ITagManager", """
                public interface ITagManager {
                    net.minecraft.tags.TagKey createTagKey(net.minecraft.resources.ResourceLocation location);
                }
                """),
            Map.entry("net.minecraftforge.registries.ForgeRegistries", """
                public class ForgeRegistries {
                    public static final IForgeRegistry ITEMS = new IForgeRegistry() {
                        public Object getValue(net.minecraft.resources.ResourceLocation location) {
                            return new net.minecraft.world.item.Item(location.id, true);
                        }
                        public net.minecraftforge.registries.tags.ITagManager tags() {
                            return location -> new net.minecraft.tags.TagKey(location.id);
                        }
                    };
                }
                """),
            Map.entry("net.minecraftforge.common.capabilities.Capability", "public class Capability {}"),
            Map.entry("net.minecraftforge.common.util.LazyOptional", """
                public class LazyOptional {
                    public final Object value;
                    public LazyOptional(Object value) { this.value = value; }
                    public Object orElse(Object fallback) { return value == null ? fallback : value; }
                }
                """),
            Map.entry("net.dyrohc.cravings.network.CravingsModVariables", """
                public class CravingsModVariables {
                    public static final net.minecraftforge.common.capabilities.Capability PLAYER_VARIABLES =
                        new net.minecraftforge.common.capabilities.Capability();
                    public static class PlayerVariables {
                        public final String usedItemID;
                        public PlayerVariables(String id) { usedItemID = id; }
                    }
                }
                """),
            Map.entry("net.minecraft.world.entity.Entity", """
                public class Entity {
                    public final String id;
                    public Entity(String id) { this.id = id; }
                    public net.minecraftforge.common.util.LazyOptional getCapability(
                            net.minecraftforge.common.capabilities.Capability capability) {
                        return new net.minecraftforge.common.util.LazyOptional(
                            new net.dyrohc.cravings.network.CravingsModVariables.PlayerVariables(id));
                    }
                }
                """),
            Map.entry("net.minecraft.world.entity.player.Player", """
                public class Player extends net.minecraft.world.entity.Entity {
                    public Player() { super("placed"); }
                    public net.minecraft.world.food.FoodData food() { return new net.minecraft.world.food.FoodData(); }
                }
                """),
            Map.entry("net.minecraft.world.food.FoodData", """
                public class FoodData { public void m_38707_(int hunger, float saturation) {} }
                """),
            Map.entry("net.minecraft.world.level.block.state.BlockState", "public class BlockState {}"),
            Map.entry("net.minecraft.world.level.block.CakeBlock", """
                public class CakeBlock {
                    public static void eat(net.minecraft.world.level.block.state.BlockState state,
                            net.minecraft.world.entity.player.Player player) {
                        player.food().m_38707_(2, 0.1f);
                    }
                }
                """)
        );
        for (var entry : fixtures.entrySet()) {
            String name = entry.getKey();
            Path source = directory.resolve(name.replace('.', '/') + ".java");
            Files.createDirectories(source.getParent());
            Files.writeString(source, "package " + name.substring(0, name.lastIndexOf('.')) + ";\n" + entry.getValue());
            sources.add(source.toString());
        }
        var compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null || compiler.run(null, null, null, sources.toArray(String[]::new)) != 0) {
            throw new AssertionError("Could not compile bytecode fixtures");
        }
    }
}
