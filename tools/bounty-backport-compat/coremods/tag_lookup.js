function initializeCoreMod() {
  var ASMAPI = Java.type('net.minecraftforge.coremod.api.ASMAPI');
  var O = Java.type('org.objectweb.asm.Opcodes');
  var InsnList = Java.type('org.objectweb.asm.tree.InsnList');
  var InsnNode = Java.type('org.objectweb.asm.tree.InsnNode');
  var VarInsnNode = Java.type('org.objectweb.asm.tree.VarInsnNode');
  var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
  var TypeInsnNode = Java.type('org.objectweb.asm.tree.TypeInsnNode');
  var JumpInsnNode = Java.type('org.objectweb.asm.tree.JumpInsnNode');
  var LabelNode = Java.type('org.objectweb.asm.tree.LabelNode');
  var FrameNode = Java.type('org.objectweb.asm.tree.FrameNode');
  var owner = 'io/ejekta/bountiful/util/ExtMiscKt';
  var targetDesc = '(Lnet/minecraft/core/RegistryAccess;Lnet/minecraft/tags/TagKey;)Ljava/util/List;';
  var toValues = 'getRegistryTags$lambda$10';
  var toValuesDesc = '(Lcom/mojang/datafixers/util/Pair;)Ljava/util/List;';
  function find(classNode, name, desc) {
    for (var i = 0; i < classNode.methods.size(); i++) {
      var method = classNode.methods.get(i);
      if (method.name === name && method.desc === desc) return method;
    }
    return null;
  }
  return {
    registry_tag_lookup: {
      target: { type: 'CLASS', name: owner.replace(/\//g, '.') },
      transformer: function(classNode) {
        var method = find(classNode, 'getRegistryTags', targetDesc);
        if (method === null || find(classNode, toValues, toValuesDesc) === null) {
          ASMAPI.log('WARN', 'Bountiful registry tag lookup not patched: expected methods are missing');
          return classNode;
        }
        // Bountiful scans every registry tag for one key; use the registry's keyed lookup instead.
        var found = new LabelNode();
        var nativeBody = new LabelNode();
        var code = new InsnList();
        code.add(new VarInsnNode(O.ALOAD, 0));
        code.add(new VarInsnNode(O.ALOAD, 1));
        code.add(new MethodInsnNode(O.INVOKEVIRTUAL, 'net/minecraft/tags/TagKey',
          ASMAPI.mapField('f_203867_'), '()Lnet/minecraft/resources/ResourceKey;', false));
        code.add(new MethodInsnNode(O.INVOKEINTERFACE, 'net/minecraft/core/RegistryAccess',
          ASMAPI.mapMethod('m_175515_'), '(Lnet/minecraft/resources/ResourceKey;)Lnet/minecraft/core/Registry;', true));
        code.add(new VarInsnNode(O.ALOAD, 1));
        code.add(new MethodInsnNode(O.INVOKEINTERFACE, 'net/minecraft/core/Registry',
          ASMAPI.mapMethod('m_203431_'), '(Lnet/minecraft/tags/TagKey;)Ljava/util/Optional;', true));
        code.add(new InsnNode(O.ACONST_NULL));
        code.add(new MethodInsnNode(O.INVOKEVIRTUAL, 'java/util/Optional', 'orElse',
          '(Ljava/lang/Object;)Ljava/lang/Object;', false));
        code.add(new InsnNode(O.DUP));
        code.add(new JumpInsnNode(O.IFNONNULL, found));
        code.add(new InsnNode(O.POP));
        code.add(new TypeInsnNode(O.NEW, 'java/util/ArrayList'));
        code.add(new InsnNode(O.DUP));
        code.add(new MethodInsnNode(O.INVOKESPECIAL, 'java/util/ArrayList', '<init>', '()V', false));
        code.add(new InsnNode(O.ARETURN));
        code.add(found);
        code.add(new FrameNode(O.F_SAME1, 0, null, 1, ['java/lang/Object']));
        code.add(new VarInsnNode(O.ALOAD, 1));
        code.add(new InsnNode(O.SWAP));
        code.add(new MethodInsnNode(O.INVOKESTATIC, 'com/mojang/datafixers/util/Pair', 'of',
          '(Ljava/lang/Object;Ljava/lang/Object;)Lcom/mojang/datafixers/util/Pair;', false));
        code.add(new MethodInsnNode(O.INVOKESTATIC, owner, toValues, toValuesDesc, false));
        code.add(new InsnNode(O.ARETURN));
        code.add(nativeBody);
        code.add(new FrameNode(O.F_SAME, 0, null, 0, null));
        method.instructions.insert(code);
        method.maxStack = Math.max(method.maxStack, 3);
        return classNode;
      }
    }
  };
}
