function initializeCoreMod() {
  var ASMAPI = Java.type('net.minecraftforge.coremod.api.ASMAPI');
  var O = Java.type('org.objectweb.asm.Opcodes');
  var Type = Java.type('org.objectweb.asm.Type');
  var InsnList = Java.type('org.objectweb.asm.tree.InsnList');
  var InsnNode = Java.type('org.objectweb.asm.tree.InsnNode');
  var VarInsnNode = Java.type('org.objectweb.asm.tree.VarInsnNode');
  var FieldInsnNode = Java.type('org.objectweb.asm.tree.FieldInsnNode');
  var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
  var TypeInsnNode = Java.type('org.objectweb.asm.tree.TypeInsnNode');
  var LdcInsnNode = Java.type('org.objectweb.asm.tree.LdcInsnNode');
  var JumpInsnNode = Java.type('org.objectweb.asm.tree.JumpInsnNode');
  var LabelNode = Java.type('org.objectweb.asm.tree.LabelNode');
  var MethodNode = Java.type('org.objectweb.asm.tree.MethodNode');
  var eating = 'net/dyrohc/cravings/procedures/EatingCheckProcedure';
  var variables = 'net/dyrohc/cravings/network/CravingsModVariables';
  var item = 'net/minecraft/world/item/Item';
  var stack = 'net/minecraft/world/item/ItemStack';
  var entity = 'net/minecraft/world/entity/Entity';
  var location = 'net/minecraft/resources/ResourceLocation';
  var registry = 'net/minecraftforge/registries/IForgeRegistry';
  var scaleDesc = '(DL' + entity + ';)D';

  function call(code, opcode, owner, name, desc, mapped, itf) {
    code.add(new MethodInsnNode(opcode, owner, mapped ? ASMAPI.mapMethod(name) : name, desc, !!itf));
  }

  function tagTest(code, local, tag) {
    code.add(new VarInsnNode(O.ALOAD, local));
    code.add(new FieldInsnNode(O.GETSTATIC, 'net/minecraftforge/registries/ForgeRegistries',
      'ITEMS', 'L' + registry + ';'));
    call(code, O.INVOKEINTERFACE, registry, 'tags',
      '()Lnet/minecraftforge/registries/tags/ITagManager;', false, true);
    code.add(new TypeInsnNode(O.NEW, location));
    code.add(new InsnNode(O.DUP));
    code.add(new LdcInsnNode('cravings:' + tag));
    call(code, O.INVOKESPECIAL, location, '<init>', '(Ljava/lang/String;)V');
    call(code, O.INVOKEINTERFACE, 'net/minecraftforge/registries/tags/ITagManager', 'createTagKey',
      '(L' + location + ';)Lnet/minecraft/tags/TagKey;', false, true);
    call(code, O.INVOKEVIRTUAL, stack, 'm_204117_', '(Lnet/minecraft/tags/TagKey;)Z', true);
  }

  function newMethod(name, desc) {
    var method = new MethodNode(O.ACC_PUBLIC | O.ACC_STATIC, name, desc, null, null);
    method.maxStack = 8;
    method.maxLocals = 4;
    return method;
  }

  function addHelpers(node) {
    var food = newMethod('serverfixes$isFood', '(L' + item + ';)Z');
    var edible = new LabelNode();
    food.instructions.add(new VarInsnNode(O.ALOAD, 0));
    call(food.instructions, O.INVOKEVIRTUAL, item, 'm_41472_', '()Z', true);
    food.instructions.add(new JumpInsnNode(O.IFNE, edible));
    food.instructions.add(new TypeInsnNode(O.NEW, stack));
    food.instructions.add(new InsnNode(O.DUP));
    food.instructions.add(new VarInsnNode(O.ALOAD, 0));
    call(food.instructions, O.INVOKESPECIAL, stack, '<init>', '(Lnet/minecraft/world/level/ItemLike;)V');
    food.instructions.add(new VarInsnNode(O.ASTORE, 1));
    tagTest(food.instructions, 1, 'foods');
    food.instructions.add(new InsnNode(O.IRETURN));
    food.instructions.add(edible);
    food.instructions.add(new InsnNode(O.ICONST_1));
    food.instructions.add(new InsnNode(O.IRETURN));
    node.methods.add(food);

    var scale = newMethod('serverfixes$scaleDuration', scaleDesc);
    var code = scale.instructions;
    code.add(new VarInsnNode(O.ALOAD, 2));
    code.add(new FieldInsnNode(O.GETSTATIC, variables, 'PLAYER_VARIABLES',
      'Lnet/minecraftforge/common/capabilities/Capability;'));
    call(code, O.INVOKEVIRTUAL, entity, 'getCapability',
      '(Lnet/minecraftforge/common/capabilities/Capability;)Lnet/minecraftforge/common/util/LazyOptional;');
    code.add(new InsnNode(O.ACONST_NULL));
    call(code, O.INVOKEVIRTUAL, 'net/minecraftforge/common/util/LazyOptional', 'orElse',
      '(Ljava/lang/Object;)Ljava/lang/Object;');
    code.add(new TypeInsnNode(O.CHECKCAST, variables + '$PlayerVariables'));
    code.add(new FieldInsnNode(O.GETFIELD, variables + '$PlayerVariables', 'usedItemID', 'Ljava/lang/String;'));
    code.add(new VarInsnNode(O.ASTORE, 3));
    code.add(new TypeInsnNode(O.NEW, stack));
    code.add(new InsnNode(O.DUP));
    code.add(new FieldInsnNode(O.GETSTATIC, 'net/minecraftforge/registries/ForgeRegistries',
      'ITEMS', 'L' + registry + ';'));
    code.add(new TypeInsnNode(O.NEW, location));
    code.add(new InsnNode(O.DUP));
    code.add(new VarInsnNode(O.ALOAD, 3));
    call(code, O.INVOKESPECIAL, location, '<init>', '(Ljava/lang/String;)V');
    call(code, O.INVOKEINTERFACE, registry, 'getValue', '(L' + location + ';)Ljava/lang/Object;', false, true);
    code.add(new TypeInsnNode(O.CHECKCAST, item));
    call(code, O.INVOKESPECIAL, stack, '<init>', '(Lnet/minecraft/world/level/ItemLike;)V');
    code.add(new VarInsnNode(O.ASTORE, 3));
    var simple = new LabelNode();
    var regular = new LabelNode();
    tagTest(code, 3, 'big_meal');
    code.add(new JumpInsnNode(O.IFEQ, simple));
    // Forge's coremod sandbox blocks java.lang.Double, so build 2.0 from an int.
    code.add(new VarInsnNode(O.DLOAD, 0));
    code.add(new InsnNode(O.ICONST_2));
    code.add(new InsnNode(O.I2D));
    code.add(new InsnNode(O.DMUL));
    code.add(new InsnNode(O.DRETURN));
    code.add(simple);
    tagTest(code, 3, 'simple_food');
    code.add(new JumpInsnNode(O.IFEQ, regular));
    code.add(new VarInsnNode(O.DLOAD, 0));
    code.add(new InsnNode(O.ICONST_2));
    code.add(new InsnNode(O.I2D));
    code.add(new InsnNode(O.DDIV));
    code.add(new InsnNode(O.DRETURN));
    code.add(regular);
    code.add(new VarInsnNode(O.DLOAD, 0));
    code.add(new InsnNode(O.DRETURN));
    node.methods.add(scale);
  }

  function foodGate(node) {
    var count = 0;
    // Visit before adding helpers, so their native isEdible call is not rewritten.
    node.methods.forEach(function(method) {
      Java.from(method.instructions.toArray()).forEach(function(insn) {
        if (insn instanceof MethodInsnNode && insn.owner === item &&
            insn.name === ASMAPI.mapMethod('m_41472_') && insn.desc === '()Z') {
          method.instructions.set(insn, new MethodInsnNode(O.INVOKESTATIC, eating,
            'serverfixes$isFood', '(L' + item + ';)Z', false));
          count++;
        }
      });
    });
    if (count !== 1) throw new Error('Cravings food gate changed in ' + node.name + ': ' + count);
    if (node.name === eating) addHelpers(node);
    return node;
  }

  // Scales the base effect duration and base XP; streak bonus_* values stay flat.
  function rewardDuration(method, category) {
    var count = 0;
    var xp = 0;
    Java.from(method.instructions.toArray()).forEach(function(insn) {
      if (insn instanceof FieldInsnNode && insn.getOpcode() === O.GETFIELD &&
          insn.owner === variables + '$MapVariables' &&
          /^(sweet|healthy|meaty|fishy|gross|fancy|hearty)_(.*_duration|xp_amount)$/.test(String(insn.name))) {
        if (/_xp_amount$/.test(String(insn.name))) xp++;
        var code = new InsnList();
        code.add(new VarInsnNode(O.ALOAD, 7));
        call(code, O.INVOKESTATIC, eating, 'serverfixes$scaleDuration', scaleDesc);
        method.instructions.insert(insn, code);
        count++;
      }
    });
    // Fishy also times its advancement eligibility window with the base reward duration.
    var expected = (category === 'Fishy' ? 3 : 2) + 2;
    if (count !== expected || xp !== 2) throw new Error('Cravings reward layout changed: ' + count + '/' + xp);
    return method;
  }

  function emitFinish(code, playerLocal, stackLocal, stateLocal) {
    var done = new LabelNode();
    code.add(new VarInsnNode(O.ALOAD, playerLocal));
    call(code, O.INVOKEVIRTUAL, entity, 'm_9236_', '()Lnet/minecraft/world/level/Level;', true);
    call(code, O.INVOKEVIRTUAL, 'net/minecraft/world/level/Level', 'm_5776_', '()Z', true);
    code.add(new JumpInsnNode(O.IFNE, done));
    code.add(new VarInsnNode(O.ALOAD, playerLocal));
    code.add(new TypeInsnNode(O.CHECKCAST, 'net/minecraft/world/entity/LivingEntity'));
    if (stackLocal >= 0) {
      code.add(new VarInsnNode(O.ALOAD, stackLocal));
      call(code, O.INVOKEVIRTUAL, stack, 'm_41777_', '()L' + stack + ';', true);
    } else {
      code.add(new VarInsnNode(O.ALOAD, stateLocal));
      call(code, O.INVOKEVIRTUAL, 'net/minecraft/world/level/block/state/BlockState',
        'm_60734_', '()Lnet/minecraft/world/level/block/Block;', true);
      call(code, O.INVOKEVIRTUAL, 'net/minecraft/world/level/block/Block', 'm_5456_', '()L' + item + ';', true);
      call(code, O.INVOKEVIRTUAL, item, 'm_7968_', '()L' + stack + ';', true);
    }
    code.add(new InsnNode(O.ICONST_0));
    code.add(new FieldInsnNode(O.GETSTATIC, stack, ASMAPI.mapField('f_41583_'), 'L' + stack + ';'));
    call(code, O.INVOKESTATIC, 'net/minecraftforge/event/ForgeEventFactory', 'onItemUseFinish',
      '(Lnet/minecraft/world/entity/LivingEntity;L' + stack + ';IL' + stack + ';)L' + stack + ';');
    code.add(new InsnNode(O.POP));
    code.add(done);
  }

  function placedFood(node) {
    var count = 0;
    node.methods.forEach(function(method) {
      var playerLocal = -1;
      var stateLocal = -1;
      var local = (method.access & O.ACC_STATIC) !== 0 ? 0 : 1;
      Java.from(Type.getArgumentTypes(method.desc)).forEach(function(type) {
        var name = String(type.getClassName());
        if (name === 'net.minecraft.world.entity.player.Player' || name === 'net.minecraft.world.entity.Entity') playerLocal = local;
        if (name === 'net.minecraft.world.level.block.state.BlockState') stateLocal = local;
        local += type.getSize();
      });
      if (playerLocal < 0 || stateLocal < 0) return;
      Java.from(method.instructions.toArray()).forEach(function(insn) {
        if (!(insn instanceof MethodInsnNode) || insn.owner !== 'net/minecraft/world/food/FoodData') return;
        var sliced = insn.name === ASMAPI.mapMethod('m_38712_');
        var numeric = insn.name === ASMAPI.mapMethod('m_38707_');
        var sponge = node.name === 'net/mcreator/oceanicdelight/procedures/SpongeCakeSliceEatenProcedure' &&
          insn.name === ASMAPI.mapMethod('m_38717_');
        if (!sliced && !numeric && !sponge) return;
        var stackLocal = -1;
        if (sliced) {
          stackLocal = method.maxLocals++;
          var save = new InsnList();
          save.add(new InsnNode(O.DUP));
          save.add(new VarInsnNode(O.ASTORE, stackLocal));
          method.instructions.insertBefore(insn, save);
        }
        var code = new InsnList();
        emitFinish(code, playerLocal, stackLocal, stateLocal);
        method.instructions.insert(insn, code);
        count++;
      });
    });
    if (count !== 1) throw new Error('Placed-food consumption changed in ' + node.name + ': ' + count);
    return node;
  }

  var transforms = {};
  ['EatingCheckProcedure', 'FDEatingCheckProcedure', 'DebugEatingCheckProcedure', 'FDDebugEatingCheckProcedure'].forEach(function(name) {
    transforms[name] = {
      target: {type: 'CLASS', name: 'net.dyrohc.cravings.procedures.' + name},
      transformer: foodGate
    };
  });
  ['Sweet', 'Healthy', 'Meaty', 'Fishy', 'Gross', 'Fancy', 'Hearty'].forEach(function(category) {
    transforms[category + 'Duration'] = {
      target: {type: 'METHOD', class: 'net.dyrohc.cravings.procedures.' + category + 'SatisfiedProcedure',
        methodName: 'execute', methodDesc: '(Lnet/minecraft/world/level/LevelAccessor;DDDL' + entity + ';)V'},
      transformer: function(method) { return rewardDuration(method, category); }
    };
  });
  // Farmer's Delight pies already emit Finish; feasts and displays return servings to eat normally.
  ['net.minecraft.world.level.block.CakeBlock',
    'net.mehvahdjukaar.supplementaries.common.block.blocks.PancakeBlock',
    'com.axedgaming.endersdelight.block.PieBlock',
    'com.soytutta.mynethersdelight.common.block.MagmaCakeBlock',
    'net.mcreator.oceanicdelight.procedures.SpongeCakeSliceEatenProcedure'].forEach(function(name) {
    transforms[name] = {target: {type: 'CLASS', name: name}, transformer: placedFood};
  });
  return transforms;
}
