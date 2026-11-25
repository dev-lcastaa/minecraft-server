function initializeCoreMod() {
  var ASMAPI = Java.type('net.minecraftforge.coremod.api.ASMAPI');
  var O = Java.type('org.objectweb.asm.Opcodes');
  var InsnList = Java.type('org.objectweb.asm.tree.InsnList');
  var InsnNode = Java.type('org.objectweb.asm.tree.InsnNode');
  var JumpInsnNode = Java.type('org.objectweb.asm.tree.JumpInsnNode');
  var FieldInsnNode = Java.type('org.objectweb.asm.tree.FieldInsnNode');
  var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
  var TypeInsnNode = Java.type('org.objectweb.asm.tree.TypeInsnNode');
  var LdcInsnNode = Java.type('org.objectweb.asm.tree.LdcInsnNode');
  return {
    blood_on_kill_only: {
      target: {
        type: 'METHOD',
        class: 'net.mcreator.sonsofsins.procedures.DamagesHurtProcedure',
        methodName: 'execute',
        methodDesc: '(Lnet/minecraftforge/eventbus/api/Event;Lnet/minecraft/world/level/LevelAccessor;DDDLnet/minecraft/world/entity/Entity;Lnet/minecraft/world/entity/Entity;D)V'
      },
      transformer: function(method) {
        var matches = 0;
        for (var insn = method.instructions.getFirst(); insn !== null; insn = insn.getNext()) {
          if (insn instanceof MethodInsnNode && insn.owner === 'net/minecraft/world/entity/player/Inventory' &&
              insn.name === ASMAPI.mapMethod('m_36063_')) {
            var branch = insn.getNext();
            while (branch !== null && branch.getOpcode() < 0) branch = branch.getNext();
            if (!(branch instanceof JumpInsnNode) || branch.getOpcode() !== O.IFEQ) {
              throw new Error('Mob loot compatibility: unexpected blood inventory branch');
            }
            // Skip only the native blood exchange, leaving slicing, combat and other hurt effects intact.
            var patch = new InsnList();
            patch.add(new InsnNode(O.POP));
            patch.add(new JumpInsnNode(O.GOTO, branch.label));
            method.instructions.insertBefore(branch, patch);
            method.instructions.remove(branch);
            matches++;
          }
        }
        if (matches !== 1) throw new Error('Mob loot compatibility: blood branch count ' + matches);
        return method;
      }
    },
    obtainable_quiver_arrows: {
      target: {
        type: 'METHOD',
        class: 'net.mehvahdjukaar.supplementaries.common.items.loot.RandomArrowFunction',
        methodName: 'setup',
        methodDesc: '()V'
      },
      transformer: function(method) {
        var owner = 'net/mehvahdjukaar/supplementaries/common/items/loot/RandomArrowFunction';
        var patch = new InsnList();
        patch.add(new FieldInsnNode(O.GETSTATIC, owner, 'RANDOM_ARROWS', 'Ljava/util/List;'));
        patch.add(new MethodInsnNode(O.INVOKEINTERFACE, 'java/util/List', 'clear', '()V', true));
        patch.add(new FieldInsnNode(O.GETSTATIC, owner, 'RANDOM_ARROWS', 'Ljava/util/List;'));
        patch.add(new TypeInsnNode(O.NEW, 'net/minecraft/world/item/ItemStack'));
        patch.add(new InsnNode(O.DUP));
        patch.add(new FieldInsnNode(O.GETSTATIC, 'net/minecraftforge/registries/ForgeRegistries', 'ITEMS',
          'Lnet/minecraftforge/registries/IForgeRegistry;'));
        patch.add(new TypeInsnNode(O.NEW, 'net/minecraft/resources/ResourceLocation'));
        patch.add(new InsnNode(O.DUP));
        patch.add(new LdcInsnNode('minecraft:arrow'));
        patch.add(new MethodInsnNode(O.INVOKESPECIAL, 'net/minecraft/resources/ResourceLocation', '<init>',
          '(Ljava/lang/String;)V', false));
        patch.add(new MethodInsnNode(O.INVOKEINTERFACE, 'net/minecraftforge/registries/IForgeRegistry',
          'getValue', '(Lnet/minecraft/resources/ResourceLocation;)Ljava/lang/Object;', true));
        patch.add(new TypeInsnNode(O.CHECKCAST, 'net/minecraft/world/level/ItemLike'));
        patch.add(new MethodInsnNode(O.INVOKESPECIAL, 'net/minecraft/world/item/ItemStack', '<init>',
          '(Lnet/minecraft/world/level/ItemLike;)V', false));
        patch.add(new MethodInsnNode(O.INVOKEINTERFACE, 'java/util/List', 'add', '(Ljava/lang/Object;)Z', true));
        patch.add(new InsnNode(O.POP));
        patch.add(new InsnNode(O.RETURN));
        method.instructions.clear();
        method.tryCatchBlocks.clear();
        if (method.localVariables !== null) method.localVariables.clear();
        method.instructions.add(patch);
        method.maxStack = Math.max(method.maxStack, 7);
        return method;
      }
    }
  };
}
