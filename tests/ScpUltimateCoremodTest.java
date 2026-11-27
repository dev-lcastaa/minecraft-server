import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Map;
import java.util.Set;
import java.util.jar.JarFile;
import javax.tools.ToolProvider;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.analysis.Analyzer;
import org.objectweb.asm.tree.analysis.BasicVerifier;
import org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory;

class ScpUltimateCoremodTest {
    // Mirrors CoreModEngine's sandbox in Forge coremods 5.2.4.
    private static final Set<String> ALLOWED_CLASSES = Set.of(
        "net.minecraftforge.coremod.api.ASMAPI", "org.objectweb.asm.Opcodes",
        "org.objectweb.asm.tree.FieldInsnNode", "org.objectweb.asm.tree.InsnList",
        "org.objectweb.asm.tree.InsnNode", "org.objectweb.asm.tree.JumpInsnNode",
        "org.objectweb.asm.tree.LabelNode", "org.objectweb.asm.tree.MethodInsnNode",
        "org.objectweb.asm.tree.TypeInsnNode", "org.objectweb.asm.tree.VarInsnNode");
    private static final String PROCEDURE = "net/mcreator/scpultimate/procedures/Scp250worldProcedure";

    public static void main(String[] args) throws Exception {
        Path directory = Files.createTempDirectory("scp-ultimate-bytecode-test-");
        try {
            fixtures(directory);
            try (var loader = new URLClassLoader(new java.net.URL[]{directory.toUri().toURL()},
                    ScpUltimateCoremodTest.class.getClassLoader())) {
                var engine = new NashornScriptEngineFactory().getScriptEngine(
                    new String[]{"--language=es6"}, loader, ALLOWED_CLASSES::contains);
                engine.eval(Files.readString(Path.of(args[0])));
                engine.eval("var transform = initializeCoreMod().scp250_day_sync");
                ClassNode node = new ClassNode();
                try (var jar = new JarFile(Path.of(args[1]).toFile())) {
                    try (var stream = jar.getInputStream(jar.getJarEntry(PROCEDURE + ".class"))) {
                        new ClassReader(stream).accept(node, 0);
                    }
                }
                var targets = node.methods.stream().filter(m -> m.name.equals(eval(engine, "transform.target.methodName"))
                    && m.desc.equals(eval(engine, "transform.target.methodDesc"))).toList();
                if (targets.size() != 1) throw new AssertionError("Installed SCP-250 procedure target changed");
                MethodNode method = targets.get(0);
                engine.put("testMethod", method);
                engine.eval("transform.transformer(testMethod)");
                new Analyzer<>(new BasicVerifier()).analyze(node.name, method);
                try {
                    engine.eval("transform.transformer(testMethod)");
                    throw new AssertionError("A changed procedure must be rejected");
                } catch (javax.script.ScriptException expected) {
                    if (!expected.getMessage().contains("procedure changed")) throw expected;
                }
                ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_FRAMES) {
                    @Override protected ClassLoader getClassLoader() { return loader; }
                };
                node.accept(writer);
                Path output = directory.resolve(PROCEDURE + ".class");
                Files.createDirectories(output.getParent());
                Files.write(output, writer.toByteArray());
                scenarios(loader);
            }
            System.out.println("SCP Ultimate installed-bytecode sync tests passed");
        } finally {
            try (var paths = Files.walk(directory)) {
                for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(path);
            }
        }
    }

    private static String eval(javax.script.ScriptEngine engine, String script) {
        try {
            return (String)engine.eval(script);
        } catch (javax.script.ScriptException e) {
            throw new RuntimeException(e);
        }
    }

    private static void scenarios(ClassLoader loader) throws Exception {
        Class<?> keyClass = loader.loadClass("net.minecraft.resources.ResourceKey");
        Class<?> levelClass = loader.loadClass("net.minecraft.world.level.Level");
        Class<?> serverClass = loader.loadClass("net.minecraft.server.level.ServerLevel");
        Class<?> vars = loader.loadClass("net.mcreator.scpultimate.network.ScpUltimateModVariables$MapVariables");
        var execute = loader.loadClass(PROCEDURE.replace('/', '.'))
            .getMethod("execute", loader.loadClass("net.minecraft.world.level.LevelAccessor"));
        Object overworld = levelClass.getField("f_46428_").get(null);
        Object nether = keyClass.getConstructor(String.class).newInstance("the_nether");
        var serverLevel = serverClass.getConstructor(keyClass, boolean.class);
        var clientLevel = levelClass.getConstructor(keyClass, boolean.class);
        Object server = vars.getField("SERVER").get(null);
        Object client = vars.getField("CLIENT").get(null);
        var flag = vars.getField("scp250logic1");
        var dirty = vars.getField("dirty");

        Object day = serverLevel.newInstance(overworld, true);
        for (int i = 0; i < 20; i++) execute.invoke(null, day);
        check(flag.getBoolean(server) && dirty.getInt(server) == 1, "Overworld day must sync once");
        for (int i = 0; i < 20; i++) execute.invoke(null, serverLevel.newInstance(nether, false));
        check(flag.getBoolean(server) && dirty.getInt(server) == 1, "Other dimensions must not flip or resync");
        execute.invoke(null, serverLevel.newInstance(overworld, false));
        execute.invoke(null, serverLevel.newInstance(overworld, false));
        check(!flag.getBoolean(server) && dirty.getInt(server) == 2, "Overworld nightfall must sync once");

        Object clientDay = clientLevel.newInstance(nether, true);
        execute.invoke(null, clientDay);
        execute.invoke(null, clientDay);
        check(flag.getBoolean(client) && dirty.getInt(client) == 2, "Client-side behavior must be unchanged");
        check(dirty.getInt(server) == 2, "Client ticks must not touch server variables");
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static void fixtures(Path directory) throws Exception {
        var sources = new ArrayList<String>(java.util.List.of("-source", "17", "-target", "17", "-d", directory.toString()));
        Map<String, String> fixtures = Map.of(
            "net.minecraftforge.coremod.api.ASMAPI", """
                public class ASMAPI {
                    public static String mapMethod(String name) { return name; }
                    public static String mapField(String name) { return name; }
                }
                """,
            "net.minecraft.resources.ResourceKey", """
                public class ResourceKey {
                    public final String id;
                    public ResourceKey(String id) { this.id = id; }
                }
                """,
            "net.minecraft.world.level.LevelAccessor", "public interface LevelAccessor {}",
            "net.minecraft.world.level.Level", """
                public class Level implements LevelAccessor {
                    public static final net.minecraft.resources.ResourceKey f_46428_ =
                        new net.minecraft.resources.ResourceKey("overworld");
                    private final net.minecraft.resources.ResourceKey dimension;
                    private final boolean day;
                    public Level(net.minecraft.resources.ResourceKey dimension, boolean day) {
                        this.dimension = dimension;
                        this.day = day;
                    }
                    public net.minecraft.resources.ResourceKey m_46472_() { return dimension; }
                    public boolean m_46461_() { return day; }
                }
                """,
            "net.minecraft.server.level.ServerLevel", """
                public class ServerLevel extends net.minecraft.world.level.Level {
                    public ServerLevel(net.minecraft.resources.ResourceKey dimension, boolean day) {
                        super(dimension, day);
                    }
                }
                """,
            "net.minecraftforge.eventbus.api.Event", "public class Event {}",
            "net.minecraftforge.event.TickEvent", """
                public class TickEvent extends net.minecraftforge.eventbus.api.Event {
                    public enum Phase { START, END }
                    public Phase phase;
                    public static class LevelTickEvent extends TickEvent {
                        public net.minecraft.world.level.Level level;
                    }
                }
                """,
            "net.mcreator.scpultimate.network.ScpUltimateModVariables", """
                public class ScpUltimateModVariables {
                    public static class MapVariables {
                        public static final MapVariables SERVER = new MapVariables();
                        public static final MapVariables CLIENT = new MapVariables();
                        public boolean scp250logic1;
                        public int dirty;
                        public static MapVariables get(net.minecraft.world.level.LevelAccessor world) {
                            return world instanceof net.minecraft.server.level.ServerLevel ? SERVER : CLIENT;
                        }
                        public void markSyncDirty() { dirty++; }
                    }
                }
                """
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
