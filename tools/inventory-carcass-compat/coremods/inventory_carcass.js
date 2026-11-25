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
  var MethodNode = Java.type('org.objectweb.asm.tree.MethodNode');
  var probe = 'net/serverfixes/inventory/CarryOnPermissionProbeEvent';
  var breakEvent = 'net/minecraftforge/event/level/BlockEvent$BreakEvent';
  var handler = 'dev/fallingcloud/betterinventory/inv/handler/';
  var result = {
    carry_permission_probe: {
      target: {type: 'METHOD', class: 'tschipp.carryon.events.CommonEvents',
        methodName: 'lambda$onBlockClick$0',
        methodDesc: '(Lnet/minecraft/world/level/Level;Lnet/minecraft/world/entity/player/Player;Lnet/minecraft/world/level/block/state/BlockState;Lnet/minecraft/core/BlockPos;)Ljava/lang/Boolean;'},
      transformer: function(method) {
        var allocations = 0;
        var constructors = 0;
        for (var i = 0; i < method.instructions.size(); i++) {
          var node = method.instructions.get(i);
          if (node instanceof TypeInsnNode && node.getOpcode() === O.NEW && node.desc === breakEvent) {
            node.desc = probe;
            allocations++;
          }
          if (node instanceof MethodInsnNode && node.owner === breakEvent && node.name === '<init>') {
            node.owner = probe;
            constructors++;
          }
        }
        if (allocations !== 1 || constructors !== 1) throw new Error('Carry On permission callback changed');
        return method;
      }
    },
    inventory_slot_dirty: {
      target: {type: 'CLASS', name: 'dev.fallingcloud.betterinventory.inv.handler.SlotItemHandler'},
      transformer: function(clazz) {
        var name = ASMAPI.mapMethod('m_6654_');
        for (var i = 0; i < clazz.methods.size(); i++) {
          if (clazz.methods.get(i).name === name && clazz.methods.get(i).desc === '()V') {
            throw new Error('Better Inventory now implements Slot.setChanged; review this compatibility patch');
          }
        }
        // Slot's empty-container notification misses in-place stack mutations (partial shift-click).
        // Use the modifiable handler API so PageView delegates to writeBack and its native dirty listener.
        var method = new MethodNode(O.ACC_PUBLIC, name, '()V', null, null);
        var end = new LabelNode();
        method.instructions.add(new VarInsnNode(O.ALOAD, 0));
        method.instructions.add(new MethodInsnNode(O.INVOKEVIRTUAL, handler + 'SlotItemHandler',
          'getItemHandler', '()L' + handler + 'IItemHandler;', false));
        method.instructions.add(new VarInsnNode(O.ASTORE, 1));
        method.instructions.add(new VarInsnNode(O.ALOAD, 1));
        method.instructions.add(new TypeInsnNode(O.INSTANCEOF, handler + 'IItemHandlerModifiable'));
        method.instructions.add(new JumpInsnNode(O.IFEQ, end));
        method.instructions.add(new VarInsnNode(O.ALOAD, 1));
        method.instructions.add(new TypeInsnNode(O.CHECKCAST, handler + 'IItemHandlerModifiable'));
        method.instructions.add(new VarInsnNode(O.ALOAD, 0));
        method.instructions.add(new FieldInsnNode(O.GETFIELD, handler + 'SlotItemHandler', 'index', 'I'));
        method.instructions.add(new VarInsnNode(O.ALOAD, 1));
        method.instructions.add(new VarInsnNode(O.ALOAD, 0));
        method.instructions.add(new FieldInsnNode(O.GETFIELD, handler + 'SlotItemHandler', 'index', 'I'));
        method.instructions.add(new MethodInsnNode(O.INVOKEINTERFACE, handler + 'IItemHandler',
          'getStackInSlot', '(I)Lnet/minecraft/world/item/ItemStack;', true));
        method.instructions.add(new MethodInsnNode(O.INVOKEINTERFACE, handler + 'IItemHandlerModifiable',
          'setStackInSlot', '(ILnet/minecraft/world/item/ItemStack;)V', true));
        method.instructions.add(end);
        method.instructions.add(new InsnNode(O.RETURN));
        method.maxStack = 4;
        method.maxLocals = 2;
        clazz.methods.add(method);
        return clazz;
      }
    }
  };
  var procedures = [
    'HookedchickenBlock', 'HookedcowBlock', 'Hookedgoatblock', 'HookedhoglinBlock',
    'Hookedllamablock', 'HookedpigBlock', 'HookedsheepBlock',
    'RackcowBlock', 'RackgoatBlock', 'RackhoglinBlock', 'RacksheepBlock'
  ];
  procedures.forEach(function(prefix) {
    result['carcass_probe_' + prefix] = {
      target: {type: 'METHOD',
        class: 'net.mcreator.butchersdelight.procedures.' + prefix + 'DestroyedByPlayerProcedure',
        methodName: 'onBlockBreak', methodDesc: '(L' + breakEvent + ';)V'},
      transformer: function(method) {
        var harvest = new LabelNode();
        var patch = new InsnList();
        patch.add(new VarInsnNode(O.ALOAD, 0));
        patch.add(new TypeInsnNode(O.INSTANCEOF, probe));
        patch.add(new JumpInsnNode(O.IFEQ, harvest));
        patch.add(new InsnNode(O.RETURN));
        patch.add(harvest);
        method.instructions.insert(patch);
        return method;
      }
    };
  });
  return result;
}
