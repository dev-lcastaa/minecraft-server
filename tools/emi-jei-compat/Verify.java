import java.nio.file.*;
import java.util.*;
import java.util.jar.JarFile;
import javax.script.ScriptEngine;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.tree.analysis.*;
import org.openjdk.nashorn.api.scripting.NashornScriptEngineFactory;

/** Applies the coremod to the installed EMI classes and checks the result against the installed JEI API. */
class Verify {
    public static void main(String[] args) throws Exception {
        ScriptEngine engine = new NashornScriptEngineFactory().getScriptEngine("--language=es6");
        engine.eval(Files.readString(Path.of(args[0])));
        engine.put("t", engine.eval("initializeCoreMod()"));
        String emi = args[1], jei = args[2];

        ClassNode util = read(emi, "dev/emi/emi/jemi/JemiUtil");
        MethodNode getStack = util.methods.stream().filter(m -> m.name.equals("getStack")
            && m.desc.equals("(Lmezz/jei/api/ingredients/ITypedIngredient;)Ldev/emi/emi/api/stack/EmiStack;")).findFirst().orElseThrow();
        engine.put("method", getStack);
        engine.eval("t.emi_jei_null_ingredient.transformer(method)");
        if (getStack.instructions.getFirst().getOpcode() != Opcodes.ALOAD) throw new AssertionError("Null guard not first");
        new Analyzer<>(new BasicVerifier()).analyze(util.name, getStack);
        System.out.println("JemiUtil.getStack null guard verified");

        ClassNode slot = read(emi, "dev/emi/emi/jemi/impl/JemiRecipeSlot");
        if (slot.methods.stream().anyMatch(m -> m.name.equals("getAllIngredientsList")))
            throw new AssertionError("Installed EMI already implements getAllIngredientsList; remove this patch");
        engine.put("node", slot);
        engine.eval("t.emi_jei_slot_list.transformer(node)");
        MethodNode added = slot.methods.stream().filter(m -> m.name.equals("getAllIngredientsList")).findFirst().orElseThrow();
        new Analyzer<>(new BasicVerifier()).analyze(slot.name, added);
        if (slot.methods.stream().noneMatch(m -> m.name.equals("getAllIngredients") && m.desc.equals("()Ljava/util/stream/Stream;")))
            throw new AssertionError("EMI getAllIngredients changed");
        ClassNode view = read(jei, "mezz/jei/api/gui/ingredient/IRecipeSlotView");
        MethodNode required = view.methods.stream().filter(m -> m.name.equals("getAllIngredientsList")).findFirst().orElseThrow();
        if (!required.desc.equals(added.desc) || (required.access & Opcodes.ACC_ABSTRACT) == 0)
            throw new AssertionError("JEI getAllIngredientsList signature changed");
        if (!slot.interfaces.contains(view.name)) throw new AssertionError("JemiRecipeSlot no longer implements IRecipeSlotView");
        new ClassWriter(ClassWriter.COMPUTE_MAXS).visitEnd();
        System.out.println("JemiRecipeSlot.getAllIngredientsList verified against installed JEI");
    }

    static ClassNode read(String jar, String type) throws Exception {
        try (JarFile file = new JarFile(jar); var stream = file.getInputStream(file.getJarEntry(type + ".class"))) {
            ClassNode node = new ClassNode();
            new ClassReader(stream).accept(node, 0);
            return node;
        }
    }
}
