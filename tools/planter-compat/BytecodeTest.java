import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Set;
import java.util.jar.JarFile;
import javax.script.ScriptEngine;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.tree.analysis.Analyzer;
import org.objectweb.asm.tree.analysis.BasicVerifier;
import org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory;
import org.openjdk.nashorn.api.scripting.ScriptObjectMirror;

/** Applies coremods/planter_compat.js to the installed (SRG) classes and verifies the result. */
class BytecodeTest {
    static final String HELPER = "serverfixes/plantercompat/Compat";

    // args: coremod, forge-client.jar, FarmersDelight, ColdSweat, BWG, planter-compat jar, supplementaries
    public static void main(String[] args) throws Exception {
        ScriptEngine engine = new NashornScriptEngineFactory().getScriptEngine(new String[]{"--language=es6"},
            BytecodeTest.class.getClassLoader(), name -> name.startsWith("org.objectweb.asm."));
        engine.eval(Files.readString(Path.of(args[0])));
        ScriptObjectMirror transforms = (ScriptObjectMirror) engine.eval("initializeCoreMod()");
        Set<String> jars = Set.of(args[1], args[2], args[3], args[4]);
        Set<String> helperMethods = new HashSet<>();
        ClassNode compat = read(args[5], HELPER);
        for (MethodNode m : compat.methods)
            if ((m.access & (Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC)) == (Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC))
                helperMethods.add(m.name + m.desc);
        int applied = 0;
        for (String key : transforms.keySet()) {
            ScriptObjectMirror transform = (ScriptObjectMirror) transforms.get(key);
            ScriptObjectMirror target = (ScriptObjectMirror) transform.get("target");
            String owner = ((String) target.get("class")).replace('.', '/');
            ClassNode node = null;
            for (String jar : jars) {
                node = readOptional(jar, owner);
                if (node != null) break;
            }
            if (node == null) throw new AssertionError("Installed target class missing: " + owner);
            var matches = node.methods.stream().filter(m -> m.name.equals(target.get("methodName"))
                && m.desc.equals(target.get("methodDesc"))).toList();
            if (matches.size() != 1) throw new AssertionError("Installed signature changed: " + owner + "." + target.get("methodName"));
            MethodNode method = matches.get(0);
            AbstractInsnNode[] original = method.instructions.toArray();
            ((ScriptObjectMirror) transform.get("transformer")).call(null, method);
            int calls = 0;
            for (AbstractInsnNode insn : method.instructions)
                if (insn instanceof MethodInsnNode call && call.owner.equals(HELPER)) {
                    if (!helperMethods.contains(call.name + call.desc))
                        throw new AssertionError("Hook calls a helper the packaged jar lacks: " + call.name + call.desc);
                    calls++;
                }
            if (calls != 1) throw new AssertionError("Missing/duplicate helper hook in " + owner);
            for (AbstractInsnNode insn : original)
                if (!method.instructions.contains(insn)) throw new AssertionError("Original behavior removed in " + owner);
            method.maxStack += 4;
            new Analyzer<>(new BasicVerifier()).analyze(node.name, method);
            applied++;
            System.out.println("Transformed and ASM-verified " + owner + "." + method.name);
        }
        if (applied != 5) throw new AssertionError("Expected 5 transforms, got " + applied);

        // Root-cause evidence in the installed, unmodified mods.
        ClassNode richSoil = read(args[2], "vectorwing/farmersdelight/common/block/RichSoilBlock");
        Set<String> converted = new HashSet<>();
        for (AbstractInsnNode insn : method(richSoil, "convertMushroomToColony").instructions)
            if (insn instanceof FieldInsnNode field && field.owner.equals("net/minecraft/world/level/block/Blocks"))
                converted.add(field.name);
        if (!converted.equals(Set.of("f_50072_", "f_50073_")))
            throw new AssertionError("Rich soil now converts more than brown/red mushrooms: " + converted);
        ClassNode colony = read(args[2], "vectorwing/farmersdelight/common/block/MushroomColonyBlock");
        boolean growthTag = false;
        for (AbstractInsnNode insn : method(colony, "m_213897_").instructions)
            if (insn instanceof FieldInsnNode field && field.name.equals("MUSHROOM_COLONY_GROWABLE_ON")) growthTag = true;
        if (!growthTag) throw new AssertionError("Colony growth no longer requires mushroom_colony_growable_on");
        ClassNode planter = read(args[6], "net/mehvahdjukaar/supplementaries/integration/FarmersDelightCompat$PlanterRichBlock");
        boolean delegates = false;
        for (AbstractInsnNode insn : method(planter, "m_213898_").instructions)
            if (insn instanceof MethodInsnNode call && call.name.equals("m_222972_")) delegates = true;
        if (!delegates) throw new AssertionError("Rich planter no longer delegates random ticks to rich soil");
        System.out.println("Planter coremod bytecode tests passed");
    }

    static MethodNode method(ClassNode node, String name) {
        return node.methods.stream().filter(m -> m.name.equals(name)).findFirst().orElseThrow();
    }

    static ClassNode read(String jar, String type) throws Exception {
        ClassNode node = readOptional(jar, type);
        if (node == null) throw new AssertionError(type + " missing from " + jar);
        return node;
    }

    static ClassNode readOptional(String jar, String type) throws Exception {
        try (JarFile file = new JarFile(jar)) {
            var entry = file.getJarEntry(type + ".class");
            if (entry == null) return null;
            try (var stream = file.getInputStream(entry)) {
                ClassNode node = new ClassNode();
                new ClassReader(stream).accept(node, 0);
                return node;
            }
        }
    }
}
