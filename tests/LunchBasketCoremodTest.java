import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.Map;
import java.util.jar.JarFile;
import javax.tools.ToolProvider;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.MethodNode;
import org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory;

class LunchBasketCoremodTest {
    public static void main(String[] args) throws Exception {
        Path directory = Files.createTempDirectory("lunch-basket-bytecode-test-");
        try {
            Map<String, String> stubs = Map.of(
                "net.minecraftforge.coremod.api.ASMAPI",
                "public static String mapMethod(String name) { return name; }",
                "net.minecraft.resources.ResourceLocation",
                "public final String id; public ResourceLocation(String id) { this.id = id; }",
                "net.minecraft.tags.TagKey",
                "public final String id; public TagKey(String id) { this.id = id; }",
                "net.minecraft.world.item.Item",
                """
                public final boolean fits;
                public final UseAnim animation;
                public Item(boolean fits, String animation) {
                    this.fits = fits; this.animation = UseAnim.valueOf(animation);
                }
                public boolean m_142095_() { return fits; }
                public UseAnim m_6164_(ItemStack stack) { return animation; }
                """,
                "net.minecraft.world.item.ItemStack",
                """
                public final Item item;
                public final boolean food;
                public final boolean blacklisted;
                public ItemStack(boolean fits, String animation, boolean food, boolean blacklisted) {
                    item = new Item(fits, animation); this.food = food; this.blacklisted = blacklisted;
                }
                public Item m_41720_() { return item; }
                public boolean m_204117_(net.minecraft.tags.TagKey tag) {
                    return tag.id.equals("serverfixes:lunch_basket_foods") ? food : blacklisted;
                }
                """,
                "net.mehvahdjukaar.supplementaries.reg.ModTags",
                """
                public static final net.minecraft.tags.TagKey LUNCH_BASKET_BLACKLIST =
                    new net.minecraft.tags.TagKey("supplementaries:lunch_basket_blacklist");
                """,
                "net.minecraftforge.registries.ForgeRegistries",
                """
                public static final IForgeRegistry ITEMS = () -> location ->
                    new net.minecraft.tags.TagKey(location.id);
                """
            );
            for (var entry : stubs.entrySet()) {
                String name = entry.getKey();
                writeSource(directory, name, "public class " + simpleName(name) + " {" + entry.getValue() + "}");
            }
            writeSource(directory, "net.minecraft.world.item.UseAnim",
                "public enum UseAnim { NONE, EAT, DRINK, BOW }");
            writeSource(directory, "net.minecraftforge.registries.IForgeRegistry",
                "public interface IForgeRegistry { net.minecraftforge.registries.tags.ITagManager tags(); }");
            writeSource(directory, "net.minecraftforge.registries.tags.ITagManager",
                """
                public interface ITagManager {
                    net.minecraft.tags.TagKey createTagKey(net.minecraft.resources.ResourceLocation location);
                }
                """);
            String[] sources;
            try (var paths = Files.walk(directory)) {
                sources = paths.filter(path -> path.toString().endsWith(".java"))
                    .map(Path::toString).toArray(String[]::new);
            }
            var compiler = ToolProvider.getSystemJavaCompiler();
            if (compiler == null || compiler.run(null, null, null, sources) != 0) {
                throw new AssertionError("Could not compile integration-test fixtures");
            }
            try (var loader = new URLClassLoader(new java.net.URL[]{directory.toUri().toURL()},
                    LunchBasketCoremodTest.class.getClassLoader())) {
                Thread.currentThread().setContextClassLoader(loader);
                ClassNode original = new ClassNode();
                try (JarFile jar = new JarFile(args[1]);
                        var stream = jar.getInputStream(jar.getJarEntry(
                            "net/mehvahdjukaar/supplementaries/common/items/LunchBoxItem.class"))) {
                    new ClassReader(stream).accept(original, 0);
                }
                var matches = original.methods.stream().filter(method ->
                    method.name.equals("canAcceptItem") &&
                    method.desc.equals("(Lnet/minecraft/world/item/ItemStack;)Z")).toList();
                if (matches.size() != 1) throw new AssertionError("Supplementaries predicate changed");
                MethodNode method = matches.get(0);
                savePredicate(directory, "OriginalPredicate", method);
                var engine = new NashornScriptEngineFactory().getScriptEngine(
                    new String[]{"--language=es6"}, loader);
                engine.eval(Files.readString(Path.of(args[0])));
                engine.put("method", method);
                engine.eval("initializeCoreMod().lunch_basket_foods.transformer(method)");
                for (var insn : method.instructions) {
                    if (insn instanceof org.objectweb.asm.tree.MethodInsnNode call && call.name.equals("m_41472_")) {
                        throw new AssertionError("Patch must not gate on Item.isEdible; placeable foods are not edible");
                    }
                }
                savePredicate(directory, "PatchedPredicate", method);
                Class<?> stack = loader.loadClass("net.minecraft.world.item.ItemStack");
                var constructor = stack.getConstructor(boolean.class, String.class, boolean.class, boolean.class);
                var before = loader.loadClass("OriginalPredicate").getMethod("canAcceptItem", stack);
                var after = loader.loadClass("PatchedPredicate").getMethod("canAcceptItem", stack);
                Object[][] cases = {
                    // fits, animation, food-tag member, blacklisted, original result, patched result
                    {true, "EAT", true, false, true, true},
                    {true, "DRINK", true, false, true, true},
                    // Non-edible placeable foods (cake, pie, feast BlockItems use UseAnim.NONE)
                    {true, "NONE", true, false, false, true},
                    {true, "BOW", true, false, false, true},
                    {true, "EAT", true, true, false, true},
                    {true, "NONE", false, false, false, false},
                    {true, "BOW", false, false, false, false},
                    {true, "DRINK", false, false, true, true},
                    {true, "DRINK", false, true, false, false},
                    {false, "EAT", true, false, false, false},
                    {false, "DRINK", false, false, false, false}
                };
                for (Object[] test : cases) {
                    Object item = constructor.newInstance(test[0], test[1], test[2], test[3]);
                    if (!before.invoke(null, item).equals(test[4]) ||
                            !after.invoke(null, item).equals(test[5])) {
                        throw new AssertionError(java.util.Arrays.toString(test));
                    }
                }
                System.out.println("Executed installed predicate and Nashorn/ASM patch: " + cases.length + " cases passed");
            }
        } finally {
            try (var paths = Files.walk(directory)) {
                for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(path);
            }
        }
    }

    private static String simpleName(String name) {
        return name.substring(name.lastIndexOf('.') + 1);
    }

    private static void writeSource(Path directory, String name, String body) throws Exception {
        Path file = directory.resolve(name.replace('.', '/') + ".java");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "package " + name.substring(0, name.lastIndexOf('.')) + ";\n" + body);
    }

    private static void savePredicate(Path directory, String name, MethodNode method) throws Exception {
        ClassNode predicate = new ClassNode();
        predicate.version = Opcodes.V17;
        predicate.access = Opcodes.ACC_PUBLIC;
        predicate.name = name;
        predicate.superName = "java/lang/Object";
        predicate.methods.add(method);
        ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_FRAMES | ClassWriter.COMPUTE_MAXS);
        predicate.accept(writer);
        Files.write(directory.resolve(name + ".class"), writer.toByteArray());
    }
}
