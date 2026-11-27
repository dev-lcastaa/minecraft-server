import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.HashSet;
import java.util.Set;
import java.util.jar.JarFile;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.analysis.Analyzer;
import org.objectweb.asm.tree.analysis.BasicVerifier;
import javax.tools.ToolProvider;
import org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory;

class LunarClockCoremodTest {
    // Mirrors CoreModEngine's sandbox in Forge coremods 5.2.4.
    private static final Set<String> ALLOWED_CLASSES = Set.of(
        "net.minecraftforge.coremod.api.ASMAPI", "org.objectweb.asm.Opcodes", "org.objectweb.asm.tree.MethodInsnNode");
    private static final String FORECAST = "dev/corgitaco/enhancedcelestials2core/api/lunarevent/LunarForecast";

    public static void main(String[] args) throws Exception {
        Path directory = Files.createTempDirectory("lunar-clock-coremod-test-");
        try (var loader = new URLClassLoader(new java.net.URL[]{asmapi(directory).toUri().toURL()},
                LunarClockCoremodTest.class.getClassLoader())) {
            run(args, new NashornScriptEngineFactory().getScriptEngine(
                new String[]{"--language=es6"}, loader, ALLOWED_CLASSES::contains));
        } finally {
            try (var paths = Files.walk(directory)) {
                for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(path);
            }
        }
    }

    /** Development names are already SRG names here, as on a production server. */
    private static Path asmapi(Path directory) throws Exception {
        Path source = directory.resolve("net/minecraftforge/coremod/api/ASMAPI.java");
        Files.createDirectories(source.getParent());
        Files.writeString(source, "package net.minecraftforge.coremod.api;\n"
            + "public class ASMAPI { public static String mapMethod(String name) { return name; } }\n");
        var compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null || compiler.run(null, null, null, "-d", directory.toString(), source.toString()) != 0) {
            throw new AssertionError("Could not compile the ASMAPI fixture");
        }
        return directory;
    }

    private static void run(String[] args, javax.script.ScriptEngine engine) throws Exception {
        engine.eval(Files.readString(Path.of(args[0])));
        engine.eval("var transform = initializeCoreMod().seasonal_moon_night");
        if (!FORECAST.replace('/', '.').equals(engine.eval("transform.target.name"))) {
            throw new AssertionError("Coremod targets the wrong class");
        }
        ClassNode node = new ClassNode();
        try (var jar = new JarFile(Path.of(args[1]).toFile())) {
            try (var stream = jar.getInputStream(jar.getJarEntry(FORECAST + ".class"))) {
                new ClassReader(stream).accept(node, 0);
            }
        }
        engine.put("testClass", node);
        engine.eval("transform.transformer(testClass)");

        Set<String> patched = new HashSet<>();
        for (MethodNode method : node.methods) {
            new Analyzer<>(new BasicVerifier()).analyze(node.name, method);
            for (var insn : method.instructions) {
                if (!(insn instanceof MethodInsnNode call)) continue;
                boolean clock = call.owner.equals("net/minecraft/world/level/Level")
                    && (call.name.equals("m_46468_") || call.name.equals("m_8044_"));
                if (clock && !method.name.equals("debugInfo")) throw new AssertionError("Unpatched day time in " + method.name);
                if (call.owner.equals("serverfixes/lunar/LunarClock")) {
                    if (method.name.equals("debugInfo")) throw new AssertionError("Debug info must show the real day time");
                    if (!call.desc.equals("(Lnet/minecraft/world/level/Level;)J")) throw new AssertionError("Bad descriptor");
                    patched.add(method.name);
                }
            }
        }
        for (String method : Set.of("buildSchedule", "setLunarEventTonight", "insertLunarEvent", "getBlend",
                "currentLunarEventOrDefault", "lastLunarEventHolder", "getNextScheduledLunarEvent")) {
            if (!patched.contains(method)) throw new AssertionError(method + " must use the seasonal clock");
        }
        try {
            engine.eval("transform.transformer(testClass)");
            throw new AssertionError("A changed LunarForecast must be rejected");
        } catch (javax.script.ScriptException expected) {
            if (!expected.getMessage().contains("LunarForecast changed")) throw expected;
        }
        System.out.println("Seasonal moon night coremod tests passed");
    }
}
