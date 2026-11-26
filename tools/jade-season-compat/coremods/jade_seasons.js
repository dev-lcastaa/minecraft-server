function initializeCoreMod() {
    var Opcodes = Java.type('org.objectweb.asm.Opcodes');
    var InsnList = Java.type('org.objectweb.asm.tree.InsnList');
    var VarInsnNode = Java.type('org.objectweb.asm.tree.VarInsnNode');
    var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
    var JumpInsnNode = Java.type('org.objectweb.asm.tree.JumpInsnNode');
    var LabelNode = Java.type('org.objectweb.asm.tree.LabelNode');
    var InsnNode = Java.type('org.objectweb.asm.tree.InsnNode');
    var helper = 'serverfixes/jadeseasons/Compat';
    return {
        season_bonemeal: {
            target: {type: 'METHOD', class: 'com.teamtea.eclipticseasons.common.core.crop.CropGrowthHandler',
                methodName: 'beforeCropGrowUp',
                methodDesc: '(Lnet/minecraftforge/event/entity/player/BonemealEvent;)V'},
            transformer: function (method) {
                // if (Compat.bonemeal(event)) return;
                var code = new InsnList();
                var original = new LabelNode();
                code.add(new VarInsnNode(Opcodes.ALOAD, 0));
                code.add(new MethodInsnNode(Opcodes.INVOKESTATIC, helper, 'bonemeal',
                    '(Lnet/minecraftforge/event/entity/player/BonemealEvent;)Z', false));
                code.add(new JumpInsnNode(Opcodes.IFEQ, original));
                code.add(new InsnNode(Opcodes.RETURN));
                code.add(original);
                method.instructions.insert(code);
                return method;
            }
        },
        growth_detector: {
            target: {type: 'METHOD', class: 'com.teamtea.eclipticseasons.common.item.GrowthDetectorItem',
                methodName: 'm_6225_',
                methodDesc: '(Lnet/minecraft/world/item/context/UseOnContext;)Lnet/minecraft/world/InteractionResult;'},
            transformer: function (method) {
                // InteractionResult r = Compat.detect(context); if (r != null) return r;
                var code = new InsnList();
                var original = new LabelNode();
                code.add(new VarInsnNode(Opcodes.ALOAD, 1));
                code.add(new MethodInsnNode(Opcodes.INVOKESTATIC, helper, 'detect',
                    '(Lnet/minecraft/world/item/context/UseOnContext;)Lnet/minecraft/world/InteractionResult;', false));
                code.add(new InsnNode(Opcodes.DUP));
                code.add(new JumpInsnNode(Opcodes.IFNULL, original));
                code.add(new InsnNode(Opcodes.ARETURN));
                code.add(original);
                code.add(new InsnNode(Opcodes.POP));
                method.instructions.insert(code);
                return method;
            }
        }
    };
}
