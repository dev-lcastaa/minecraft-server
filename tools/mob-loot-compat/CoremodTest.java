import java.net.URLClassLoader;
import java.nio.file.*;
import java.util.*;
import java.util.jar.JarFile;
import javax.tools.ToolProvider;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.tree.analysis.*;
import org.openjdk.nashorn.api.scripting.*;

public class CoremodTest {
    public static void main(String[] args) throws Exception {
        Path source = Path.of(args[0]);
        Path work = source.resolve(".test-work-" + UUID.randomUUID());
        Files.createDirectory(work);
        try {
            Map<String, String> stubs = Map.of(
                "net.minecraftforge.coremod.api.ASMAPI",
                "public class ASMAPI { public static String mapMethod(String name) { return name; }}",
                "net.minecraft.resources.ResourceLocation",
                "public class ResourceLocation { public final String id; public ResourceLocation(String id) { this.id=id; }}",
                "net.minecraft.world.level.ItemLike", "public interface ItemLike {}",
                "net.minecraft.world.item.Item",
                "public class Item implements net.minecraft.world.level.ItemLike { public final String id; public Item(String id) { this.id=id; }}",
                "net.minecraft.world.item.ItemStack",
                "public class ItemStack { public final net.minecraft.world.level.ItemLike item; public ItemStack(net.minecraft.world.level.ItemLike item) { this.item=item; }}",
                "net.minecraftforge.registries.IForgeRegistry",
                "public interface IForgeRegistry { Object getValue(net.minecraft.resources.ResourceLocation id); }",
                "net.minecraftforge.registries.ForgeRegistries",
                "public class ForgeRegistries { public static final IForgeRegistry ITEMS = id -> new net.minecraft.world.item.Item(id.id); }"
            );
            List<String> compilerArgs = new ArrayList<>(List.of("-source", "17", "-target", "17", "-Xlint:-options"));
            for (var entry : stubs.entrySet()) {
                Path file = work.resolve(entry.getKey().replace('.', '/') + ".java");
                Files.createDirectories(file.getParent());
                Files.writeString(file, "package " + entry.getKey().substring(0, entry.getKey().lastIndexOf('.')) +
                    "; " + entry.getValue());
                compilerArgs.add(file.toString());
            }
            if (ToolProvider.getSystemJavaCompiler().run(null, null, null, compilerArgs.toArray(String[]::new)) != 0) {
                throw new AssertionError("Fixture compiler failed");
            }
            try (var loader = new URLClassLoader(new java.net.URL[]{work.toUri().toURL()}, CoremodTest.class.getClassLoader())) {
                var engine = new NashornScriptEngineFactory().getScriptEngine(new String[0], loader);
                engine.eval(Files.readString(source.resolve("coremods/mob_loot_compat.js")));
                ScriptObjectMirror transforms = (ScriptObjectMirror) engine.eval("initializeCoreMod()");
                ClassNode hurt = read(Path.of(args[1]).resolve("sons_of_sins-2.2.1-forge-1.20.1.jar"),
                    "net/mcreator/sonsofsins/procedures/DamagesHurtProcedure");
                ScriptObjectMirror blood = (ScriptObjectMirror) transforms.get("blood_on_kill_only");
                MethodNode method = target(hurt, blood);
                ((ScriptObjectMirror) blood.get("transformer")).call(null, method);
                Frame<BasicValue>[] frames = new Analyzer<>(new BasicVerifier()).analyze(hurt.name, method);
                int bottles = 0, reachableBottles = 0, preservedSlicing = 0;
                for (int i = 0; i < method.instructions.size(); i++) {
                    AbstractInsnNode insn = method.instructions.get(i);
                    if (insn instanceof FieldInsnNode field && field.name.equals("BOTTLE_OF_BLOOD")) {
                        bottles++;
                        if (frames[i] != null) reachableBottles++;
                    }
                    if (insn instanceof LdcInsnNode ldc && ldc.cst.equals("sons_of_sins:is_slicer") && frames[i] != null) {
                        preservedSlicing++;
                    }
                }
                if (bottles != 1 || reachableBottles != 0 || preservedSlicing != 1) {
                    throw new AssertionError("Native blood must be unreachable; combat/slicing must remain reachable");
                }
                ClassNode death = read(Path.of(args[1]).resolve("sons_of_sins-2.2.1-forge-1.20.1.jar"),
                    "net/mcreator/sonsofsins/procedures/WhenEntityDieProcedure");
                for (MethodNode nativeDeath : death.methods) {
                    for (AbstractInsnNode insn : nativeDeath.instructions) {
                        if (insn instanceof FieldInsnNode field && field.name.equals("BOTTLE_OF_BLOOD")) {
                            throw new AssertionError("Unexpected native death blood path would double sickle extraction");
                        }
                    }
                }
                ClassNode arrow = read(Path.of(args[1]).resolve("supplementaries-1.20-3.1.44-forge.jar"),
                    "net/mehvahdjukaar/supplementaries/common/items/loot/RandomArrowFunction");
                ScriptObjectMirror arrows = (ScriptObjectMirror) transforms.get("obtainable_quiver_arrows");
                MethodNode setup = target(arrow, arrows);
                ((ScriptObjectMirror) arrows.get("transformer")).call(null, setup);
                new Analyzer<>(new BasicVerifier()).analyze(arrow.name, setup);
                ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS | ClassWriter.COMPUTE_FRAMES);
                writer.visit(Opcodes.V17, Opcodes.ACC_PUBLIC, arrow.name, null, "java/lang/Object", null);
                writer.visitField(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "RANDOM_ARROWS", "Ljava/util/List;", null, null).visitEnd();
                setup.accept(writer);
                MethodVisitor init = writer.visitMethod(Opcodes.ACC_STATIC, "<clinit>", "()V", null, null);
                init.visitCode();
                init.visitTypeInsn(Opcodes.NEW, "java/util/ArrayList");
                init.visitInsn(Opcodes.DUP);
                init.visitMethodInsn(Opcodes.INVOKESPECIAL, "java/util/ArrayList", "<init>", "()V", false);
                init.visitFieldInsn(Opcodes.PUTSTATIC, arrow.name, "RANDOM_ARROWS", "Ljava/util/List;");
                init.visitInsn(Opcodes.RETURN);
                init.visitMaxs(0, 0);
                init.visitEnd();
                writer.visitEnd();
                Path fixture = work.resolve(arrow.name + ".class");
                Files.createDirectories(fixture.getParent());
                Files.write(fixture, writer.toByteArray());
                Class<?> actual = loader.loadClass(arrow.name.replace('/', '.'));
                for (int i = 0; i < 2; i++) {
                    actual.getMethod("setup").invoke(null);
                    List<?> list = (List<?>) actual.getField("RANDOM_ARROWS").get(null);
                    if (list.size() != 1) throw new AssertionError("Arrow pool must contain exactly one obtainable item");
                    Object item = list.get(0).getClass().getField("item").get(list.get(0));
                    if (!item.getClass().getField("id").get(item).equals("minecraft:arrow")) {
                        throw new AssertionError("Random quiver arrow must be obtainable");
                    }
                }
            }
            System.out.println("Installed mob loot bytecode verification and arrow execution passed");
        } finally {
            try (var paths = Files.walk(work)) {
                for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(path);
            }
        }
    }

    static ClassNode read(Path jar, String name) throws Exception {
        try (JarFile zip = new JarFile(jar.toFile())) {
            ClassNode node = new ClassNode();
            new ClassReader(zip.getInputStream(zip.getJarEntry(name + ".class")).readAllBytes()).accept(node, 0);
            return node;
        }
    }

    static MethodNode target(ClassNode node, ScriptObjectMirror transform) {
        ScriptObjectMirror target = (ScriptObjectMirror) transform.get("target");
        return node.methods.stream().filter(m -> m.name.equals(target.get("methodName")) &&
            m.desc.equals(target.get("methodDesc"))).findFirst().orElseThrow();
    }
}
