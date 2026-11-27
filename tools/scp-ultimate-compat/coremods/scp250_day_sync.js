function initializeCoreMod() {
  var ASMAPI = Java.type('net.minecraftforge.coremod.api.ASMAPI');
  var O = Java.type('org.objectweb.asm.Opcodes');
  var InsnList = Java.type('org.objectweb.asm.tree.InsnList');
  var InsnNode = Java.type('org.objectweb.asm.tree.InsnNode');
  var VarInsnNode = Java.type('org.objectweb.asm.tree.VarInsnNode');
  var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
  var FieldInsnNode = Java.type('org.objectweb.asm.tree.FieldInsnNode');
  var TypeInsnNode = Java.type('org.objectweb.asm.tree.TypeInsnNode');
  var JumpInsnNode = Java.type('org.objectweb.asm.tree.JumpInsnNode');
  var LabelNode = Java.type('org.objectweb.asm.tree.LabelNode');
  var level = 'net/minecraft/world/level/Level';
  var accessor = 'net/minecraft/world/level/LevelAccessor';
  var vars = 'net/mcreator/scpultimate/network/ScpUltimateModVariables$MapVariables';
  var isDay = ASMAPI.mapMethod('m_46461_');
  return {
    scp250_day_sync: {
      target: {type: 'METHOD', class: 'net.mcreator.scpultimate.procedures.Scp250worldProcedure',
        methodName: 'execute', methodDesc: '(Lnet/minecraftforge/eventbus/api/Event;L' + accessor + ';)V'},
      transformer: function(method) {
        var dirty = 0;
        var dayChecks = 0;
        for (var i = 0; i < method.instructions.size(); i++) {
          var node = method.instructions.get(i);
          if (node instanceof MethodInsnNode && node.owner === vars && node.name === 'markSyncDirty') dirty++;
          if (node instanceof MethodInsnNode && node.name === isDay) dayChecks++;
        }
        if (dirty !== 2 || dayChecks !== 1) throw new Error('SCP-250 world procedure changed; review this patch');
        // MapVariables is shared by every dimension and markSyncDirty broadcasts it to all players at the
        // end of each dimension tick. On the server, follow only the overworld and sync actual changes.
        var original = new LabelNode();
        var done = new LabelNode();
        var data = method.maxLocals;
        var day = data + 1;
        var patch = new InsnList();
        patch.add(new VarInsnNode(O.ALOAD, 1));
        patch.add(new TypeInsnNode(O.INSTANCEOF, 'net/minecraft/server/level/ServerLevel'));
        patch.add(new JumpInsnNode(O.IFEQ, original));
        patch.add(new VarInsnNode(O.ALOAD, 1));
        patch.add(new TypeInsnNode(O.CHECKCAST, level));
        patch.add(new MethodInsnNode(O.INVOKEVIRTUAL, level, ASMAPI.mapMethod('m_46472_'),
          '()Lnet/minecraft/resources/ResourceKey;', false));
        patch.add(new FieldInsnNode(O.GETSTATIC, level, ASMAPI.mapField('f_46428_'),
          'Lnet/minecraft/resources/ResourceKey;'));
        patch.add(new JumpInsnNode(O.IF_ACMPNE, done));
        patch.add(new VarInsnNode(O.ALOAD, 1));
        patch.add(new MethodInsnNode(O.INVOKESTATIC, vars, 'get', '(L' + accessor + ';)L' + vars + ';', false));
        patch.add(new VarInsnNode(O.ASTORE, data));
        patch.add(new VarInsnNode(O.ALOAD, 1));
        patch.add(new TypeInsnNode(O.CHECKCAST, level));
        patch.add(new MethodInsnNode(O.INVOKEVIRTUAL, level, isDay, '()Z', false));
        patch.add(new VarInsnNode(O.ISTORE, day));
        patch.add(new VarInsnNode(O.ALOAD, data));
        patch.add(new FieldInsnNode(O.GETFIELD, vars, 'scp250logic1', 'Z'));
        patch.add(new VarInsnNode(O.ILOAD, day));
        patch.add(new JumpInsnNode(O.IF_ICMPEQ, done));
        patch.add(new VarInsnNode(O.ALOAD, data));
        patch.add(new VarInsnNode(O.ILOAD, day));
        patch.add(new FieldInsnNode(O.PUTFIELD, vars, 'scp250logic1', 'Z'));
        patch.add(new VarInsnNode(O.ALOAD, data));
        patch.add(new MethodInsnNode(O.INVOKEVIRTUAL, vars, 'markSyncDirty', '()V', false));
        patch.add(done);
        patch.add(new InsnNode(O.RETURN));
        patch.add(original);
        method.instructions.insert(patch);
        method.maxLocals = day + 1;
        method.maxStack = Math.max(method.maxStack, 2);
        return method;
      }
    }
  };
}
