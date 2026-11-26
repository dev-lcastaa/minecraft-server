import java.nio.file.*;
import java.net.URLClassLoader;
import java.util.*;
import java.util.jar.JarFile;
import javax.tools.ToolProvider;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.tree.analysis.*;
import org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory;

class Verify {
    public static void main(String[] args) throws Exception {
        Path root = Path.of(args[0]);
        Path work = root.resolve("tools/hydration-compat/.test-work-" + UUID.randomUUID());
        Path stub = work.resolve("net/minecraftforge/coremod/api/ASMAPI.java");
        Files.createDirectories(stub.getParent());
        try {
            Files.writeString(stub, "package net.minecraftforge.coremod.api; public class ASMAPI { public static String mapMethod(String n) { return n; } public static String mapField(String n) { return n; } }");
            if (ToolProvider.getSystemJavaCompiler().run(null, null, null, "-source", "17", "-target", "17", stub.toString()) != 0)
                throw new AssertionError("Stub compilation failed");
            try (var loader = new URLClassLoader(new java.net.URL[]{work.toUri().toURL()}, Verify.class.getClassLoader())) {
                var engine = new NashornScriptEngineFactory().getScriptEngine(new String[]{"--language=es6"}, loader);
                engine.eval(Files.readString(root.resolve("tools/hydration-compat/coremods/hydration_outputs.js")));
                Object transforms = engine.eval("initializeCoreMod()");
                engine.put("transforms", transforms);
                for (String key : List.of("hydration_pot", "hydration_kettle", "hydration_monster_pot", "hydration_create",
                        "hydration_kettle_pour_use", "hydration_kettle_boil", "hydration_skillet_block", "hydration_skillet_item")) {
                    String jarName = switch (key) {
                        case "hydration_pot" -> "FarmersDelight-1.20.1-1.3.4.jar";
                        case "hydration_monster_pot" -> "forge-dungeonsdelight-1.20.1-1.3.1.jar";
                        case "hydration_create" -> "create-1.20.1-6.0.8.jar";
                        case "hydration_skillet_block", "hydration_skillet_item" -> "FarmersDelight-1.20.1-1.3.4.jar";
                        default -> "farmersrespite-1.20.1-2.1.2.jar";
                    };
                    String cls = engine.eval("transforms." + key + ".target.class").toString();
                    String methodName = engine.eval("transforms." + key + ".target.methodName").toString();
                    String desc = engine.eval("transforms." + key + ".target.methodDesc").toString();
                    ClassNode node = new ClassNode();
                    try (var jar = new JarFile(root.resolve("mods/" + jarName).toFile())) {
                        new ClassReader(jar.getInputStream(jar.getJarEntry(cls.replace('.', '/') + ".class"))).accept(node, 0);
                    }
                    var methods = node.methods.stream().filter(m -> m.name.equals(methodName) && m.desc.equals(desc)).toList();
                    if (methods.size() != 1) throw new AssertionError("Verified hook missing: " + key);
                    MethodNode method = methods.get(0);
                    engine.put("method", method);
                    engine.eval("transforms." + key + ".transformer(method)");
                    method.maxStack += 8;
                    new Analyzer<BasicValue>(new BasicVerifier()).analyze(node.name, method);
                    if (key.equals("hydration_kettle_boil") && Arrays.stream(method.instructions.toArray()).noneMatch(n ->
                            n instanceof MethodInsnNode m && m.owner.equals("serverfixes/hydration/KettleBoil") && m.name.equals("tick")))
                        throw new AssertionError("Kettle boil hook missing");
                    if (key.startsWith("hydration_kettle_pour") || key.equals("hydration_kettle_boil") || key.startsWith("hydration_skillet")) {
                        String marker = key.startsWith("hydration_skillet") ? "thirst" : null;
                        boolean found = Arrays.stream(method.instructions.toArray()).anyMatch(n -> marker != null
                            ? n instanceof LdcInsnNode ldc && marker.equals(ldc.cst)
                            : n instanceof FieldInsnNode f && f.name.equals("f_42589_"));
                        if (!found) throw new AssertionError("Guard missing: " + key);
                        System.out.println(key + ": installed bytecode verified");
                        continue;
                    }
                    long tags = Arrays.stream(method.instructions.toArray())
                        .filter(n -> n instanceof LdcInsnNode ldc && "Purity".equals(ldc.cst)).count();
                    if (tags != (key.equals("hydration_kettle") ? 3 : key.equals("hydration_create") ? 2 : 1))
                        throw new AssertionError("Missing purity writes");
                    long returns = Arrays.stream(method.instructions.toArray())
                        .filter(n -> n.getOpcode() == (key.equals("hydration_kettle") ? Opcodes.IRETURN : Opcodes.ARETURN)).count();
                    if (returns != tags) throw new AssertionError("Changed original return behavior");
                    System.out.println(key + ": installed bytecode verified");
                }
                MethodNode changed = new MethodNode();
                engine.put("method", changed);
                boolean failed = false;
                try { engine.eval("transforms.hydration_kettle.transformer(method)"); }
                catch (javax.script.ScriptException expected) { failed = true; }
                if (!failed) throw new AssertionError("Changed mod methods must fail loudly");
            }
        } finally {
            try (var paths = Files.walk(work)) {
                for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) Files.delete(path);
            }
        }
    }
}
