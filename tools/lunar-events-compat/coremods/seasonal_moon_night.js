function initializeCoreMod() {
  var ASMAPI = Java.type('net.minecraftforge.coremod.api.ASMAPI');
  var O = Java.type('org.objectweb.asm.Opcodes');
  var MethodInsnNode = Java.type('org.objectweb.asm.tree.MethodInsnNode');
  var level = 'net/minecraft/world/level/Level';
  var clock = [ASMAPI.mapMethod('m_46468_'), ASMAPI.mapMethod('m_8044_')];
  // These decide when a moon starts, ends and fades; each must still read the day time.
  var required = ['buildSchedule', 'setLunarEventTonight', 'getBlend', 'currentLunarEventOrDefault'];
  return {
    seasonal_moon_night: {
      target: {type: 'CLASS', name: 'dev.corgitaco.enhancedcelestials2core.api.lunarevent.LunarForecast'},
      transformer: function(node) {
        var patched = {};
        for (var m = 0; m < node.methods.size(); m++) {
          var method = node.methods.get(m);
          if (method.name === 'debugInfo') continue; // keep showing the real day time
          for (var i = 0; i < method.instructions.size(); i++) {
            var insn = method.instructions.get(i);
            if (!(insn instanceof MethodInsnNode) || insn.getOpcode() !== O.INVOKEVIRTUAL || insn.owner !== level
                || insn.desc !== '()J' || clock.indexOf(insn.name) < 0) continue;
            // Ecliptic Seasons moves sunset and sunrise with the season; EC2's moon night is fixed at 12500-23999.
            method.instructions.set(insn, new MethodInsnNode(O.INVOKESTATIC, 'serverfixes/lunar/LunarClock', 'dayTime',
              '(L' + level + ';)J', false));
            patched[method.name] = true;
          }
        }
        for (var r = 0; r < required.length; r++) {
          if (!patched[required[r]]) throw new Error('LunarForecast changed; review the seasonal moon night patch');
        }
        return node;
      }
    }
  };
}
