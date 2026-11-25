function initializeCoreMod() {
    var Opcodes = Java.type('org.objectweb.asm.Opcodes');
    var InsnList = Java.type('org.objectweb.asm.tree.InsnList');
    var VarInsnNode = Java.type('org.objectweb.asm.tree.VarInsnNode');
    var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
    var JumpInsnNode = Java.type('org.objectweb.asm.tree.JumpInsnNode');
    var LabelNode = Java.type('org.objectweb.asm.tree.LabelNode');
    var InsnNode = Java.type('org.objectweb.asm.tree.InsnNode');
    var helper = 'serverfixes/jadeseasons/Compat';
    function early(method, name, descriptor, vars, result) {
        var code = new InsnList();
        vars.forEach(function (v) { code.add(new VarInsnNode(Opcodes.ALOAD, v)); });
        code.add(new MethodInsnNode(Opcodes.INVOKESTATIC, helper, name, descriptor, false));
        var original = new LabelNode();
        code.add(new JumpInsnNode(Opcodes.IFEQ, original));
        if (result) code.add(new InsnNode(Opcodes.ICONST_1));
        code.add(new InsnNode(result ? Opcodes.IRETURN : Opcodes.RETURN));
        code.add(original);
        return code;
    }
    return {
        jade_season_requests: {
            target: {type: 'METHOD', class: 'snownee.jade.impl.BlockAccessorClientHandler',
                methodName: 'shouldRequestData', methodDesc: '(Lsnownee/jade/api/BlockAccessor;)Z'},
            transformer: function (method) {
                method.instructions.insert(early(method, 'request', '(Lsnownee/jade/api/BlockAccessor;)Z', [1], true));
                return method;
            }
        },
        jade_season_sync: {
            target: {type: 'METHOD', class: 'snownee.jade.impl.BlockAccessorImpl',
                methodName: 'lambda$handleRequest$0',
                methodDesc: '(Lsnownee/jade/api/BlockAccessor;Lnet/minecraft/server/level/ServerPlayer;Ljava/util/function/Consumer;)V'},
            transformer: function (method) {
                var nodes = method.instructions.toArray();
                var matches = 0;
                for (var i = 0; i < nodes.length; i++) {
                    if (nodes[i] instanceof MethodInsnNode && nodes[i].name === 'getBlockEntity') {
                        // Insert after Jade's loaded-chunk/distance checks, before its no-block-entity return.
                        method.instructions.insertBefore(nodes[i].getPrevious(),
                            early(method, 'sync', '(Lsnownee/jade/api/BlockAccessor;Ljava/util/function/Consumer;)Z', [0, 2], false));
                        matches++;
                    }
                }
                if (matches !== 1) throw new Error('Jade season server hook expected exactly one getBlockEntity');
                return method;
            }
        },
        season_bonemeal: {
            target: {type: 'METHOD', class: 'com.teamtea.eclipticseasons.common.core.crop.CropGrowthHandler',
                methodName: 'beforeCropGrowUp',
                methodDesc: '(Lnet/minecraftforge/event/entity/player/BonemealEvent;)V'},
            transformer: function (method) {
                method.instructions.insert(early(method, 'bonemeal', '(Ljava/lang/Object;)Z', [0], false));
                return method;
            }
        }
    };
}
