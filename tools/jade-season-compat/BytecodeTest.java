import java.nio.file.Files;
import java.nio.file.Path;
import java.util.jar.JarFile;
import javax.script.ScriptEngine;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.tree.analysis.*;
import org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory;

class BytecodeTest {
    public static void main(String[] args) throws Exception {
        ScriptEngine engine = new NashornScriptEngineFactory().getScriptEngine("--language=es6");
        engine.eval(Files.readString(Path.of(args[0])));
        String[][] targets = {
            {args[1], "com/teamtea/eclipticseasons/common/core/crop/CropGrowthHandler", "beforeCropGrowUp",
                "(Lnet/minecraftforge/event/entity/player/BonemealEvent;)V", "season_bonemeal", "bonemeal"},
            {args[1], "com/teamtea/eclipticseasons/common/item/GrowthDetectorItem", "m_6225_",
                "(Lnet/minecraft/world/item/context/UseOnContext;)Lnet/minecraft/world/InteractionResult;",
                "growth_detector", "detect"}
        };
        for (String[] target : targets) {
            ClassNode node = read(target[0], target[1]);
            var matches = node.methods.stream().filter(m -> m.name.equals(target[2]) && m.desc.equals(target[3])).toList();
            if (matches.size() != 1) throw new AssertionError("Installed API signature changed: " + target[2]);
            MethodNode method = matches.get(0);
            AbstractInsnNode[] original = method.instructions.toArray();
            engine.put("method", method);
            engine.eval("initializeCoreMod()." + target[4] + ".transformer(method)");
            int calls = 0;
            for (AbstractInsnNode insn : method.instructions) {
                if (insn instanceof MethodInsnNode call) {
                    if (call.owner.equals("serverfixes/jadeseasons/Compat") && call.name.equals(target[5])) calls++;
                }
            }
            if (calls != 1) throw new AssertionError("Missing/duplicate helper hook");
            for (var insn : original) {
                if (!method.instructions.contains(insn)) throw new AssertionError("Original behavior removed");
            }
            method.maxStack += 8;
            new Analyzer<>(new BasicVerifier()).analyze(node.name, method);
            System.out.println("Transformed and ASM-verified installed " + target[1] + "." + target[2]);
        }
        ClassNode handler = read(args[1], "com/teamtea/eclipticseasons/common/core/crop/CropGrowthHandler");
        ClassNode listener = read(args[1], "com/teamtea/eclipticseasons/common/AllListener");
        MethodNode bonemealListener = listener.methods.stream().filter(m ->
            m.desc.equals("(Lnet/minecraftforge/event/entity/player/BonemealEvent;)V")).findFirst().orElseThrow();
        long nativeGates = 0;
        for (var insn : bonemealListener.instructions)
            if (insn instanceof MethodInsnNode call && call.owner.equals(handler.name)
                && call.name.equals("beforeCropGrowUp")) nativeGates++;
        if (nativeGates != 1) throw new AssertionError("Native bonemeal event dispatch changed");
        for (String crop : new String[]{"TomatoBlock", "RiceBlock"}) {
            ClassNode installedCrop = read(args[2], "vectorwing/farmersdelight/common/block/" + crop);
            MethodNode perform = installedCrop.methods.stream().filter(m -> m.name.equals("m_214148_")).findFirst().orElseThrow();
            boolean writesGrowth = false;
            for (var insn : perform.instructions) {
                if (insn instanceof MethodInsnNode call) {
                    if (call.name.equals("m_46597_")) writesGrowth = true;
                    if (call.name.equals("onCropsGrowPre") || call.name.equals("canExtraCropGrow")
                        || call.owner.startsWith("com/teamtea/eclipticseasons/"))
                        throw new AssertionError("Later native season gate in bonemeal growth: " + crop);
                }
            }
            if (!writesGrowth) throw new AssertionError("Native crop bonemeal no longer writes growth: " + crop);
        }
        System.out.println("Verified successful gate skips the sole Ecliptic bonemeal handler; native tomato/rice bonemeal writes growth without another season gate");
    }
    static ClassNode read(String jar, String type) throws Exception {
        try (JarFile file = new JarFile(jar); var stream = file.getInputStream(file.getJarEntry(type + ".class"))) {
            ClassNode node = new ClassNode();
            new ClassReader(stream).accept(node, 0);
            return node;
        }
    }
}
