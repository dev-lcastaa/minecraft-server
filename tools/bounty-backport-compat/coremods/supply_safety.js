function initializeCoreMod() {
  var ASMAPI = Java.type('net.minecraftforge.coremod.api.ASMAPI');
  var O = Java.type('org.objectweb.asm.Opcodes');
  var InsnList = Java.type('org.objectweb.asm.tree.InsnList');
  var InsnNode = Java.type('org.objectweb.asm.tree.InsnNode');
  var VarInsnNode = Java.type('org.objectweb.asm.tree.VarInsnNode');
  var FieldInsnNode = Java.type('org.objectweb.asm.tree.FieldInsnNode');
  var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
  var TypeInsnNode = Java.type('org.objectweb.asm.tree.TypeInsnNode');
  var LdcInsnNode = Java.type('org.objectweb.asm.tree.LdcInsnNode');
  var JumpInsnNode = Java.type('org.objectweb.asm.tree.JumpInsnNode');
  var LabelNode = Java.type('org.objectweb.asm.tree.LabelNode');
  var FrameNode = Java.type('org.objectweb.asm.tree.FrameNode');
  var owner = 'io/ejekta/bountiful/data/PoolEntry';
  return {
    supply_state_safety: {
      target: {
        type: 'METHOD', class: owner.replace(/\//g, '.'),
        methodName: 'isValid', methodDesc: '(Lnet/minecraft/server/MinecraftServer;)Z'
      },
      transformer: function(method) {
        var nativePath = new LabelNode();
        var blockPath = new LabelNode();
        var code = new InsnList();
        code.add(new VarInsnNode(O.ALOAD, 0));
        code.add(new FieldInsnNode(O.GETFIELD, owner, 'id', 'Ljava/lang/String;'));
        code.add(new JumpInsnNode(O.IFNULL, nativePath));
        code.add(new VarInsnNode(O.ALOAD, 0));
        code.add(new FieldInsnNode(O.GETFIELD, owner, 'id', 'Ljava/lang/String;'));
        code.add(new LdcInsnNode('bounty_backport_compat_'));
        code.add(new MethodInsnNode(O.INVOKEVIRTUAL, 'java/lang/String', 'contains', '(Ljava/lang/CharSequence;)Z', false));
        code.add(new JumpInsnNode(O.IFEQ, nativePath));
        code.add(new VarInsnNode(O.ALOAD, 0));
        code.add(new FieldInsnNode(O.GETFIELD, owner, 'type', 'Lnet/minecraft/resources/ResourceLocation;'));
        code.add(new MethodInsnNode(O.INVOKEVIRTUAL, 'java/lang/Object', 'toString', '()Ljava/lang/String;', false));
        code.add(new LdcInsnNode(':item'));
        code.add(new MethodInsnNode(O.INVOKEVIRTUAL, 'java/lang/String', 'endsWith', '(Ljava/lang/String;)Z', false));
        code.add(new JumpInsnNode(O.IFEQ, nativePath));
        code.add(new FieldInsnNode(O.GETSTATIC, 'net/minecraftforge/registries/ForgeRegistries',
          'ITEMS', 'Lnet/minecraftforge/registries/IForgeRegistry;'));
        code.add(new TypeInsnNode(O.NEW, 'net/minecraft/resources/ResourceLocation'));
        code.add(new InsnNode(O.DUP));
        code.add(new VarInsnNode(O.ALOAD, 0));
        code.add(new FieldInsnNode(O.GETFIELD, owner, 'content', 'Ljava/lang/String;'));
        code.add(new MethodInsnNode(O.INVOKESPECIAL, 'net/minecraft/resources/ResourceLocation',
          '<init>', '(Ljava/lang/String;)V', false));
        code.add(new MethodInsnNode(O.INVOKEINTERFACE, 'net/minecraftforge/registries/IForgeRegistry',
          'getValue', '(Lnet/minecraft/resources/ResourceLocation;)Ljava/lang/Object;', true));
        code.add(new InsnNode(O.DUP));
        code.add(new TypeInsnNode(O.INSTANCEOF, 'net/minecraft/world/item/BlockItem'));
        code.add(new JumpInsnNode(O.IFNE, blockPath));
        code.add(new InsnNode(O.POP));
        code.add(new JumpInsnNode(O.GOTO, nativePath));
        code.add(blockPath);
        code.add(new FrameNode(O.F_SAME1, 0, null, 1, ['java/lang/Object']));
        code.add(new TypeInsnNode(O.CHECKCAST, 'net/minecraft/world/item/BlockItem'));
        code.add(new MethodInsnNode(O.INVOKEVIRTUAL, 'net/minecraft/world/item/BlockItem',
          ASMAPI.mapMethod('m_40614_'), '()Lnet/minecraft/world/level/block/Block;', false));
        code.add(new TypeInsnNode(O.INSTANCEOF, 'net/minecraft/world/level/block/EntityBlock'));
        code.add(new JumpInsnNode(O.IFEQ, nativePath));
        code.add(new InsnNode(O.ICONST_0));
        code.add(new InsnNode(O.IRETURN));
        code.add(nativePath);
        code.add(new FrameNode(O.F_SAME, 0, null, 0, null));
        method.instructions.insert(code);
        method.maxStack = Math.max(method.maxStack, 5);
        return method;
      }
    }
  };
}
