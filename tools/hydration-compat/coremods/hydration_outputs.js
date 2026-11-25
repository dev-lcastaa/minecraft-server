function initializeCoreMod() {
  var ASMAPI = Java.type('net.minecraftforge.coremod.api.ASMAPI');
  var O = Java.type('org.objectweb.asm.Opcodes');
  var List = Java.type('org.objectweb.asm.tree.InsnList');
  var Insn = Java.type('org.objectweb.asm.tree.InsnNode');
  var Var = Java.type('org.objectweb.asm.tree.VarInsnNode');
  var Call = Java.type('org.objectweb.asm.tree.MethodInsnNode');
  var Field = Java.type('org.objectweb.asm.tree.FieldInsnNode');
  var Jump = Java.type('org.objectweb.asm.tree.JumpInsnNode');
  var Label = Java.type('org.objectweb.asm.tree.LabelNode');
  var Ldc = Java.type('org.objectweb.asm.tree.LdcInsnNode');
  function call(owner, name, desc) {
    return new Call(O.INVOKEVIRTUAL, owner, ASMAPI.mapMethod(name), desc, false);
  }
  function writePurity(patch, fluid) {
    patch.add(call(fluid ? 'net/minecraftforge/fluids/FluidStack' : 'net/minecraft/world/item/ItemStack',
      fluid ? 'getOrCreateTag' : 'm_41784_', '()Lnet/minecraft/nbt/CompoundTag;'));
    patch.add(new Ldc('Purity'));
    patch.add(new Insn(O.ICONST_3));
    patch.add(call('net/minecraft/nbt/CompoundTag', 'm_128405_', '(Ljava/lang/String;I)V'));
  }
  var transforms = {
    hydration_pot: {
      target: {type: 'METHOD', class: 'vectorwing.farmersdelight.common.crafting.CookingPotRecipe',
        methodName: 'assemble',
        methodDesc: '(Lnet/minecraftforge/items/wrapper/RecipeWrapper;Lnet/minecraft/core/RegistryAccess;)Lnet/minecraft/world/item/ItemStack;'},
      transformer: function(method) {
        var count = 0;
        var nodes = method.instructions.toArray();
        for (var i = 0; i < nodes.length; i++) {
          if (nodes[i].getOpcode() !== O.ARETURN) continue;
          var patch = new List();
          var drink = new Label();
          var done = new Label();
          patch.add(new Insn(O.DUP));
          patch.add(new Call(O.INVOKESTATIC, 'dev/ghen/thirst/api/ThirstHelper', 'isDrink',
            '(Lnet/minecraft/world/item/ItemStack;)Z', false));
          patch.add(new Jump(O.IFNE, drink));
          patch.add(new Insn(O.DUP));
          patch.add(call('net/minecraft/world/item/ItemStack', 'm_41780_', '()Lnet/minecraft/world/item/UseAnim;'));
          patch.add(new Field(O.GETSTATIC, 'net/minecraft/world/item/UseAnim', 'DRINK',
            'Lnet/minecraft/world/item/UseAnim;'));
          patch.add(new Jump(O.IF_ACMPNE, done));
          patch.add(drink);
          patch.add(new Insn(O.DUP));
          writePurity(patch, false);
          patch.add(done);
          method.instructions.insertBefore(nodes[i], patch);
          count++;
        }
        var expected = method.name === 'rollOutput' ? 2 : 1;
        if (count !== expected) throw new Error('Hydration: drink output method changed: ' + method.name + ': ' + count);
        return method;
      }
    },
    hydration_kettle: {
      target: {type: 'METHOD', class: 'umpaz.farmersrespite.common.block.entity.KettleBlockEntity',
        methodName: 'processBrewing',
        methodDesc: '(Lumpaz/farmersrespite/common/crafting/KettleRecipe;Lumpaz/farmersrespite/common/block/entity/KettleBlockEntity;)Z'},
      transformer: function(method) {
        var count = 0;
        var nodes = method.instructions.toArray();
        for (var i = 0; i < nodes.length; i++) {
          if (nodes[i].getOpcode() !== O.IRETURN) continue;
          var patch = new List();
          var done = new Label();
          // Run after Thirst's setFluid redirect, and only after completed heating.
          patch.add(new Insn(O.DUP));
          patch.add(new Jump(O.IFEQ, done));
          patch.add(new Var(O.ALOAD, 2));
          patch.add(call('umpaz/farmersrespite/common/block/entity/KettleBlockEntity', 'getFluidTank',
            '()Lnet/minecraftforge/fluids/capability/templates/FluidTank;'));
          patch.add(call('net/minecraftforge/fluids/capability/templates/FluidTank', 'getFluid',
            '()Lnet/minecraftforge/fluids/FluidStack;'));
          writePurity(patch, true);
          patch.add(done);
          method.instructions.insertBefore(nodes[i], patch);
          count++;
        }
        if (count !== 3) throw new Error('Hydration: Kettle processBrewing changed: ' + count);
        return method;
      }
    }
  };
  transforms.hydration_monster_pot = {
    target: {type: 'METHOD', class: 'net.yirmiri.dungeonsdelight.common.block.entity.container.MonsterPotRecipe',
      methodName: 'assemble',
      methodDesc: '(Lnet/minecraftforge/items/wrapper/RecipeWrapper;Lnet/minecraft/core/RegistryAccess;)Lnet/minecraft/world/item/ItemStack;'},
    transformer: transforms.hydration_pot.transformer
  };
  transforms.hydration_create = {
    target: {type: 'METHOD', class: 'com.simibubi.create.content.processing.recipe.ProcessingOutput',
      methodName: 'rollOutput', methodDesc: '()Lnet/minecraft/world/item/ItemStack;'},
    transformer: transforms.hydration_pot.transformer
  };
  return transforms;
}
