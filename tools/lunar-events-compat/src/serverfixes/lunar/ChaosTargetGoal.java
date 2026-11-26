package serverfixes.lunar;

import java.util.EnumSet;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.player.Player;

/**
 * Highest-priority target goal during the Chaos Moon: picks the nearest mob (or sometimes a player) and keeps it,
 * so the mob's own player-targeting goals cannot immediately pull it back off another mob.
 */
final class ChaosTargetGoal extends Goal {
    private final Mob mob;
    private LivingEntity victim;
    private int cooldown;
    private long until;

    ChaosTargetGoal(Mob mob) {
        this.mob = mob;
        m_7021_(EnumSet.of(Goal.Flag.TARGET));
    }

    @Override
    public boolean m_8036_() {
        if (!Rules.isChaos(LunarEvents.moon(mob.m_9236_()))) return false;
        if (--cooldown > 0) return false;
        cooldown = 10 + mob.m_217043_().m_188503_(20);
        LivingEntity current = mob.m_5448_();
        // Keep real fights (including retaliation); only players get swapped out for another mob.
        if (current != null && current.m_6084_() && !(current instanceof Player)) return false;
        victim = LunarEvents.pickVictim(mob);
        return victim != null && victim != current;
    }

    @Override
    public void m_8056_() {
        until = mob.m_9236_().m_46467_() + Rules.CHAOS_RETARGET_TICKS * 3;
        LunarEvents.setChaosTarget(mob, victim);
    }

    @Override
    public boolean m_8045_() {
        return victim != null && victim.m_6084_() && mob.m_5448_() == victim
            && Rules.isChaos(LunarEvents.moon(mob.m_9236_()))
            && mob.m_20280_(victim) < 4 * Rules.CHAOS_RANGE * Rules.CHAOS_RANGE
            && mob.m_9236_().m_46467_() < until && LunarEvents.isValidVictim(victim);
    }

    @Override
    public void m_8041_() {
        if (mob.m_5448_() == victim) mob.m_6710_(null);
        victim = null;
    }
}
