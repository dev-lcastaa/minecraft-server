import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;

public class RegistryAudit {
    static final Map<String, String[]> EXTERNAL_NAMESPACES = Map.of(
        "com/lion/graveyard/init/TGEntities",
        new String[]{"graveyard", "com/lion/graveyard/platform/forge/RegistryHelperImpl"},
        "com/teamabnormals/endergetic/core/registry/EEEntityTypes",
        new String[]{"endergetic", "com/teamabnormals/endergetic/core/EndergeticExpansion"},
        "com/lgow/endofherobrine/entity/EntityInit",
        new String[]{"endofherobrine", "com/lgow/endofherobrine/registries/ModRegistries"}
    );
    public static void main(String[] args) throws Exception {
        for (Path jar : Files.list(Path.of(args[0])).filter(p -> p.toString().endsWith(".jar")).sorted().toList()) {
            try (ZipFile zip = new ZipFile(jar.toFile())) {
                for (var entry : Collections.list(zip.entries())) {
                    if (!entry.getName().endsWith(".class")) continue;
                    byte[] bytes = zip.getInputStream(entry).readAllBytes();
                    String raw = new String(bytes, java.nio.charset.StandardCharsets.ISO_8859_1);
                    ClassNode node = new ClassNode();
                    new ClassReader(bytes).accept(node, ClassReader.SKIP_DEBUG | ClassReader.SKIP_FRAMES);
                    System.out.println("H\t" + node.name.replace('/', '.') + "\t" +
                        String.valueOf(node.superName).replace('/', '.') + "\t" +
                        String.join(",", node.interfaces).replace('/', '.'));
                    for (MethodNode method : node.methods) {
                        if (!method.desc.equals("()Lnet/minecraft/world/entity/MobType;")) continue;
                        for (AbstractInsnNode insn : method.instructions) {
                            if (insn instanceof FieldInsnNode field && field.owner.equals("net/minecraft/world/entity/MobType")) {
                                System.out.println("M\t" + node.name.replace('/', '.') + "\t" + field.name);
                            }
                        }
                    }
                    if (node.name.contains("Entity") || node.name.endsWith("Renderer")) {
                        Set<String> strings = new TreeSet<>();
                        for (MethodNode method : node.methods) {
                            for (AbstractInsnNode insn : method.instructions) {
                                if (insn instanceof LdcInsnNode ldc && ldc.cst instanceof String s) strings.add(s.replace('\t', ' '));
                            }
                        }
                        if (!strings.isEmpty()) System.out.println("S\t" + node.name.replace('/', '.') + "\t" + String.join("\t", strings));
                    }
                    if (node.name.contains("/client/model/") || node.name.contains("/entity/model/") || node.name.endsWith("Model")) {
                        Set<String> labels = new TreeSet<>();
                        for (FieldNode field : node.fields) {
                            if (field.desc.endsWith("/ModelPart;") || field.desc.endsWith("/AdvancedModelBox;")) labels.add(field.name);
                        }
                        for (MethodNode method : node.methods) {
                            for (AbstractInsnNode insn : method.instructions) {
                                if (insn instanceof LdcInsnNode ldc && ldc.cst instanceof String label) labels.add(label);
                            }
                        }
                        System.out.println("G\t" + node.name.replace('/', '.') + "\t" + String.join(",", labels));
                    }
                    if (node.name.contains("/renderer/") || node.name.contains("/render/") || node.name.contains("Renderer")) {
                        Set<String> models = new TreeSet<>();
                        for (MethodNode method : node.methods) {
                            for (AbstractInsnNode insn : method.instructions) {
                                if (insn instanceof TypeInsnNode type && type.getOpcode() == Opcodes.NEW &&
                                    type.desc.toLowerCase().contains("model")) models.add(type.desc.replace('/', '.'));
                                if (insn instanceof FieldInsnNode field && field.owner.contains("/model/")) models.add(field.owner.replace('/', '.'));
                            }
                        }
                        if (!models.isEmpty()) System.out.println("V\t" + node.name.replace('/', '.') + "\t" +
                            String.valueOf(node.signature).replace('/', '.') + "\t" + String.join(",", models));
                    }
                    if (!raw.contains("EntityType") || !(raw.contains("DeferredRegister") ||
                        raw.contains("ResourcefulRegistry") || raw.contains("EntityRegistry") ||
                        EXTERNAL_NAMESPACES.containsKey(node.name))) continue;
                    String namespace = null;
                    if (EXTERNAL_NAMESPACES.containsKey(node.name)) {
                        String[] binding = EXTERNAL_NAMESPACES.get(node.name);
                        ClassNode backing = new ClassNode();
                        new ClassReader(zip.getInputStream(zip.getEntry(binding[1] + ".class")).readAllBytes()).accept(backing, 0);
                        boolean verified = backing.methods.stream().filter(m -> m.name.equals("<clinit>"))
                            .anyMatch(m -> Arrays.stream(m.instructions.toArray()).anyMatch(i ->
                                i instanceof LdcInsnNode ldc && binding[0].equals(ldc.cst)));
                        if (!verified) throw new IllegalStateException("External namespace binding changed: " + node.name);
                        namespace = binding[0];
                    }
                    for (MethodNode method : node.methods) {
                        if (!method.name.equals("<clinit>")) continue;
                        for (AbstractInsnNode insn : method.instructions) {
                            if (!(insn instanceof MethodInsnNode call)) continue;
                            if (((call.owner.contains("Registr") || call.owner.endsWith("DeferredRegister")) && call.name.equals("create")) ||
                                (call.owner.endsWith("EntityRegistry") && call.name.equals("<init>"))) {
                                for (AbstractInsnNode prev = insn.getPrevious(); prev != null; prev = prev.getPrevious()) {
                                    if (prev instanceof LdcInsnNode ldc && ldc.cst instanceof String s) {
                                        if (s.matches("[a-z][a-z0-9_]*")) namespace = s;
                                        break;
                                    }
                                    if (prev instanceof MethodInsnNode || prev.getOpcode() == Opcodes.PUTSTATIC) break;
                                }
                            }
                            if (namespace == null || !(call.name.startsWith("register") || call.name.equals("reg") ||
                                call.name.equals("entity") || call.name.equals("createLivingEntity")) ||
                                    !call.desc.startsWith("(Ljava/lang/String;")) continue;
                            String id = null;
                            Set<String> types = new TreeSet<>();
                            for (AbstractInsnNode prev = insn.getPrevious(); prev != null; prev = prev.getPrevious()) {
                                if (prev.getOpcode() == Opcodes.PUTSTATIC || prev.getOpcode() == Opcodes.RETURN) break;
                                if (prev instanceof InvokeDynamicInsnNode supplier) inspect(node, supplier, types, new HashSet<>());
                                if (prev instanceof LdcInsnNode ldc && ldc.cst instanceof String s) {
                                    id = s;
                                    break;
                                }
                            }
                            if (id == null) continue;
                            for (String type : types) {
                                System.out.println("R\t" + namespace + ":" + id + "\t" + type.replace('/', '.') +
                                    "\t" + jar.getFileName() + "\t" + node.name.replace('/', '.'));
                            }
                        }
                    }
                }
            }
        }
    }

    static void inspect(ClassNode node, InvokeDynamicInsnNode dyn, Set<String> types, Set<String> seen) {
        for (Object arg : dyn.bsmArgs) {
            if (!(arg instanceof Handle handle)) continue;
            if (handle.getName().equals("<init>")) {
                types.add(handle.getOwner());
            } else if (handle.getOwner().equals(node.name) && seen.add(handle.getName())) {
                for (MethodNode method : node.methods) {
                    if (!method.name.equals(handle.getName())) continue;
                    for (AbstractInsnNode insn : method.instructions) {
                        if (insn instanceof InvokeDynamicInsnNode child) inspect(node, child, types, seen);
                        if (insn instanceof TypeInsnNode type && type.getOpcode() == Opcodes.NEW) types.add(type.desc);
                    }
                }
            }
        }
    }
}
