function initializeCoreMod() {
    var Opcodes = Java.type('org.objectweb.asm.Opcodes');
    var InsnList = Java.type('org.objectweb.asm.tree.InsnList');
    var VarInsnNode = Java.type('org.objectweb.asm.tree.VarInsnNode');
    var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
    var JumpInsnNode = Java.type('org.objectweb.asm.tree.JumpInsnNode');
    var LabelNode = Java.type('org.objectweb.asm.tree.LabelNode');
    var InsnNode = Java.type('org.objectweb.asm.tree.InsnNode');
    var helper = 'serverfixes/plantercompat/Compat';
    var surviveDesc = '(Lnet/minecraft/world/level/block/state/BlockBehaviour$BlockStateBase;'
        + 'Lnet/minecraft/world/level/LevelReader;Lnet/minecraft/core/BlockPos;)Z';
    var blockSurviveDesc = '(Lnet/minecraft/world/level/block/state/BlockState;'
        + 'Lnet/minecraft/world/level/LevelReader;Lnet/minecraft/core/BlockPos;)Z';

    // if (Compat.<name>(vars...)) return true; then the untouched original method.
    function returnTrueWhen(name, descriptor, vars) {
        return function (method) {
            var code = new InsnList();
            for (var i = 0; i < vars.length; i++) code.add(new VarInsnNode(Opcodes.ALOAD, vars[i]));
            code.add(new MethodInsnNode(Opcodes.INVOKESTATIC, helper, name, descriptor, false));
            var original = new LabelNode();
            code.add(new JumpInsnNode(Opcodes.IFEQ, original));
            code.add(new InsnNode(Opcodes.ICONST_1));
            code.add(new InsnNode(Opcodes.IRETURN));
            code.add(original);
            method.instructions.insert(code);
            return method;
        };
    }

    var transforms = {
        // Every placement/updateShape/tick survival check that goes through BlockState.canSurvive.
        planter_state_survival: {
            target: {type: 'METHOD', class: 'net.minecraft.world.level.block.state.BlockBehaviour$BlockStateBase',
                methodName: 'm_60710_', methodDesc: '(Lnet/minecraft/world/level/LevelReader;Lnet/minecraft/core/BlockPos;)Z'},
            transformer: returnTrueWhen('survivesOnPlanter', surviveDesc, [0, 1, 2])
        },
        // Rich soil and Supplementaries' rich planter turn crimson/warped fungi into My Nether's Delight colonies.
        rich_soil_fungus_colonies: {
            target: {type: 'METHOD', class: 'vectorwing.farmersdelight.common.block.RichSoilBlock',
                methodName: 'convertMushroomToColony',
                methodDesc: '(Lnet/minecraft/world/level/block/state/BlockState;Lnet/minecraft/core/BlockPos;'
                    + 'Lnet/minecraft/server/level/ServerLevel;)Z'},
            transformer: returnTrueWhen('convertFungus',
                '(Lnet/minecraft/world/level/block/state/BlockState;Lnet/minecraft/core/BlockPos;'
                    + 'Lnet/minecraft/world/level/Level;)Z', [1, 2, 3])
        }
    };
    // Installed plants that call their own Block.canSurvive directly instead of BlockState.canSurvive.
    var directCallers = [
        'com.momosoftworks.coldsweat.common.block.SoulStalkBlock',
        'net.potionstudios.biomeswevegone.world.level.block.plants.vegetation.CattailPlantBlock',
        'net.potionstudios.biomeswevegone.world.level.block.plants.vegetation.CattailSproutBlock'
    ];
    for (var i = 0; i < directCallers.length; i++) {
        transforms['planter_block_survival_' + i] = {
            target: {type: 'METHOD', class: directCallers[i], methodName: 'm_7898_', methodDesc: blockSurviveDesc},
            transformer: returnTrueWhen('survivesOnPlanter', surviveDesc, [1, 2, 3])
        };
    }
    return transforms;
}
