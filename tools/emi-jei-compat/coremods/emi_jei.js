function initializeCoreMod() {
  var O = Java.type('org.objectweb.asm.Opcodes');
  var List = Java.type('org.objectweb.asm.tree.InsnList');
  var Insn = Java.type('org.objectweb.asm.tree.InsnNode');
  var Var = Java.type('org.objectweb.asm.tree.VarInsnNode');
  var Call = Java.type('org.objectweb.asm.tree.MethodInsnNode');
  var Field = Java.type('org.objectweb.asm.tree.FieldInsnNode');
  var Jump = Java.type('org.objectweb.asm.tree.JumpInsnNode');
  var Label = Java.type('org.objectweb.asm.tree.LabelNode');
  var MethodNode = Java.type('org.objectweb.asm.tree.MethodNode');
  return {
    // Farmer's Respite's kettle screen reports a clickable ingredient with a null typed ingredient for an empty tank.
    emi_jei_null_ingredient: {
      target: {type: 'METHOD', class: 'dev.emi.emi.jemi.JemiUtil', methodName: 'getStack',
        methodDesc: '(Lmezz/jei/api/ingredients/ITypedIngredient;)Ldev/emi/emi/api/stack/EmiStack;'},
      transformer: function(method) {
        var patch = new List();
        var present = new Label();
        patch.add(new Var(O.ALOAD, 0));
        patch.add(new Jump(O.IFNONNULL, present));
        patch.add(new Field(O.GETSTATIC, 'dev/emi/emi/api/stack/EmiStack', 'EMPTY', 'Ldev/emi/emi/api/stack/EmiStack;'));
        patch.add(new Insn(O.ARETURN));
        patch.add(present);
        method.instructions.insert(patch);
        return method;
      }
    },
    // JEI 15.35+ recipe transfer calls IRecipeSlotView.getAllIngredientsList(), which EMI 1.1.24 does not implement.
    emi_jei_slot_list: {
      target: {type: 'CLASS', name: 'dev.emi.emi.jemi.impl.JemiRecipeSlot'},
      transformer: function(node) {
        for (var i = 0; i < node.methods.size(); i++) {
          if (node.methods.get(i).name === 'getAllIngredientsList') return node;
        }
        var method = new MethodNode(O.ACC_PUBLIC, 'getAllIngredientsList', '()Ljava/util/List;',
          '()Ljava/util/List<Lmezz/jei/api/ingredients/ITypedIngredient<*>;>;', null);
        method.instructions.add(new Var(O.ALOAD, 0));
        method.instructions.add(new Call(O.INVOKEVIRTUAL, 'dev/emi/emi/jemi/impl/JemiRecipeSlot', 'getAllIngredients',
          '()Ljava/util/stream/Stream;', false));
        method.instructions.add(new Call(O.INVOKEINTERFACE, 'java/util/stream/Stream', 'toList', '()Ljava/util/List;', true));
        method.instructions.add(new Insn(O.ARETURN));
        method.maxStack = 1;
        method.maxLocals = 1;
        node.methods.add(method);
        return node;
      }
    }
  };
}
