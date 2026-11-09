function initializeCoreMod() {
  var ASMAPI = Java.type('net.minecraftforge.coremod.api.ASMAPI');
  var Opcodes = Java.type('org.objectweb.asm.Opcodes');
  var InsnList = Java.type('org.objectweb.asm.tree.InsnList');
  var InsnNode = Java.type('org.objectweb.asm.tree.InsnNode');
  var VarInsnNode = Java.type('org.objectweb.asm.tree.VarInsnNode');
  var FieldInsnNode = Java.type('org.objectweb.asm.tree.FieldInsnNode');
  var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
  var TypeInsnNode = Java.type('org.objectweb.asm.tree.TypeInsnNode');
  var LdcInsnNode = Java.type('org.objectweb.asm.tree.LdcInsnNode');
  var JumpInsnNode = Java.type('org.objectweb.asm.tree.JumpInsnNode');
  var LabelNode = Java.type('org.objectweb.asm.tree.LabelNode');

  return {
    lunch_basket_foods: {
      target: {
        type: 'METHOD',
        class: 'net.mehvahdjukaar.supplementaries.common.items.LunchBoxItem',
        methodName: 'canAcceptItem',
        methodDesc: '(Lnet/minecraft/world/item/ItemStack;)Z'
      },
      transformer: function(method) {
        var original = new LabelNode();
        var patch = new InsnList();
        // m_142095_ is Item.canFitInsideContainerItems (anti-nesting), not isEdible (m_41472_), so
        // non-edible placeable foods (cakes, pies, feasts) in the tag bypass the eat/drink-only check.
        patch.add(new VarInsnNode(Opcodes.ALOAD, 0));
        patch.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'net/minecraft/world/item/ItemStack',
          ASMAPI.mapMethod('m_41720_'), '()Lnet/minecraft/world/item/Item;', false));
        patch.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'net/minecraft/world/item/Item',
          ASMAPI.mapMethod('m_142095_'), '()Z', false));
        patch.add(new JumpInsnNode(Opcodes.IFEQ, original));
        patch.add(new VarInsnNode(Opcodes.ALOAD, 0));
        patch.add(new FieldInsnNode(Opcodes.GETSTATIC, 'net/minecraftforge/registries/ForgeRegistries',
          'ITEMS', 'Lnet/minecraftforge/registries/IForgeRegistry;'));
        patch.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'net/minecraftforge/registries/IForgeRegistry',
          'tags', '()Lnet/minecraftforge/registries/tags/ITagManager;', true));
        patch.add(new TypeInsnNode(Opcodes.NEW, 'net/minecraft/resources/ResourceLocation'));
        patch.add(new InsnNode(Opcodes.DUP));
        patch.add(new LdcInsnNode('serverfixes:lunch_basket_foods'));
        patch.add(new MethodInsnNode(Opcodes.INVOKESPECIAL, 'net/minecraft/resources/ResourceLocation',
          '<init>', '(Ljava/lang/String;)V', false));
        patch.add(new MethodInsnNode(Opcodes.INVOKEINTERFACE, 'net/minecraftforge/registries/tags/ITagManager',
          'createTagKey', '(Lnet/minecraft/resources/ResourceLocation;)Lnet/minecraft/tags/TagKey;', true));
        patch.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, 'net/minecraft/world/item/ItemStack',
          ASMAPI.mapMethod('m_204117_'), '(Lnet/minecraft/tags/TagKey;)Z', false));
        patch.add(new JumpInsnNode(Opcodes.IFEQ, original));
        patch.add(new InsnNode(Opcodes.ICONST_1));
        patch.add(new InsnNode(Opcodes.IRETURN));
        patch.add(original);
        method.instructions.insert(patch);
        return method;
      }
    }
  };
}
